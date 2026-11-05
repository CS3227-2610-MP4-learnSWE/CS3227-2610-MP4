# TRK-02 invocation usage reports

Date: 2026-11-05  
Branch: `feat/token-tracker-invocation-report`

## Work completed

- Added the TRK-02 spec, plan and tasks for feature-run usage reports.
- Wrote and committed the tests before implementing the report code.
- Added a manifest reader, per-invocation attribution and Markdown report generation to the token tracker.
- Updated tracker and workflow docs to record every multi-agent feature run under `workflow/usage/runs/<feature-run-id>/`.
- Kept existing `export`, aggregate `report`, A/B/C experiment files and local raw CSV behavior unchanged.

## Verification

- `python -m speccheck ../../specs/TRK-02`: passed.
- `python -m unittest discover -s tests` from `workflow/tools/token-tracker`: 37 passed.
- `git diff --check`: passed.
- Existing tracker branch report: 50 requests; 81,316 uncached input tokens, 9,427,712 cache-read tokens, 49,522 output tokens and 23,203 reasoning tokens. The reasoning count is included in output. No cache-write tokens were recorded. Cost was unavailable because the local price table is empty.

The tests use synthetic logs; no real provider logs or prompts were committed. This implementation was completed in one session, so there was no independent test-designer worktree or verifier pass.

## How to use it

Create `workflow/usage/runs/<feature-run-id>/invocations.csv` from `workflow/usage/templates/invocations.csv`, add one row per agent start, then run `python -m tracker run-report --manifest <manifest-path>` from `workflow/tools/token-tracker`. The generated `report.md` has separate rows for repeated roles and one feature-run total. The details are in `workflow/usage/README.md`.
