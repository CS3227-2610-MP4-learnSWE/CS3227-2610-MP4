"""Strict survey validation independent of HTTP and database access."""
import json
from uuid import UUID

from feedback_errors import fail
from text_validation import is_postgres_text

FEATURES = {f"{prefix}-{i:02d}": label for prefix, labels in {
    "STU": ["Study materials", "Practice questions", "AI learning assistant", "Progress dashboard", "Submit feedback", "Student inbox"],
    "TEA": ["Manage learning materials", "AI content generation", "Review and publish", "Publish three-question practice sets", "Learning overview", "Feedback and teacher inbox"],
    "ADM": ["Feature analytics", "Targeted feedback forms", "AI feedback analysis", "Feedback follow-up", "User and access management", "AI usage monitoring"],
    "SHR": ["Authentication and authorisation", "AI safeguards", "Resource management", "Minimalist, Responsive and Accessible Interface", "Data boundaries"],
    "OPT": ["Run code against test cases", "AI teaching preferences", "AI generation preferences"],
}.items() for i, label in enumerate(labels, 1)}
TYPES = {"short_answer", "paragraph", "multiple_choice", "dropdown", "checkbox", "linear_scale"}
CHOICE = {"multiple_choice", "dropdown", "checkbox"}


def keys(value, expected, kind="input"):
    if type(value) is not dict or set(value) != set(expected):
        raise fail(kind)
    return value


def integer(value, minimum=0, kind="input"):
    if type(value) is not int or value < minimum or value > 2_147_483_647:
        raise fail(kind)
    return value


def uuid(value, kind="missing"):
    try:
        if type(value) is not str:
            raise ValueError
        return str(UUID(value))
    except (ValueError, AttributeError):
        raise fail(kind) from None


def text(value, minimum, maximum, kind, trim=True):
    if type(value) is not str or not is_postgres_text(value):
        raise fail(kind)
    result = value.strip() if trim else value
    if not minimum <= len(result) <= maximum:
        raise fail(kind)
    return result


def parse(raw):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError
            result[k] = v
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise fail("input") from None


def definition(body):
    keys(body, {"title", "description", "association", "questions"})
    title = text(body["title"], 1, 160, "title")
    description = text(body["description"], 0, 2000, "text")
    raw_questions = body["questions"]
    if type(raw_questions) is not list or not 1 <= len(raw_questions) <= 30:
        raise fail("questions")
    result, ids = [], set()
    for raw in raw_questions:
        keys(raw, {"id", "type", "prompt", "required", "options", "scale"}, "questions")
        qid = uuid(raw["id"], "questions")
        if qid in ids or type(raw["type"]) is not str or raw["type"] not in TYPES or type(raw["required"]) is not bool:
            raise fail("questions")
        ids.add(qid)
        question = {"id": qid, "type": raw["type"], "required": raw["required"],
                    "prompt": text(raw["prompt"], 1, 500, "questions"), "options": [], "scale": None}
        options, scale = raw["options"], raw["scale"]
        if type(options) is not list:
            raise fail("options")
        if raw["type"] in CHOICE:
            if not 2 <= len(options) <= 20 or scale is not None:
                raise fail("options")
            option_ids, labels = set(), set()
            for option in options:
                keys(option, {"id", "label"}, "options")
                oid = uuid(option["id"], "options")
                label = text(option["label"], 1, 200, "options")
                if oid in option_ids or label.casefold() in labels:
                    raise fail("options")
                option_ids.add(oid)
                labels.add(label.casefold())
                question["options"].append({"id": oid, "label": label})
        elif options:
            raise fail("options")
        if raw["type"] == "linear_scale":
            keys(scale, {"min", "max", "min_label", "max_label"}, "scale")
            low, high = integer(scale["min"], 0, "scale"), integer(scale["max"], 0, "scale")
            if not low < high <= 10:
                raise fail("scale")
            question["scale"] = {"min": low, "max": high, "min_label": text(scale["min_label"], 0, 80, "scale"),
                                 "max_label": text(scale["max_label"], 0, 80, "scale")}
        elif scale is not None:
            raise fail("scale")
        result.append(question)
    association = body["association"]
    if association is not None:
        keys(association, {"kind", "id"}, "association")
        if association["kind"] == "feature":
            aid = text(association["id"], 1, 16, "association")
            if aid not in FEATURES:
                raise fail("association")
        elif association["kind"] == "lesson":
            aid = uuid(association["id"], "association")
        else:
            raise fail("association")
        association = {"kind": association["kind"], "id": aid}
    return {"title": title, "description": description, "questions": result, "association": association}


def answers(raw, questions, draft=False):
    kind = "draft_answers" if draft else "answers"
    if type(raw) is not list or len(raw) > len(questions):
        raise fail(kind)
    by_id = {q["id"]: q for q in questions}
    values, total = {}, 0
    for answer in raw:
        keys(answer, {"question_id", "value"}, kind)
        qid = uuid(answer["question_id"], kind)
        if qid not in by_id or qid in values:
            raise fail(kind)
        q, value = by_id[qid], answer["value"]
        if value is None or value == "" or value == []:
            value = None
        elif q["type"] in {"short_answer", "paragraph"}:
            value = text(value, 0, 500 if q["type"] == "short_answer" else 5000, kind, trim=not draft)
            total += len(value)
            if not draft and not value:
                value = None
        elif q["type"] in {"multiple_choice", "dropdown"}:
            value = uuid(value, kind)
            if value not in {o["id"] for o in q["options"]}:
                raise fail(kind)
        elif q["type"] == "checkbox":
            if type(value) is not list or not 1 <= len(value) <= 20:
                raise fail(kind)
            chosen = [uuid(v, kind) for v in value]
            if len(set(chosen)) != len(chosen) or not set(chosen) <= {o["id"] for o in q["options"]}:
                raise fail(kind)
            value = [o["id"] for o in q["options"] if o["id"] in chosen]
        else:
            value = integer(value, q["scale"]["min"], kind)
            if value > q["scale"]["max"]:
                raise fail(kind)
        if not draft and q["required"] and value is None:
            raise fail(kind)
        values[qid] = value
    if total > 20000 or (not draft and set(values) != set(by_id)):
        raise fail(kind)
    return [{"question_id": q["id"], "value": values[q["id"]]} for q in questions if q["id"] in values]
