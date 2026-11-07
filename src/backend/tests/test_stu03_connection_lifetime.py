"""Companion reads must not need a second connection while holding auth's first."""
import pytest
from sqlalchemy import create_engine

from auth.settings import load_settings
from companion_helpers import BENIGN, SET_ID, ask, new_student, start


@pytest.mark.parametrize("page", ["other", "practice"])
def test_stu03_companion_releases_auth_connection_before_model_and_nested_reads(
    fake, monkeypatch, page,
):
    student = new_student()
    attempt = start(student)
    engine = create_engine(
        load_settings().database_url,
        pool_size=1,
        max_overflow=0,
        pool_timeout=0.25,
    )
    # All request/session/store paths share the same deliberately bounded pool.
    for module in ("auth.db", "attempt_store", "companion_routes"):
        monkeypatch.setattr(f"{module}.engine_for", lambda _url: engine)
    held_during_model = []

    def reply(_messages):
        held_during_model.append(engine.pool.checkedout())
        return BENIGN

    fake.reply = reply
    try:
        response = ask(
            student, "Help me understand functions", page=page,
            set_id=SET_ID if page == "practice" else None,
            attempt_id=attempt if page == "practice" else None,
        )
        assert response.status_code == 200, response.text
        assert response.json()["mode"] == ("help" if page == "other" else "hint")
        assert held_during_model == [0]
        assert engine.pool.checkedout() == 0
    finally:
        engine.dispose()
