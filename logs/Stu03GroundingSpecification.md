# STU-03 lesson grounding: specification (Phase 1)

Date: 2026-11-09
Branch: `claude/stu03-lesson-grounding-5ac797` (local commit only; not pushed, no pull request)

## Work completed

- Read the project rules, the STU-03 spec/plan/tasks, the STU-02 set-provider pattern, the companion backend (`companion_routes.py`, `companion_service.py`, `companion_prompts.py`), `study_lessons/` access helpers and the widget `StudyCompanion.tsx`.
- Wrote `workflow/specs/STU-03-grounding/spec.md`, `plan.md` and `tasks.md` (draft). Speccheck: `OK STU-03-grounding`.
- Updated `workflow/notes.md`, `workflow/STATUS.md` and `workflow/experiments/resource-log.md`.

## Findings

- The companion never reads lesson content today; only practice questions and the fixed help text reach the model.
- The STU-03 plan still describes an `X-Student-Id` header; the code uses the signed-in session. The new plan follows the code.
- Teacher MCQs are written from the same lessons, so a choice-text leak check in lesson replies would withhold normal explanations; the draft proposes letters and verdicts only (open question 3).

## Not done

- No application code, tests, user guide or developer guide changes. `docs/FeatureList.md` line 25 and `docs/UserStories.md` US-STU-03-05 last bullet are reworded in Phase 2, once built.
- Chat history persistence across reload (US-STU-03-04) is left out of scope and flagged as a separate decision.
- Awaiting the user's approval and answers to open questions 1 to 8 before any build.
