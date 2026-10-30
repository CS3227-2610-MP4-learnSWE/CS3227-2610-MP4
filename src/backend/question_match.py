"""Detects a pasted practice question in a student's message. Pure: no I/O, no model call."""
import re
import unicodedata
from collections.abc import Sequence

from practice_data import PracticeSet, Question

WORD_SHARE = 0.8  # our choice, unmeasured (spec decision 2)
MIN_CHOICE_CHARS = 4  # shorter choice texts ("2", "3") would match ordinary prose
_NON_WORD = re.compile(r"[\W_]+")


def normalise(text: str) -> str:
    """NFKC, case-fold, drop markdown/quote/punctuation, collapse whitespace."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return _NON_WORD.sub(" ", folded).strip()


def _contains(haystack: str, needle: str) -> bool:
    return bool(needle) and f" {needle} " in f" {haystack} "


def _rank(message: str, words: set[str], q: Question) -> tuple[int, float] | None:
    """Higher tuple is a stronger match; None means no match."""
    text = normalise(q.text)
    full = normalise(f"{q.text} {q.code}") if q.code else text
    if _contains(message, full):
        return (3, 1.0)
    choices = [normalise(t) for _, t in q.choices]
    if sum(1 for c in choices if len(c) >= MIN_CHOICE_CHARS and _contains(message, c)) >= 2:
        return (2, 1.0)
    q_words = set(text.split())
    if q_words:
        share = len(q_words & words) / len(q_words)
        if share >= WORD_SHARE:
            return (1, share)
    return None


def find_match(message: str, sets: Sequence[PracticeSet]) -> Question | None:
    norm = normalise(message)
    words = set(norm.split())
    best: tuple[tuple[int, float], Question] | None = None
    for practice_set in sets:
        for q in practice_set.questions:
            rank = _rank(norm, words, q)
            if rank is not None and (best is None or rank > best[0]):
                best = (rank, q)
    return best[1] if best else None
