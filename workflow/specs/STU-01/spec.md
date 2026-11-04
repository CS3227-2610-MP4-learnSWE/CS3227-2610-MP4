# Spec: STU-01 Study materials

Status: Draft (written 2026-11-04 for review; decisions recorded 2026-11-04; approved by the user 2026-11-04)

## Goal
From the user stories: a student browses lessons by course and topic and opens a lesson (US-STU-01-01), and marks a lesson complete or incomplete so that the change persists and updates completion totals and the progress view (US-STU-01-02).

## Behaviour
- A signed-in student sees only the courses they are a member of (`course_membership`). In each course the student sees only published lessons, grouped by topic. A lesson with no topic is grouped under "General".
- A lesson is a read-only snapshot of teacher-approved study notes: a title and plain-text content (at most 2,000 characters). It is rendered as text, never as HTML.
- On a lesson the student presses one button to mark it complete, or (if complete) incomplete. The server stores the new state in PostgreSQL. The state is per student and per lesson, survives sign-out, sign-in, browser reload and a server restart, and is read back from the server each time a page loads (nothing is kept in browser storage).
- The study materials list shows "N of M lessons complete" for the selected course. The student Overview shows the total "Lessons completed N / M" across all of the student's courses. Both are computed from the stored records and only count lessons that are currently published.
- Withdrawn lessons (withdrawn_at set) disappear from lists and totals and cannot be opened; the completion record is kept in the database.
- Drafts (`study_note_draft`) have no student endpoint. A student request for a draft id, an id of another course, or an unknown id gets the same answer as a missing lesson.
- A signed-out visitor in demo mode (`VITE_ENABLE_DEMO_ACCESS` not false) sees the sign-in notice on the materials pages instead of data. The old built-in sample lessons are removed from student code.
- Teachers and admins get 403 on every study endpoint. Teacher preview of drafts stays in the teacher pages (TEA-03).
- This feature adds no AI call.

## Acceptance criteria
Criteria AC1 to AC4 are copied from the user stories. AC5 onward are derived from them and from the shared acceptance criteria (SHR-01, SHR-04, SHR-05); the derived ones are marked.

- [ ] AC1 (US-STU-01-01): Only published lessons in courses I can access are listed and readable.
- [ ] AC2 (US-STU-01-01): Drafts and unauthorised lessons remain inaccessible through direct requests.
- [ ] AC3 (US-STU-01-02): I can mark an incomplete lesson complete and a completed lesson incomplete.
- [ ] AC4 (US-STU-01-02): Either status persists after signing in again and updates my completion totals and progress view.
- [ ] AC5 (derived, browse): The student can choose a course, filter by topic ("All topics" or one topic), search lesson titles, and open a lesson. Topics shown are those that have at least one published lesson in that course. Order is fixed by the plan.
- [ ] AC6 (derived, SHR-01): Every study endpoint rejects a request without a session (401 `unauthenticated`), with a teacher or admin session (403 `forbidden`), and an unsafe request without a valid CSRF token (403 `csrf_failed`). No identity header, query or body field is used. Order of checks is fixed by the plan.
- [ ] AC7 (derived, SHR-05): A student cannot read, list, or change completion for a lesson in a course they are not a member of, a withdrawn lesson, a draft id or a random id; all give the same 404 `not_found` body. A student cannot read another student's completion: no endpoint returns other users' records and the user is never taken from the request.
- [ ] AC8 (derived, persistence): Completion is stored in the `lesson_completion` table (not in server memory). After a new login, a new browser, or a new server process, the same status is returned.
- [ ] AC9 (derived, idempotent and concurrent): The request states the target (`completed: true|false`), so repeating it gives the same result. Two or more simultaneous requests for the same student and lesson leave exactly one row, whose state is that of one of the requests; none returns 500. Different students never affect each other.
- [ ] AC10 (derived, totals): Course and overall counts include only lessons that are published and not withdrawn in courses the student belongs to; a completed lesson that is later withdrawn stops counting without deleting the record. Marking complete then incomplete returns the counts to their earlier values.
- [ ] AC11 (derived, STU-04 contract): The completion data model and the read helpers named in the plan (`completion_counts`, `completed_lessons`) are the only supported way for STU-04 to read completion; their output follows AC10.
- [ ] AC12 (derived, safe rendering): Lesson title and content are shown as text. Content containing HTML or script tags is displayed literally and does not run. Line breaks in content are preserved.
- [ ] AC13 (derived, UI): The materials list, lesson page and Overview total show every state in "UI states and copy" below with the exact messages and accessible names in the plan's UI contract. No failure shows a raw body, stack trace or HTTP code.
- [ ] AC14 (derived, session): On 401 `unauthenticated` while signed in the app returns to `/login` (SHR-01 behaviour) and nothing is shown from the earlier session; in demo mode the sign-in notice is shown.
- [ ] AC15 (derived, migration): One additive Alembic revision after `20261103_shr01_auth` creates `published_lesson` and `lesson_completion`. Upgrade, downgrade and re-upgrade work on a fresh and on a populated schema; downgrade drops only the two new tables; no existing table or row changes.
- [ ] AC16 (derived, regression): The existing backend, mocked Playwright, typecheck, lint and format checks pass, except tests that asserted the removed built-in sample lessons (the app.spec "lesson completion is reversible and reflected in dashboard" test and the lesson outline test), which are rewritten against the new behaviour.
- [ ] AC17 (derived, docs): `docs/UserGuide.md`, `docs/DeveloperGuide.md`, `docs/SharedDataContract.md` and `workflow/security/test-log.md` describe what works and no more. The UserGuide does not claim teachers can publish lessons unless TEA-03 publication exists (see Decision 1).

