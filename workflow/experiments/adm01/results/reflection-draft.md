# Reflection draft (not added to docs/Reflections.md; needs G5 approval)

- Question: do three agent-setup changes (cheaper model, context allowlist, structured verifier input) cut the cost of building ADM-01 without lowering quality?
- Result: no. All three cost 54-78% more than the unchanged baseline, and all exceeded the 1.5x cap. One run each, so the quality evidence is weak.
- Why: not established. Possible factors (untested): the H arms ran their own Postgres and used one revision round while A used none. A cheaper per-request model (H3) did not give lower total cost.
- Lesson on measurement: a frozen suite can have false positives (AC11) and gaps (H2's AC9 defect). Using both a suite and a blind review caught different defects.
- Lesson on process: arms should have been given the same database; this confound makes cost comparison unfair to A's quality and to H's cost.
- Not concluded: whether C (single session) is cheaper; not run.
