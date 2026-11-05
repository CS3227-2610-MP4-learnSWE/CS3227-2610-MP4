# 2026-11-06 — ADM-01 workflow experiment: grading and results — isaac

Branch: `exp/adm01-coord`. Model: Claude Sonnet 5.5 (coordinator); verifiers via the `verifier` agent. Reasoning setting not exposed.

## What happened
- Resumed from `state.json` (phase 4). Postgres `adm01-pg` was already running on 127.0.0.1:55432.
- First frozen-suite grading failed nearly all tests: wrong URL scheme (`postgresql://`); the app needs `postgresql+psycopg://`. Reran.
- Result v1: A 151, H3 153, H1 152, H2 152 of 153. The AC11 test false-positive (case-insensitive `\bUPDATE\b` matched `counts.update(...)`). With USER approval, fixed in suite v2 (`exp/adm01-frozen` d8da50d; two edit attempts failed on backslash handling before it applied) and re-graded: A 152, H1/H2/H3 153.
- Blind Q2 on H3, H2, H1 (x1-x3), then A (x4) with USER approval: H3, H1, A PASS; H2 NOT PASS (AC9 outcome event missing when content read fails). Verifiers did not run the suite.
- Comparison: all H arms capped and +54% to +78% vs A, so reject; C not run. USER chose the strict cap rule by saying to continue.
- Wrote results/review-pack.md, try-it.md, reflection-draft.md, comparison.html; resource-log row; notes.md handoff.

## Not done
- No push, no PR, nothing added to docs/Reflections.md or STATUS.md (G5 pending). Worktrees x1-x4 and container remain.
