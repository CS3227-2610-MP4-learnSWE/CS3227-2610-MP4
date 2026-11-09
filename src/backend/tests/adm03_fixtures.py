"""Fixtures imported by the ADM-03 test modules (`from adm03_fixtures import llm, admin, other_admin`)."""
import pytest

from adm02_helpers import actor
from adm03_helpers import FakeAnalysisLlm, install, uninstall


@pytest.fixture
def llm():
    fake = FakeAnalysisLlm()
    install(fake)
    yield fake
    if fake.gate is not None:
        fake.gate.set()
    uninstall()


@pytest.fixture
def admin():
    return actor("admin")


@pytest.fixture
def other_admin():
    return actor("admin")
