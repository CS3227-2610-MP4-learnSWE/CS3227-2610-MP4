"""DEPLOY-01 deployment commands may only promote the exact green commit."""
import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
BRANCH = "deploy/production-pages"


@pytest.fixture
def deploy(monkeypatch):
    spec = importlib.util.spec_from_file_location("deploy01_command", ROOT / "scripts/deploy_render.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, value in {"GITHUB_REPOSITORY": "owner/repo", "GITHUB_TOKEN": "test-github-token", "DEPLOY_COMMIT": SHA, "RENDER_API_KEY": "test-render-token", "RENDER_SERVICE_ID": "srv-test"}.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("WAIT_FOR_CI", raising=False)
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, stdout="", stderr=""))
    return module


def run_record(**overrides):
    result = dict(id=1, name="CI", path=".github/workflows/ci.yml", event="push", head_branch=BRANCH, head_sha=SHA, status="completed", conclusion="success")
    result.update(overrides)
    return result


@pytest.mark.parametrize("runs", [[], [run_record(conclusion="failure")], [run_record(status="in_progress", conclusion=None)], [run_record(event="pull_request")], [run_record(head_sha="b" * 40)], [run_record(head_branch="feature/unreviewed")], [run_record(head_branch="master")]])
def test_deploy01_ac3_missing_exact_green_deployment_branch_ci_blocks_promotion(deploy, monkeypatch, runs):
    monkeypatch.setattr(deploy, "request_json", lambda *a, **kw: {"total_count": len(runs), "workflow_runs": runs})
    with pytest.raises((RuntimeError, ValueError, SystemExit)):
        deploy.verify_commit(SHA)


def test_deploy01_ac3_green_exact_deployment_branch_push_is_accepted(deploy, monkeypatch):
    monkeypatch.setattr(deploy, "request_json", lambda *a, **kw: {"total_count": 1, "workflow_runs": [run_record()]})
    assert deploy.verify_commit(SHA) is None


def test_deploy01_ac3_unreachable_commit_blocks_promotion(deploy, monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args)
    monkeypatch.setattr(deploy.subprocess, "run", fail)
    monkeypatch.setattr(deploy, "request_json", lambda *a, **kw: {"workflow_runs": [run_record()]})
    with pytest.raises((RuntimeError, ValueError, SystemExit, subprocess.CalledProcessError)):
        deploy.verify_commit(SHA)


def test_deploy01_ac3_no_provider_deploy_before_commit_verification(deploy, monkeypatch):
    calls = []
    def reject(sha): raise RuntimeError("CI not approved")
    monkeypatch.setattr(deploy, "verify_commit", reject)
    monkeypatch.setattr(deploy, "request_json", lambda *a, **kw: calls.append((a, kw)))
    with pytest.raises((RuntimeError, SystemExit)):
        deploy.main()
    assert not calls


def test_deploy01_ac3_provider_commit_mismatch_never_reports_success(deploy, monkeypatch, capsys):
    monkeypatch.setattr(deploy, "verify_commit", lambda sha: None)
    wrong = {"id": "dep-test", "status": "live", "commit": {"id": "b" * 40}}
    def request(url, token, data=None):
        if "api.render.com" in url:
            return {**wrong, "deploy": wrong, "service": {"serviceDetails": {"url": "https://app.example"}}, "serviceDetails": {"url": "https://app.example"}}
        return {"status": "ready"}
    monkeypatch.setattr(deploy, "request_json", request)
    monkeypatch.setattr(deploy.time, "sleep", lambda seconds: None)
    with pytest.raises((RuntimeError, ValueError, SystemExit)):
        deploy.main()
    assert "https://app.example" not in capsys.readouterr().out


@pytest.fixture
def clock(deploy, monkeypatch):
    state = SimpleNamespace(now=0.0, sleeps=[])
    def sleep(seconds):
        state.sleeps.append(seconds)
        state.now += seconds
    monkeypatch.setattr(deploy.time, "monotonic", lambda: state.now)
    monkeypatch.setattr(deploy.time, "sleep", sleep)
    return state


def ci_responses(deploy, monkeypatch, batches):
    calls = []
    remaining = iter(batches)
    last = []
    def request(url, token, data=None):
        nonlocal last
        assert "api.render.com" not in url
        assert data is None
        assert token == "test-github-token"
        assert urlsplit(url).path == "/repos/owner/repo/actions/workflows/ci.yml/runs"
        query = parse_qs(urlsplit(url).query)
        assert query["head_sha"] == [SHA]
        assert query["event"] == ["push"]
        assert query["branch"] == [BRANCH]
        calls.append(url)
        last = next(remaining, last)
        return {"workflow_runs": last}
    monkeypatch.setattr(deploy, "request_json", request)
    return calls


