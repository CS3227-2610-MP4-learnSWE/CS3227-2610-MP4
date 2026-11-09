"""Offline pinned-model smoke: representative English fixtures, never a completeness guarantee.

No seam substitution or download. Provisioning is required for this focused suite.
Arbitrary unknown names/unlabelled secrets remain explicitly outside the guarantee.
"""
import time

import pytest

from feature_analytics.privacy import privacy_ready, scan_person_spans


@pytest.fixture(scope="module")
def offline_model():
    try:
        import spacy  # noqa: F401
    except ImportError as error:
        if "Application Control policy has blocked this file" in str(error) and "cblas" in str(error):
            pytest.skip("Windows Application Control blocks thinc cblas DLL; offline smoke runs in Linux CI")
        raise
    deadline = time.monotonic() + 10
    while not privacy_ready() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert privacy_ready(), "Pinned local model must be provisioned and warmed up before this smoke suite"


@pytest.mark.parametrize("text,name", [
    ("Alice went to school yesterday.", "Alice"),
    ("John Smith wrote the report yesterday.", "John Smith"),
    ("Mary Johnson attended the meeting.", "Mary Johnson"),
])
def test_adm01_privacy_real_offline_model_recognises_representative_names_within_bound(text, name, offline_model):
    start = time.monotonic()
    spans = scan_person_spans(text)
    assert time.monotonic() - start < 0.5
    assert any(name in text[left:right] for left, right in spans)
