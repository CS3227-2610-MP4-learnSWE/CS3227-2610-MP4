"""Create, read, list, delete and evidence for stored analyses. Every query is filtered by the caller's admin id."""
import json
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from errors import ApiError
from feedback_models import FeedbackForm, FeedbackResponse
from feedback_store import response_json
from timestamps import utc_timestamp

from feedback_analysis import config, failures
from feedback_analysis.aggregates import compute_aggregates, ordered
from feedback_analysis.entries import build_entries, sample_and_batch
from feedback_analysis.models import FeedbackAnalysis

_LABEL = re.compile(r"R[1-9][0-9]{0,2}")
_CREATE_KEYS = {"form_id", "request_id", "response_ids", "select_all", "expected_count"}


def now():
    return datetime.now(timezone.utc)


def error(code, extra=None, **values):
    return ApiError(failures.STATUS[code], code, failures.render(code, **values), **(extra or {}))


def invalid(reason_key, **values):
    reason = failures.INVALID_REASONS[reason_key] if reason_key != "unknown" else f"unknown field {values['name']}"
    return error("invalid_request", reason=reason)


def parse_uuid(value):
    if type(value) is not str:
        return None
    try:
        return UUID(value.strip().lower())
    except ValueError:
        return None


# ---- request parsing -------------------------------------------------------------------------------------------

def parse_create(raw):
    try:
        body = json.loads(raw)
    except (ValueError, RecursionError):
        body = None
    if not isinstance(body, dict):
        raise invalid("neither")
    for name in body:
        if name not in _CREATE_KEYS:
            raise invalid("unknown", name=re.sub(r"[^A-Za-z0-9_]", "_", str(name))[:40])
    form_id, request_id = parse_uuid(body.get("form_id")), parse_uuid(body.get("request_id"))
    if form_id is None:
        raise invalid("form_id")
    if request_id is None:
        raise invalid("request_id")
    has_ids, has_all = "response_ids" in body, "select_all" in body
    if has_all and body["select_all"] is not True:
        raise invalid("select_all")
    if has_ids and has_all:
        raise invalid("both")
    if not has_ids and not has_all:
        raise invalid("neither")
    if "expected_count" in body and not has_all:
        raise invalid("expected_only")
    ids = expected = None
    if has_all:
        if body["select_all"] is not True:
            raise invalid("select_all")
        if "expected_count" in body:
            expected = body["expected_count"]
            if type(expected) is not int or not 0 <= expected <= config.MAX_RESPONSES:
                raise invalid("expected")
    else:
        if not isinstance(body["response_ids"], list):
            raise invalid("ids_type")
        ids = []
        for value in body["response_ids"]:
            parsed = parse_uuid(value)
            if parsed is None:
                raise invalid("ids_value")
            if parsed not in ids:
                ids.append(parsed)
    return form_id, request_id, ids, expected


# ---- stored object ---------------------------------------------------------------------------------------------

def seconds_since(moment):
    return max(0, int((now() - moment).total_seconds()))


def sweep_stale(db, admin_id):
    cutoff = now() - timedelta(seconds=config.JOB_BOUND_SECONDS)
    rows = db.scalars(select(FeedbackAnalysis).where(
        FeedbackAnalysis.admin_id == admin_id, FeedbackAnalysis.ai_status == "running", FeedbackAnalysis.created_at < cutoff)).all()
    for row in rows:
        record = failures.interrupted(seconds_since(row.created_at), row.ai_done, row.ai_total)
        db.execute(update(FeedbackAnalysis).where(FeedbackAnalysis.id == row.id, FeedbackAnalysis.ai_status == "running")
                   .values(ai_status="failed", ai_error=record.as_dict(), ai_completed_at=now()))
    db.commit()


def progress_step(row):
    if row.ai_status != "running":
        return None
    maps = row.ai_total - 1
    return failures.step("batch", row.ai_done + 1, maps) if row.ai_done < maps else failures.step("merge")


