# Phase 2 runner

Runs the backend half of "Phase 2, verify" without an agent: merges the run branch into the test-designer's worktree, runs pytest and writes a compact report.

```powershell
python workflow/tools/phase2/phase2.py RUN_BRANCH TEST_WORKTREE PYTHON [--out DIR]
```

- `RUN_BRANCH`: the developer's run branch. `TEST_WORKTREE`: the test-designer's worktree (the script merges into it). `PYTHON`: the interpreter that has the backend dependencies (on machines where `uv run` is blocked in new folders, use the main folder's `.venv` interpreter). `--out`: where the report goes (default: the worktree).
- Needs the test database variable used by the backend tests (for example `TEA01_TEST_DATABASE_URL`).
- Writes `phase2-report.md`, `phase2-report.json` and `phase2-junit.xml`. Exit code 0: all tests pass; 1: some fail; 2: merge failed or pytest produced no JUnit file.
- It never edits a test. Failure hints ("possible contract mismatch" or "possible logic bug") are keyword matches only, not a diagnosis.
- Backend only. It does not run `npm test`; the test-designer still runs frontend suites.
- The full backend suite can take about 30 minutes. Run it in the background and wait for the completion notification; do not poll.
- Tests: `python -m pytest workflow/tools/phase2 -q` (parser only; no database needed).

Why it exists and the evidence: `workflow/experiments/results/adm01-phase2-script.md`.
