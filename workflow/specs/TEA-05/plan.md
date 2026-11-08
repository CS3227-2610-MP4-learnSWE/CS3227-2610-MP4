# Plan: TEA-05 Learning overview

Status: Approved by the user on 2026-11-09. Open questions 1-11 resolved with the recommended answers, except 9: the greeting is fixed in this feature (AC17).

## Data model
No new table, column, index or migration. Read-only over existing tables (all existing, verified in code):
- `course`, `course_membership(course_id, user_id)`, `user(id, role, access_status)` (`teacher_materials/models.py`): courses the teacher manages and the student roster (`user.role = 'student'`).
- `published_lesson(id, course_id, topic_id, title, published_at, withdrawn_at)` and `lesson_completion(user_id, lesson_id, completed, completed_at)` (`study_lessons/models.py`); `topic(id, name)`.
- `published_practice_set(id, course_id, topic_id, title, published_at)` and `published_practice_question(id, set_id, position, question, ...)` (`teacher_publications/models.py`). Columns `choices`, `correct_choice_index`, `explanation` are never selected.
- `practice_attempt(id, seq, student_id, set_id text, status, answers jsonb, score_correct, score_total, correct_question_ids jsonb, submitted_at)` (`attempt_models.py`). `set_id` is text: compare against `str(published_practice_set.id)` computed in Python (no SQL cast), so built-in non-UUID set ids never match.
Existing indexes (`ix_lesson_completion_lesson`, `ix_practice_attempt_submitted`) are enough at the expected size; no migration is justified.

## API endpoints
### `GET /api/teacher/overview?period=7d|30d|all`
Roles: teacher only, via `teacher_access.teacher_session(request)` (cookie session; 401 `unauthenticated` for anonymous or expired, 403 `forbidden` for student or admin, as for the other `/api/teacher/*` routes; database failure inside it is 503 `service_unavailable`, message "Teacher service is unavailable. Please try again."). Query: exactly one key `period`, value trimmed of surrounding ASCII whitespace, one of `7d`, `30d`, `all` (case-sensitive). No body, no write, no CSRF.

Order of checks: (1) `teacher_session` (401/403), (2) period validation (422), (3) rate limit (429), (4) build report. Rate limit: `auth.rate_limit.admit(f"teacher-overview:{teacher.id}", 30, 60)`; a returned wait is `ApiError(429, "overview_rate_limited", "Too many overview requests. Try again shortly.", retry_after_seconds=wait)` (rendered with a `Retry-After` header like `ai_usage/routes.py`).

200 response, exactly these keys (example):
```json
{
  "period": {"preset": "30d", "start": "2026-10-11T00:00:00Z", "end": "2026-11-10T00:00:00Z",
             "start_date": "2026-10-11", "end_date": "2026-11-09", "timezone": "UTC"},
  "as_of": "2026-11-09T12:00:00Z",
  "courses": [{
    "course_id": "<uuid>", "title": "Intro to SE",
    "student_count": 5, "lesson_count": 2, "completion_rate_percent": 40,
    "lessons": [{"lesson_id": "<uuid>", "title": "Clean code", "topic": "General", "completed_students": 3, "rate_percent": 60}],
    "practice": {
      "sets": [{"set_id": "<uuid>", "title": "Testing basics", "topic": "Testing", "students_attempted": 4,
                "submitted_attempts": 6, "average_score_percent": 58}],
      "missed_questions": [{"set_id": "<uuid>", "set_title": "Testing basics", "position": 2,
                            "question": "What does a unit test check?", "missed": 3, "answered": 4, "miss_rate_percent": 75}]
    }
  }]
}
```
Field rules:
- `period.start` / `period.start_date` are `null` for `all`; `end` is exclusive (00:00 UTC of tomorrow), `end_date` is today's UTC date (inclusive display); `timezone` is `"UTC"`. `as_of` is the server instant (`utc_timestamp`, `...Z`).
- `courses` is `[]` when the teacher has no membership. Order: lower(title), id.
- `completion_rate_percent`, `rate_percent`, `average_score_percent` are integers 0-100 or `null` (null when the denominator is 0 or there are no attempts). All percentages floor (`progress_rules.accuracy_percent(answered, correct)` = `correct * 100 // answered`, guarded so a zero denominator gives `null`, not 0).
- `lessons`: non-withdrawn lessons of the course, ordered `published_at`, `id`. `topic` = topic name or `"General"`. `completed_students` counts roster students with `completed = true` and `start <= completed_at < end` (no lower bound for `all`). `rate_percent = floor(completed_students * 100 / student_count)`.
- `completion_rate_percent = floor(sum(completed_students) * 100 / (student_count * lesson_count))`, `null` when `student_count == 0` or `lesson_count == 0`.
- `practice.sets`: every published set of the course, ordered lower(title), id. `students_attempted` = distinct roster students with at least one submitted attempt in the period; `submitted_attempts` = number of such attempts (all, not only latest); `average_score_percent = floor(100 * sum(latest.score_correct) / sum(latest.score_total))` over each student's latest attempt (greatest `(submitted_at, seq)` in the period), `null` when none.
- `practice.missed_questions`: for each latest attempt and each published question of its set: `answered` when the question id is a key of `answers`; `missed` when answered and the id is not in `correct_question_ids`. Only questions with `missed >= 1`. `miss_rate_percent = floor(missed * 100 / answered)`. Sorted by exact `missed/answered` descending (compare as fractions, not floored values), then `missed` descending, then `lower(set_title)`, then `position`, then `set_id`; first 5 per course.
- No other keys. Never present: student id, name, email, answers, scores per student, choices, correct answer, explanation, draft or withdrawn content.

