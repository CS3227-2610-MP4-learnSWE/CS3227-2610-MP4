"""Bounded, strict message transport and text validation."""
import json
import unicodedata
from uuid import UUID

from messaging_errors import fail
from text_validation import is_postgres_text


def identifier(value):
    try:
        if type(value) is not str:
            raise ValueError()
        return UUID(value)
    except (ValueError, AttributeError):
        raise fail("INVALID_REQUEST") from None


def keys(value, required, optional=()):
    if type(value) is not dict or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise fail("INVALID_REQUEST")


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise fail("INVALID_REQUEST")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError, RecursionError):
        raise fail("INVALID_REQUEST") from None
    if type(value) is not dict:
        raise fail("INVALID_REQUEST")
    return value


def text(value, subject=False):
    code = "INVALID_SUBJECT" if subject else "INVALID_BODY"
    if type(value) is not str:
        raise fail(code)
    value = value.replace("\r\n", "\n").strip()
    if not 1 <= len(value) <= (120 if subject else 5000) or not is_postgres_text(value):
        raise fail(code)
    if any(unicodedata.category(c) == "Cc" and (subject or c not in "\t\n") for c in value):
        raise fail(code)
    return value


def account_ids(value):
    if type(value) is not list:
        raise fail("INVALID_RECIPIENTS")
    if any(type(i) is not str or not 1 <= len(i) <= 64 or i != i.strip() or not is_postgres_text(i) for i in value):
        raise fail("INVALID_REQUEST")
    ids = sorted(set(value))
    if not 1 <= len(ids) <= 500:
        raise fail("INVALID_RECIPIENTS")
    return ids


def query(request, allowed=()):
    q = request.query_params
    if any(k not in allowed or len(q.getlist(k)) != 1 for k in q):
        raise fail("INVALID_REQUEST")
    return q


def integer(value, minimum=0):
    if not value.isascii() or not value.isdecimal() or len(value) > 9 or int(value) < minimum:
        raise fail("INVALID_REQUEST")
    return int(value)
