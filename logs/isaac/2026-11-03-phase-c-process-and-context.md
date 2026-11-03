# 2026-11-03 — Phase C: process and context — isaac

Branch: `chore/workflow-cleanup-and-refactor`. Model: Claude Sonnet 5.5. One commit per task (T8–T12). Docs only; no backend or frontend suites were run.

## Commits

| Task | Commit message | Change |
|---|---|---|
| T8 | `docs: archive older handoff notes and add a feature status table (T8)` | `workflow/notes.md` keeps the newest 10 entries (74 lines); the other 175 lines moved unchanged to new `workflow/notes-archive.md`. New `workflow/STATUS.md`: one row per feature (ID, stage, branch, PR, open items), ADM-01 to ADM-06 "not started". `workflow/README.md` index lists `STATUS.md`, `notes.md` and `notes-archive.md`. |
| T9 | `docs: give the spec-writer the shared criteria and open decisions (T9)` | `AGENTS.md` (spec-writer role) and `.claude/agents/spec-writer.md`: inputs now include the "Shared acceptance criteria" (SHR-01 to SHR-05) and "Decisions to resolve before implementation" sections of `docs/UserStories.md`; relevant decisions must be listed as Open questions. |
| T10 | `docs: add admin rows to the threat model and fill the test column (T10)` | `workflow/security/threat-model.md`: five admin rows (ADM-05 self-escalation, SHR-05 raw feedback, ADM-03 prompt injection, ADM-06 key or personal data, admin quota), all "not yet" with a planned test prefix. The empty Test/Check cells of the existing rows now name an existing test or CI job, or "not yet". |
| T11 | `docs: add standing concurrency and cross-user tasks to the tasks template (T11)` | `workflow/templates/tasks.md`: tasks 6 (concurrent-request test) and 7 (cross-user test) for features that touch records; task 3 depends on them. New `workflow/templates/tasks-sample-ADM-06.md` shows them filled in. `templates/spec.md` already covers concurrency, normalisation and access, so it is unchanged. |
| T12 | `docs: make resource measurement a required handoff field (T12)` | `workflow/templates/handoff.md`: required tracker run (yes/no), model, total tokens, cost, retries and revision rounds. `workflow/experiments/resource-log.md` header and `workflow/README.md` state that a feature is not closed until its resource row exists. |

## How each was tested

- T8: a script checked that every original line of `notes.md` is in `notes.md` or `notes-archive.md` (only the extended header sentence differs), so the diff is moved text. `notes.md` is 74 lines. README index lists both new files.
- T9: dry run in a fresh `claude -p --agent spec-writer` process with Write/Edit disabled, asked for ADM-05 open questions only. Nothing was written. It listed the course-join and teacher-approval decision, the feedback retention decision and several ADM-05 questions, each with its source. The "login" decision was only partly covered (its question 9 asks how accounts are created and identified), because `docs/UserStories.md` has no explicit login item in that list.
- T10: every table row has a control and a Test/Check value (checked column counts); each named test exists in `src/backend/tests/` or `src/frontend/tests/` (grep). Admin rows are all "not yet".
- T11: read the template; the sample has both tasks with ADM-06 wording.
- T12: read the template and the two statements. The README statement is one sentence.

## Decisions that differ from the task text

- T8 said to move entries from about line 197; that would leave 28 entries and about 190 lines, contradicting "newest 10" and "under about 120 lines". I followed the 10-entry rule.
- T10: existing rows now reference tests; "Test" for process rows is the "Check" column.
- T11: the sample is `workflow/templates/tasks-sample-ADM-06.md`, not `specs/ADM-06/tasks.md`, so the spec-writer is not handed a pre-written ADM-06 folder.
- STATUS.md: STU-02 PR numbers are given as "1–5 per checklist" because the individual numbers are not recorded in the repo docs.

## Notes

- The pre-existing untracked `logs/isaac/2026-10-30-1334-orchestration-optimization.md` is not part of these commits.
- Not run: backend or frontend suites, GitHub CI.
