"""Real offline model checks run in a fresh process, isolated from failure-state tests."""
import json
import subprocess
import sys
import textwrap

import pytest


CASES = [
    ("Alice went to school yesterday.", "Alice"),
    ("John Smith wrote the report yesterday.", "John Smith"),
    ("Mary Johnson attended the meeting.", "Mary Johnson"),
]


@pytest.fixture(scope="module")
def offline_model():
    try:
        import spacy  # noqa: F401
    except ImportError as error:
        if "Application Control policy has blocked this file" in str(error) and "cblas" in str(error):
            pytest.skip("Windows Application Control blocks thinc cblas DLL; offline smoke runs in Linux CI")
        raise
    # Other cases intentionally poison the shared scanner until restart. Provisioning
    # must be checked in a clean process, without resetting that safety invariant.
    script = textwrap.dedent("""
        import json, time
        from feature_analytics import privacy
        deadline = time.monotonic() + 60
        while not privacy.privacy_ready() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert privacy.privacy_ready(), "Pinned local model must be provisioned and warmed up"
        results = {}
        for text, name in json.loads(__import__('sys').argv[1]):
            start = time.monotonic()
            spans = privacy.scan_person_spans(text)
            results[text] = {"elapsed": time.monotonic() - start, "spans": spans}
        print(json.dumps(results))
    """)
    result = subprocess.run(
        [sys.executable, "-c", script, json.dumps(CASES)],
        capture_output=True, text=True, timeout=75,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("text,name", CASES)
def test_adm01_privacy_real_offline_model_recognises_representative_names_within_bound(text, name, offline_model):
    result = offline_model[text]
    assert result["elapsed"] < 0.5
    assert any(name in text[left:right] for left, right in result["spans"])