Errors (envelope `{"detail": {"code", "message"}}` via `errors.ApiError` and `practice_routes.error_response`):

| Status | `detail.code` | Message | When |
|---|---|---|---|
| 401 | `unauthenticated` | existing | no or expired session |
| 403 | `forbidden` | existing | student or admin |
| 422 | `invalid_overview_period` | "Choose Last 7 days, Last 30 days or All time." | missing, unknown, repeated or extra query key; bad value |
| 429 | `overview_rate_limited` | "Too many overview requests. Try again shortly." | more than 30 accepted in 60 s; `Retry-After` integer seconds |
| 503 | `service_unavailable` | existing | database failure |

All responses carry `Cache-Control: private, no-store` (existing `auth.routes.add_no_store` middleware; do not set it twice).

## Components and modules
### Backend (new package `src/backend/teacher_overview/`, registered in `main.py` with `app.include_router(teacher_overview_router)` next to the other teacher routers)
- `schemas.py`: constant `PERIODS = ("7d", "30d", "all")`; `@dataclass(frozen=True) class ReportingPeriod: preset: str; start: datetime | None; end: datetime`; `resolve_period(preset: str, now: datetime) -> ReportingPeriod`; `period_json(period: ReportingPeriod) -> dict` (the `period` object above); `parse_period(query_params) -> str` (raises `ApiError(422, "invalid_overview_period", ...)`).
- `service.py`: `utc_now() -> datetime` (aware UTC; the single clock, tests monkeypatch `teacher_overview.service.utc_now`); `TOP_MISSED = 5`; `build_overview(db: Session, teacher_id: str, period: ReportingPeriod, now: datetime) -> dict`. Per course: roster first (`course_student_ids`), then lessons (`lesson_completion_stats`), published sets and questions (direct read-only queries on `teacher_publications.models`, plus `Topic` names), then attempts (`submitted_in_period`). Pure helpers for the arithmetic live here (`_rate`, `_missed_questions`), reusing `progress_rules.accuracy_percent` (do not copy the formula).
- `routes.py`: `router = APIRouter(prefix="/api/teacher", tags=["teacher overview"])`; `learning_overview(request: Request) -> dict` implementing the check order above.
- Reused: `teacher_access.teacher_session`, `teacher_materials.models` (`Course`, `CourseMembership`, `User`, `Topic`), `study_lessons.models`, `teacher_publications.models`, `progress_rules.accuracy_percent`, `timestamps.utc_timestamp`, `auth.rate_limit.admit`, `errors.ApiError`, `auth.db.open_session` (inside the attempt helper).

### Additive helpers in student-owned modules (user decision 3a; no existing function, signature, constant or test changes)
In `study_lessons/progress.py`:
```python
@dataclass(frozen=True)
class LessonCompletionStat:
    lesson_id: UUID
    title: str
    topic_id: UUID | None
    completed_students: int

def course_student_ids(db: Session, course_ids: Sequence[UUID]) -> dict[UUID, frozenset[str]]:
    """Current members with account role 'student' per course; every requested course is present (empty set if none)."""

def lesson_completion_stats(db: Session, course_id: UUID, student_ids: Collection[str],
                            start: datetime | None, end: datetime) -> list[LessonCompletionStat]:
    """Non-withdrawn lessons of the course ordered published_at, id. completed_students counts users in student_ids with
    completed = true and start <= completed_at < end (no lower bound when start is None). Empty student_ids gives zeros, no IN ()."""
```
In `attempt_store.py` (module-level function, not added to the `AttemptStore` protocol, so existing fakes stay valid):
```python
@dataclass(frozen=True)
class PeriodAttempts:
    set_id: str
    student_id: str
    submitted_count: int
    latest: Attempt

def submitted_in_period(set_ids: Collection[str], student_ids: Collection[str],
                        start: datetime | None, end: datetime) -> list[PeriodAttempts]:
    """Per (set, student) with at least one submitted attempt whose submitted_at is in [start, end); `latest` is the one with the
    greatest (submitted_at, seq). Returns [] without a query when either collection is empty. Own session via open_session()."""
```
Both modules' existing exports stay as they are. The service filters rows to the roster of the set's course (a student in two courses only counts in the course owning the set, because sets belong to one course).

