# Merge master into publication preparation — 2026-11-05

User had already started merging master5d2b23d (PR19, including STU-01 PR18) into feat/tea03-publish-content at6cbd5ef. Two unmerged files: workflow/notes.md and workflow/experiments/resource-log.md. Both sides retained; newest ten handoffs remain live and older ones archived. One identical archived entry was deduplicated without removing unique history.

Preserved incoming live student lessons/completion, session-scoped request handling, migration20261104_stu01_lessons and spec checker. Preserved this branch's removed assembly screen/sidebar, legacy redirect, three-question batch scope and existing test adaptation. No runtime implementation was manually changed by conflict resolution.

Semantic integration: checker initially rejected our pre-checker preparation files. Added required sections, AC checkboxes, owner roles, UI-state table and explicit labels without waiving checks or changing behaviour. Speccheck --all passes (3checked,0failed,12pre-existingwaivers); checker289unit tests pass. One documentation-edit command initially used the wrong working directory; it failed before any file was written and was rerun with absolute paths.

STU-01 introduces published_lesson, study_lessons.publish_lesson and /api/study. Recorded that the future teacher publishing plan must reuse these, chain migrations after the new head and retain the chosen one-publication/no-withdrawal teacher scope. The earlier plan to create another note-publication store must be revised; publishing implementation has not started. Current student practice fixture/attempt integration remains separate.

Types, lint, format and frontend build passed. Full backend tests use isolated schemas in the existing PostgreSQL16 test container, not developer data; full browser suite running. No .env, developer database, real AI calls, push, PR or deployment touched. This mechanical merge/docs integration uses the single-session workflow exception.

Final merge verification:855backend tests passed (188.56s) using isolated PostgreSQL16 schemas;352browser tests passed (3.0m). Types/lint/format/build, speccheck --all and289checker unit tests passed. No runtime fix or test relaxation was required. Incoming historical flake notes are retained but no such failure occurred in this run.

Token tracker attempted branch report; no attributable requests, actual tokens/cost unavailable rather than zero usage. Summary workflow/experiments/results/merge-master-publishing-20261105.csv. Conflict-resolution rounds0; template-format adjustments do not implement publishing.
