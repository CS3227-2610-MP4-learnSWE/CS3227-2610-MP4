# Plan: STU-02 Practice on teacher-published sets

Status: Draft (2026-11-06). The contract below is binding for developer and test-designer once the spec is approved. Defaults for the open questions in the spec are used until a human answers. Read it with `spec.md`; contracts of STU-02 (`workflow/specs/STU-02/plan.md`), STU-04 and TEA-03 (`workflow/specs/TEA-03-publishing/plan.md`) stay in force except where this plan says otherwise.

## Data model

No new table and no new column. No Alembic revision is added.

- Source tables (TEA-03, read only here): `published_practice_set` (id, course_id, topic_id, title, source_draft_id, source_version, published_by, published_at) and `published_practice_question` (id, set_id, position 1 to 3, question, choices JSONB of four strings, correct_choice_index 0 to 3, explanation), joined to `course_membership` (course_id, user_id), `course` and `topic`. Nothing in these tables is written by this feature, except by the development seed below.
- `practice_attempt.set_id` is `varchar(64)` (STU-04). A published set id is a 36-character UUID string and fits. No foreign key is added from `practice_attempt.set_id` (open question 10): old development rows with `intro-se-1` stay valid and the stores stay independent. The single Alembic head stays `20261105_stu04_practice_attempt` (its `down_revision` is `20261105_tea03_publications`); a test asserts that `alembic heads` lists exactly one head.
- Mapping of one published set to the domain type (`practice_data.PracticeSet`, `Question`, which stay as they are):

| Domain field | Source |
|---|---|
| `PracticeSet.id` | `str(published_practice_set.id)` (lowercase hyphenated UUID) |
| `PracticeSet.title` | `title` |
| `Question.id` | `str(published_practice_question.id)` |
| `Question.text` | `question` |
| `Question.code` | always `None` |
| `Question.choices` | `tuple((choice_id(i), text) for i, text in enumerate(choices))` where `choice_id(i)` is `"abcd"[i]` |
| `Question.correct` | `choice_id(correct_choice_index)` |
| `Question.explanation` | `explanation` |
| `Question.topic_id` | `str(published_practice_set.topic_id)` for every question of the set (one topic per set) |
| order of questions | `position` ascending |
| key version | `practice_data.KEY_VERSION` (`"v1"`) for every published set |

- `practice_data.py` keeps `KEY_VERSION`, `Question` and `PracticeSet`. It loses the fixture `_SET`, `PRACTICE_SETS`, `get_set` and `SE_BASICS_TOPIC_ID`. The fixture moves into the tests (`tests/fake_sets.py`, owned by the test-designer, see Test plan).

### Development seed (dev only, idempotent)
- File: `src/backend/teacher_publications/seed.py`. Run after migrations, `teacher_materials.seed` (it needs the user `demo-teacher`, the course `11111111-1111-4111-8111-111111111111` and the topic `66666666-6666-4666-8666-666666666661`) and optionally `auth.seed` and `study_lessons.seed`:
  `uv run --env-file .env python -m teacher_publications.seed` (from `src/backend`). In CI the real-backend job gets a new step `uv run python -m teacher_publications.seed` after `study_lessons.seed` in `.github/workflows/ci.yml` (that job already sets `APP_ENV: development`).
- Signatures:

```python
SEED_SET_ID = UUID("77777777-7777-4777-8777-777777777774")
def seed_practice_set(session: Session) -> None   # idempotent; commits once; no environment check
def main(env: Mapping[str, str] = os.environ) -> int
    # returns 1 and prints "The practice seed is for development databases only (set APP_ENV=development)." when env.get("APP_ENV") != "development"; creates nothing
    # otherwise opens create_engine(env["DATABASE_URL"]), calls seed_practice_set, returns 0
# if __name__ == "__main__": raise SystemExit(main())
```
- Rows (each created only if its fixed id is absent; an existing row is never updated; flush between parents and children because of the restrictive foreign keys):

| Table | Fixed id (last group) | Key values |
|---|---|---|
| `material` | `77777777-7777-4777-8777-777777777771` | course 1111..., topic 6666...61, uploaded_by `demo-teacher`, title "Software engineering basics source", filename `se-basics.txt`, media_type `text/plain`, size_bytes equal to the content length |
| `material_file` | primary key is the material id | content: the bytes of a short text, at least one byte |
| `mcq_draft_batch` | `77777777-7777-4777-8777-777777777772` | course 1111..., source_material_id the material above, created_by and updated_by `demo-teacher`, source_title "Software engineering basics source", version 1 |
| `mcq_draft_question` x3 | `...777731`, `...777732`, `...777733` | batch above, positions 1 to 3, texts below |
| `published_practice_set` | `77777777-7777-4777-8777-777777777774` | course 1111..., topic 6666...61, title "Software engineering practice", source_draft_id the batch, source_version 1, published_by `demo-teacher` |
| `published_practice_question` x3 | `...777751`, `...777752`, `...777753` | set above, positions 1 to 3, source_question_id the matching draft question, same texts |

Seed questions (the draft and the published rows hold the same values; each explanation is at most 200 characters, each choice at most 80):
1. "What should a well-designed function have?" Choices: "A single, focused responsibility", "As many responsibilities as possible", "No descriptive name", "Hidden side effects only". Correct index 0. Explanation: "One focused responsibility makes a function easier to understand, test and change."
2. "Why do we keep automated tests alongside our code?" Choices: "To make the repository larger", "To catch regressions when code changes", "To avoid ever reviewing code", "To slow down every release". Correct index 1. Explanation: "Tests protect expected behaviour and can catch regressions introduced by later changes."
3. "What does len([1, 2, 3]) return in Python?" Choices: "2", "4", "3", "6". Correct index 2. Explanation: "len returns the number of items. The list contains three items."