## UI states and copy
Roles and names are fixed in the plan's "UI contract". Messages below are exact (straight text, including the final full stop).

Shared failure messages (used by every screen below that loads data):

| Cause | Message | Retry control |
|---|---|---|
| Backend unreachable, timeout (10 s per request) | Could not reach the server. Check your connection and try again. | button "Try again" |
| 503 `service_unavailable` or any other 5xx | Study materials are unavailable right now. Please try again. | button "Try again" |
| 200 with a body of the wrong shape (bad response) | Study materials could not be read. Please try again. | button "Try again" |
| 403 `forbidden` (the role changed after the page loaded; a teacher or admin who opens `/student/...` is redirected by the SHR-01 role guard to their own area before any request is sent) | You do not have access to study materials. | none |
| 401 `unauthenticated`, signed in | none shown; the app goes to `/login` | not applicable |
| 401 `unauthenticated`, demo mode | Sign in to read study materials and track your progress. with link "Go to sign in" to `/login` | not applicable |

| Screen or action | Control and exact label | Loading | Success | Empty | Failures and exact message | After a failed action |
|---|---|---|---|---|---|---|
| Materials list `/student/materials`, first load (courses) | Page heading level 1 "Small lessons. Lasting understanding."; native select labelled "Course"; topic buttons "All topics" and one per topic; text field "Search materials" | status "Loading study materials…" (no course select, no lessons yet) | Course select lists member courses (A to Z by title); first course selected (or the course in `?course=` if it is a member course); lessons grouped by topic; text "N of M lessons complete" for the selected course | No courses: heading level 3 "No courses yet", text "You are not enrolled in any course yet. Ask your teacher or an administrator to add you." | Shared failure messages, shown in an element with role alert | Heading stays; no stale data from an earlier load is shown; "Try again" repeats the courses request only |
| Materials list, lessons of the selected course | Lesson cards as links; topic buttons; "Search materials" | status "Loading study materials…" over the lesson area; course select stays usable | Cards: topic label, title, excerpt, "Complete" or "Start learning". Topic buttons have aria-pressed | Course has no published lessons: heading level 3 "No lessons published yet", text "Your teacher has not published lessons in this course yet. Check back soon." Filter or search matches nothing: heading level 3 "Nothing here just yet", text "Try another topic or a different search." | Shared messages; 404 `not_found` (membership removed meanwhile): "This course is not available to you." (no retry; the course select still works) | Course select, search text and topic choice are kept; "Try again" repeats the lessons request only |
| Change course or topic, type in search | select "Course"; topic buttons; "Search materials" | course change shows the loading status again; topic and search are instant (client side) | `?course=<id>` in the URL changes with the course; search and topic reset on course change | as above | as above | not applicable |
| Open a lesson (card link) | link whose name contains the lesson title | status "Loading lesson…" | Back link "All study materials"; heading level 1 = lesson title; eyebrow "<TOPIC NAME> · <COURSE TITLE>" upper-case; content in a region named "Lesson content"; button "Mark as complete" or "Mark as incomplete"; link "Try the practice set"; button "Ask your companion" | not applicable (content is never empty) | 404 `not_found` or invalid id (422): heading level 3 "Lesson not found" with link "Return to materials". Shared messages for the other causes | Back link stays usable; "Try again" repeats the lesson request only |
| Mark as complete / Mark as incomplete | button, label shows the action available (current state complete: "Mark as incomplete") | button disabled with label "Saving…" while the request runs (sent once even on double click); the lesson text stays | button label flips to the new action only after the server confirms (no optimistic change); status message "Marked as complete." or "Marked as incomplete." (role status) | not applicable | Network or timeout: "Could not reach the server. Your progress was not saved." 5xx or 503: "Could not save your progress. Nothing was changed." 404: the page shows "Lesson not found" as above (lesson withdrawn). 401: as in the shared table. 403 `csrf_failed`: "Could not save your progress. Nothing was changed." (the next click retries; the CSRF token is renewed by the next sign-in) | Lesson text stays; the button returns to its previous label and is enabled, so clicking again is the retry; no automatic retry |
| Overview total, `/student/overview` | Stat labelled "Lessons completed" | value "…" with detail "Loading…" | value "N / M", detail "N of M lessons" (totals across member courses; "0 / 0" and "0 of 0 lessons" when none) | covered by 0 / 0 | Any failure: value "–", detail "Unavailable. Open Study materials to try again."; demo-mode 401: value "–", detail "Sign in to see your progress" | The rest of the Overview is unaffected |
| Direct URL `/student/materials/<not-a-uuid>` | as "Open a lesson" | | | | "Lesson not found" panel (server answers 422) | |

