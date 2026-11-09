"""The background AI step: map calls in order, then one reduce call. Own DB sessions, conditional writes only."""
import logging
import threading
from uuid import UUID

from sqlalchemy import func, select, update

from auth.db import open_session
from feedback_models import FeedbackResponse
from llm_client import LlmError, Limits, get_llm_client, usage_feature

from feedback_analysis import config, failures
from feedback_analysis.entries import build_entries, sample_and_batch
from feedback_analysis.models import FeedbackAnalysis
from feedback_analysis.prompts import fit_partials, map_messages, reduce_messages
from feedback_analysis.service import now
from feedback_analysis.validate import InvalidReply, parse_map_reply, parse_reduce_reply

log = logging.getLogger("feedback_analysis")


def start(analysis_id, llm=None):
    """Run the job in a daemon thread so the create request returns at once."""
    threading.Thread(target=run_job, args=(analysis_id, llm), daemon=True, name=f"analysis-{analysis_id}").start()


def _write(analysis_id, **values):
    """Update a still-running analysis; False means it was swept, failed or deleted and the job must stop quietly."""
    with open_session() as db:
        result = db.execute(update(FeedbackAnalysis).where(FeedbackAnalysis.id == analysis_id, FeedbackAnalysis.ai_status == "running")
                            .values(**values))
        db.commit()
        return result.rowcount > 0


def _fail(analysis_id, record):
    _write(analysis_id, ai_status="failed", ai_error=record.as_dict(), ai_completed_at=now())


def _load(analysis_id):
    with open_session() as db:
        row = db.get(FeedbackAnalysis, analysis_id)
        if row is None or row.ai_status != "running":
            return None
        ids = [UUID(v) for v in row.label_map.values()]
        responses = db.scalars(select(FeedbackResponse).where(FeedbackResponse.id.in_(ids))).all()
        labels = {v: k for k, v in row.label_map.items()}
        return row.admin_id, list(row.aggregates), set(row.label_map), responses, labels, row.ai_total


def run_job(analysis_id, llm=None):
    progress = {"step": failures.step("start"), "phrase": "starting the AI step"}
    try:
        _run(analysis_id, llm, progress)
    except Exception as exc:  # noqa: BLE001 - the job must always end in a stored state
        try:
            _fail(analysis_id, failures.internal(progress["step"], progress["phrase"], exc))
        except Exception:  # noqa: BLE001
            log.error("analysis %s could not store its failure, class=%s", analysis_id, type(exc).__name__)


def _call(llm, messages, max_tokens, admin_id, step, limits, timeout_seconds=None):
    """(reply text, None) or (None, failure record)."""
    try:
        with usage_feature(config.USAGE_FEATURE):
            # Only a call with its own limit passes the keyword; other calls use the client's default.
            extra = {} if timeout_seconds is None else {"timeout_seconds": timeout_seconds}
            reply = llm.complete(messages, max_tokens=max_tokens, caller_id=f"admin:{admin_id}", **extra)
    except LlmError as exc:
        return None, failures.from_llm_error(exc, step, limits, sum(len(m.content) for m in messages), timeout_seconds)
    if reply.finish_reason == "length":
        return None, failures.cut_off(step, max_tokens)
    return reply.text, None


def _missing(ids):
    """How many of the selected responses no longer exist."""
    with open_session() as db:
        return len(ids) - db.scalar(select(func.count()).select_from(FeedbackResponse).where(FeedbackResponse.id.in_(ids)))


def _run(analysis_id, llm, progress):
    loaded = _load(analysis_id)
    if loaded is None:
        return
    admin_id, aggregates, selection, responses, labels, ai_total = loaded
    ids = [UUID(r) for r in labels]
    gone = len(ids) - len(responses)
    if gone:  # deleted after the analysis started, before the first call
        _fail(analysis_id, failures.responses_deleted(failures.step("start"), "starting the AI step", gone, len(ids)))
        return
    batches, _used, _total = sample_and_batch(build_entries(responses, labels))
    if len(batches) + 1 != ai_total:
        # All selected responses exist yet the step count differs: a real defect, stopped with a reference.
        raise RuntimeError("stored snapshot no longer matches the stored step count")
    llm = llm or get_llm_client()
    limits = Limits()
    partials = []
    for index, batch in enumerate(batches, 1):
        step = failures.step("batch", index, len(batches))
        gone = _missing(ids)
        if gone:  # a selected response was deleted while earlier steps ran: no partial result
            _fail(analysis_id, failures.responses_deleted(step, f"processing batch {index} of {len(batches)}", gone, len(ids)))
            return
        # An unexpected exception is recorded against the step that was running (kind map).
        progress.update(step=failures.step("map", index, len(batches)), phrase=f"processing batch {index} of {len(batches)}")
        text, record = _call(llm, map_messages(batch), config.MAP_MAX_TOKENS, admin_id, step, limits)
        if record is None:
            try:
                partials += parse_map_reply(text, batch.labels, selection)
            except InvalidReply as exc:
                record = failures.from_invalid_reply(exc, step)
        if record is not None:
            _fail(analysis_id, record)
            return
        if not _write(analysis_id, ai_done=FeedbackAnalysis.ai_done + 1):
            return
    step = failures.step("merge")
    progress.update(step=failures.step("reduce"), phrase="merging themes")
    partials = fit_partials(partials)
    text, record = _call(llm, reduce_messages(aggregates, partials), config.REDUCE_MAX_TOKENS, admin_id, step, limits,
                          config.REDUCE_TIMEOUT_SECONDS)
    if record is None:
        try:
            result = parse_reduce_reply(text, {label for t in partials for label in t["evidence"]}, selection)
        except InvalidReply as exc:
            record = failures.from_invalid_reply(exc, step)
    if record is not None:
        _fail(analysis_id, record)
        return
    _write(analysis_id, ai_status="complete", ai_result=result, ai_done=ai_total, ai_completed_at=now())
