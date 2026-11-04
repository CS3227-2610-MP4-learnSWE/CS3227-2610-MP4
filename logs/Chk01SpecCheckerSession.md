# CHK-01 spec checker session, 2026-11-04

Started from another session. Goal: enforce the spec-writer rules (UI states table, UI contract, three added items) with a script, a CI step and a coordination gate.

What happened, in order: spec-writer wrote a narrow spec; the user asked whether everything the agents ask for could be enforced and chose the full, table-driven scope; the user approved the revised spec; the spec was committed (d4dbd42) and the test-designer (own worktree) and developer started together. The first merged run gave 267 tests, 7 failing: three list-rules output format (plan wording, clarified), one README word, one test that wrongly treated UI contract rules as Tier 1, one sub-heading case the plan did not decide. These were fixed in tests or plan, not by weakening logic. Verifier round 1: heading regex quadratic (blocking), plus performance, blank line after a label, BOM, spelling, path items. Fixed, 286 tests. Verifier round 2: the path fix followed links (blocking, introduced by me). The user approved a one-line fix and a link test; 289 tests pass. No third verifier review.

Decisions made by me as orchestrator, not by the user: blank lines after heading/bold labels are skipped; `normali[sz]`; content caps documented. Flagged for confirmation in notes.md.

Not done or not verified: CI job not run on GitHub; no real STU-01 spec checked; AGENTS.md verifier line left for the user; nothing pushed, no PR. The deck was built with pptxgenjs (installed with the user's OK into the scratch folder) and rendered through PowerPoint to check layout.

Usage (tracker, list prices): about $9.73 for 189 requests before the last fix and deck. See resource-log.md.
