"""Password hashing (stdlib scrypt), password rules and email normalisation."""
import base64
import hashlib
import hmac
import secrets
import unicodedata
from functools import lru_cache

from text_validation import is_postgres_text

_N, _R, _P, _DKLEN = 16384, 8, 1, 32
_MAXMEM = 64 * 1024 * 1024
PASSWORD_MIN, PASSWORD_MAX = 10, 128
EMAIL_MAX = 254
DISPLAY_NAME_MAX = 100

# Short built-in blocklist, compared case-insensitively. Only entries of 10+ characters can matter.
COMMON_PASSWORDS = frozenset(
    """password12 password123 password1234 password12345 passw0rd123 password1! password123!
    1234567890 12345678910 123456789012 0123456789 1234512345 1111111111 0000000000 9876543210
    qwertyuiop qwerty1234 qwerty12345 qwerty123456 qwertyuiop123 asdfghjkl1 asdfghjklqwerty zxcvbnm123
    1q2w3e4r5t 1qaz2wsx3edc q1w2e3r4t5 iloveyou12 iloveyou123 letmein123 letmein1234 welcome123 welcome1234
    administrator admin12345 admin123456 administrator1 changeme123 changemenow trustno1234 monkey1234
    dragon12345 football123 baseball123 superman123 sunshine123 princess123 abc1234567 abcdefghij
    learnswe123 learnswe1234 learnswepassword""".split()
)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _derive(password: str, salt: bytes, n: int, r: int, p: int, dklen: int) -> bytes:
    # surrogatepass: hashing never fails on odd input; the rules reject such passwords at signup.
    return hashlib.scrypt(
        password.encode("utf-8", "surrogatepass"), salt=salt, n=n, r=r, p=p, maxmem=_MAXMEM, dklen=dklen
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(_derive(password, salt, _N, _R, _P, _DKLEN))}"


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return hash_password("learnswe-dummy-password")


def _parse(stored: str) -> tuple[int, int, int, bytes, bytes] | None:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        n, r, p = int(n), int(r), int(p)
        salt_bytes, digest_bytes = base64.b64decode(salt, validate=True), base64.b64decode(digest, validate=True)
    except ValueError:
        return None
    # Bounds keep a tampered row from asking for unbounded memory or time.
    sane = 2 <= n <= 2**16 and n & (n - 1) == 0 and 1 <= r <= 16 and 1 <= p <= 4
    if scheme != "scrypt" or not sane or not digest_bytes:
        return None
    return n, r, p, salt_bytes, digest_bytes


def verify_password(password: str, stored: str | None) -> bool:
    """Constant-time check. Always spends one hash, also when there is no usable stored hash."""
    parsed = _parse(stored) if stored else None
    usable = parsed is not None
    if parsed is None:
        parsed = _parse(_dummy_hash())
    n, r, p, salt, digest = parsed  # type: ignore[misc]
    matches = hmac.compare_digest(_derive(password, salt, n, r, p, len(digest)), digest)
    return usable and matches


def clean_email(raw: str) -> str:
    """Trim and lower-case; the single normal form for storage, lookup and limiter keys."""
    return raw.strip().lower()


def normalise_email(raw: str) -> str:
    """clean_email plus format rules. Raises ValueError for an invalid address."""
    email = clean_email(raw)
    if not 1 <= len(email) <= EMAIL_MAX or not is_postgres_text(email):
        raise ValueError("email length")
    if any(c.isspace() or unicodedata.category(c) == "Cc" for c in email) or email.count("@") != 1:
        raise ValueError("email characters")
    local, domain = email.split("@")
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("email shape")
    return email


def normalise_display_name(raw: str) -> str:
    """Trim; 1 to 100 code points without control characters. Raises ValueError."""
    name = raw.strip()
    has_control = any(unicodedata.category(c) == "Cc" for c in name)
    if not 1 <= len(name) <= DISPLAY_NAME_MAX or not is_postgres_text(name) or has_control:
        raise ValueError("display name")
    return name


def check_password_rules(password: str, email: str) -> list[str]:
    """Violated rules, empty when acceptable. The password is never altered or echoed."""
    problems = []
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        problems.append("length")
    if not is_postgres_text(password):
        problems.append("characters")
    lowered = password.casefold()
    if lowered in (email.casefold(), email.split("@")[0].casefold()):
        problems.append("same_as_email")
    if lowered in COMMON_PASSWORDS:
        problems.append("common")
    return problems