def test_deploy01_ac3_branch_is_fixed_and_ancestry_precedes_ci(deploy, monkeypatch):
    assert deploy.DEPLOYMENT_BRANCH == BRANCH
    order = []
    def run(args, **kwargs):
        order.append(args)
        return subprocess.CompletedProcess(args, 0)
    monkeypatch.setattr(deploy.subprocess, "run", run)
    def request(*args, **kwargs):
        assert ["git", "fetch", "origin", BRANCH] in order
        assert ["git", "merge-base", "--is-ancestor", SHA, "origin/" + BRANCH] in order
        return {"workflow_runs": [run_record()]}
    monkeypatch.setattr(deploy, "request_json", request)
    deploy.verify_commit(SHA)


def test_deploy01_ac3_ci_wait_defaults_are_bounded(deploy):
    assert deploy.CI_WAIT_TIMEOUT_SECONDS == 900
    assert deploy.CI_POLL_INTERVAL_SECONDS == 10


def test_deploy01_ac3_waits_through_missing_and_pending_before_success(deploy, monkeypatch, clock):
    calls = ci_responses(deploy, monkeypatch, [[], [run_record(status="in_progress", conclusion=None)], [run_record()]])
    assert deploy.wait_for_ci(SHA) is None
    assert len(calls) == 3
    assert clock.sleeps == [10, 10]


@pytest.mark.parametrize("status", ["queued", "requested", "waiting", "pending", "in_progress"])
def test_deploy01_ac3_pending_ci_never_becomes_success_without_green_run(deploy, monkeypatch, clock, status):
    monkeypatch.setattr(deploy, "CI_WAIT_TIMEOUT_SECONDS", 12, raising=False)
    calls = ci_responses(deploy, monkeypatch, [[run_record(status=status, conclusion=None)]])
    with pytest.raises(ValueError, match="^CI did not pass within 15 minutes\\.$"):
        deploy.wait_for_ci(SHA)
    assert len(calls) == 2
    assert clock.sleeps == [10, 2]


def test_deploy01_ac3_missing_ci_times_out_without_extra_request(deploy, monkeypatch, clock):
    monkeypatch.setattr(deploy, "CI_WAIT_TIMEOUT_SECONDS", 12, raising=False)
    calls = ci_responses(deploy, monkeypatch, [[]])
    with pytest.raises(ValueError, match="^CI did not pass within 15 minutes\\.$"):
        deploy.wait_for_ci(SHA)
    assert len(calls) == 2
    assert clock.sleeps == [10, 2]


def test_deploy01_ac3_expired_deadline_stops_before_http(deploy, monkeypatch, clock):
    monkeypatch.setattr(deploy, "CI_WAIT_TIMEOUT_SECONDS", 0, raising=False)
    calls = ci_responses(deploy, monkeypatch, [[run_record()]])
    with pytest.raises(ValueError, match="^CI did not pass within 15 minutes\\.$"):
        deploy.wait_for_ci(SHA)
    assert calls == []


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out", "skipped", "neutral", "action_required", None])
def test_deploy01_ac3_completed_non_success_ci_fails_immediately(deploy, monkeypatch, clock, conclusion):
    calls = ci_responses(deploy, monkeypatch, [[run_record(conclusion=conclusion)]])
    with pytest.raises(ValueError, match="^CI failed for the selected deployment commit\\.$"):
        deploy.wait_for_ci(SHA)
    assert len(calls) == 1
    assert clock.sleeps == []


@pytest.mark.parametrize("unrelated", [run_record(head_branch="master"), run_record(head_branch="feature/other"), run_record(event="pull_request"), run_record(head_sha="b" * 40)])
def test_deploy01_ac3_unrelated_green_ci_does_not_authorize_wait(deploy, monkeypatch, clock, unrelated):
    calls = ci_responses(deploy, monkeypatch, [[unrelated], [run_record()]])
    deploy.wait_for_ci(SHA)
    assert len(calls) == 2
    assert clock.sleeps == [10]


