# 2026-11-03 — Local merge, doc/code consistency check and PR preparation — isaac

Branch: `chore/workflow-cleanup-and-refactor`. Model: Claude Sonnet 5.5.

## Follow-ups approved by the user
- Merge `request` and `requestTeacher` in `client.ts` (branch `refactor/r5-client-transport`): yes.
- Move the generation error mapping to `llm_errors.py` (branch `refactor/r4-llm-errors`): yes.
- Port 8000 in the backend start commands: "ok", read as leave unchanged.
- The ADM-06 pilot retro waits until ADM-06 starts: ok.
Both code follow-ups were tested before being merged (backend 483; frontend typecheck, lint and mocked browser suite 155).

## Local merge
Merged `refactor/r1` to `r5` into the chore branch with `--no-ff`, in order. One conflict, R2 against R4, in the imports of `teacher_notes/generation.py`; resolved by keeping both changes. My earlier remark that these would merge cleanly was wrong for that file. Combined result: backend 488 passed (database-backed tests run against a throwaway Postgres container, since stopped), typecheck and lint clean, mocked browser suite 155 passed. The two greps (no `from teacher_materials.routes import _`, no `from practice_routes import require_student`) find nothing. Not pushed after the merge.

## Do the specs and docs match the code?
The user asked whether specs matched the code. I had not checked; checking found stale references after the refactors:
- `docs/SharedDataContract.md`: said `require_teacher` enforces the gate; now names `require_demo_enabled`, `teacher_session`, `owned_material`, `parse_uuid`, `utc_timestamp`.
- `docs/DeveloperGuide.md`: text-validation paragraph now names `normalise_newlines_and_trim` and `llm_errors.generation_error`; the backend module list now says `student_identity` holds the header check.
- `workflow/specs/STU-03/plan.md`: two references to `practice_routes.require_student` now point to `student_identity.require_student` with a note.
Commits: `docs: update contract, guide and STU-03 plan for the moved helpers`, plus a follow-up for the DeveloperGuide module list.

Second pass (what I had not checked): searched `docs/`, `workflow/specs/`, READMEs and workflow files for the file names, rule files and port variable I touched. Remaining hits are accurate: the TEA specs only cite error codes, `API_PORT` and `.env.example` references match the current files, and the archive holds historical text on purpose. Not done: a line-by-line read of every guide, and no live GitHub CI run.

## Limits
- `gh` is not installed, so the PR is opened by the user from the branch link.