`demo-student` is already a member of the Software Engineering course (`teacher_materials.seed`), so the set appears in that student's picker.

## API endpoints

All JSON. Errors use `errors.ApiError`, rendered as `{"detail": {"code", "message"}}`. Identity is the session user (`require_student`). `X-Student-Id` and any query parameter are ignored. Responses of `/api/practice-sets` and `/api/attempts` carry `Cache-Control: no-store` (add both prefixes to `add_no_store` in `auth/routes.py`; `/api/progress` is already covered).

### New: `GET /api/practice-sets` (role `student` only)
- Dependencies: `Depends(require_student)`, `Depends(get_set_provider)`. No body, no parameters; a query string is ignored. No CSRF (GET).
- 200 body (`PracticeCatalogOut`):

```
{
  "courses": [{
    "id": str, "title": str,
    "sets": [{
      "id": str, "title": str,
      "topic": {"id": str, "name": str},
      "published_at": str,
      "question_count": int,
      "best": {"correct": int, "total": int} | null
    }]
  }]
}
```

- `courses`: every course where the student has a membership, ordered by `lower(title)` then id (`study_lessons.progress.member_courses`), including courses with no sets (`"sets": []`). A student with no membership gets `{"courses": []}`.
- `sets`: the published sets of that course, ordered `published_at` descending then `id` descending, at most `CATALOG_SETS_PER_COURSE = 100` per course. `published_at` is UTC ISO-8601 with `Z` (`timestamps.utc_timestamp`). `topic.name` is the `topic` row's name. `question_count` is the number of questions of the set.
- `best`: from `store.submitted_summaries(student_id)`: the highest-ratio submitted attempt of that set (STU-04 rule, ties to the earliest created); `null` when the student has no submitted attempt on the set. Attempts on sets not in the list (for example `intro-se-1`) are ignored.
- Never present: question text, choices, ids of questions or attempts, correct choices, explanations, other students' data, source draft ids, publisher.
- Errors: 401 `unauthenticated`, 403 `forbidden`, 503 `service_unavailable`. No 404 or 422.

### Existing endpoints (paths unchanged; behaviour changes only as listed)

| Method and path | Success | Errors |
|---|---|---|
| `GET /api/practice-sets/{set_id}` | 200 `PracticeSetOut` `{"id", "title", "questions": [{"id", "text", "code": null, "choices": [{"id", "text"}]}]}` (shape unchanged; `id` and question ids are UUID strings; choice ids `a` to `d`) | 401; 403; 422 `validation_error` (id not a UUID); 404 `set_not_found` |
| `POST /api/practice-sets/{set_id}/attempts` | 201 `AttemptOut` `{"attempt_id", "set_id", "status": "in_progress", "answers": {}}` | 401; 403; 422 `validation_error` (id not a UUID); 404 `set_not_found` |
| `GET /api/attempts/{attempt_id}` | 200 `AttemptOut` | 401; 403; 404 `attempt_not_found`; 404 `set_not_found` |
| `PUT /api/attempts/{attempt_id}/answers` | 200 `AnswersSaved` | 401; 403; 404 `attempt_not_found`; 404 `set_not_found`; 409 `already_submitted`; 422 `unknown_question` or `invalid_choice` |
| `POST /api/attempts/{attempt_id}/submit` | 200 `SubmitOut` | 401; 403; 404 `attempt_not_found`; 404 `set_not_found`; 409 `already_submitted`; 422 `incomplete` with `missing` |
| `GET /api/attempts/{attempt_id}/results` | 200 `ResultsOut` (`key_version` `"v1"`; `correct_choice` is `a` to `d`) | 401; 403; 404 `attempt_not_found`; 404 `set_not_found`; 403 `not_submitted` |

Messages (exact): 422 `validation_error` "A valid UUID is required." (from `teacher_access.parse_uuid`, unchanged); 404 `set_not_found` "Practice set not found."; 404 `attempt_not_found` "Attempt not found."; 401 `unauthenticated` "Sign in to continue."; 403 `forbidden` "You do not have access to this."; 409 `already_submitted` "Attempt is already submitted."; 403 `not_submitted` "Results are available after submission."; 503 `service_unavailable` "The service is unavailable." (existing handler). Other messages are unchanged from STU-02.

