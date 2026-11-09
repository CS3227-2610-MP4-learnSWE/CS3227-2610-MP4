"""ADM-03 AC19, AC23: idempotency, one running AI step per admin, progress, interruption (task 9)."""
import re
import time

from auth_helpers import sql
from adm02_helpers import uid
from adm03_fixtures import admin, llm, other_admin  # noqa: F401
from adm03_helpers import (POOL, create, expect, get, listing, release, row_count, run, start_blocked, text_form,
                           wait_done)

IN_PROGRESS = re.compile(r"Another analysis started (\d+) seconds ago is still running its AI step\. "
                         r"A running AI step finishes or fails within 780 seconds\. Wait for it, then generate again\.")
INTERRUPTED = re.compile(r"The AI step was interrupted: it had been running for (\d+) seconds without finishing "
                         r"\(the limit is 780 seconds\), probably because the server restarted\. It had finished (\d+) of (\d+) steps\. "
                         r"The statistics are unaffected\. Start a new analysis\.")


def settle(llm, futures, ready):
    """Wait until `ready()` (the fast replies are in), release the held job, collect all replies."""
    end = time.monotonic() + 30
    while not ready() and time.monotonic() < end:
        time.sleep(0.02)
    llm.gate.set()
    return [f.result(60) for f in futures]


def test_adm03_ac19_same_request_id_twice_at_once_gives_one_row_and_one_job(admin, llm):
    import threading
    form, ids = text_form(admin, 3)
    rid = uid()
    llm.gate = threading.Event()
    futures = [POOL.submit(create, admin, form, ids, request_id=rid) for _ in range(2)]
    replies = settle(llm, futures, lambda: any(f.done() for f in futures) or llm.entered.is_set())
    assert sorted(r.status_code for r in replies) == [200, 201], [r.text for r in replies]
    assert replies[0].json()["id"] == replies[1].json()["id"]
    wait_done(admin, replies[0].json()["id"])
    assert len(listing(admin)["items"]) == 1
    assert len(llm.of("map")) == 1 and len(llm.of("reduce")) == 1  # one job only


def test_adm03_ac19_same_request_id_later_returns_the_existing_analysis_in_any_state(admin, llm):
    form, ids = text_form(admin, 2)
    rid = uid()
    first = create(admin, form, ids, request_id=rid)
    assert first.status_code == 201
    done = wait_done(admin, first.json()["id"])
    calls = len(llm.calls)
    again = create(admin, form, ids, request_id=rid)
    assert again.status_code == 200 and again.json() == done and len(llm.calls) == calls
    k = len(llm.calls) + 1
    llm.script = {k: "nonsense", k + 1: "nonsense"}  # both attempts of the step
    failed = run(admin, form, ids, request_id=(rid2 := uid()))
    assert failed["ai"]["status"] == "failed"
    replay = create(admin, form, ids, request_id=rid2)
    assert replay.status_code == 200 and replay.json() == failed
    assert len(listing(admin, "?limit=50")["items"]) == 2


def test_adm03_ac19_two_different_submits_at_once_give_one_201_and_one_409(admin, llm):
    import threading
    form, ids = text_form(admin, 3)
    llm.gate = threading.Event()
    futures = [POOL.submit(create, admin, form, ids) for _ in range(2)]
    replies = settle(llm, futures, lambda: any(f.done() for f in futures))
    codes = sorted(r.status_code for r in replies)
    assert codes == [201, 409], [r.text for r in replies]
    loser = next(r for r in replies if r.status_code == 409)
    d = expect(loser, 409, "analysis_in_progress")
    assert IN_PROGRESS.fullmatch(d["message"]), d["message"]
    assert len(listing(admin)["items"]) == 1
    winner = next(r for r in replies if r.status_code == 201)
    wait_done(admin, winner.json()["id"])
    assert len(llm.of("reduce")) == 1
    assert create(admin, form, ids).status_code == 201  # the slot is free again


def test_adm03_ac19_a_second_submit_while_the_first_runs_is_409_and_creates_nothing(admin, llm):
    form, ids = text_form(admin, 3)
    fut, aid = start_blocked(admin, llm, form, ids)
    calls = len(llm.calls)
    d = expect(create(admin, form, ids), 409, "analysis_in_progress")
    assert IN_PROGRESS.fullmatch(d["message"]) and len(listing(admin)["items"]) == 1
    release(llm, fut)
    assert len(llm.calls) >= calls
    wait_done(admin, aid)


