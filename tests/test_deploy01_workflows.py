"""DEPLOY-01 deployment commands may only promote the exact green commit."""
import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40


@pytest.fixture
def deploy(monkeypatch):
    spec = importlib.util.spec_from_file_location("deploy01_command", ROOT / "scripts/deploy_render.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, value in {"GITHUB_REPOSITORY": "owner/repo", "GITHUB_TOKEN": "test-github-token", "DEPLOY_COMMIT": SHA, "RENDER_API_KEY": "test-render-token", "RENDER_SERVICE_ID": "srv-test"}.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, stdout="", stderr=""))
    return module


def run_record(**overrides):
    result = dict(id=1, name="CI", path=".github/workflows/ci.yml", event="push", head_branch="master", head_sha=SHA, status="completed", conclusion="success")
    result.update(overrides)
    return result


@pytest.mark.parametrize("runs", [[], [run_record(conclusion="failure")], [run_record(status="in_progress", conclusion=None)], [run_record(event="pull_request")], [run_record(head_sha="b" * 40)], [run_record(head_branch="feature/unreviewed")]])
def test_deploy01_ac3_missing_exact_green_master_ci_blocks_promotion(deploy, monkeypatch, runs):
    monkeypatch.setattr(deploy, "request_json", lambda *a, **kw: {"total_count": len(runs), "workflow_runs": runs})
    with pytest.raises((RuntimeError, ValueError, SystemExit)):
        deploy.verify_commit(SHA)


def test_deploy01_ac3_green_exact_master_push_is_accepted(deploy, monkeypatch):
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
