"""STU-03 gap tests, written AFTER reading the implementation (practice_data.PRACTICE_SETS,
the real SoclaasClient wired to a MockTransport). They cover two items phase 1 could not
test from the contract alone."""
import httpx
import llm_client
import practice_data
from companion_helpers import (
    CORRECT,
    EXPLANATIONS,
    SET_ID,
    FakeLlm,
    ask,
    code_of,
    install,
    new_student,
    save,
    start,
    submit,
    uninstall,
)
from llm_client import Limits, Settings, SoclaasClient
from main import app

OTHER_Q = "Which keyword starts a function definition in Python?"
OTHER_CHOICES = ("Zebra keyword alpha", "Zebra keyword beta")
OTHER_EXPL = "Because OTHER-SET-EXPLANATION-TEXT says so."


def other_set():
    q = practice_data.Question(
        id="z1",
        text=OTHER_Q,
        code=None,
        choices=(("a", OTHER_CHOICES[0]), ("b", OTHER_CHOICES[1])),
        correct="a",
        explanation=OTHER_EXPL,
    )
    return practice_data.PracticeSet(id="other-set-1", title="Other", questions=(q,))


def test_stu03_ac7_post_impl_pasted_question_of_another_set_forces_hint_in_explain(monkeypatch):
    monkeypatch.setitem(practice_data.PRACTICE_SETS, "other-set-1", other_set())
    fake = FakeLlm()
    install(fake)
    try:
        s = new_student()
        aid = start(s)
        save(aid, s, CORRECT)
        submit(aid, s)
        r = ask(s, OTHER_Q, page="practice", set_id=SET_ID, attempt_id=aid)
        assert r.status_code == 200, r.text
        assert r.json()["mode"] == "hint"
        text = fake.last.all_text
        assert OTHER_Q in text
        assert fake.last.max_tokens == 100
        for secret in (*OTHER_CHOICES, OTHER_EXPL, *EXPLANATIONS):
            assert secret not in text
        # a plain follow-up on the same attempt is still explain
        assert ask(s, "why?", page="practice", attempt_id=aid).json()["mode"] == "explain"
    finally:
        uninstall()


def test_stu03_ac15_post_impl_rejected_requests_do_not_use_up_the_real_limiter():
    hits = []

    def handler(request):
        hits.append(1)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Think about it."}}]})

    client = SoclaasClient(
        Settings("https://llm.test/v1", "sk-test-sentinel", "m"),
        limits=Limits(per_caller_per_minute=2),
        transport=httpx.MockTransport(handler),
        clock=lambda: 0.0,
        sleep=lambda s: None,
    )
    app.dependency_overrides[llm_client.get_llm_client] = lambda: client
    try:
        s = new_student()
        for _ in range(5):
            assert code_of(ask(s, "   ")) == "invalid_message"
            assert code_of(ask(s, "x", history=[{"role": "system", "text": "x"}])) == "invalid_history"
            assert code_of(ask(s, "x", page="practice", attempt_id="nope")) == "attempt_not_found"
        assert hits == []
        assert ask(s, "hello").status_code == 200
        assert ask(s, "hello again").status_code == 200
        r = ask(s, "third")
        assert r.status_code == 429 and code_of(r) == "rate_limited"
        assert len(hits) == 2
    finally:
        app.dependency_overrides.pop(llm_client.get_llm_client, None)
