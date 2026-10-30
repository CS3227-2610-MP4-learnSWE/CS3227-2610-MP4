# Tasks: STU-03 AI study companion (first slice: hint, explain, help)

Variant B. Nothing starts until the user reviews and approves `spec.md` and `plan.md`. Tasks 1 to 3 run in parallel (test-designer on tests, developer on the build); the test-designer sees only the spec and the plan contract, not `src/`.

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 0 | Review the still-open items a to j in `spec.md`; approve spec and plan (human) | user | draft | todo |
| 1 | Backend tests: route and logic tests (AC1 to AC18, AC25, AC26, error mapping, concurrency) with a fake LLM, plus unit tests for `find_match` and `find_leak` from the plan lists | test-designer | 0 | todo |
| 2 | Shared-client tests (AC19 to AC24, input ceiling) with `httpx.MockTransport` and an injected clock; no sleeping, no network | test-designer | 0 | todo |
| 3 | Frontend tests (AC27 to AC30) with a mocked companion endpoint and helper `tests/companionApi.ts`; update only the old preview-wording assertions | test-designer | 0 | todo |
| 4 | Implement `llm_client.py` (settings, limiter, retry, error classes, `get_llm_client`) and `.env.example` names; add `httpx` as runtime dependency if needed | developer | 0 | todo |
| 5 | Implement `question_match.py` and `leak_check.py` to the plan signatures and required cases | developer | 0 | todo |
| 6 | Implement the store method, schemas, prompts, help text, config, service (mode selection, assembly, history trimming) and the route; wire the router into `main.py` | developer | 4, 5 | todo |
| 7 | Frontend: client timeout option and `retryAfterSeconds`, `services/companion.ts`, `PracticeContext` exposure, `StudyCompanion.tsx` send/pending/error flow, wording | developer | 0 | todo |
| 8 | Run backend suite (`uv run pytest -q`) and frontend checks (`npm run typecheck`, `lint`, `format:check`, `test`); report pass/fail, no live calls | test-designer | 1, 2, 3, 4, 5, 6, 7 | todo |
| 9 | Docs: `docs/UserGuide.md` (what works, limits, residual leak risk), `docs/DeveloperGuide.md` (client, env names, how to fake the LLM), help text matches the guide; security cases in `workflow/security/test-log.md`; resource log | developer | 6, 7 | todo |
| 10 | Verify: code, docs and security review (key never logged, no key in non-explain contexts, ownership, check order, rendered output), re-run suites, confirm no live call in tests or CI | verifier | 8, 9 | todo |
| 11 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 10 | todo |
| 12 | Manual live check by the user with approval and a local ignored `.env`; record results in `workflow/security/test-log.md` and `logs/` | user | 11 | todo |
| 14 | Iterative live testing after verification (AC35): user-run with approval; record leaks, over-refusal and thin replies in `workflow/security/test-log.md` and `logs/`; adjust unmeasured settings only by an approved change | user, developer | 12 | todo |
| 13 | Note in the `workflow/notes.md` handoff that `llm_client.py` exists and is generic (telling the Teacher and Admin owners is the user's optional step) | developer | 4 | todo |
