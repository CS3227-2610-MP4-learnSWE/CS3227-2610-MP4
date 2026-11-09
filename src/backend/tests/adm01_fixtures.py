"""Fixtures imported by the ADM-01 test modules (`from adm01_fixtures import ...`)."""
import pytest

from adm01_helpers import BlockedAiClient, install_ai_block, wipe_runs, wipe_user_rows
from adm02_helpers import actor
from auth_helpers import sql


@pytest.fixture(scope="module")
def analytics_admin():
    return actor("admin")


@pytest.fixture(scope="module")
def analytics_student():
    return actor("student")


@pytest.fixture(scope="module")
def analytics_teacher():
    return actor("teacher")


@pytest.fixture
def disabled_admin():
    user = actor("admin")
    sql('UPDATE "user" SET access_status=\'disabled\' WHERE id=%s', (str(user),))
    return user


@pytest.fixture
def no_ai(monkeypatch):
    """The AI seam is blocked and runs stay queued; yields the BlockedAiClient (its `.calls` must stay empty)."""
    wipe_runs()
    client = install_ai_block(monkeypatch, BlockedAiClient())
    yield client
    wipe_runs()


@pytest.fixture
def tracked_users():
    """A list tests append users to; their analytics rows are removed afterwards."""
    users = []
    yield users
    wipe_user_rows(users)


@pytest.fixture
def grader(tracked_users):
    """The fake SoC LLM installed through the dependency override (plan decision 7); no run state leaks.

    Yields a FakeGrader. Runs are wiped before and after so the hourly quota and the single active run
    never leak between tests. `tracked_users` rows are removed afterwards.
    """
    from adm01_grading_helpers import FakeGrader, install_grader, uninstall_grader

    wipe_runs()
    fake = FakeGrader()
    install_grader(fake)
    yield fake
    if fake.gate is not None:
        fake.gate.set()
    uninstall_grader()
    wipe_runs()


@pytest.fixture
def recording_start():
    """Lets a test move analytics_meta.recording_started_at; restored afterwards."""
    from adm01_grading_helpers import RecordingStart

    holder = RecordingStart()
    yield holder
    holder.restore()
