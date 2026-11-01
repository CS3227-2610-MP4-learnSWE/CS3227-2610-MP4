"""Shared helpers for the STU-03 companion tests (contract: workflow/specs/STU-03/plan.md).

A FakeLlm replaces the shared client through
app.dependency_overrides[llm_client.get_llm_client]; it records every call and
never touches the network or a key.
"""
import asyncio
import threading
import uuid
from dataclasses import dataclass

import httpx
import llm_client
from llm_client import LlmReply
from main import app

SET_ID = "intro-se-1"
URL = "/api/companion/messages"
CANNED = (
    "I can't share or confirm answers while this practice set is open. "
    "Tell me what you have tried and which idea is unclear, and I will give you a hint."
)
CORRECT = {"q1": "a", "q2": "b", "q3": "c"}
WRONG = {"q1": "b", "q2": "a", "q3": "a"}

QUESTION_TEXTS = [
    "What should a well-designed function have?",
    "Why do we keep automated tests alongside our code?",
    "What does this Python code print?",
]
CODE_Q3 = "values = [1, 2, 3]\nprint(len(values))"
CHOICE_TEXTS = [
    "A single, focused responsibility",
    "As many responsibilities as possible",
    "No descriptive name",
    "To make the repository larger",
    "To catch regressions when code changes",
    "To avoid ever reviewing code",
]
EXPLANATIONS = [
    "One focused responsibility makes a function easier to understand, test and change.",
    "Tests protect expected behaviour and can catch regressions introduced by later changes.",
    "len returns the number of items. The list contains three items.",
]
BENIGN = "Think about what makes a function easy to understand and change."


@dataclass
class Call:
    messages: list
    max_tokens: int
    caller_id: str

    @property
    def all_text(self) -> str:
        return "\n".join(m.content for m in self.messages)

    @property
    def trusted_text(self) -> str:
        """The two fixed system messages (rules and server-built context)."""
        return "\n".join(m.content for m in self.messages[:2])


class FakeLlm:
    """Implements LlmClient.complete; thread safe; records calls."""

    def __init__(self, reply=BENIGN):
        self.reply = reply
        self.raises = None
        self.calls: list[Call] = []
        self.gate: threading.Event | None = None
        self.entered = threading.Event()
        self._lock = threading.Lock()

    def complete(self, messages, *, max_tokens, caller_id):
        with self._lock:
            self.calls.append(Call(list(messages), max_tokens, caller_id))
        if self.gate is not None:
            self.entered.set()
            assert self.gate.wait(15), "test gate never released"
        if self.raises is not None:
            raise self.raises
        text = self.reply(messages) if callable(self.reply) else self.reply
        return LlmReply(text=text, finish_reason="stop", prompt_tokens=10, completion_tokens=5)

    @property
    def last(self) -> Call:
        return self.calls[-1]


def install(fake) -> None:
    app.dependency_overrides[llm_client.get_llm_client] = lambda: fake


def uninstall() -> None:
    app.dependency_overrides.pop(llm_client.get_llm_client, None)


def call(method, path, student=None, json=None):
    headers = {"X-Student-Id": student} if student is not None else {}

    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            return await client.request(method, path, headers=headers, json=json)

    return asyncio.run(send())


def new_student() -> str:
    return "stu03-" + uuid.uuid4().hex


def body_of(message="hello", page="other", set_id=None, attempt_id=None, history=None,
            label=None, extra=None, context_extra=None):
    context = {"page": page, "set_id": set_id, "attempt_id": attempt_id, "label": label}
    context.update(context_extra or {})
    body = {"message": message, "history": history if history is not None else [], "context": context}
    body.update(extra or {})
    return body


def ask(student, message="hello", **kw):
    return call("POST", URL, student, body_of(message, **kw))


def code_of(r):
    return r.json()["detail"]["code"]


def start(student, set_id=SET_ID):
    r = call("POST", f"/api/practice-sets/{set_id}/attempts", student)
    assert r.status_code == 201, r.text
    return r.json()["attempt_id"]


def save(aid, student, answers):
    r = call("PUT", f"/api/attempts/{aid}/answers", student, {"answers": answers})
    assert r.status_code == 200, r.text


def submit(aid, student):
    r = call("POST", f"/api/attempts/{aid}/submit", student)
    assert r.status_code == 200, r.text


def submitted_attempt(student, answers=CORRECT):
    aid = start(student)
    save(aid, student, answers)
    submit(aid, student)
    return aid


def assert_no_key_in(text: str) -> None:
    for e in EXPLANATIONS:
        assert e not in text
    for c in CHOICE_TEXTS:
        assert c not in text