Check order on attempt endpoints: 401, then 403 (`csrf_failed` for unsafe methods, then `forbidden`), then 404 `attempt_not_found` (unknown, not owned, or an id the store cannot hold), then 404 `set_not_found` (the attempt's set cannot be resolved for this student), then state (409, 403 `not_submitted`), then input validation (422). On `POST /api/practice-sets/{set_id}/attempts` and `GET /api/practice-sets/{set_id}`: 401, 403, then 422 `validation_error` (id not a UUID), then 404 `set_not_found`. The attempt endpoints take no set id from the client, so they have no new 422. A path that the server does not route at all (a set id that contains an encoded slash) is FastAPI's own 404; the front end treats every 404 and 422 on a set load as "not available".

How an id is judged (decided 2026-11-06, same as TEA-03): routes with a set id from the client call `teacher_access.parse_uuid(set_id)` (reuse the one function; do not copy it). It raises 422 `validation_error` "A valid UUID is required." for anything `UUID(value)` rejects (`intro-se-1`, spaces, NUL, control characters, wrong length, non-strings) and never reaches the database. A value it accepts (including uppercase, braces, urn form, no hyphens) is normalised with `str(uuid)` to lowercase hyphenated text and that string is passed to the provider, so alternative spellings of one real id find the same set. The provider still keeps a defence: `get_for_student` and `get_many_for_student` return no set (no query) for any string that is not canonical lowercase hyphenated UUID text, because the ids stored in old attempts (`intro-se-1`) and companion contexts reach it as plain strings; on the attempt endpoints and in progress that means 404 `set_not_found` and a skipped set, never 422. A valid UUID that matches no accessible set gives 404 `set_not_found`.

### Existing TEA-03 endpoints, same contract, now backed by the provider
`GET /api/study/courses/{course_id}/practice-sets` and `GET /api/study/practice-sets/{set_id}` keep every URL, response shape, status code, error code, message, ordering and `no-store` header of `workflow/specs/TEA-03-publishing/plan.md` (list: bare array of student set metadata `{id, kind "practice_set", course_id, topic_id, topic_name, title, published_at, question_count}`, `published_at` descending then `id` descending, no cap; detail: `{id, title, questions: [{id, text, code null, choices: [{id, text}]}]}`). What changes is only where the data comes from.
- List route: `parse_uuid(course_id)` (422 for a malformed id, as now), then `provider.catalog_for_student(user.id, course_id=course_uuid)`; an empty result (not a member, or no such course) raises 404 `not_found` "Course not found." exactly as `require_course_member` did; otherwise the sets of that one course are mapped to the metadata shape. The provider must supply per set: id, title, topic id, topic name, `published_at`, question count; the course id comes from the catalog course.
- Detail route: `parse_uuid(set_id)` (422 as now), then `provider.get_for_student(str(set_uuid), user.id)`; `None` raises 404 `not_found` "Publication not found." as now; otherwise return `practice_schemas.public_set(practice_set)`.
- Malformed ids are 422 `validation_error` on the TEA-03 routes and on the practice routes alike (decided 2026-11-06). The two families still differ in their 404 code and message (`not_found` against `set_not_found`), which is each family's existing contract.

### Existing endpoint, changed dependency: `GET /api/progress`
Contract of STU-04 unchanged. `build_progress` now resolves the sets of the student's submitted attempts through the provider (see signatures); summaries whose set the provider does not return are skipped. Response shapes and the weak-topic rule are unchanged.

### Existing endpoint, changed lookup: `POST /api/companion/messages`
Request, response, error codes and check order of STU-03 are unchanged except: the set named by `context.set_id` (or by the attempt) is looked up with `provider.get_for_student(set_id, student)`; `None` gives 404 `set_not_found` "Practice set not found." before any model call. When the context has no `attempt_id`, `context.set_id` is first parsed with `parse_uuid` (after the existing attempt lookup and consistency checks, before the set lookup): a value that is not a UUID gives 422 `validation_error` "A valid UUID is required." and no model call. With an attempt, the set is the attempt's stored set id (no parse; an unresolvable stored id is 404). `find_match` receives `provider.accessible_sets(student)`; `_leak_scope` for mode `help` uses the questions of the same list. The list is loaded once per message.

## Components and modules

### Backend (`src/backend/`, one responsibility per file)

| File | Change | Responsibility |
|---|---|---|
| `set_provider.py` | new | `SetProvider` protocol, `DbSetProvider`, module-level `provider`, `get_set_provider`, `choice_id`, `CatalogSet`, `CatalogCourse`, limits. The only place that reads the published tables for practice and the only place that decides practice-set access |
| `practice_data.py` | edit | remove the fixture, `PRACTICE_SETS`, `get_set`, `SE_BASICS_TOPIC_ID`; keep `KEY_VERSION`, `Question`, `PracticeSet` |
| `practice_routes.py` | edit | import `parse_uuid` from `teacher_access` (reused unchanged, not copied; it is the shared id parser of the TEA-03 routes) and parse the path set id; take the provider as a dependency; `_set_or_404(provider, set_id, student)`; set check after attempt ownership on every attempt endpoint; new route `GET /api/practice-sets` (catalog with best scores from `store.submitted_summaries`) |
| `practice_schemas.py` | edit | add `TopicRefOut`, `BestScoreOut`, `CatalogSetOut`, `CatalogCourseOut`, `PracticeCatalogOut` and `public_set(practice_set)`; existing schemas unchanged |
| `companion_routes.py` | edit | `parse_uuid` on a context `set_id` that has no attempt (422); provider dependency; `_resolve_context(ctx, student, provider)`; `find_match` and `_leak_scope` use the student's accessible sets; drop `import practice_data` if unused |
| `progress_service.py` | edit | `build_progress(db, student_id, attempts=store, sets=provider)`; resolve sets with `get_many_for_student`; no other change |
| `progress_routes.py` | edit | pass `Depends(get_set_provider)` to `build_progress` |
| `auth/db.py` | edit | add `open_session() -> Session` (the body of `attempt_store._session`); `attempt_store.py` imports it and drops its private copy; `set_provider.py` uses it |
| `auth/routes.py` | edit | `add_no_store` also covers `/api/practice-sets` and `/api/attempts` |
| `teacher_publications/seed.py` | new | the dev seed above |
| `teacher_publications/routes.py` | edit (two student routes only) | `student_sets` and `student_set` call the provider instead of their own query; contract unchanged; see "Changes to the teacher's TEA-03 files" |
| `.github/workflows/ci.yml` | edit | real-backend job runs the seed |

Not changed: `practice_logic.py`, `attempt_store.py` behaviour, `attempt_models.py`, `companion_service.py`, `companion_prompts.py`, `companion_config.py`, `companion_help.py`, `companion_schemas.py`, `leak_check.py`, `question_match.py`, `llm_client.py`, `student_identity.py`, `study_lessons/*`, `teacher_publications/models.py`, all migrations.

#### `set_provider.py` signatures (contract)

```python
ACCESSIBLE_SETS_LIMIT = 200        # companion: newest sets per student
CATALOG_SETS_PER_COURSE = 100      # picker

def choice_id(index: int) -> str   # "abcd"[index]

@dataclass(frozen=True)
class CatalogSet:        # supplies every field the TEA-03 student list needs (id, course id via the course, topic_id, topic_name, title, published_at, question_count)
    id: str
    title: str
    topic_id: str
    topic_name: str      # the topic row's name; "General" if the topic row cannot be found
    published_at: datetime
    question_count: int  # counted from the question rows (3 today)

@dataclass(frozen=True)
class CatalogCourse:
    id: str
    title: str
    sets: tuple[CatalogSet, ...]

class SetProvider(Protocol):
    def get_for_student(self, set_id: str, student_id: str) -> PracticeSet | None: ...
        # None for a non-canonical id string (defence only: routes call parse_uuid first), an unknown set, or a set in a course the student is not a member of
    def get_many_for_student(self, student_id: str, set_ids: Collection[str]) -> dict[str, PracticeSet]: ...
        # only accessible sets; malformed ids are dropped without a query; no query at all if none remain
    def catalog_for_student(self, student_id: str, *, course_id: UUID | None = None, per_course_limit: int | None = None) -> list[CatalogCourse]: ...
        # member courses (lower(title), id), each with its sets newest first (published_at desc, id desc);
        # course_id given: only that course, and an empty list if the student is not a member of it;
        # per_course_limit given: at most that many sets per course (None: all). The one query for "which sets can this student see"
    def accessible_sets(self, student_id: str) -> list[PracticeSet]: ...
        # accessible sets with questions, newest first (published_at desc, id desc), at most ACCESSIBLE_SETS_LIMIT

class DbSetProvider: ...            # opens its own short Session per call via auth.db.open_session()
provider: SetProvider = DbSetProvider()
def get_set_provider() -> SetProvider   # FastAPI dependency; returns `provider`; tests override it
```

- Access is one join: `published_practice_set` to `course_membership` on `course_id` where `course_membership.user_id` equals the student id. No separate "is this course visible" step.
- `get_for_student` loads the set and its questions in one session at READ COMMITTED (published rows are immutable, so two reads cannot disagree).
- `SQLAlchemyError` is not caught; the existing handler in `main.py` maps it to 503 `service_unavailable`. There is no fallback to fixture data.
- Domain objects returned by the provider hold the key. Only `practice_logic` (scoring, results) and `companion_service`/`leak_check` read `Question.correct` and `Question.explanation`; the set read route serialises only `id`, `title`, `text`, `code`, choices.

#### `practice_routes.py` behaviour (contract)
- `read_set(set_id, student, provider)` and `start_attempt`: first `key = str(parse_uuid(set_id))` (422 as above), then `_set_or_404(provider, key, student)`; the rest of `read_set`: build the body with `practice_schemas.public_set(practice_set) -> PracticeSetOut`, a new function in `practice_schemas.py` that is the one answer-free view of a set (id, title, per question id, text, code, choices with id and text; never `correct` or `explanation`). The TEA-03 route `student_set` uses the same function.
- `start_attempt`: after the parse and `_set_or_404` above, `store.create(student, key)` with the canonical lowercase string.
- Attempt endpoints (`read_attempt`, `save_answers`, `submit`, `results`): `owned_attempt` as today, then `practice_set = _set_or_404(provider, attempt.set_id, student)` before the state check and before taking the row lock; `save_answers` and `submit` pass that `practice_set` to `validate_answers`, `missing_questions`, `score`, `correct_question_ids` inside the `store.lock` block (the set is immutable, so the value read before the lock is the value the lock block needs). `results` builds the response with `logic.build_results(...)` using that set.
- `list_sets` (`GET /api/practice-sets`): `provider.catalog_for_student(student, per_course_limit=CATALOG_SETS_PER_COURSE)` (the only source of sets and courses; this route runs no query of its own for them); `best` from `store.submitted_summaries(student)` keyed by `set_id`; build `PracticeCatalogOut`.

#### `companion_routes.py` behaviour (contract)
- `_resolve_context` keeps its order (attempt lookup 404, consistency 422, set lookup 404) and replaces `practice_data.get_set(set_id)` by `provider.get_for_student(set_id, student)`.
- `post_message` calls `accessible = provider.accessible_sets(student)` once and passes it to `find_match` and `_leak_scope`. `_leak_scope` mode `hint` is unchanged; mode `help` uses the questions of `accessible`.
- When the context set is not in `accessible` (beyond the 200 cap), the plan for hint/explain still uses the set fetched by `get_for_student`; only the paste-match and the help-mode leak scope are bounded by the cap.

### Frontend (`src/frontend/src/`)

| File | Change |
|---|---|
| `config.ts` | delete (it only held `PRACTICE_SET_ID`) |
| `services/practice.ts` | add `listPracticeSets(): Promise<PracticeCatalogCourse[]>` built on `readOnce("/api/practice-sets")` (`services/readOnce.ts`), shape-checked field by field (a wrong shape throws `ApiError(0, "bad_response")`); export types `PracticeCatalogCourse`, `PracticeCatalogSet`. The existing functions are unchanged |
| `services/practiceMessages.ts` | new: single source of the exact texts below: `catalogErrorMessage(error: ApiError): string or null` (null for 401 `unauthenticated`), `SET_NOT_AVAILABLE`, `SET_NO_LONGER_AVAILABLE`, `PRACTICE_FORBIDDEN` |
| `pages/PracticePicker.tsx` | new: the picker page |
| `pages/Practice.tsx` | takes `setId` as a prop; shows the not-available states; removes the hard-coded "SOFTWARE ENGINEERING ESSENTIALS" tag; everything else unchanged |
| `practice/PracticeContext.tsx` | `loadSet(setId)` replaces `loadSet()`; state gains `setId: string or null` and `unavailable: "load" or "later" or null`; a different `setId` resets the whole state (choices, attempt id, step, results, message) before loading; the same `setId` with `load` of `ready` or `loading` does nothing (no new request); a 404 or a 422 on `GET /api/practice-sets/SETID` sets `unavailable: "load"` (same message for both); a 404 `set_not_found` from start, save, submit or results sets `unavailable: "later"` and clears `set`, `choices`, `results` and `submittedAttemptId`; 403 on load shows `PRACTICE_FORBIDDEN` |
| `pages/Student.tsx` | `case "practice"`: `path[3]` present renders `<Practice key={path[3]} setId={path[3]} />`, otherwise `<PracticePicker />` (same pattern as materials) |
| `components/StudyCompanion.tsx` | `onPractice` is true only when the URL is `/student/practice/SETID`; `set_id` is the URL's set id; `attempt_id` is `submittedAttemptId` only when the practice state's `setId` equals the URL's set id, else null; on the picker the context is page "other" |
| `pages/Progress.tsx` | no change (its link "Go to practice" already targets `/student/practice`) |
| `data.ts` | no change (sidebar "Practice" targets `/student/practice`) |
| `tests/` | the test-designer owns the tests |

No browser storage is used. The set id comes from the URL path segment and is passed unchanged (once encoded by the service) to the request; whatever the segment, one request is sent and the server's 404 decides.

## UI contract

Accessible role and name that tests use (exact). Copy for every state is in the spec's "UI states and copy"; this section fixes controls.

Picker page `/student/practice`:
- Heading level 1 "Choose a practice set" (eyebrow "UNDERSTAND IT. THEN TRY IT.", description "Pick a set your teacher has published for one of your courses."). Sidebar link role link name "Practice" in the navigation named "student navigation".
- Loading: element `role="status"` with text "Loading practice sets…".
- Per course: a `section` with `aria-labelledby` (role region named by the course title) with a heading level 2 of the course title. If the course has sets: a list (role list, accessible name "Practice sets in " followed by the course title) with one listitem per set. Each listitem contains a heading level 3 whose only content is a link (role link, name equal to the set title, target `/student/practice/` plus the set id), a paragraph "Topic: " plus the topic name, and a paragraph "Best score: C / T" or "No attempts yet". If the course has no sets: the paragraph "No practice sets published in this course yet." and no list.
- No courses: heading level 3 "Join a course to start" and the paragraph "You are not enrolled in any course yet. Ask your teacher or an administrator to add you, and practice sets will appear here."
- Error: element `role="alert"` containing the exact message; button role button name "Try again" where the spec lists one. Demo-mode 401: the SignInNotice alert with text "Sign in to see your practice sets." and link "Go to sign in".
- Retry: "Try again" starts a new request, shows the loading status, replaces the message with the result.

Practice page `/student/practice/SETID`:
- Heading level 1 "Put your knowledge to work." always shown. Loading: element `role="status"` with text "Loading the practice set…".
- Load failure (network, timeout, 5xx, bad response): `role="alert"` with "We could not load the practice set. Please try again." and button "Try again". 404 or 422: `role="alert"` with "This practice set is not available to you." and a link (role link, name "Back to practice sets", target `/student/practice`); no "Try again". 403: `role="alert"` with "You do not have access to practice."; no "Try again". Demo-mode 401: SignInNotice with its default text and link "Go to sign in".
- Later 404 `set_not_found` (start, save, submit or results): `role="alert"` with "This practice set is no longer available to you." and the link "Back to practice sets"; no radio group, no result and no "Submit practice set" button remain.
- All other controls and names are those of STU-02-frontend: radio groups named by the question text, radios named by the choice text, button "Submit practice set", button "Start another attempt", button "Try again", the incomplete message in a `role="alert"`, "N of M answered", score heading "N / M — Nicely done!" or "N / M — Keep building your understanding.", "Correct answer:" lines. The tag "SOFTWARE ENGINEERING ESSENTIALS" no longer exists.

Also fixed per screen (labelled entries):
- Requests per load and per retry: the picker sends one `GET /api/practice-sets` on load and one per "Try again", and no other picker-data request (no `/api/study/courses`, no `/api/progress`); the shared signed-in shell separately loads one metadata-only `GET /api/messaging/unread-count` on activation for the approved ADM-04 badge (no message bodies and no additional shell read on picker retry); the practice page sends one `GET /api/practice-sets/SETID` on load (none when the state already holds that set) and one per "Try again"; identical in-flight GETs are shared (StrictMode double effects must not send two); opening the picker again after Back sends a new request; the submission sequence (start, save, submit, results) is unchanged.
- Wrong role: a teacher or admin who opens `/student/practice` or `/student/practice/SETID` is redirected by the SHR-01 `RequireRole` guard to `/teacher/overview` or `/admin/overview` before any request is sent; a 403 alert appears only if the role changes after load; demo mode (anonymous) requests the endpoint, receives 401 and shows the sign-in notice.
- Link history: push or replace: sidebar "Practice", every set link, "Back to practice sets", "Go to sign in" and the Progress page link "Go to practice" push; nothing in this feature replaces; "Try again" and "Start another attempt" do not change the URL.
- No generic failure message: every failure uses the exact message in the spec's tables (picker: network or timeout, 5xx, bad response, 403, demo 401; practice page: the retained STU-02-frontend messages plus "This practice set is not available to you." and "This practice set is no longer available to you."); there is no catch-all text, and "Could not reach the server" is used only for status 0 with code `network` on the picker.

Timeouts: every request uses `REQUEST_TIMEOUT_MS` (10 s) from `client.ts`. No custom timeout, no automatic retry.

Responsive and theme: no fixed-width elements; existing CSS classes and theme tokens (picker rows reuse the panel and link styles of the materials cards); no new dependency.

## Changes to the teacher's TEA-03 files
Every edit this feature makes in the teacher's area, so the teacher can be briefed before merge (open question 11):
1. `src/backend/teacher_publications/routes.py`: only the functions `student_sets` (`GET /api/study/courses/{course_id}/practice-sets`) and `student_set` (`GET /api/study/practice-sets/{set_id}`) change; they call `set_provider` and `practice_schemas.public_set`. Their URLs, response shapes, status codes, error codes and messages stay as in TEA-03. The now unused imports in that file (`require_course_member`, `PublishedPracticeQuestion` if unused, and so on) are removed if nothing else uses them. Publishing and teacher routes are not touched.
2. `src/backend/teacher_publications/seed.py`: new file (the dev seed).
3. `src/backend/tests/test_tea03_publications.py`: rewrite of `test_tea03_publications_student_set_reads_are_allowlisted_and_old_attempt_flow_unmodified`. Its assertions at lines 123 to 125 (the fixture set `intro-se-1` is served; a published set id gets 404 `set_not_found` from `/api/practice-sets/ID` and from the attempts route) are reversed by this feature: the fixture is gone and published sets are served to members. The allow-list assertions on the two TEA-03 routes in that test stay as they are.
Tests that guard the unchanged TEA-03 student-route contract and must pass without any edit: that same test (its lines 112 to 122, the list and detail checks) and `test_tea03_publications_auth_access_order_and_no_store_errors` (lines 149 to 170: 401, 403, 404 `not_found` for another course, no-store on success and failure). `test_tea03_publications_student_notes_reuse_existing_lessons_and_completion` and the teacher catalogue tests are not affected.
Nothing else in the teacher folders (`teacher_materials`, `teacher_notes`, `teacher_mcqs`, `teacher_publications/models.py`, migrations, teacher frontend) is edited. `teacher_materials/seed.py` is read by the new seed but not changed.

## AI usage

None added. The companion's prompts, modes, context size, rate limits, quotas, leak check and model client are unchanged. The only AI-related change is where the companion finds its practice set: the provider, with the same access rules as the practice endpoints, so the context it builds and the leak scope it checks contain only sets the student can access. Before submission the context contains no key and no explanation (unchanged); a set the student cannot access gives 404 before any model call. Lesson grounding, hint quality and prompt changes belong to the later STU-03 run.

## Test plan

Test types and how tests supply sets (decision for this feature):
1. Fake provider (most tests). A test fake `FakeSetProvider` in `src/backend/tests/fake_sets.py` implements the `SetProvider` protocol over an in-memory list of `PracticeSet` objects and a membership map (`members: dict[str, set[str]] or None`, where `None` means every student sees every set, plus `revoke(student_id, set_id)` and `grant(...)` to change membership mid-test). The old fixture set moves there as `FIXTURE_SET` with a canonical UUID id (a constant such as `"a0000000-0000-4000-8000-000000000001"`; questions `q1`, `q2`, `q3` with choices `a` to `c`, key `a`, `b`, `c`; plus the `SE_BASICS_TOPIC_ID` constant). Tests install it with `app.dependency_overrides[set_provider.get_set_provider]` (restored after each test) and pass it as the `sets` argument of `build_progress`. Used for: the STU-02 behaviour suites (attempts, fixes, grader), STU-03 companion suites, STU-04 progress, concurrency and cross-user suites, multi-set and multi-topic cases, and mid-attempt membership changes.
2. Database rows (a smaller set of integration tests, `test_stu02ps_db_*`). A helper `src/backend/tests/published_sets.py` inserts a published set with SQL in the style of `stu01_helpers.py`: `insert_published_set(conn, course_id, topic_id, title, questions, published_at=None, set_id=None) -> str`, where `questions` is a list of (text, four choices, correct index, explanation); it also inserts the `material`, `material_file`, `mcq_draft_batch` and three `mcq_draft_question` rows the foreign keys require. Memberships are inserted with the existing helpers. These tests use the real `DbSetProvider` through the HTTP API and cover: membership, malformed ids (422), the a-d mapping, topic names, picker order and contents, companion 404, progress skipping, and the seed.
3. Frontend: mocked Playwright. `tests/practiceApi.ts` gains the picker route and a configurable set id; `tests/progressApi.ts` uses the shared set id constant.

### Acceptance criteria to tests (backend names start `test_stu02ps_`; Playwright titles contain `stu02ps`)

| AC | Tests |
|---|---|
| AC1 to AC6 | The existing STU-02 behaviour tests (`test_stu02_attempts.py`, `test_stu02_fixes.py`, `grader/test_stu02_grader.py`) rewritten against `FakeSetProvider` with the same assertions (missing questions in set order, one answer per question, revise answers, score saved with key version, failed submit keeps answers, results only after submit). One DB test runs the complete flow on a real published set with four choices |
| AC7 | Recursive check that the set read body for a DB-published set has exactly the keys `id`, `title`, `questions[id, text, code, choices[id, text]]` and that no value equals the stored explanation or contains it; error responses (404, 409, 422, 403 `not_submitted`) hold no key or explanation; results before submit are 403 |
| AC8 | Another student's attempt id on all four attempt endpoints gives 404 `attempt_not_found` identical to an unknown id (existing cross-user tests rewritten) |
| AC9 | `GET /api/practice-sets/intro-se-1` 422 `validation_error` (not a UUID); `POST /api/practice-sets/intro-se-1/attempts` 422; a valid UUID of no set 404 `set_not_found`; a published set in a member course is served; a published set in a course with no membership is not |
| AC10 | Parametrised over read set, start, read attempt, save, submit, results: unknown valid UUID, a real set in another course, and a set whose membership row was deleted give identical status, code and message (compare the full JSON bodies) |
| AC11 | On read set and start attempt (and the companion context without an attempt): `intro-se-1`, leading or trailing space, 5,000 characters, `%00`, `a%00b`, `%0d%0a`, a SQL-looking string, a 35-character UUID: 422 `validation_error` "A valid UUID is required." (same body as the TEA-03 routes for the same input), never 500, no database query (a spy on the provider's session); `..%2F` and other encoded slashes: FastAPI's routing 404. Uppercase UUID, braces, urn form and no-hyphen UUID of a real accessible set: 200 (normalised to the same set); of an inaccessible set: 404 `set_not_found`. 401 and 403 come before 422. A test also compares the 422 body of a practice route and of `GET /api/study/practice-sets/ID` for the same bad id |
| AC12 | No cookie 401; teacher and admin 403 on each endpoint and on the picker (also for the teacher who owns the course); `X-Student-Id`, `X-Demo-User-Id`, `?student_id=` ignored |
| AC13 | DB test: four-choice set read gives choice ids `a` to `d` in stored order, `code` null, question order by position, snapshot ids; submitting choices that match `correct_choice_index` 0, 1, 2, 3 scores correctly (one set per index); `e`, `A` and an unknown question id give 422 |
| AC14 | Picker: ordering of courses and sets, empty course, no membership, a set in a non-member course absent, `best` null then set after a submit, best is the highest of several attempts, another student's score never appears, response keys exactly as the contract, no answer data, 100-set cap per course |
| AC15, AC16 | Playwright for every row of the "UI states and copy" tables: loading, success, no courses, empty course, each picker failure with its exact message and button (offline, timeout with a fake clock past 10 s, 503, 500, bad shape, 403, demo 401, signed-in 401 goes to `/login`), the practice page 404, 422 (same message as 404, for example the bookmark `/student/practice/intro-se-1`) and later-404 messages and links, kept existing states, request counts, wrong-role redirect without a request, link targets and history entries, refresh, Back and Forward (same set keeps answers without a request; different set resets), the removed tag, no `PRACTICE_SET_ID` or fixed set in any request, 390 px and 1440 px in both themes |
| AC17 | Fake provider: start an attempt, `revoke`, then read, save, submit and results each give 404 `set_not_found` and change nothing; `grant` again and the same attempt works; DB test deletes the membership row between calls; a submitted attempt's results are 404 after revoke |
| AC18 | DB test: delete the `published_practice_*` rows with SQL (in a test schema) and check that attempt endpoints give 404 `set_not_found`, the `practice_attempt` row is unchanged, and `GET /api/progress` is 200 without the set |
| AC19 | Companion tests rewritten onto `FakeSetProvider`: `set_id` of an inaccessible set 404 `set_not_found` and the fake LLM is never called; non-UUID `set_id` without an attempt 422 `validation_error` "A valid UUID is required." with the fake LLM never called; an old attempt whose stored set id is `intro-se-1` gives 404 `set_not_found`; attempt on a revoked set 404; context check order (attempt 404, then 422, then set 404) kept; a pasted question of an inaccessible set is not matched (mode `help`); hint context holds no key or explanation text before submit; explain after submit unchanged; all existing STU-03 assertions otherwise unchanged. A DB test runs one companion hint request on a real published set |
| AC20 | `build_progress` unit tests with `FakeSetProvider` (several sets and topics, a set the student cannot access skipped, an unresolvable id such as `intro-se-1` skipped, all questions of a set reported under the set's topic); API test: a DB-published set with a seed-style topic gives that topic name; the STU-04 rule tests (`test_stu04_rules_unit.py`) are unchanged |
| AC21 | Three submits of one set by one student: picker `best` is the highest, progress shows `attempts_submitted` 3, `best` and `latest` |
| AC22 | Threads: two submits of one attempt (one 200, one 409); eight simultaneous starts by one student create eight independent attempts; two students submitting the same set at once; a revoke racing a save gives only 200 or 404 and a consistent stored attempt |
| AC23 | Seed: `seed_practice_set` twice gives one set, three published questions, one batch, three draft questions, one material; `main({"APP_ENV": "production", ...})` returns 1 and inserts nothing; unset `APP_ENV` also returns 1; an existing row with the same id is not changed; the seeded set is readable by `demo-student` and not by a student of another course |
| AC24 | `alembic heads` lists exactly `20261105_stu04_practice_attempt`; a `practice_attempt` row with a UUID `set_id` can be inserted and read through the store |
| AC25 | Every file in the rewrite list below passes; a repository search for `intro-se-1` and `PRACTICE_SET_ID` under `src/` finds no use other than tests that assert the 404 and the seed texts |
| AC27 | TEA-03 route behaviour unchanged: the two guard tests named in "Changes to the teacher's TEA-03 files" pass unedited (except the rewritten part); new `test_stu02ps_tea03_routes_*`: list and detail bodies, order, keys and error bodies of the two routes equal the TEA-03 contract for a DB-published set (including `topic_name`, `published_at`, `question_count` 3 and the 422 for a malformed id); both TEA-03 routes, `GET /api/practice-sets`, `GET /api/practice-sets/{set_id}` and the attempt endpoints agree on membership for a member, a non-member, a former member (row deleted) and a restored member; the detail body of `GET /api/study/practice-sets/{set_id}` equals `GET /api/practice-sets/{set_id}`; a spy shows the picker and both TEA-03 routes call the provider's catalog or get method and that no module other than `set_provider.py` selects from `published_practice_set` for students (a search of `src/backend` outside `teacher_publications` publishing code and the seed) |
| AC26 | Verifier reads the guides against behaviour |

### Tests and helpers to rewrite (not delete)
Backend (`src/backend/tests/`): `companion_helpers.py` (`SET_ID`), `stu04_helpers.py` (`SET_ID`), `test_stu02_attempts.py`, `test_stu02_fixes.py`, `grader/test_stu02_grader.py` (fixed path `/api/practice-sets/intro-se-1` and `data["id"] == "intro-se-1"`), `test_stu03_companion_routes.py`, `test_stu03_fix_round1.py` and `test_stu03_fix_round2.py` (they monkeypatch `practice_data.PRACTICE_SETS`), `test_stu03_helpers_unit.py` (`practice_data.get_set("intro-se-1")`), `test_stu03_post_impl_gaps.py` (`monkeypatch.setitem(practice_data.PRACTICE_SETS, ...)`), `test_stu04_service_unit.py` (passes a mapping as `sets`), `test_stu04_progress_api.py`, `test_stu04_persistence.py`, `test_stu04_cross_user.py`, `test_stu04_concurrency.py` (posts to `/api/practice-sets/intro-se-1/attempts`), `test_stu04_migration.py` (`set_id="intro-se-1"` rows may keep an arbitrary string, but rename to a UUID text so the file has no fixture name), `test_shr01_access.py` and `test_shr01_accounts.py` (use the intro set as a protected sample), `test_tea01_materials.py` (lines that read the intro set before and after a teacher action), `test_tea02_notes.py` (same), and `test_tea03_publications.py` (asserts the old set is served and that new set ids are not served by the old routes: this reverses, rewrite it to assert that a published set is served by the practice routes only to members and that teacher actions do not change a student's view). Start by searching `src/backend/tests` for `intro-se-1`, `PRACTICE_SETS`, `get_set` and `practice_data`; the lists above come from that search and may be incomplete.

Frontend (`src/frontend/tests/`): `practiceApi.ts` (`SET_ID`, routes, add the picker), `progressApi.ts` (`SET_ID`), `practice.spec.ts`, `practice-recovery.spec.ts`, `practice-locked.spec.ts`, `practice-wrong-answer.spec.ts`, `companion.spec.ts`, `companion-limit.spec.ts`, `auth-session.spec.ts`, `auth-guard.spec.ts`, `app.spec.ts`, `stu04-progress.spec.ts`, `stu01-lesson.spec.ts`, `real-backend.spec.ts` (sign in, open `/student/practice`, click the seeded set "Software engineering practice", answer with the seed texts, expect the server score), `teacher-batch-publication-scope.spec.ts` and `teacherPublicationsApi.ts` if they open or mock the practice page. Start by searching for `SET_ID`, `practiceApi`, `/student/practice` and `practice-sets`.

Historical experiment files under `workflow/experiments/` that mention `intro-se-1` are records of past runs and are not edited.

### Security cases (add to `workflow/security/test-log.md`; threat model `workflow/security/threat-model.md`)
Non-member 404 identical to unknown valid UUID on every practice endpoint; teacher and admin 403; unauthenticated 401; malformed and hostile set ids give 422 and no query; answer key absent from the set read and from all error bodies; results denied before submit and after the membership is removed; another student's attempt ids; membership removed mid-attempt; companion with an inaccessible set (no model call) and with a pasted question from another course; progress and picker never list or score an inaccessible set; picker shows only the caller's best scores; concurrent submits; seed refuses outside development.

Workflow: Variant B (developer and test-designer in separate worktrees from the approved spec and plan, then verifier, at most two correction rounds).

## Decisions
- A set provider with one access query is the single source of practice sets; routes, companion and progress receive it as a dependency (or argument), so tests replace it with a fake and production never reads fixture data.
- One picker endpoint instead of composing three existing calls: one request, one failure mode, and unattempted sets are visible. It adds only grouping and best scores to the provider catalog.
- The TEA-03 student endpoints keep their contract but call the provider, so there is exactly one place (and one membership query) deciding which published sets a student can see; they are unused by the UI.
- Access failures use 404 `set_not_found` everywhere, including for an attempt whose set became inaccessible; the attempt ownership check (`attempt_not_found`) still comes first, so nothing is revealed that the student did not already own.
- Malformed set ids are rejected with 422 by the TEA-03 `parse_uuid` before the database (decided 2026-11-06): it removes the NUL-byte failure mode of PostgreSQL and makes the practice, TEA-03 and companion routes answer the same bad input the same way. Unknown and non-member valid UUIDs stay indistinguishable (404 `set_not_found`).
- The domain types `PracticeSet` and `Question` are kept; the provider adapts the published rows to them, so scoring, results, progress, the companion and the leak check need no change. Question and set ids become UUID strings; choice ids stay single letters.
- `topic_id` is set on every question from the set's topic, so the STU-04 service and the weak-topic rule run unchanged.
- No migration and no foreign key from attempts to sets; old development attempts stay in the table and are skipped.
- The seed lives with the publication code, is guarded by `APP_ENV`, and only creates rows with fixed ids that are missing.
- The practice state is keyed by the set id held in the URL; only the last opened set's state is kept, which keeps the provider small and avoids cross-set leaks of answers in memory.
- No new Python or npm dependency, no new environment variable.