def test_deploy01_ac3_newest_failure_overrides_older_success(deploy, monkeypatch, clock):
    ci_responses(deploy, monkeypatch, [[run_record(id=8, conclusion="failure"), run_record(id=2)]])
    with pytest.raises(ValueError, match="^CI failed for the selected deployment commit\\.$"):
        deploy.wait_for_ci(SHA)
    assert not clock.sleeps


def test_deploy01_ac3_newest_pending_overrides_older_success_until_newest_passes(deploy, monkeypatch, clock):
    calls = ci_responses(deploy, monkeypatch, [[run_record(id=2), run_record(id=9, status="in_progress", conclusion=None)], [run_record(id=2), run_record(id=9)]])
    deploy.wait_for_ci(SHA)
    assert len(calls) == 2
    assert clock.sleeps == [10]


def test_deploy01_ac3_newest_success_overrides_older_failure(deploy, monkeypatch, clock):
    ci_responses(deploy, monkeypatch, [[run_record(id=7), run_record(id=2, conclusion="failure")]])
    deploy.wait_for_ci(SHA)
    assert not clock.sleeps


@pytest.mark.parametrize("sha", ["", "main", "a" * 39, "z" * 40, "a" * 41])
def test_deploy01_ac3_wait_rejects_invalid_sha_before_any_provider(deploy, monkeypatch, clock, sha):
    calls = []
    monkeypatch.setattr(deploy, "request_json", lambda *a, **kw: calls.append(a))
    with pytest.raises((ValueError, SystemExit)):
        deploy.wait_for_ci(sha)
    assert not calls


def test_deploy01_ac3_wait_rejects_unreachable_commit_before_http(deploy, monkeypatch, clock):
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args)
    monkeypatch.setattr(deploy.subprocess, "run", fail)
    calls = []
    monkeypatch.setattr(deploy, "request_json", lambda *a, **kw: calls.append(a))
    with pytest.raises((subprocess.CalledProcessError, ValueError, SystemExit)):
        deploy.wait_for_ci(SHA)
    assert not calls


def test_deploy01_ac3_ci_http_error_never_authorizes_render(deploy, monkeypatch, clock):
    calls = []
    def fail(url, *args, **kwargs):
        calls.append(url)
        raise RuntimeError("HTTP failure")
    monkeypatch.setattr(deploy, "request_json", fail)
    with pytest.raises((RuntimeError, ValueError, SystemExit)):
        deploy.wait_for_ci(SHA)
    assert len(calls) == 1
    assert all("api.render.com" not in url for url in calls)


@pytest.mark.parametrize("response", [{}, {"workflow_runs": None}, {"workflow_runs": [run_record(id="invalid")]}])
def test_deploy01_ac3_malformed_ci_response_fails_closed(deploy, monkeypatch, clock, response):
    monkeypatch.setattr(deploy, "request_json", lambda *a, **kw: response)
    with pytest.raises((KeyError, TypeError, ValueError, RuntimeError, SystemExit)):
        deploy.wait_for_ci(SHA)


@pytest.mark.parametrize("value,expected", [("true", ["wait", "verify"]), ("false", ["verify"]), ("TRUE", ["verify"]), ("1", ["verify"])])
def test_deploy01_ac3_main_waits_only_when_explicitly_enabled_then_reverifies(deploy, monkeypatch, value, expected):
    monkeypatch.setenv("WAIT_FOR_CI", value)
    order = []
    monkeypatch.setattr(deploy, "wait_for_ci", lambda sha: order.append("wait"), raising=False)
    def verify(sha):
        order.append("verify")
        raise ValueError("stop after verification")
    monkeypatch.setattr(deploy, "verify_commit", verify)
    calls = []
    monkeypatch.setattr(deploy, "request_json", lambda *a, **kw: calls.append(a))
    with pytest.raises(ValueError):
        deploy.main()
    assert order == expected
    assert not calls


def test_deploy01_ac3_wait_failure_prevents_final_verify_and_render(deploy, monkeypatch):
    monkeypatch.setenv("WAIT_FOR_CI", "true")
    def wait(sha):
        raise ValueError("CI did not pass within 15 minutes.")
    monkeypatch.setattr(deploy, "wait_for_ci", wait, raising=False)
    calls = []
    monkeypatch.setattr(deploy, "verify_commit", lambda sha: calls.append("verify"))
    monkeypatch.setattr(deploy, "request_json", lambda *a, **kw: calls.append("render"))
    with pytest.raises(ValueError):
        deploy.main()
    assert not calls
