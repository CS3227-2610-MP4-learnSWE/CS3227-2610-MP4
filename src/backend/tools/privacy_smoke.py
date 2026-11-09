"""Offline scanner provisioning check: run after frozen install, before serving grading."""
import json
import resource
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from feature_analytics import privacy
from feature_analytics.grading_text import GradingContent

until = time.monotonic() + 60
while not privacy.privacy_ready() and time.monotonic() < until:
    time.sleep(0.05)
assert privacy.privacy_ready(), "local scanner health failed"
measurements = []
for name in ("Barack Obama", "Alice Johnson", "John Smith"):
    started = time.monotonic()
    result = privacy.prepare_grading_content(source="student_hint", content=GradingContent(
        "Can you explain testing?", f"{name} recommends checking expected behavior. password=cat", ""), identity_values=())
    elapsed = (time.monotonic() - started) * 1000
    assert result.state == "eligible", result.code
    assert name not in result.content.response_text
    assert "cat" not in result.content.response_text
    assert elapsed <= 500
    measurements.append(round(elapsed, 2))
started = time.monotonic()
result = privacy.prepare_grading_content(source="student_hint", content=GradingContent("Explain testing. " * 110, "Check expected behavior. " * 220, ""), identity_values=())
assert result.state == "eligible", result.code
elapsed = (time.monotonic() - started) * 1000
assert elapsed <= 500
print(json.dumps({"policy": privacy.POLICY_VERSION, "fixture_ms": measurements, "near_cap_ms": round(elapsed, 2), "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "detection_is_not_a_guarantee": True}))
