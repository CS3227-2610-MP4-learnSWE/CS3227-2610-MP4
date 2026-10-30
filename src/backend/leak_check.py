"""Deterministic check for replies that state or rule on an answer. Pure: no I/O, no model call.

Looks only for the correct choice (by letter or text) and for verdicts (right/wrong) on any
choice of the questions it is given. Paraphrased leaks are a known residual risk (see spec).
"""
import re
import unicodedata
from collections.abc import Sequence

from practice_data import Question

MIN_TEXT_CHARS = 4  # shorter or purely numeric choice texts are matched near output words only
ARTICLE_IDS = {"a"}  # ids that are also an ordinary English word
VERDICT_WORDS = r"(?:correct|right|wrong|incorrect)"
OUTPUT_WORDS = r"(?:prints?|printed|outputs?|results?|returns?|equals?|answer)"
_NON_WORD = re.compile(r"[\W_]+")
_SEPARATOR = r"\s*(?:,|and|or|&)\s*"
_END_OR_PUNCT = re.compile(r"\s*(?:$|[.,;:!?)])")


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


def _words(text: str) -> str:
    return _NON_WORD.sub(" ", _fold(text)).strip()


def _alt(ids: set[str]) -> str:
    return "|".join(re.escape(i) for i in sorted(ids, key=len, reverse=True))


def _id_pattern(ids: set[str]) -> str:
    return rf"(?<!\w)(?:{_alt(ids)})(?!\w)"


def _letter_reference(text: str, all_ids: set[str], correct_ids: set[str]) -> bool:
    ident = _id_pattern(all_ids)
    chain = rf"(?:\()?{ident}(?:\))?(?:{_SEPARATOR}(?:\()?{ident}(?:\))?)*"
    pattern = re.compile(
        rf"\b(?:option|choice|answer)s?\b\s*(?:is\s+|:\s*|would be\s+|should be\s+)?({chain})"
    )
    for m in pattern.finditer(text):
        found = re.findall(ident, m.group(1))
        # The article "a" alone only counts when bracketed or ending the clause.
        if len(found) == 1 and found[0] in ARTICLE_IDS and not m.group(1).startswith("("):
            if not _END_OR_PUNCT.match(text, m.end()):
                continue
        if any(i in correct_ids for i in found):
            return True
    correct = _alt(correct_ids)
    # "(b)" not glued to a word (so not print(b)), and a list marker such as "b)".
    return bool(re.search(rf"(?<!\w)\((?:{correct})\)|(?<![\w(])(?:{correct})\)", text))


def _letter_verdict(text: str, all_ids: set[str]) -> bool:
    ident = _id_pattern(all_ids)
    chain = rf"(?:\()?{ident}(?:\))?(?:{_SEPARATOR}(?:\()?{ident}(?:\))?)*"
    verdict = rf"\s+(?:is|are|isn't|aren't)\s+(?:not\s+|definitely\s+|also\s+|both\s+)*(?:the\s+)?{VERDICT_WORDS}\b"
    named = rf"\b(?:option|choice|answer)s?\s*{chain}{verdict}"
    bare = rf"(?<![\w'])(?:\()?{ident}(?:\))?(?:{_SEPARATOR}(?:\()?{ident}(?:\))?)*{verdict}"
    return bool(re.search(named, text) or re.search(bare, text))


def _text_leak(words: str, folded: str, q: Question) -> bool:
    correct = dict(q.choices).get(q.correct, "")
    norm = _words(correct)
    if not norm:
        return False
    if len(norm) >= MIN_TEXT_CHARS and not norm.isdigit():
        return f" {norm} " in f" {words} "
    near = rf"\b{OUTPUT_WORDS}\b[^.\n\[\],()]{{0,12}}?(?<!\w){re.escape(norm)}(?!\w)"
    return bool(re.search(near, folded))


def _text_verdict(words: str, q: Question) -> bool:
    for _, choice_text in q.choices:
        norm = _words(choice_text)
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
    folded = _fold(reply)
    words = _words(reply)
    all_ids = {_fold(cid) for q in questions for cid, _ in q.choices}
    correct_ids = {_fold(q.correct) for q in questions}
    if _letter_reference(folded, all_ids, correct_ids):
        return "letter"
    if any(_text_leak(words, folded, q) for q in questions):
        return "text"
    if _letter_verdict(folded, all_ids) or any(_text_verdict(words, q) for q in questions):
        return "verdict"
    return None
