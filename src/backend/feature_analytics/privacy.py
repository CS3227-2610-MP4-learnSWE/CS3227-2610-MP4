"""Bounded, offline English DLP gate. Detection is deliberately not a privacy guarantee."""
import hashlib
import importlib.metadata
import os
import re
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from feature_analytics.grading_text import GradingContent

POLICY_VERSION = "adm01-local-dlp-v1"
MODEL_DIGEST = "5f7701300a1a25bbbec7861933e9aadfa7e5de254b290201fd1f8975b07862f3"
REDACTED = "[REDACTED]"
DEADLINE_S = 0.5
_nlp = None
_healthy = False
_slot = threading.Lock()
_task_ready = threading.Event()
_task = None


def privacy_mode() -> str:
    return "strict" if os.environ.get("ANALYTICS_PRIVACY_MODE", "local_dlp") != "local_dlp" else "local_dlp"


@dataclass(frozen=True)
class PrivacyResult:
    state: Literal["eligible", "blocked"]
    code: Literal["privacy_disabled", "privacy_source_excluded", "privacy_input_unsupported", "privacy_scanner_unavailable"] | None
    content: GradingContent | None
    policy_version: str | None


class _Unsupported(Exception):
    pass


def _initialize() -> None:
    global _nlp, _healthy
    try:
        if importlib.metadata.version("spacy") != "3.8.18" or importlib.metadata.version("en-core-web-sm") != "3.8.0":
            return
        dist = importlib.metadata.distribution("en-core-web-sm")
        path = Path(dist.locate_file("en_core_web_sm/en_core_web_sm-3.8.0"))
        digest = hashlib.sha256()
        for file in sorted(path.rglob("*"), key=lambda file: file.relative_to(path).as_posix()):
            if file.is_file():
                digest.update(file.relative_to(path).as_posix().encode())
                digest.update(file.read_bytes())
        if digest.hexdigest() != MODEL_DIGEST:
            return
        import spacy
        spacy.require_cpu()
        _nlp = spacy.load(path, enable=["tok2vec", "ner"])
        fixture = "Alice Johnson met Barack Obama in London."
        spans = scan_person_spans(fixture)
        if not any(fixture[a:b] == "Barack Obama" for a, b in spans):
            return
        _healthy = True
    except Exception:
        return  # no raw scanner exception or text is logged


def _worker() -> None:
    global _healthy
    while True:
        _task_ready.wait()
        _task_ready.clear()
        task = _task
        if task is None:
            return
        function, done, result = task
        try:
            result.append((True, function()))
        except _Unsupported:
            result.append((False, "privacy_input_unsupported"))
        except Exception:
            _healthy = False
            result.append((False, "privacy_scanner_unavailable"))
        finally:
            done.set()


def scan_person_spans(text: str) -> tuple[tuple[int, int], ...]:
    if _nlp is None:
        raise RuntimeError("scanner unavailable")
    return tuple((ent.start_char, ent.end_char) for ent in _nlp(text.replace(REDACTED, " " * len(REDACTED))).ents if ent.label_ == "PERSON")


def privacy_ready() -> bool:
    return privacy_mode() == "local_dlp" and _healthy


def _bounded(function):
    global _task, _healthy
    if not privacy_ready() or not _slot.acquire(blocking=False):
        return False, "privacy_scanner_unavailable"
    try:
        done, result = threading.Event(), []
        _task = (function, done, result)
        _task_ready.set()
        if not done.wait(DEADLINE_S):
            _healthy = False
            return False, "privacy_scanner_unavailable"
        return result[0]
    finally:
        _slot.release()


_PATTERNS = tuple(re.compile(p, re.I | re.M) for p in (
    r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----",
    r"\b(?:bearer|basic)\s+[A-Za-z0-9+/=_\-.]+",
    r"\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
    r"\b[a-z][a-z0-9+.-]*://[^\s/@:]+:[^\s/@]+@[^\s]+",
    r"\b(?:password|passwd|pwd|secret|token|api[_ -]?key)\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)",
    r"\b(?:sk-|sk_|pk_|ghp_|github_pat_|AKIA)[A-Za-z0-9_-]+",
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}",
    r"\b[uU]-[A-Za-z0-9_-]+\b",
    r"\b[STFGM]\d{7}[A-Z]\b|\b\d{3}-\d{2}-\d{4}\b",
    r"(?<!\w)\+?\d[\d ()-]{6,}\d(?!\w)",
    r"[A-Za-z0-9_-]{32,}",
))
_MARKERS = re.compile(r"answer\s+key|correct\s+(?:answer|option|choice)|\bsolution\b|worked\s+solution|answer\s+is|explanation\s*(?::|of\s+the\s+correct)", re.I)


def _normal(text: str) -> str:
    try:
        text.encode("utf-8", errors="strict")
    except UnicodeError:
        raise _Unsupported from None
    text = unicodedata.normalize("NFKC", text)
    if any((ch.isalpha() and not ch.isascii()) or unicodedata.category(ch) in ("Cc", "Cs", "Co", "Cf") and ch not in "\n\r\t" for ch in text):
        raise _Unsupported
    if re.search(r"[<>]|```|^\s*\{|^\s*\[(?!REDACTED\])|data:|\\x[0-9a-f]{2}", text, re.I):
        raise _Unsupported
    return text


def _sanitize(text: str, identities: tuple[str, ...]) -> str:
    text = _normal(text)
    spans = list(scan_person_spans(text)) if text else []
    for pattern in _PATTERNS:
        spans.extend(match.span() for match in pattern.finditer(text))
    for identity in identities:
        if not identity:
            continue
        alias = unicodedata.normalize("NFKC", identity).strip()
        if alias:
            spans.extend(m.span() for m in re.finditer(re.escape(alias), text, re.I))
    merged = []
    for start, end in sorted(spans):
        if not 0 <= start < end <= len(text):
            raise RuntimeError("invalid span")
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    for start, end in reversed(merged):
        text = text[:start] + REDACTED + text[end:]
    return text


def prepare_grading_content(*, source: Literal['student_hint', 'teacher_notes', 'student_explanation', 'teacher_mcq', 'legacy'], content: GradingContent, identity_values: tuple[str, ...]) -> PrivacyResult:
    def blocked(code):
        return PrivacyResult("blocked", code, None, None)
    if privacy_mode() == "strict":
        return blocked("privacy_disabled")
    if source not in ("student_hint", "teacher_notes"):
        return blocked("privacy_source_excluded")
    def scan():
        values = (content.request_text, content.response_text, content.context_text or "")
        if any(not isinstance(t, str) or len(t) > cap for t, cap in zip(values, (2000, 6000, 3000))):
            raise _Unsupported
        # Context is never retained or dispatched, even when supplied by an old caller.
        for text in values:
            if _MARKERS.search(" ".join(_normal(text).split())):
                raise _Unsupported
        request, response = (_sanitize(t, identity_values) for t in values[:2])
        if len(request) > 2000 or len(response) > 6000:
            raise _Unsupported
        return GradingContent(request, response, "")
    ok, result = _bounded(scan)
    return PrivacyResult("eligible", None, result, POLICY_VERSION) if ok else blocked(result)


def validate_grader_privacy(*, reasons: tuple[str, ...]) -> bool:
    def scan():
        return all(_sanitize(reason, ()) == reason for reason in reasons)
    ok, result = _bounded(scan)
    return bool(ok and result)


threading.Thread(target=_worker, daemon=True, name="analytics-privacy").start()
threading.Thread(target=_initialize, daemon=True, name="analytics-privacy-warmup").start()
