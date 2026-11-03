# Merge master into PostgreSQL storage branch — 2026-11-03

User requested merging master into the current branch. Clean working tree confirmed on fix/teacher-postgres-file-storage at644108a. Local master and origin/master both pointed toda389a5 (PR14); no fetch/push or master checkout/update performed.

Resolved conflicts in README, SharedDataContract, material/note/MCQ routes and handoff notes. Preserved master's shared teacher_access/timestamps/normalisation/error mapping and frontend send transport. Applied BYTEA storage changes to those shared callers; teacher_access no longer checks filesystem storage and explicitly uses READ COMMITTED for concurrent quota accounting. No shared LLM-client changes. Historical notes retained/archived under the new10-entry rule; feature status updated.

Verification:504backend tests passed using an isolated PostgreSQL schema/temp test data.159browser tests, frontend types/lint/format/build and whitespace checks passed. Initial backend attempt found Docker stopped; started Docker Desktop and existing learnswe-tea01-test then reran successfully. No developer database/upload files/.env or live LLM used. Single-session merge resolution; no new feature/test design. Tracker not run, inherited Codex model, token/cost totals unavailable. No push, PR, production deployment or optional real-backend browser verification.
