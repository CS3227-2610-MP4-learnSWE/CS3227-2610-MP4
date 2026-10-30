"""Deterministic check for replies that state or rule on an answer. Pure: no I/O, no model call.

Looks only for the correct choice (by letter or text) and for verdicts (right/wrong) on any
choice of the questions it is given. Paraphrased leaks ("go with b", "the second option") are
a known residual risk (see spec).
"""
import re
from collections.abc import Sequence

from practice_data import Question
from text_normalise import normalise, strip_format

MIN_TEXT_CHARS = 4  # shorter or purely numeric choice texts are matched near output words only
ARTICLE_IDS = {"a"}  # ids that are also an ordinary English word
VERDICT_WORDS = r"(?:correct|right|wrong|incorrect)"
OUTPUT_WORDS = (
    r"(?:prints?|printed|outputs?|results?|returns?|equals?|answer|shows?|gives?|displays?"
    r"|produces?|yields?|evaluates to)"
)
OUTPUT_AFTER = r"(?:is |are )?(?:printed|output|returned|the (?:output|result|answer))"
_SEPARATOR = r"\s*(?:,|and|or|&)\s*"
_END_OR_PUNCT = re.compile(r"\s*(?:$|[.,;:!?)])")
_VERB = r"(?:is|are|isn't|aren't|looks?|seems?|would be|should be|must be|will be)"
_VERDICT = (
    rf"\s+{_VERB}\s+(?:to be\s+)?(?:not\s+|definitely\s+|also\s+|both\s+|the\s+)*{VERDICT_WORDS}\b"
)
_TICKS = "✓✔"


def _clean(text: str) -> str:
    """Letter-matching text: no format characters, markdown or quote marks (case is kept)."""
    text = strip_format(text).replace("‘", "'").replace("’", "'")
    text = re.sub(r"[*_`\"“”]", "", text)
    text = re.sub(r"(?<!\w)'|'(?!\w)", "", text)  # quote marks, but keep "it's"
    return re.sub(r"\s+", " ", text).strip()


def _alt(ids: set[str]) -> str:
    return "|".join(re.escape(i) for i in sorted(ids, key=len, reverse=True))


def _id_pattern(ids: set[str]) -> str:
    return rf"(?<!\w)(?:{_alt(ids)})(?!\w)"


def _chain(ident: str) -> str:
    one = rf"(?:\()?{ident}(?:\))?"
    return rf"{one}(?:{_SEPARATOR}{one})*"


def _letters(group: str, end: int, text: str, ident: str) -> list[str]:
    """Letters in a matched chain, lower-cased. The article "a" alone counts only when it is
    a capital A, is bracketed, or ends the clause."""
    found = re.findall(ident, group, re.IGNORECASE)
    if len(found) == 1 and found[0] in ARTICLE_IDS and not group.startswith("("):
        if not _END_OR_PUNCT.match(text, end):
            return []
    return [f.lower() for f in found]


def _letter_reference(text: str, all_ids: set[str], correct_ids: set[str]) -> bool:
    ident = _id_pattern(all_ids)
    chain = _chain(ident)
    named = re.compile(
        rf"\b(?:option|choice|answer)s?\b\s*(?:is\s+|:\s*|would be\s+|should be\s+)?({chain})",
        re.IGNORECASE,
    )
    for m in named.finditer(text):
        if any(i in correct_ids for i in _letters(m.group(1), m.end(), text, ident)):
            return True
    # "Correct: b" names a letter as the answer whichever letter it is.
    marked = re.compile(rf"\bcorrect(?: answer)?\s*[:—–-]\s*({chain})", re.IGNORECASE)
    if any(_letters(m.group(1), m.end(), text, ident) for m in marked.finditer(text)):
        return True
    correct = _alt(correct_ids)
    # "(b)" not glued to a word (so not print(b)), a list marker "b)", a tick, a key dump "q1: a".
    return bool(
        re.search(
            rf"(?<!\w)\((?:{correct})\)|(?<![\w(])(?:{correct})\)"
            rf"|(?<!\w)(?:{correct})\s*[{_TICKS}]|[{_TICKS}]\s*(?:{correct})(?!\w)"
            rf"|\bq\d+\s*[:\-]\s*(?:{correct})(?!\w)",
            text,
            re.IGNORECASE,
        )
    )


def _letter_verdict(text: str, all_ids: set[str]) -> bool:
    ident = _id_pattern(all_ids)
    chain = _chain(ident)
    named = rf"\b(?:option|choice|answer)s?\s*{chain}{_VERDICT}"
    bare = rf"(?<![\w']){chain}{_VERDICT}"
    return bool(re.search(named, text, re.IGNORECASE) or re.search(bare, text, re.IGNORECASE))


def _text_leak(words: str, clean: str, q: Question) -> bool:
    correct = dict(q.choices).get(q.correct, "")
    norm = normalise(correct)
    if not norm:
        return False
    if len(norm) >= MIN_TEXT_CHARS and not norm.isdigit():
        return f" {norm} " in f" {words} "
    value = rf"(?<!\w){re.escape(norm)}(?!\w)"
    gap = r"[^.\n\[\],()]{0,12}?"
    patterns = (
        rf"\b{OUTPUT_WORDS}\b{gap}{value}",  # "it prints 3"
        rf"{value}\s*{OUTPUT_AFTER}",  # "3 is printed"
        rf"\)\s*(?:is|returns?|gives?|equals?)\s*{value}",  # "len(values) is 3"
    )
    return any(re.search(p, clean, re.IGNORECASE) for p in patterns)


def _text_verdict(words: str, q: Question) -> bool:
    for _, choice_text in q.choices:
        norm = normalise(choice_text)
        if len(norm) < MIN_TEXT_CHARS or norm.isdigit():
            continue
        for m in re.finditer(re.escape(norm), words):
            after = words[m.end() : m.end() + 30]
            before = words[max(0, m.start() - 30) : m.start()]
            if re.search(rf"\b{VERDICT_WORDS}\b", after) or re.search(
                rf"\b{VERDICT_WORDS}\b", before
            ):
                return True
    return False


def find_leak(reply: str, questions: Sequence[Question]) -> str | None:
    """Return "letter", "text" or "verdict" if the reply states or marks the answer, else None."""
    if not questions:
        return None
    clean = _clean(reply)
    words = normalise(reply)
    all_ids = {cid.lower() for q in questions for cid, _ in q.choices}
    correct_ids = {q.correct.lower() for q in questions}
    if _letter_reference(clean, all_ids, correct_ids):
        return "letter"
    if any(_text_leak(words, clean, q) for q in questions):
        return "text"
    if _letter_verdict(clean, all_ids) or any(_text_verdict(words, q) for q in questions):
        return "verdict"
    return None
