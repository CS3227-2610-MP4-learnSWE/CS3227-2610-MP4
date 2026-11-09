"""Pure statistics over responses, each read with its own stored form snapshot (no I/O, no LLM)."""
from statistics import mean, median

KINDS = {"short_answer": "text", "paragraph": "text", "multiple_choice": "single",
         "dropdown": "single", "checkbox": "multi", "linear_scale": "scale"}


def field(item, name):
    return item[name] if isinstance(item, dict) else getattr(item, name)


def ordered(responses):
    """Deterministic order: submitted_at then id."""
    return sorted(responses, key=lambda r: (field(r, "submitted_at"), str(field(r, "id"))))


def snapshot_questions(response):
    snapshot = field(response, "form_snapshot") or {}
    return {q["id"]: q for q in snapshot.get("questions", [])}, [q["id"] for q in snapshot.get("questions", [])]


def _is_int(value):
    return type(value) is int


class _Question:
    def __init__(self, qid):
        self.id, self.latest, self.defs = qid, None, []
        self.options, self.option_order = {}, []
        self.lo = self.hi = None

    def absorb(self, definition):
        self.latest = definition
        self.defs.append(definition)
        for option in definition.get("options") or []:
            self.options[option["id"]] = option["label"]
        scale = definition.get("scale")
        if scale:
            self.lo = scale["min"] if self.lo is None else min(self.lo, scale["min"])
            self.hi = scale["max"] if self.hi is None else max(self.hi, scale["max"])

    @property
    def kind(self):
        return KINDS.get(self.latest["type"], "text")


def _collect(responses):
    questions, first_seen = {}, []
    snapshots = [snapshot_questions(r) for r in responses]
    for by_id, order in snapshots:
        for qid in order:
            if qid not in questions:
                questions[qid] = _Question(qid)
                first_seen.append(qid)
            questions[qid].absorb(by_id[qid])
    newest = snapshots[-1][1] if snapshots else []
    qorder = newest + [q for q in first_seen if q not in newest]
    for q in questions.values():
        # Option order: newest snapshot that has the question, then older-only options in first-seen order.
        newest_ids = [o["id"] for o in q.latest.get("options") or []]
        seen = []
        for d in q.defs:
            seen += [o["id"] for o in d.get("options") or [] if o["id"] not in seen]
        q.option_order = newest_ids + [o for o in seen if o not in newest_ids]
    return questions, qorder, snapshots


def _fitted(question, value):
    """The value normalised to the newest kind, or None when it counts as skipped."""
    kind = question.kind
    if value is None:
        return None
    if kind == "text":
        return value if isinstance(value, str) and value.strip() else None
    if kind == "single":
        return value if isinstance(value, str) and value in question.options else None
    if kind == "multi":
        if (isinstance(value, list) and value and len(set(value)) == len(value)
                and all(isinstance(v, str) and v in question.options for v in value)):
            return value
        return None
    if _is_int(value) and question.lo is not None and question.lo <= value <= question.hi:
        return value
    return None


def _percent(count, answered):
    return round(count * 100 / answered, 1) if answered else 0.0


def compute_aggregates(responses):
    responses = ordered(responses)
    questions, qorder, snapshots = _collect(responses)
    tallies = {qid: {"answered": 0, "skipped": 0, "counts": {}, "values": []} for qid in qorder}
    for response, (by_id, _order) in zip(responses, snapshots):
        answers = {a["question_id"]: a.get("value") for a in field(response, "answers") or []}
        for qid in by_id:
            question, tally = questions[qid], tallies[qid]
            value = _fitted(question, answers.get(qid))
            if value is None:
                tally["skipped"] += 1
                continue
            tally["answered"] += 1
            if question.kind in ("single", "multi"):
                for option_id in ([value] if question.kind == "single" else value):
                    tally["counts"][option_id] = tally["counts"].get(option_id, 0) + 1
            elif question.kind == "scale":
                tally["values"].append(value)
    return [_item(questions[qid], tallies[qid]) for qid in qorder]


def _item(question, tally):
    answered = tally["answered"]
    item = {"question_id": question.id, "prompt": question.latest["prompt"], "kind": question.kind,
            "answered": answered, "skipped": tally["skipped"]}
    if question.kind in ("single", "multi"):
        item["options"] = [{"option_id": o, "label": question.options[o], "count": tally["counts"].get(o, 0),
                            "percent": _percent(tally["counts"].get(o, 0), answered)} for o in question.option_order]
    elif question.kind == "scale" and question.lo is not None:
        values, scale = tally["values"], question.latest.get("scale") or {}
        item.update(min=question.lo, max=question.hi, min_label=scale.get("min_label"), max_label=scale.get("max_label"),
                    mean=round(float(mean(values)), 2) if values else None,
                    median=round(float(median(values)), 2) if values else None,
                    distribution=[{"label": str(n), "count": values.count(n), "percent": _percent(values.count(n), answered)}
                                  for n in range(question.lo, question.hi + 1)])
    return item
