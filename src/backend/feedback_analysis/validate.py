"""Strict validation of map and reduce replies. Model output is untrusted; any violation names its rule."""
import json
import re

_CONTROL = re.compile(r"[\x00-\x09\x0b-\x1f\x7f]")


class InvalidReply(Exception):
    def __init__(self, code, rule=None, field=None, label=None, max=None, count=None):
        super().__init__(code)
        self.code, self.rule, self.field, self.label, self.max, self.count = code, rule, field, label, max, count

    @property
    def details(self):
        pairs = (("rule", self.rule), ("field", self.field), ("label", self.label), ("max", self.max), ("count", self.count))
        return {k: v for k, v in pairs if v is not None}


def _bad(rule, **values):
    return InvalidReply("ai_reply_invalid", rule, **values)


def _safe_name(name):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(name))[:30]


def _object(text):
    stripped = text.strip()
    try:
        data = json.loads(stripped) if stripped.startswith("{") and stripped.endswith("}") else None
    except (ValueError, RecursionError):
        data = None
    if not isinstance(data, dict):
        raise InvalidReply("ai_reply_not_json")
    return data


def _keys(data, required, name="reply"):
    for key in data:
        if key not in required:
            raise _bad("unexpected_field", field=_safe_name(key))
    for key in required:
        if key not in data:
            raise _bad("missing_field", field=key)


def _text(value, field, limit):
    if not isinstance(value, str):
        raise _bad("wrong_type", field=field)
    value = _CONTROL.sub("", value).strip()
    if not value:
        raise _bad("empty", field=field)
    if len(value) > limit:
        raise _bad("too_long", field=field, max=limit)
    return value


def _list(value, field, low, high):
    if not isinstance(value, list):
        raise _bad("wrong_type", field=field)
    if len(value) > high:
        raise _bad("too_many_items", field=field, max=high, count=len(value))
    return value


def _labels(value, limit, selection, allowed, need_one):
    items = _list(value, "evidence", 0, limit)
    out = []
    for label in items:
        if not isinstance(label, str):
            raise _bad("wrong_type", field="evidence")
        label = label.strip().upper()
        if label not in selection:
            raise _bad("label_outside_selection", label=_safe_name(label))
        if label not in allowed:
            raise _bad("label_outside_input", label=label)
        if label not in out:
            out.append(label)
    if need_one and not out:
        raise _bad("theme_no_evidence")
    return out


def _themes(value, caps, limit, selection, allowed):
    title_max, desc_max, evidence_max = caps
    themes = []
    for item in _list(value, "themes", 0, limit):
        if not isinstance(item, dict):
            raise _bad("wrong_type", field="themes")
        _keys(item, ("title", "description", "evidence"))
        themes.append({"title": _text(item["title"], "title", title_max),
                       "description": _text(item["description"], "description", desc_max),
                       "evidence": _labels(item["evidence"], evidence_max, selection, allowed, True)})
    return themes


def parse_map_reply(text, allowed_labels, selection_labels=None):
    """Validated list of partial themes. `allowed_labels` are the labels of this batch."""
    allowed = set(allowed_labels)
    selection = set(selection_labels) if selection_labels is not None else allowed
    data = _object(text)
    _keys(data, ("themes",))
    return _themes(data["themes"], (50, 100, 6), 3, selection, allowed)


def parse_reduce_reply(text, allowed_labels, selection_labels=None):
    """Validated final result. `allowed_labels` are the labels present in the partial themes."""
    allowed = set(allowed_labels)
    selection = set(selection_labels) if selection_labels is not None else allowed
    data = _object(text)
    _keys(data, ("summary", "themes", "suggestions"))
    result = {"summary": _text(data["summary"], "summary", 400),
              "themes": _themes(data["themes"], (80, 250, 20), 5, selection, allowed), "suggestions": []}
    for item in _list(data["suggestions"], "suggestions", 0, 6):
        if not isinstance(item, dict):
            raise _bad("wrong_type", field="suggestions")
        _keys(item, ("text", "basis", "evidence"))
        suggestion_text = _text(item["text"], "text", 200)
        basis = item["basis"]
        if not isinstance(basis, str):
            raise _bad("wrong_type", field="basis")
        if basis not in ("feedback", "ai"):
            raise _bad("bad_basis")
        evidence = _labels(item["evidence"], 20, selection, allowed, False)
        if basis == "feedback" and not evidence:
            raise _bad("feedback_without_evidence")
        if basis == "ai" and evidence:
            raise _bad("ai_with_evidence")
        result["suggestions"].append({"text": suggestion_text, "basis": basis, "evidence": evidence})
    return result