### Frontend
- New `src/frontend/src/services/teacherOverview.ts`: `OVERVIEW_PERIODS` (`[{value:"7d",label:"Last 7 days"},{value:"30d",label:"Last 30 days"},{value:"all",label:"All time"}]`), `DEFAULT_PERIOD = "30d"`, types `Overview`, `OverviewCourse`, `readOverview(period): Promise<Overview>` (uses `request("GET", "/api/teacher/overview?period=..." , undefined, { timeoutMs: 15_000, distinguishTimeout: true, cache: "no-store" })` and rejects a malformed body with `ApiError(0, "bad_response")`, validating keys and types as `aiUsage.ts` does), `overviewError(error): string` (messages from the spec table; unknown status or `bad_response` maps to the invalid-report message; code `network` and `timeout` map to their messages), `periodLine(period): string`.
- New `src/frontend/src/pages/TeacherOverview.tsx` (default export `TeacherOverviewReport`): the report section only (select, status, alert, period line, course panels, note). Pattern copied from `AdminAiUsage.tsx`: remount key `${user?.id}:${getSessionGeneration()}:${location.key}`, a `serial` ref and `getSessionGeneration()` checks to drop stale and cross-session responses, an `initial` promise ref so the StrictMode replay attaches to the one activation read. Anonymous: `SignInNotice` with the spec message. Small presentational parts (`CourseReport`, `LessonTable`, `PracticeTable`, `MissedList`, `CalculationNote`) in the same file or `components/` if the file passes about 250 lines.
- `src/frontend/src/pages/Teacher.tsx`: `Overview` keeps `PageHeading` and `teacher-hero` and renders `<TeacherOverviewReport />` in place of `stats-grid` and `dashboard-columns`; imports no longer used (`Stat`, `Progress`, `SectionHeading`, `FileText`, `ArrowRight`, `Tag`, `PreviewNote` if unused) are removed. No other case of the switch changes. No route or navigation change.
- `src/frontend/src/styles.css`: scoped `.teacher-overview-*` rules only.
- Reused: `PageHeading`, `Panel`, `EmptyState` (not required), `LocalTime`, `SignInNotice`, `useAuth`, `client.ts` (`request`, `ApiError`, `getSessionGeneration`), MUI `Alert`, `Button`, `MenuItem`, `TextField`, existing `.table-scroll` pattern.
- Docs: `docs/UserGuide.md` (replace the "sample preview" wording for the teacher Overview near lines 11, 35 and 165; add "Teacher learning overview" with the calculation bullets and limits); `docs/DeveloperGuide.md` (TEA-05 section: endpoint, helpers, clock hook, test commands).

## UI contract
Applies `workflow/ui-design.md`. Exact copy is in the spec's "UI states and copy" table; names below are what tests use.

Hierarchy: existing h1 and hero (unchanged) > `<section aria-labelledby>` with h2 "Learning overview" and intro text > control row panel (the select, period line, "Data as of") > one `Panel` per course (h3 title; summary; h4 sections) > `Panel` "How these figures are calculated" (h3). Neutral surfaces (`--paper`, `--line`), blue only for focus and the primary action; no green or red except the error `Alert`. Panel padding 24-28 px desktop, 16 px at 320-390 px; 8 px rhythm. Course panels stack vertically; inside a course the lesson and practice tables stack on mobile and may sit side by side from about 1000 px width; the missed list spans full width. Course titles, lesson titles, set titles and question text wrap (`overflow-wrap: anywhere`); tables scroll horizontally inside their own focusable region, never the page.

