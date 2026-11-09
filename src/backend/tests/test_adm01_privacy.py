"""Approved privacy amendment contract; no implementation inspection or remote AI/model calls."""
import subprocess
import sys
import textwrap

import pytest

from feature_analytics import privacy
from feature_analytics.grading_text import GradingContent


@pytest.fixture
def scanner(monkeypatch):
    calls = []

    def scan(text):
        calls.append(text)
        return tuple((text.index(name), text.index(name) + len(name))
                     for name in ("Alice", "John Smith") if name in text)

    monkeypatch.setattr(privacy, "scan_person_spans", scan)
    monkeypatch.setattr(privacy, "privacy_ready", lambda: True)
    return calls


def prepare(request="Please give a hint.", response="Consider the loop invariant.",
            context="", source="student_hint", identities=()):
    return privacy.prepare_grading_content(
        source=source, content=GradingContent(request, response, context), identity_values=identities)


def blocked(result, code):
    assert (result.state, result.code, result.content) == ("blocked", code, None)


@pytest.mark.parametrize("sensitive", [
    "Alice", "John Smith", "person@example.org", "+1 (415) 555-2671", "S1234567D",
    "u-12345678", "password=x", "PaSsWd: ab", "PWD = 7", "secret=hi", "token=z",
    "api_key=abc", "Bearer abcdef", "Basic dXNlcjpwYXNz",
    "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijk",
    "postgresql://user:short@localhost/db", "sk-abcdefghijklmno", "a" * 32,
    "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
])
def test_adm01_privacy_detected_names_and_credentials_are_redacted(scanner, sensitive):
    result = prepare(response=f"Review {sensitive} before the loop.")
    assert result.state == "eligible"
    assert result.policy_version == "adm01-local-dlp-v1"
    assert result.content.response_text == "Review [REDACTED] before the loop."
    assert result.content.context_text in (None, "")


def test_adm01_privacy_identity_normalisation_and_unrelated_name(scanner):
    result = prepare(response="ISAAC and John Smith discuss loops.", identities=("Isaac",))
    assert result.content.response_text == "[REDACTED] and [REDACTED] discuss loops."
    result = prepare(response="ＩＳＡＡＣ discusses loops.", identities=("Isaac",))
    assert result.state == "eligible"
    assert "isaac" not in result.content.response_text.casefold()
    assert "ＩＳＡＡＣ" not in result.content.response_text


@pytest.mark.parametrize("text,secret", [("my password is abc", "abc"), ("API key is q", "q")])
def test_adm01_privacy_short_natural_language_labelled_credentials_are_removed(scanner, text, secret):
    result = prepare(response=text)
    assert result.state == "eligible"
    assert "[REDACTED]" in result.content.response_text
    assert secret not in result.content.response_text.split()


@pytest.mark.parametrize("source", ["student_explanation", "teacher_mcq", "legacy"])
def test_adm01_privacy_excluded_sources_are_never_scanned(scanner, source):
    blocked(prepare(source=source), "privacy_source_excluded")
    assert scanner == []


@pytest.mark.parametrize("marker", ["correct answer", "CoRrEcT   ChOiCe", "answer key",
                                        "solution", "explanation:"])
def test_adm01_privacy_solution_markers_block_whole_candidate(scanner, marker):
    blocked(prepare(response=f"The {marker} is the second option."), "privacy_input_unsupported")


def test_adm01_privacy_context_is_excluded_and_safe_text_is_preserved(scanner):
    result = prepare(context="PRIVATE teacher upload: ordinary prose revealing a key.")
    assert result.content.request_text == "Please give a hint."
    assert result.content.response_text == "Consider the loop invariant."
    assert result.content.context_text in (None, "")
    assert all("PRIVATE" not in text for text in scanner)
    assert "Please give a hint." in scanner
    assert "Consider the loop invariant." in scanner


@pytest.mark.parametrize("field,cap", [("request", 2000), ("response", 6000), ("context", 3000)])
def test_adm01_privacy_over_cap_is_rejected_without_truncating(field, cap, scanner):
    blocked(prepare(**{field: "a " * (cap // 2) + "password=x"}), "privacy_input_unsupported")


@pytest.mark.parametrize("value", ["中文", "Привет", "\ud800", "\x00binary", '{"nested":"text"}'])
def test_adm01_privacy_unsupported_input_fails_closed(scanner, value):
    blocked(prepare(response=value), "privacy_input_unsupported")


def test_adm01_privacy_unready_or_scanner_exception_has_no_regex_fallback(scanner, monkeypatch, caplog):
    monkeypatch.setattr(privacy, "privacy_ready", lambda: False)
    blocked(prepare(), "privacy_scanner_unavailable")
    assert scanner == []
    monkeypatch.setattr(privacy, "privacy_ready", lambda: True)

    def fail(text):
        raise RuntimeError("PRIVATE scanner exception password=x")

    monkeypatch.setattr(privacy, "scan_person_spans", fail)
    blocked(prepare(), "privacy_scanner_unavailable")
    assert "PRIVATE" not in caplog.text


def test_adm01_privacy_deadline_and_busy_worker_are_bounded():
    # A timed-out scanner must remain unhealthy until restart: isolate that intentional
    # process-lifetime state rather than resetting implementation internals in the suite.
    script = textwrap.dedent('''
        import threading, time
        from feature_analytics import privacy
        from feature_analytics.grading_text import GradingContent
        entered, release = threading.Event(), threading.Event()
        calls = []
        def slow(text):
            calls.append(text)
            entered.set()
            release.wait(3)
            return ()
        privacy.scan_person_spans = slow
        privacy.privacy_ready = lambda: True
        try:
            for attempt in range(2):
                start = time.monotonic()
                result = privacy.prepare_grading_content(source="student_hint",
                    content=GradingContent("Give a hint.", "Consider loops.", ""), identity_values=())
                assert (result.state, result.code, result.content) == ("blocked", "privacy_scanner_unavailable", None)
                assert time.monotonic() - start < .8
            assert entered.is_set() and len(calls) == 1
        finally:
            release.set()
    ''')
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("reason", ["Alice wrote clearly.", "The password=x was exposed."])
def test_adm01_privacy_grade_reasons_reject_detected_spans_without_partial_redaction(scanner, reason):
    assert privacy.validate_grader_privacy(reasons=("A clear response.", reason)) is False


def test_adm01_privacy_safe_grade_reasons_pass(scanner):
    assert privacy.validate_grader_privacy(reasons=("The response is clear.",)) is True


def test_adm01_privacy_grade_reason_with_solution_marker_is_rejected(scanner):
    assert privacy.validate_grader_privacy(reasons=("The correct answer is B.",)) is False


def test_adm01_privacy_strict_setting_blocks_even_a_healthy_scanner(scanner, monkeypatch):
    monkeypatch.setenv("ANALYTICS_PRIVACY_MODE", "strict")
    blocked(prepare(), "privacy_disabled")
    assert scanner == []