def analysis_object(row, title):
    ai = {"status": row.ai_status,
          "progress": {"done": row.ai_done, "total": row.ai_total, "step": progress_step(row)},
          "result": row.ai_result if row.ai_status == "complete" else None,
          "error": row.ai_error if row.ai_status == "failed" else None,
          "completed_at": utc_timestamp(row.ai_completed_at) if row.ai_completed_at else None}
    labels = sorted(row.label_dates.items(), key=lambda kv: int(kv[0][1:]))
    return {"id": str(row.id), "form_id": str(row.form_id), "form_title": title, "created_at": utc_timestamp(row.created_at),
            "response_count": row.response_count, "mode": row.mode, "expected_count": row.expected_count,
            "labels": [{"label": label, "submitted_at": date} for label, date in labels],
            "aggregates": row.aggregates, "free_text": {"total": row.free_text_total, "used": row.free_text_used}, "ai": ai}


def _title(db, form_id):
    return db.scalar(select(FeedbackForm.title).where(FeedbackForm.id == form_id)) or ""


def _owned(db, admin_id, raw_id):
    parsed = parse_uuid(raw_id)
    if parsed is None:
        return None
    return db.scalar(select(FeedbackAnalysis).where(FeedbackAnalysis.id == parsed, FeedbackAnalysis.admin_id == admin_id))


# ---- create ----------------------------------------------------------------------------------------------------

def _existing(db, admin_id, request_id):
    return db.scalar(select(FeedbackAnalysis).where(FeedbackAnalysis.admin_id == admin_id, FeedbackAnalysis.request_id == request_id))


def _resolve(db, form_id, ids, select_all):
    """The response rows of the snapshot, validated against the form."""
    if select_all:
        rows = db.scalars(select(FeedbackResponse).where(FeedbackResponse.form_id == form_id)
                          .order_by(FeedbackResponse.submitted_at, FeedbackResponse.id).limit(config.MAX_RESPONSES + 1)).all()
        if not rows:
            raise error("no_responses")
        if len(rows) > config.MAX_RESPONSES:
            raise error("too_many_responses", n=db.scalar(select(func.count()).select_from(FeedbackResponse).where(FeedbackResponse.form_id == form_id)))
        return rows
    rows = db.scalars(select(FeedbackResponse).where(FeedbackResponse.form_id == form_id, FeedbackResponse.id.in_(ids))).all()
    if len(rows) != len(ids):
        raise error("response_not_found", k=len(ids) - len(rows), n=len(ids))
    return rows


def create(db, admin_id, raw):
    """(analysis object, new analysis id or None). None means an existing analysis was returned and no job may start."""
    sweep_stale(db, admin_id)
    form_id, request_id, ids, expected = parse_create(raw)
    previous = _existing(db, admin_id, request_id)
    if previous is not None:
        obj = analysis_object(previous, _title(db, previous.form_id))
        db.commit()
        return obj, None
    stage = "reading the responses"
    try:
        if ids is not None and not ids:
            raise error("selection_required")
        if ids is not None and len(ids) > config.MAX_RESPONSES:
            raise error("too_many_responses", n=len(ids))
        title = db.scalar(select(FeedbackForm.title).where(FeedbackForm.id == form_id))
        if title is None:
            raise error("form_not_found")
        rows = ordered(_resolve(db, form_id, ids, ids is None))
        db.commit()  # release the read transaction (objects stay loaded); nothing below reads the database until the insert
        stage = "computing the statistics"
        labels = {str(r.id): f"R{i}" for i, r in enumerate(rows, 1)}
        aggregates = compute_aggregates(rows)
        if not any(item["answered"] for item in aggregates):
            raise error("nothing_to_analyse", n=len(rows))
        entries = build_entries(rows, labels)
        batches, used, total = sample_and_batch(entries)
        row = FeedbackAnalysis(
            id=uuid4(), admin_id=admin_id, request_id=request_id, form_id=form_id,
            mode="explicit" if ids is not None else "select_all", expected_count=expected, response_count=len(rows),
            label_map={label: rid for rid, label in labels.items()},
            label_dates={labels[str(r.id)]: utc_timestamp(r.submitted_at) for r in rows},
            aggregates=aggregates, free_text_total=total, free_text_used=used, ai_status="running",
            ai_done=0, ai_total=len(batches) + 1, created_at=now())
        obj = analysis_object(row, title)
    except (ApiError, SQLAlchemyError):
        raise
    except Exception as exc:
        record = failures.internal(None, stage, exc)
        raise error("internal_error", {"reference": record.details["reference"]}, step=stage, ref=record.details["reference"]) from None
    return _insert(db, admin_id, request_id, row, obj)