Accessible roles and names (tests use only these):
- combobox "Reporting period" (MUI `TextField select`, outlined, persistent label; same `SelectDisplayProps` aria-label trick as `AdminAiUsage.tsx`); options (role option) "Last 7 days", "Last 30 days", "All time". Changing the option sends the request immediately (no apply button).
- status "Loading learning overview…"; alert (exact message text); button "Try again" inside the alert.
- heading level 2 "Learning overview"; level 3 course title; level 4 "Lesson completion", "Practice results", "Commonly missed questions"; level 3 "How these figures are calculated".
- region "Lesson completion results, {course}" > table "Lesson completion, {course}" (column headers "Lesson", "Topic", "Students completed", "Completion rate"; `th scope=col`); region "Practice set results, {course}" > table "Practice results, {course}" (headers "Practice set", "Topic", "Students attempted", "Submitted attempts", "Average score"); regions have `tabIndex=0`.
- list (ordered) "Commonly missed questions, {course}"; each `li` text "{set title}, question {position}: {question}" then "Missed {missed} of {answered} answers ({rate}%)".
- text lines "Period: ...", "Data as of" with `<time dateTime=as_of>` via `LocalTime`; "Students enrolled: {n}", "Published lessons: {n}", "Lesson completion rate: {n}%" / "Lesson completion rate: Not available".
- Status texts (role status): "No lessons are published in this course yet.", "No lessons were completed in this period.", "No practice sets are published in this course yet.", "No practice attempts were submitted in this period.", "No missed questions to show because no practice attempts were submitted in this period.", "No questions were missed in this period.", "No students are enrolled in this course yet.", "You do not manage any courses yet. Ask an administrator to assign you to a course."
- Calculation note bullets (exact, in this order, as `li`):
  1. "Students are the people enrolled in the course with a student account. Disabled students still count; a student removed from the course no longer appears in any figure."
  2. "A lesson counts as completed when the student has it marked complete and the completion time falls inside the period. Lessons marked complete and later unmarked do not count. Only published lessons are included."
  3. "Completion rate for a lesson = students who completed it ÷ students enrolled. Lesson completion rate for a course = completions in the period ÷ (students enrolled × published lessons). Percentages are rounded down; Not available means there is nothing to divide by."
  4. "Practice results include submitted attempts on the course's published practice sets that were submitted inside the period. Average score uses each student's latest submitted attempt: all correct answers ÷ all answers."
  5. "A question is missed when a student's latest attempt answered it incorrectly. Miss rate = missed ÷ answered, rounded down. The five questions with the highest miss rate are listed, ties broken by more misses, then set title, then question number."
  6. "Periods use UTC calendar days and include today. All time has no start date. Figures show current enrolment and current records only. Totals are shown, never individual students."
- Anonymous: `Alert` text "Sign in to view your learning overview." and link "Go to sign in" (to `/login`).

Keyboard and focus: Tab order = select, then (if shown) Try again, then each scroll region in DOM order; visible focus ring from the theme; the select is operable with keyboard (MUI). After a successful load focus stays on the select. No animation; reduced motion needs no special case. Both themes: reuse tokens; inputs keep outlines (do not add `.panel fieldset` resets). Visual regression cases: desktop and 390 px, light and dark, with data, empty course, error alert, long titles.

Timeouts: 15 000 ms per request (`AbortController` via `request`), no retry.

- Requests per load and per retry: one GET on load, one per period change, one per `Try again`; zero for anonymous and wrong-role; unchanged shell requests are separate.
- Wrong role: `RequireRole` redirect with replace to `/student/overview` or `/admin/overview`; no overview request.
- Link history: push or replace: nav and hero links push; period change and `Try again` no history change; wrong-role and expiry redirects replace.
- No generic failure message: every failure uses its exact message from the spec table; `overviewError` has no catch-all other than the invalid-report message for unexpected status or malformed body.

## AI usage
None. No prompt, no SoC LLM call, no retrieval. A test asserts that the endpoint does not touch the shared LLM client (override `get_llm_client` with a fake that fails if called, or monkeypatch `llm_client.SoclaasClient`).

## Test plan
Backend `src/backend/tests/test_tea05_*.py`, helpers reused: `auth_helpers` (`call`, `login`, `seeded`, `new_student`, `sql`, `require_db`), `stu01_helpers` (`make_course`, `enroll`, `make_topic`, `make_lesson`, `withdraw`, `put_completion`, `sql`), `published_sets` (`insert_published_set`, `world`, `question_rows`), `stu04_helpers` (`insert_attempt`, `start`, `save`, `submit`). Time control: monkeypatch `teacher_overview.service.utc_now`, and insert `completed_at` / `submitted_at` with SQL to exact instants. Browser `src/frontend/tests/tea05-overview.spec.ts` with helper `src/frontend/tests/tea05Api.ts` (mock of `GET /api/teacher/overview`, request recording, scripted failures) built on `authApi.ts` (`mockAuthApi`, `TEACHER`, `STUDENT`, `ADMIN`, `logOutWithConfirmation`).

