"""Additional ADM-02 real-transaction ordering checks requested during review."""
from concurrent.futures import ThreadPoolExecutor
import os
import time

import psycopg
from sqlalchemy import create_engine

from auth_helpers import call, code_of, psycopg_url, sql
from adm02_helpers import (ADMIN, actor, answers, created, error, form_get,
                          payload, publish, published, race, save, submit)


def test_adm02_publish_racing_update_freezes_one_consistent_revision():
    admin, user = actor("admin"), actor()
    form = created(admin)
    changed = payload()
    updated, sent = race(
        lambda: call("PUT", f"{ADMIN}/forms/{form['id']}", admin, {**changed, "version": form["version"]}),
        lambda: publish(admin, form, [user]),
    )
    assert sorted(r.status_code for r in (updated, sent)) == [200, 409]
    current = call("GET", f"{ADMIN}/forms/{form['id']}", admin).json()
    if sent.status_code == 200:
        error(updated, 409, "feedback_state_conflict")
        assert current["state"] == "open"
        assert current["title"] == form["title"]
        assert current["questions"] == form["questions"]
    else:
        error(sent, 409, "feedback_version_conflict")
        assert current["state"] == "draft"
        assert current["questions"] == changed["questions"]
        assert current["recipient_count"] == 0
        current = publish(admin, current, [user]).json()
        assert current["state"] == "open" and current["title"] == changed["title"]
    assert form_get(user, form).json()["questions"] == current["questions"]


def test_adm02_revoked_recipient_waiting_behind_admin_disable_cannot_save(monkeypatch):
    admin, user = actor("admin"), actor()
    form = published(admin, [user])
    holder = psycopg.connect(psycopg_url())
    observer = psycopg.connect(psycopg_url(), autocommit=True)
    marker = "adm02_revocation_" + form["id"].replace("-", "")
    engine = create_engine(os.environ["DATABASE_URL"], pool_size=3, max_overflow=0,
                           connect_args={"application_name": marker})
    monkeypatch.setattr("auth.db.engine_for", lambda _url: engine)
    pool = ThreadPoolExecutor(max_workers=2)
    try:
        holder.execute('SELECT id FROM "user" WHERE id=%s FOR UPDATE', (str(user),))
        holder_pid = holder.info.backend_pid
        disabled = pool.submit(call, "PUT", f"/api/admin/accounts/{user}/status", admin, {"status": "disabled"})
        deadline = time.monotonic() + 10
        disable_pid = None
        while time.monotonic() < deadline:
            rows = observer.execute("SELECT pid FROM pg_stat_activity WHERE %s=ANY(pg_blocking_pids(pid)) AND application_name=%s", (holder_pid, marker)).fetchall()
            if rows:
                disable_pid = rows[0][0]
                break
            time.sleep(0.02)
        assert disable_pid is not None, "Admin disable never reached the deliberately held user row"
        assert observer.execute("SELECT count(*) FROM pg_locks WHERE pid=%s AND locktype='advisory' AND granted", (disable_pid,)).fetchone()[0] >= 1
        saving = pool.submit(save, user, form, answers(form))
        deadline = time.monotonic() + 10
        observed_wait = False
        while time.monotonic() < deadline:
            rows = observer.execute("SELECT pid FROM pg_stat_activity WHERE %s=ANY(pg_blocking_pids(pid)) AND application_name=%s", (disable_pid, marker)).fetchall()
            if rows:
                observed_wait = True
                break
            time.sleep(0.02)
        assert observed_wait and not saving.done(), "Recipient save must wait for pending access mutation"
        holder.commit()
        disabled_reply = disabled.result(timeout=10)
        assert disabled_reply.status_code == 200, disabled_reply.text
        error(saving.result(timeout=10), 401, "unauthenticated")
        assert sql("SELECT count(*) FROM feedback_response_drafts WHERE form_id=%s", (form["id"],))[0][0] == 0
    finally:
        holder.rollback()
        holder.close()
        observer.close()
        pool.shutdown(wait=True)
        engine.dispose()


def test_adm02_shared_single_connection_pool_handles_parallel_reads_save_and_submit(monkeypatch):
    admin, user = actor("admin"), actor()
    form = published(admin, [user])
    engine = create_engine(os.environ["DATABASE_URL"], pool_size=1, max_overflow=0, pool_timeout=3)
    # Existing shared infrastructure hook used by the older connection-lifetime
    # tests. No feedback implementation function, query or result is mocked.
    monkeypatch.setattr("auth.db.engine_for", lambda _url: engine)
    try:
        reads = race(lambda: form_get(user, form), lambda: form_get(user, form))
        assert [r.status_code for r in reads] == [200, 200]
        writes = race(lambda: save(user, form, answers(form)), lambda: save(user, form, answers(form)))
        assert sorted(r.status_code for r in writes) == [200, 409]
        assert code_of(next(r for r in writes if r.status_code == 409)) == "feedback_draft_version_conflict"
        submissions = race(lambda: submit(user, form, answers(form), 1), lambda: submit(user, form, answers(form), 1))
        assert sorted(r.status_code for r in submissions) == [201, 409]
        assert engine.pool.checkedout() == 0
    finally:
        engine.dispose()