Also:
- Refresh: both pages reload from the server; the selected course is kept through `?course=`; topic filter and search text reset. The lesson page shows the stored completion state.
- Back and Forward: Back from a lesson returns to `/student/materials?course=<course id>` and the list is reloaded, so a status changed on the lesson page is shown. The Back link on the lesson page goes to the same URL as an ordinary link: it adds a history entry and does not replace the lesson entry, so browser Back from the list returns to the lesson.
- After logout or an expired session: protected data is not shown; signed-in users go to `/login`; demo mode shows the sign-in notice. Browser Back after logout shows no lesson data.
- Backend down: the "Could not reach the server" message with "Try again". Recovery needs no reload.
- Longest wait: 10 s per request (`REQUEST_TIMEOUT_MS`). The courses and lessons requests are sequential, so the list can wait up to 20 s in total before both are reported. The lesson page makes one request (10 s). After a timeout the error appears at once; there is no hidden longer wait.
- No generic "something went wrong". "Could not reach the server" appears only for network failure or timeout (status 0).
- Layout: usable at 390 px and 1440 px width, light and dark theme; controls keyboard reachable; focus visible; no animation beyond existing styles (reduced motion respected as today).

## Out of scope
- Publishing, editing, unpublishing and withdrawing lessons (TEA-03 publication). This feature only reads published lessons; it defines the table they live in (see Decision 1).
- Practice sets and MCQs (STU-02, TEA-04). MCQs, answer keys and explanations are never part of a lesson.
- The progress dashboard views and "topics needing further practice" (STU-04). Only the data contract and helpers it needs are fixed here.
- AI explanations on lessons (STU-03), search over lesson content, reading time or duration, per-lesson partial progress ("continue lesson"), bookmarks, comments.
- Course enrolment and joining a course (ADM-05; Decision list item "How users join courses").
- Markdown or rich text, images, attachments, file downloads of source materials.
- Teacher analytics of completion (TEA-05) beyond keeping the data readable by lesson id.
- Offline use.

