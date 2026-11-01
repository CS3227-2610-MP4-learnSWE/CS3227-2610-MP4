"""One text normaliser shared by question_match and leak_check. Pure: no I/O."""
import re
import unicodedata

_NON_WORD = re.compile(r"[\W_]+")


def strip_format(text: str) -> str:
    """NFKC, then drop Unicode format characters (soft hyphen, zero width) rather than splitting words."""
    return "".join(c for c in unicodedata.normalize("NFKC", text) if unicodedata.category(c) != "Cf")


def normalise(text: str) -> str:
    """Case-fold and replace markdown, quotes and punctuation by single spaces."""
    return _NON_WORD.sub(" ", strip_format(text).casefold()).strip()
