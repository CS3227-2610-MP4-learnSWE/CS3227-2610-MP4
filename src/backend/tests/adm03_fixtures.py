"""Fixtures imported by the ADM-03 test modules (`from adm03_fixtures import llm, admin, other_admin`)."""
import pytest

from adm02_helpers import actor
from adm03_helpers import SEEDED_USERS, FakeAnalysisLlm, cleanup_from, install, uninstall


@pytest.fixture
def llm():
    mark = len(SEEDED_USERS)
    fake = FakeAnalysisLlm()
    install(fake)
    yield fake
    if fake.gate is not None:
        fake.gate.set()
    uninstall()
    cleanup_from(mark)


@pytest.fixture
def admin():
    mark = len(SEEDED_USERS)
    yield actor("admin")
    cleanup_from(mark)


@pytest.fixture
def other_admin():
    return actor("admin")