def _insert(db, admin_id, request_id, row, obj):
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        previous = _existing(db, admin_id, request_id)
        if previous is not None:
            result = analysis_object(previous, _title(db, previous.form_id))
            db.commit()
            return result, None
        running = db.scalar(select(FeedbackAnalysis.created_at).where(FeedbackAnalysis.admin_id == admin_id, FeedbackAnalysis.ai_status == "running"))
        db.rollback()
        if running is None:
            raise
        raise error("analysis_in_progress", s=seconds_since(running)) from None
    return obj, row.id


# ---- reads -----------------------------------------------------------------------------------------------------

def get(db, admin_id, raw_id):
    sweep_stale(db, admin_id)
    row = _owned(db, admin_id, raw_id)
    if row is None:
        db.rollback()
        raise error("analysis_not_found")
    obj = analysis_object(row, _title(db, row.form_id))
    db.rollback()
    return obj


def history(db, admin_id, limit, offset):
    sweep_stale(db, admin_id)
    rows = db.execute(
        select(FeedbackAnalysis, FeedbackForm.title).join(FeedbackForm, FeedbackForm.id == FeedbackAnalysis.form_id)
        .where(FeedbackAnalysis.admin_id == admin_id)
        .order_by(FeedbackAnalysis.created_at.desc(), FeedbackAnalysis.id.desc()).offset(offset).limit(limit + 1)).all()
    db.rollback()
    items = [{"id": str(r.id), "form_id": str(r.form_id), "form_title": title, "created_at": utc_timestamp(r.created_at),
              "response_count": r.response_count, "ai_status": r.ai_status} for r, title in rows[:limit]]
    return {"items": items, "next_offset": offset + limit if len(rows) > limit else None}


def evidence(db, admin_id, raw_id, raw_label):
    label = raw_label.strip().upper()
    row = _owned(db, admin_id, raw_id) if _LABEL.fullmatch(label) and int(label[1:]) <= config.MAX_RESPONSES else None
    response_id = parse_uuid(row.label_map.get(label)) if row is not None else None
    response = None
    if response_id is not None:
        response = db.scalar(select(FeedbackResponse).where(FeedbackResponse.id == response_id, FeedbackResponse.form_id == row.form_id))
    if response is None:
        db.rollback()
        raise error("evidence_not_found")
    result = {"label": label, "response": response_json(response, True)}
    db.rollback()
    return result


def response_count(db, raw_form_id):
    form_id = parse_uuid(raw_form_id)
    if form_id is None or db.scalar(select(FeedbackForm.id).where(FeedbackForm.id == form_id)) is None:
        db.rollback()
        raise error("form_not_found")
    count = db.scalar(select(func.count()).select_from(FeedbackResponse).where(FeedbackResponse.form_id == form_id))
    db.rollback()
    return {"form_id": str(form_id), "count": count}


# ---- delete ----------------------------------------------------------------------------------------------------

def delete_analysis(db, admin_id, raw_id):
    """Returns normally when deleted; raises analysis_running or analysis_not_found otherwise."""
    sweep_stale(db, admin_id)
    parsed = parse_uuid(raw_id)
    if parsed is None:
        raise error("analysis_not_found")
    deleted = db.execute(delete(FeedbackAnalysis).where(
        FeedbackAnalysis.id == parsed, FeedbackAnalysis.admin_id == admin_id, FeedbackAnalysis.ai_status != "running")
        .returning(FeedbackAnalysis.id)).first()
    db.commit()
    if deleted is not None:
        return
    created = db.scalar(select(FeedbackAnalysis.created_at).where(FeedbackAnalysis.id == parsed, FeedbackAnalysis.admin_id == admin_id))
    db.rollback()
    if created is None:
        raise error("analysis_not_found")
    ran = seconds_since(created)
    remaining = max(0, config.JOB_BOUND_SECONDS - ran)
    raise error("analysis_running", {"ran_seconds": ran, "remaining_seconds": remaining}, s=ran, r=remaining)