| AC | Tests |
|---|---|
| AC1, AC3, AC9 | Teacher sees only own courses; another teacher's course and a course after membership removal absent; student/admin 403, anonymous 401; student with a different enrolment cannot be inferred; period object present with correct dates for each preset |
| AC5 | each preset boundary: item at `start` inside, one microsecond before outside; `all` includes old items; `end` exclusive; 422 for `period=` missing/empty/`1d`/`ALL`/repeated/extra key/whitespace-padded `" 7d "` accepted after trim |
| AC2, AC6 | lessons: counts, rates with floor (e.g. 1 of 3 = 33), null with 0 students or 0 lessons, withdrawn excluded, un-done excluded, completion by teacher/non-member excluded, disabled student counted; course rate formula |
| AC4, AC7 | sets: counts, latest-per-student average (second attempt supersedes first), in-progress excluded, attempts outside the period excluded, removed student excluded, fixture-set attempts (`set_id` not a UUID) ignored, null average with no attempts |
| AC8 | missed ranking: rate then misses then title then position; max 5; zero-miss questions excluded; floor of rate; answered counts only answered questions |
| AC10 | response key allow-list recursively; seeded student names/emails/ids, answers, correct choice text and explanations absent from the JSON text; draft and withdrawn content absent; `Cache-Control` includes `no-store` |
| AC11 | 31st request in 60 s is 429 with `Retry-After`; invalid periods do not consume budget; DB failure (patched `build_overview` raising `SQLAlchemyError`) is 503 `service_unavailable`; no LLM call |
| AC12, AC13, AC15 | browser: every row of the UI table (loading, each failure message, empty states, retry), request counts on load/period change/retry/StrictMode, anonymous zero requests, wrong role replace with zero requests, Back/Forward fresh GET and default period, refresh, logout clears report and failed logout keeps it, stale-response and cross-account ignore, 15 s timeout (mocked clock/delayed fulfil), 320 px no horizontal page scroll, light and dark, keyboard path |
| AC14 | sample strings gone ("Students learning", "LEARNING PULSE · SAMPLE", "A few things to pick up"); heading and hero still present |
| AC16 | existing suites unchanged: student progress (`test_stu04_*`), STU-01 lessons, attempts; shared specs pass with the added mock |
| AC17 | browser: signed-in teacher with display name "Dana Teacher" sees "Welcome back, Dana Teacher."; anonymous demo sees "Welcome back."; "Jamie" absent from the Overview |

Security tests (log in `workflow/security/`): direct API as every role and anonymous; cross-teacher course isolation; membership removal revokes access; no answer-key leakage; parameter pollution and injection strings in `period` (422, no 500, no reflection of the value in the error); concurrent reads (10 parallel identical requests return equal bodies; with a concurrent completion/enrolment writer the invariants `completed_students <= student_count` and `rate <= 100` always hold); rate limit isolation between two teachers.

Existing shared browser specs that sign a teacher in and reach `/teacher/overview` (wrong-role or login redirect included) and therefore need the mock route (test-designer exception 3b): `auth-login.spec.ts`, `auth-demo-off.spec.ts`, `auth-guard.spec.ts`, `teacher-http-cache.spec.ts`, `tea06-inbox.spec.ts`, `adm02-feedback.spec.ts`, `stu05-06-inbox.spec.ts`, `stu04-overview.spec.ts`, `stu04-progress.spec.ts`, `stu02ps-set-page.spec.ts`, `stu02ps-picker.spec.ts`, plus any other spec found by searching `TEACHER` and `teacher/overview` in `src/frontend/tests`. Allowed change: one import of `mockTeacherOverview` from `tea05Api.ts` (or an inline `page.route("**/api/teacher/overview**", ...)`) and one call in the spec's setup, returning an empty-courses 200. No assertion, selector or expectation changes. If a request-count assertion in one of these specs fails because a signed-in teacher now sends the overview request, the test-designer reports it to the orchestrator and does not edit the assertion. Specs that open the route only as an anonymous demo send no request and need no mock.

Verification runs: TEA-05 backend and browser tests, then the files named above, `test_stu04_*`, `test_stu01_*`, the teacher materials/publication tests; `npm run typecheck`, `npm run lint`, Prettier on changed files.

## Decisions
Recorded in the spec: user decisions 1-4 (2026-11-09). Plan-level choices awaiting approval: calendar-day UTC periods; one roster per course read first; helper signatures above; `request` rather than `requestTeacher` (Open question 3); rate limit 30 per 60 s per teacher; no migration.
