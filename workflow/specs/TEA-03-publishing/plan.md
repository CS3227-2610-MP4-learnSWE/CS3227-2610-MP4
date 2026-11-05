# Plan: TEA-03 publishing preparation

Approved preparation only, based on clean master db82a18 (PR17). No database, backend API or student implementation changes.

1. Audit current teacher docs against implemented uploads, generation, editing, deletion and auth. Record discrepancies and PR17 merge state.
2. Replace TEA-04 assembly stories with batch publication requirements; preserve story IDs for traceability. Cross-reference the explicit publication workflow in US-TEA-03-04. Label future requirements and historical scope clearly.
3. Before UI changes, add browser regressions: no teacher assembly navigation/builder; old teacher practice URL redirects and refreshes; studio shows exact batch publication notice and no working Publish action; student Practice navigation remains available.
4. Remove the unused PracticeSets component and selection-only imports; remove its teacher sidebar entry, retain legacy-route redirect. Add the exact notice from spec.md to the existing MCQ studio.
5. Document compatibility: student practice currently uses fixed intro-se-1/server fixtures, string choice IDs and in-memory attempts. Publishing will require a server mapping and student discovery/version integration; do not alter those contracts during preparation.
6. Run frontend types/lint/format/build and full mocked browser suite, including student/practice/companion regressions. Confirm no backend/student runtime diff. Independent read-only review, then local commit; no push/PR/merge.

This is the repository's small docs/preview-cleanup single-session exception, not the publishing feature implementation. The latter requires a complete approved contract and Variant B before source changes. Current user request authorizes these preparation changes without another approval question.


## Data model

Preparation adds none. STU-01 now provides published_lesson and lesson_completion. Future notes publishing must reuse them; new migrations follow20261104_stu01_lessons. No migration is executed during merge resolution.

## API endpoints

No new preparation API. Legacy frontend /teacher/practice redirects to /teacher/generate?tab=questions. Existing teacher APIs and merged /api/study endpoints are retained; the future publishing contract remains pending.

## Components and modules

Teacher.tsx removes the obsolete builder, data.ts removes only its teacher navigation, TeacherMcqs.tsx shows the scope notice. Existing role guards, studio hooks and student modules remain. Future notes work reuses study_lessons.publish_lesson with teacher access/transaction checks.

## UI contract

- Requests per load and per retry: redirect adds none. Signed-in studio loads courses once then materials and saved batches once each; selected batch adds one detail GET. Course retry repeats one GET, resources retry two, detail retry one. Auth/health requests are separate; anonymous teacher data issues zero teacher requests.
- Wrong role: RequireRole redirects signed-in students/admins to their home. Anonymous demo sees `Sign in to manage teacher materials and drafts.`; demo-off goes to login.
- Link history: push or replace: legacy redirect replaces; ordinary studio links retain existing push/blocker behaviour.
- Refresh: redirected URL reloads the questions studio and persisted drafts. No builder state remains.
- Back and Forward: no legacy redirect loop; existing studio dirty guards apply.
- Expired session or logout: existing flow clears protected state and redirects to login; failed logout retains editor.
- Backend down: existing `Could not load courses. Please try again.` or `Could not load sources and saved drafts. Please try again.` alerts retain Retry controls.
- Longest wait before an error: existing10second requests and45second generation; redirect/notice adds no request.
- No generic failure message: no new error path; existing safe teacher messages/recovery remain unchanged.

## Test plan

Browser regressions check removed teacher builder/navigation, legacy redirect/refresh, exact notice and retained student Practice navigation. Full frontend suite plus types/lint/format/build verifies auto-merges. Speccheck and unit tests verify template compatibility. Backend tests use isolated PostgreSQL schemas only, never developer data.
