# Baseline run (single session, no subagents): run record

- Branch `claude/stu02-run-baseline-e1c0af`, start commit `70ab114` plus the baseline switch `464ecf4` (agent files removed), final commit `63e2091`. Session `local_a5eab133`, sonnet. The main project folder was on the baseline branch at start, so no subagent definitions were loaded.
- Hidden grader: 18/18. Own tests: 32/32 (4 existing, 28 STU-02).
- Revision rounds: 0 (self-review fixed one defect: concurrent double submit, now atomic in the store).
- Cost by session: 0.52 USD over 14 requests, about 3 minutes wall time. Cross-checked by worktree folder: the same 14 requests, one session.
- Interventions: 0.
- Process deviations: code and tests in a single commit, so git history does not show tests first (the session reports writing tests first and seeing 28 fail); self-review is not independent; no resource-log row on the run branch.
