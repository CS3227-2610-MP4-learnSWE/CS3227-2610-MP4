"""Related-lesson choice by plain word overlap. Pure: no I/O, no model call."""
from collections.abc import Sequence
from typing import TYPE_CHECKING

import companion_config as config
from text_normalise import normalise

if TYPE_CHECKING:
    from lesson_provider import LessonText


def _message_words(message: str) -> set[str]:
    return {
        w
        for w in normalise(message).split()
        if len(w) >= config.RELATED_MIN_WORD_CHARS and w not in config.RELATED_STOPWORDS
    }


def _score(words: set[str], title: str, content: str) -> int:
    if not words:
        return 0
    in_title = words & set(normalise(title).split())
    found = words & (set(normalise(f"{title} {content}").split()))
    if len(found) >= config.RELATED_MIN_WORDS or in_title:
        return len(found)
    return 0


def score_lesson(message: str, title: str, content: str) -> int:
    """Number of distinct qualifying message words found in title+content; 0 when the lesson does not qualify."""
    return _score(_message_words(message), title, content)


def select_related(message: str, lessons: Sequence["LessonText"], limit: int) -> list["LessonText"]:
    """Qualifying lessons, best score first; ties keep the input order (input is newest first)."""
    words = _message_words(message)
    scored = [(_score(words, l.title, l.content), n, l) for n, l in enumerate(lessons)]
    ranked = sorted((t for t in scored if t[0] > 0), key=lambda t: (-t[0], t[1]))
    return [l for _, _, l in ranked[:limit]]