## Security and AI safeguards
- Server-side only: every endpoint uses `current_user(role="student")` and course membership; the user id always comes from the session. A hidden button is not a control.
- Order of checks (fixed): session 401, CSRF and Origin 403 (unsafe methods), role 403, path id validity 422, record visibility 404 (lesson exists, not withdrawn, user is a member of its course), body validation 422, write.
- A lesson that is missing, withdrawn, in another course, or a draft id returns the identical 404 body `{"detail":{"code":"not_found","message":"Lesson not found."}}`; a course the student is not in returns the same 404 body as a missing course (`Course not found.`, from `require_course_member`). Response timing and bodies must not reveal which case.
- Student endpoints never read `study_note_draft`, `mcq_draft_*` or answer data. The `published_lesson` row holds only title and content; no answer key or explanation is stored there, so STU-03 may later use lesson content as context without a before-submission leak (SHR-02).
- Retrieval helper for later AI use: `get_visible_lesson(db, user, lesson_id)` is the single place that decides whether a student may read a lesson. STU-03 must reuse it rather than query the table.
- Untrusted input: path ids are parsed as UUID; the body is `{"completed": bool}` only (strict boolean, unknown fields rejected with 422). Lesson text comes from teachers and is treated as untrusted when displayed: rendered as plain text; no HTML injection; links are not auto-created.
- Concurrency: the write is a single `INSERT ... ON CONFLICT (user_id, lesson_id) DO UPDATE` statement setting the requested state. Concurrent requests for one record never create two rows or raise 500; the last committed request wins. Different students use different rows.
- Normalisation: ids are parsed as UUID (case and hyphen forms accepted by `uuid.UUID`; the stored and returned form is the lowercase hyphenated string). The only user input beyond ids is the boolean.
- Limits: list responses are bounded by what a teacher has published (content at most 2,000 characters; excerpt at most 160 characters). No pagination in the MVP; the plan caps a course list at 500 lessons and states the behaviour past it. There is no AI quota because there is no AI call.
- Privacy: completion is private to the student. Teacher or admin access to completion data is a separate feature (TEA-05, ADM-01) and is not exposed here. No endpoint takes a user id.
- Errors are the shared envelope; no SQL, paths or exception text. Database failure gives 503 and never falls back to sample data.
- No secrets are added; no new configuration variable.

## Decisions (user, 2026-11-04; formerly open questions)
1. STU-01 creates `published_lesson`. It also provides `publish_lesson(db, draft, teacher)` in `study_lessons/`; the TEA-03 owner adds the publish route and button and calls it. If TEA-03 has published nothing by about 9 Nov, STU-01 owner adds a minimal publish endpoint. Until then lessons come from `study_lessons.seed` and test SQL.
2. `withdrawn_at` is kept and honoured on read; no endpoint sets it now (TEA-03 owner decides).
3. Publication copies the source material's topic; no topic shows as "General".
4. Republishing an edited draft creates a new lesson with a new id (old one withdrawn); completion does not carry over.
5. Demo mode: built-in sample lessons, Overview sample cards, hero line and lesson outline are removed; an anonymous student sees the sign-in notice on Study materials. "Continue learning" links to `/student/materials`. STU-04 owns the rest of the Overview.
6. Study companion page label on a lesson page becomes "Study materials".
7. A new student sees "No courses yet" until a `course_membership` row exists; enrolment is ADM-05.
8. Other decision-list items do not affect STU-01 behaviour (subject and level affect only seeded texts).
9. Cap of 500 lessons per course, no pagination.
