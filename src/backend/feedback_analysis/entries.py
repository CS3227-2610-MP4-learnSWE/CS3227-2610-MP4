"""Pure free-text entry building, sampling and batching for the map calls."""
import re
from dataclasses import dataclass, field

from feedback_analysis import config
from feedback_analysis.aggregates import KINDS, field as get, ordered, snapshot_questions

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


@dataclass
class Entry:
    qid: str
    qpos: int
    prompt: str
    text: str
    labels: list = field(default_factory=list)

    @property
    def line(self):
        return f"<<<{','.join(self.labels)}|Q{self.qpos}|{self.text}>>>"

    @property
    def mapping(self):
        return f"Q{self.qpos}: {self.prompt}"


@dataclass
class Batch:
    entries: list = field(default_factory=list)

    @property
    def mappings(self):
        return sorted({e.mapping for e in self.entries}, key=lambda m: int(m[1:m.index(":")]))

    @property
    def labels(self):
        return {label for e in self.entries for label in e.labels}

    @property
    def size(self):
        return sum(len(e.line) + 1 for e in self.entries) + sum(len(m) + 1 for m in self.mappings)


def normalise(text):
    text = _CONTROL.sub(" ", text.replace("<<<", " ").replace(">>>", " "))
    return " ".join(text.split())[:config.MAX_ENTRY_CHARS].strip()


def label_number(label):
    return int(label[1:])


def build_entries(responses, labels):
    """`labels` maps response id (str) to its label. One entry per distinct normalised answer per question."""
    entries, positions, prompts = {}, {}, {}
    for response in ordered(responses):
        by_id, order = snapshot_questions(response)
        for qid in order:
            if KINDS.get(by_id[qid]["type"]) == "text":
                positions.setdefault(qid, len(positions) + 1)
                prompts[qid] = normalise(by_id[qid]["prompt"])[:config.PROMPT_QUESTION_CHARS]
        label = labels[str(get(response, "id"))]
        for answer in get(response, "answers") or []:
            qid, value = answer.get("question_id"), answer.get("value")
            if qid not in by_id or KINDS.get(by_id[qid]["type"]) != "text" or not isinstance(value, str):
                continue
            text = normalise(value)
            if not text:
                continue
            entry = entries.setdefault((qid, text.casefold()), Entry(qid, positions[qid], "", text))
            if label not in entry.labels and len(entry.labels) < config.MAX_LABELS_PER_ENTRY:
                entry.labels.append(label)
    result = list(entries.values())
    for entry in result:
        entry.qpos, entry.prompt = positions[entry.qid], prompts[entry.qid]
    return sorted(result, key=lambda e: (label_number(e.labels[0]), e.qpos))


def _pack(entries):
    batches, current = [], Batch()
    for entry in entries:
        current.entries.append(entry)
        if len(current.entries) > config.BATCH_MAX_ENTRIES or current.size > config.BATCH_DATA_CHARS:
            current.entries.pop()
            batches.append(current)
            current = Batch([entry])
    if current.entries:
        batches.append(current)
    return batches


def sample_and_batch(entries):
    """(batches, used, total): an evenly spaced deterministic sample, shrunk 10 percent at a time until it fits."""
    total = len(entries)
    used = total
    while used > 0:
        sample = [entries[i * total // used] for i in range(used)]
        batches = _pack(sample)
        if len(batches) <= config.MAX_MAP_CALLS:
            return batches, used, total
        used = min(used - 1, int(used * 0.9))
    return [], 0, total
