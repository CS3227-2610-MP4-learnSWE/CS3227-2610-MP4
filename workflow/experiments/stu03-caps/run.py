"""Runner for the STU-03 cap experiments (standard library only).

Dry run (default): uses a fake LLM, makes no network call and needs no key.
Live run: needs --live and SOCLAAS_* in .env or the environment. The key is read only to
build the Authorization header; it is never printed, logged or written to results.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases  # noqa: E402
import rules  # noqa: E402
RESULTS = HERE / "results"
BUDGET_FILE = RESULTS / "_live_calls.txt"
RATE_HEADER_WORDS = ("ratelimit", "rate-limit", "retry-after", "x-request-id")


def load_env() -> None:
    for path in (HERE / ".env", HERE.parents[2] / ".env"):
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"'))


def messages_for(case: dict) -> list[dict]:
    system = cases.SYSTEM[case["mode"]] + (cases.BRIEF if case.get("style") == "brief" else "")
    msgs = [{"role": "system", "content": system}]
    msgs += [{"role": r, "content": c} for r, c in case.get("history", [])]
    msgs.append({"role": "user", "content": case["user"]})
    return msgs


class Fake:
    """Deterministic stand-in: ~4 characters per token, honours max_tokens."""

    def chat(self, msgs, max_tokens):
        text = "Think about what the question is really asking. " * 12
        prompt_tokens = sum(len(m["content"]) for m in msgs) // 4
        completion = min(len(text) // 4, max_tokens)
        return dict(http=200, latency_s=0.0, usage=dict(prompt_tokens=prompt_tokens, completion_tokens=completion),
                    finish_reason="length" if len(text) // 4 > max_tokens else "stop", reply=text[: completion * 4], headers={})

    def models(self):
        return dict(http=200, latency_s=0.0, body=["fake-model"], headers={})


class Live:
    def __init__(self, max_calls: int):
        load_env()
        self.base = os.environ["SOCLAAS_BASE_URL"].rstrip("/")
        self.model = os.environ.get("SOCLAAS_MODEL", "default")
        self._key = os.environ["SOCLAAS_API_KEY"]
        self.max_calls = max_calls

    def _count(self) -> None:
        RESULTS.mkdir(exist_ok=True)
        n = int(BUDGET_FILE.read_text()) if BUDGET_FILE.exists() else 0
        if n >= self.max_calls:
            raise SystemExit(f"Call budget of {self.max_calls} reached; stopping.")
        BUDGET_FILE.write_text(str(n + 1))

    def _send(self, req):
        self._count()
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read(), dict(r.headers), time.monotonic() - start
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers), time.monotonic() - start
        except (urllib.error.URLError, TimeoutError) as e:
            return 0, str(e.__class__.__name__).encode(), {}, time.monotonic() - start

    @staticmethod
    def _rate_headers(h: dict) -> dict:
        return {k: v for k, v in h.items() if any(w in k.lower() for w in RATE_HEADER_WORDS)}

    def _request(self, path, body=None):
        req = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"})
        return self._send(req)

    def models(self):
        status, raw, headers, dt = self._request("/models")
        try:
            ids = [m.get("id") for m in json.loads(raw).get("data", [])]
        except ValueError:
            ids = []
        return dict(http=status, latency_s=round(dt, 3), body=ids, headers=self._rate_headers(headers))

    def chat(self, msgs, max_tokens):
        status, raw, headers, dt = self._request("/chat/completions", dict(model=self.model, messages=msgs, max_tokens=max_tokens))
        out = dict(http=status, latency_s=round(dt, 3), headers=self._rate_headers(headers), usage=None, finish_reason=None, reply=None)
        try:
            data = json.loads(raw)
            if status == 200:
                choice = data["choices"][0]
                out.update(usage=data.get("usage"), finish_reason=choice.get("finish_reason"), reply=choice["message"]["content"])
            else:
                out["error"] = str(data.get("error", data))[:300]
        except (ValueError, KeyError, IndexError):
            out["error"] = raw[:200].decode("utf-8", "replace")
        return out


def record(phase: str, case_id: str, mode: str, cap: int, res: dict, extra: dict | None = None) -> None:
    RESULTS.mkdir(exist_ok=True)
    row = dict(phase=phase, id=case_id, mode=mode, max_tokens=cap, **res, **(extra or {}))
    with open(RESULTS / f"{phase}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    u = res.get("usage") or {}
    print(f"{case_id}: http={res['http']} in={u.get('prompt_tokens')} out={u.get('completion_tokens')} "
          f"finish={res.get('finish_reason')} {res['latency_s']}s")


def leak_suspected(case: dict, reply: str | None) -> bool | None:
    if not reply or not case.get("q"):
        return None
    q = case["q"]
    low = reply.lower()
    return correct_text(q).lower() in low or f"answer is {q['correct']}" in low or f"option {q['correct']} " in low


def correct_text(q):
    return cases.correct_text(q)


def run_cases(client, phase, case_list, cap):
    for c in case_list:
        res = client.chat(messages_for(c), cap)
        record(phase, c["id"], c["mode"], cap, res, dict(input_chars=len(c["user"]), history_msgs=len(c.get("history", [])),
                                                         leak_suspected=leak_suspected(c, res.get("reply"))))


def phase1(client):
    m = client.models()
    record("phase1", "models", "-", 0, dict(http=m["http"], latency_s=m["latency_s"], headers=m["headers"], models=m["body"]))
    tiny = dict(id="tiny", mode="help", user="Reply with the single word: ok", history=[])
    run_cases(client, "phase1", [tiny], 5)


def phase6(client, delay: float):
    """Factorial sweep. Resumable (skips ids already recorded); stops at the first 429."""
    path = RESULTS / "phase6.jsonl"
    done = {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line} if path.exists() else set()
    todo = [c for c in cases.phase6_cases() if c["id"] not in done]
    print(f"{len(done)} done, {len(todo)} to run")
    for c in todo:
        res = client.chat(messages_for(c), c["cap"])
        record("phase6", c["id"], c["mode"], c["cap"], res,
               dict(style=c["style"], history_msgs=len(c["history"]), question=c["key"],
                    useful=rules.useful(c, res),
                    options_discussed=rules.options_discussed(c["q"], (res.get("reply") or "").lower()) if c["mode"] == "hint" else None))
        if res["http"] == 429:
            print("429 seen; stopping. Re-run to resume after a pause.")
            return
        time.sleep(delay)


def phase5(client):
    for i in range(10):
        res = client.chat(messages_for(dict(mode="help", user="Say ok", history=[])), 5)
        record("phase5", f"burst-{i + 1}", "help", 5, res)
        if res["http"] == 429:
            print("429 seen; stopping the burst.")
            break


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["1", "2", "3", "4", "5", "6", "7"])
    ap.add_argument("--delay", type=float, default=0.3, help="pause between calls in phase 6 (seconds)")
    ap.add_argument("--live", action="store_true", help="make real calls (default: fake, no network)")
    ap.add_argument("--max-calls", type=int, default=100, help="hard cap on live calls across all phases")
    a = ap.parse_args()
    global RESULTS, BUDGET_FILE
    RESULTS = HERE / ("results" if a.live else "results-dry")
    BUDGET_FILE = RESULTS / "_live_calls.txt"
    client = Live(a.max_calls) if a.live else Fake()
    print("LIVE" if a.live else "DRY RUN (fake, no network)")
    if a.phase == "1":
        phase1(client)
    elif a.phase == "2":
        run_cases(client, "phase2", cases.phase2_cases(), 800)
    elif a.phase == "3":
        run_cases(client, "phase3", cases.phase3_cases(), 300)
    elif a.phase == "4":
        run_cases(client, "phase4", cases.phase4_cases(), 300)
    elif a.phase == "5":
        phase5(client)
    elif a.phase == "7":
        run_cases(client, "phase7", cases.phase7_cases(), 150)
    else:
        phase6(client, a.delay)


if __name__ == "__main__":
    main()
