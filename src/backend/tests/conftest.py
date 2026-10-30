import pytest


@pytest.fixture
def fake():
    """A fake LLM injected in place of the shared client (STU-03 tests).

    Imports are lazy so the older suites still collect without llm_client.
    """
    from companion_helpers import FakeLlm, install, uninstall

    f = FakeLlm()
    install(f)
    yield f
    uninstall()
