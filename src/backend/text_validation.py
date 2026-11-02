"""Text representability shared by persistent teacher records."""


def is_postgres_text(value: str) -> bool:
    # PostgreSQL UTF-8 text cannot store NUL or unpaired surrogate code points.
    return not any(c == "\x00" or 0xD800 <= ord(c) <= 0xDFFF for c in value)
