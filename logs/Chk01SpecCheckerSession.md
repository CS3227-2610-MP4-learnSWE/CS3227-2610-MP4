# CHK-01 spec checker session, 2026-11-04

Started from another session. Goal: enforce the spec-writer rules (UI states table, UI contract, three added items) with a script, a CI step and a coordination gate.

What happened, in order: spec-writer wrote a narrow spec; the user asked whether everything the agents ask for could be enforced and chose the full, table-driven scope; the user approved the revised spec; the spec was committed (d4dbd42) and the test-designer (own worktree) and developer started together. The first merged run gave 267 tests, 7 failing: three list-rules output format (plan wording, clarified), one README word, one test that wrongly treated UI contract rules as Tier 1, one sub-heading case the plan did not decide. These were fixed in tests or plan, not by weakening logic. Verifier round 1: heading regex quadratic (blocking), plus performance, blank line after a label, BOM, spelling, path items. Fixed, 286 tests. Verifier round 2: the path fix followed links (blocking, introduced by me). The user approved a one-line fix and a link test; 289 tests pass. A narrow verifier round 3 (2026-11-05) then passed with no regressions; it also found the documented gate command path was wrong from the tool folder (fixed to ../../specs/<id>) and that `.` inside a folder link reports the link target (README now says to give an explicit path).

Decisions made by me as orchestrator (blank lines after heading/bold labels are skipped; `normali[sz]`; content caps documented) were accepted by the user on 2026-11-05.

Not done or not verified: CI job not run on GitHub; open non-blocking verifier items (an empty heading/bold label takes the next item's text) left for a later spec revision; no real STU-01 spec checked; AGENTS.md verifier line left for the user; nothing pushed, no PR. The deck was built with pptxgenjs (installed with the user's OK into the scratch folder) and rendered through PowerPoint to check layout.

Usage (tracker, list prices): about $9.73 for 189 requests before the last fix and deck. See resource-log.md.
