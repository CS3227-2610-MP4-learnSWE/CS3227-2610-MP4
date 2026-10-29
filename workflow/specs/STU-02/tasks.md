# Tasks: STU-02 Practice attempt API (server-side core)

Same task list for every workflow variant; who does what depends on the variant.

| # | Task | Depends on |
|---|---|---|
| 1 | Tests for AC1-AC11 from the spec and plan contract, including adversarial answer-leakage and cross-student cases | spec + plan |
| 2 | Implement the fixture, schemas, store, scoring and routes per the contract; wire into `main.py` | spec + plan |
| 3 | Run the full backend suite (`uv run pytest -q` in `src/backend`) | 1, 2 |
| 4 | Review the change against the spec; check for answer leakage and ownership gaps | 3 |
| 5 | Fix any defects (at most 2 rounds) | 3, 4 |