def test_adm03_ac19_the_limit_is_per_admin_not_global(admin, other_admin, llm):
    form, ids = text_form(admin, 3)
    form2, ids2 = text_form(other_admin, 3)
    fut, aid = start_blocked(admin, llm, form, ids)
    second = POOL.submit(create, other_admin, form2, ids2)
    end = time.monotonic() + 20
    while not listing(other_admin)["items"] and time.monotonic() < end:
        time.sleep(0.05)
    assert [i["ai_status"] for i in listing(other_admin)["items"]] == ["running"]
    release(llm, fut)
    assert second.result(60).status_code == 201
    wait_done(admin, aid)


def test_adm03_ac23_create_returns_running_with_progress_and_reads_show_it_advance(admin, llm):
    form, ids = text_form(admin, 65)
    fut, aid = start_blocked(admin, llm, form, ids)
    live = get(admin, aid).json()["ai"]
    assert live["status"] == "running" and live["result"] is None and live["error"] is None
    assert live["progress"]["done"] == 0 and live["progress"]["total"] == 4
    assert live["progress"]["step"] == {"kind": "batch", "index": 1, "total": 3}
    release(llm, fut)
    done = wait_done(admin, aid)
    assert done["ai"]["progress"]["done"] == 4 and done["ai"]["status"] == "complete"


def test_adm03_ac23_running_over_780_s_reads_as_interrupted_and_a_late_write_does_not_revive_it(admin, llm):
    form, ids = text_form(admin, 3)
    fut, aid = start_blocked(admin, llm, form, ids)
    before = get(admin, aid).json()
    sql("UPDATE feedback_analyses SET created_at = now() - interval '900 seconds' WHERE id=%s", (aid,))
    swept = get(admin, aid).json()
    err = swept["ai"]["error"]
    assert swept["ai"]["status"] == "failed" and err["code"] == "analysis_interrupted" and swept["ai"]["result"] is None
    m = INTERRUPTED.fullmatch(err["message"])
    assert m and int(m.group(1)) >= 900 and int(m.group(2)) == 0 and int(m.group(3)) == 2, err["message"]
    assert err["details"]["ran_seconds"] >= 900 and err["details"]["done"] == 0 and err["details"]["total"] == 2
    assert swept["aggregates"] == before["aggregates"]
    release(llm, fut)  # the job completes its calls and attempts its conditional writes
    time.sleep(1.0)
    after = get(admin, aid).json()
    assert after["ai"] == swept["ai"] and after["aggregates"] == swept["aggregates"]
    assert listing(admin)["items"][0]["ai_status"] == "failed" and row_count(aid) == 1


def test_adm03_ac23_sweeping_frees_the_slot_for_a_new_analysis(admin, llm):
    form, ids = text_form(admin, 3)
    fut, aid = start_blocked(admin, llm, form, ids)
    sql("UPDATE feedback_analyses SET created_at = now() - interval '900 seconds' WHERE id=%s", (aid,))
    nxt = create(admin, form, ids)  # POST itself sweeps stale rows first; the gate is still held
    assert nxt.status_code == 201, nxt.text
    llm.gate.set()  # now both jobs run; the first one's late conditional writes must change nothing
    fut.result(60)
    assert wait_done(admin, nxt.json()["id"])["ai"]["status"] == "complete"
    assert get(admin, aid).json()["ai"]["error"]["code"] == "analysis_interrupted"


def test_adm03_ac19_31_burst_of_distinct_submits_is_only_201_or_409_and_rows_match(admin, llm):
    """The job fails at once, so the running row may end between the insert attempt and the follow-up lookup."""
    import llm_client

    def rows():
        return sql("SELECT count(*) FROM feedback_analyses WHERE admin_id=%s", (str(admin),))[0][0]
    form, ids = text_form(admin, 2)
    llm.script = {n: llm_client.LlmNotConfigured("x") for n in range(1, 400)}
    for _ in range(10):
        before = rows()
        futures = [POOL.submit(create, admin, form, ids) for _ in range(8)]
        replies = [f.result(60) for f in futures]
        created_ok = [r for r in replies if r.status_code == 201]
        for r in replies:
            assert r.status_code in (201, 409), (r.status_code, r.text)
            if r.status_code == 409:
                assert r.json()["detail"]["code"] == "analysis_in_progress"
        assert created_ok, [r.text for r in replies]
        for r in created_ok:
            wait_done(admin, r.json()["id"])
        assert rows() - before == len(created_ok)
        assert len({r.json()["id"] for r in created_ok}) == len(created_ok)
