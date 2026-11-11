# Developer Guide — Current Preview

## Architecture and boundaries

The React/TypeScript frontend uses Vite, React Router, Material UI/Emotion and Lucide icons. `src/frontend/src/data.ts` holds fixtures and role navigation; `state.tsx` owns temporary completion and inbox state; practice state lives in `practice/PracticeContext.tsx`. Shared layout and visual components live under `components/`; each role has a page module, with shared inbox and feedback pages. The Material UI theme is configured at the root and CSS variables coordinate custom layout/illustrations in both modes.

The student `CompanionProvider` and floating widget live at the student shell boundary, outside individual route screens. Closing hides the panel without unmounting its message/draft state. Leaving the student role or returning to login unmounts it; a browser reload also resets it. No chat is stored in local/session storage or a backend. The legacy `/student/assistant` URL opens the widget and redirects to the overview; navigation and lesson CTAs now open the widget without leaving their page.

The widget derives a current-page label from routes and sample lesson metadata only, and sends it (at most 80 characters) as untrusted text. Future authenticated sessions must scope conversation history to the signed-in account until logout/clear, restore it on reload, and retrieve bounded, authorised page content on the server. Neither page content nor chat may override fixed instructions; DOM scraping and client-provided context are not security boundaries. Session persistence and lesson content as context are not implemented (see "Study companion (STU-03)" below for what is).

The React Router data router enables direct URLs and history. For future production hosting, configure SPA fallback and route `/api` to FastAPI. Vite proxies `/api` locally to `http://127.0.0.1:$API_PORT` (the port in `src/frontend/.env.example`; copy it to `.env`). The health indicator and the student Practice page fetch backend data; the health check handles checking, successful JSON, failed/malformed responses and a four-second timeout. Practice calls go only through `services/client.ts` (the single place that sends the session cookie and the in-memory `X-CSRF-Token` on state-changing calls, applies a 10 s timeout built with `setTimeout` and `AbortController`, and raises one `ApiError`) and the typed functions in `services/practice.ts`, which reject responses of the wrong shape. The study companion and teacher note generator call the SoC AI service only through the backend (`services/companion.ts` posts to `/api/companion/messages` with a 40 s timeout via the `timeoutMs` option of `request`; `ApiError.retryAfterSeconds` reads `retry_after_seconds` from the error body). The folder is not named `api/` because the Vite dev server would then serve `/src/api/...` modules, which the login test treats as API requests.

FastAPI exposes `/api/health` and `/api/health/ready` (process-only semantics) and the STU-02 practice attempt API: `GET /api/practice-sets/{set_id}`, `POST /api/practice-sets/{set_id}/attempts`, `GET /api/attempts/{attempt_id}`, `PUT /api/attempts/{attempt_id}/answers`, `POST /api/attempts/{attempt_id}/submit` and `GET /api/attempts/{attempt_id}/results`. The routes require a signed-in `student` session (SHR-01, see "Authentication and authorisation"); the attempt owner is the session user id, and other students' attempts return 404. Attempts live in PostgreSQL (table `practice_attempt`, STU-04) behind the `AttemptStore` interface; `store.lock(id)` is a context manager that opens a transaction, reads the row with `SELECT ... FOR UPDATE`, yields a fresh `Attempt`, writes the changed fields and commits on a clean exit, and rolls back on an exception, so a save cannot land after a concurrent submit, in any server process. Modules in `src/backend/`: `practice_data` (the `PracticeSet` and `Question` types and the answer key; no fixture), `set_provider` (published sets, see "Practice on published sets (STU-02-published-sets)"), `practice_schemas`, `practice_logic` (validation and scoring), `practice_routes` (HTTP), `student_identity` (the shared `require_student` check: the signed-in student's session user id, SHR-01) and `attempt_store`; `main.py` only wires the router. The key and explanations are released only in results of a submitted attempt. OpenAPI/docs are framework-generated; explicit documentation of the 401/403/404/409/422 application errors is still a follow-up. The planned check order is not guaranteed for malformed bodies: FastAPI can return 422 before handler-level checks (see the fair comparison record and security test log). Student attempts are owned by the session user and persisted; teacher features use PostgreSQL and the shared authenticated session. Backend tests use HTTPX ASGI transport against the real application.

## Teacher Materials (TEA-01)

The exact schema/API are in [SharedDataContract.md](SharedDataContract.md) and [TEA-01-db-storage](../workflow/specs/TEA-01-db-storage/plan.md). Start PostgreSQL 16 with `docker compose up -d postgres` (loopback port 5433, persistent named volume). Once, create a separate empty database with `docker compose exec postgres createdb -U learnswe learnswe_db_files`. Preserve any existing database/files/.env. Set `DATABASE_URL=postgresql+psycopg://learnswe:learnswe-local-only@127.0.0.1:5433/learnswe_db_files` in your local environment. From src/backend run `uv run --env-file .env alembic upgrade head`, then `uv run --env-file .env python -m teacher_materials.seed`. The seed is idempotent; migration/seed never run at request time. No FILE_STORAGE_DIR is required.

The Alembic online engine explicitly uses READ COMMITTED so the locked material check sees concurrent committed uploads even when the database defaults to repeatable read. Revision 20261102_tea01_db_storage refuses conversion if any materials exist, before schema changes; use the fresh database and upload sources again. Old uploads/drafts remain in the old database/files and do not appear in the fresh database. Populated downgrade also refuses: the old filesystem originals cannot be recreated automatically. Empty downgrade/reupgrade is supported; rollback to the old release requires its code, database/configuration and files. Do not drop/reset old data to make migration pass.
Teacher endpoints use `teacher_access.teacher_session`: the shared cookie/CSRF/Origin/teacher-role checks inside an explicit READ COMMITTED transaction. Seed credentials with `auth.seed` and sign in; legacy demo headers and flags are ignored. Teacher endpoints check role and membership before reading material metadata or bytes. Uploads are bounded to 10 MiB, validated as PDF/UTF-8 text, and stored in material_file.content BYTEA. The 100 MiB global original-byte budget uses transaction advisory lock 32272610 and a fresh byte sum under READ COMMITTED; oversized totals return 413 storage_quota_exceeded. Metadata/content insert and commit together; lists never load BYTEA. Downloads/generation authorise before fetching bytes. Missing content returns 503 service_unavailable. Temporary multipart spooling is closed automatically. Uploads do not create student content. The Materials page uses the shared HTTP client for multipart and blob responses while student practice keeps its existing session behaviour.

## Study companion (STU-03, first slice)

- Connection lifetime: release the initial read-only auth transaction before store/model work. Keep the fresh post-model account/session check. Nested reads must work with a one-connection pool; do not increase pool limits to hide starvation. Regression: `tests/test_stu03_connection_lifetime.py`.

One endpoint, `POST /api/companion/messages`, sends a student message and gets `{reply, mode, withheld, sources}` (`sources` is `[]` except in `lesson` mode, where it holds `{lesson_id, title}` built by the server). The request has `message`, optional `history` (untrusted, at most 50 items) and a `context` (`page` is `practice`, `lesson` or `other`, plus `set_id`, `attempt_id`, `lesson_id`, `label`). The client never names a mode; the server picks it (`companion_service.select_mode`): `lesson` on a lesson page (the viewed lesson) or on other pages when related published lessons are found (at most 2, word overlap over 200 candidates), unless the message matches a practice question; otherwise `help` on other pages; `hint` on the practice page with no attempt or an unsubmitted one; `explain` only for the student's own `submitted` attempt that has no later `in_progress` attempt on the same set. A message that matches a practice question (`question_match.find_match`: normalised, whole text, two choice texts, or 80% of the question's words) forces `hint` with that question's text and code. Hint context holds question text and code only, never choices, key, explanation or key version. Check order: header 401, set/attempt/lesson 404 `lesson_not_found` (another student's attempt gives the same 404 as an unknown one), context 422, message and history 422, per-student limit 429, model call, access recheck, then for `lesson` the NOT_IN_LESSON marker is removed first (`companion_service.finish_lesson_reply`: NFKC, case-insensitive, markdown-tolerant, every occurrence removed; a leading marker gives the limitation sentence and no sources) and the leak check runs on the exact text to be shown (`find_leak(check_text=False)`, letters and verdicts only); other modes check the raw reply. Error codes are in `workflow/specs/STU-03/plan.md`.

Lesson grounding (STU-03-grounding, addendum `workflow/specs/STU-03-grounding/`): `context.page` also accepts `lesson` with `lesson_id` (422 `invalid_context` without it; ignored on other pages). The response is `{reply, mode, withheld, sources}`, `mode` may be `lesson`, and `sources` (`[{lesson_id, title}]`, always present) is built by the server from the lessons placed in context, never from model output. Lesson mode is chosen by `companion_service.select_mode(..., lessons)` when no practice question was pasted (a match still forces hint): the viewed lesson on a lesson page, or up to 2 lessons from `lesson_provider.find_related` on page `other`. `lesson_provider` is the only reader of lesson text (own short session per call, overridable dependency `get_lesson_provider`; visibility through `study_lessons.access`); `lesson_match` scores by whole-word overlap (words of 4+ characters, stopwords in `companion_config`, 2 matching words or 1 in the title, 200 newest lessons, no model call, not rate limited). An unknown, malformed, draft, withdrawn or other-course lesson is 404 `lesson_not_found`, rechecked after the model call (the reply is discarded). Lesson context is the lesson title and content between `BEGIN LESSON TEXT` / `END LESSON TEXT` markers, 2,000 characters each, cap 200 tokens. A reply starting `NOT_IN_LESSON:` becomes the fixed limitation sentence plus the rest with `sources: []` (`finish_lesson_reply`); the marker is removed everywhere else. Leak check in Lesson mode: `find_leak(..., check_text=False)` over all accessible questions (letters and verdicts only); a hit returns `LESSON_CANNED_REPLY`, `withheld: true`, `sources: []`. `student_identity.student_user` is the shared session dependency so the route reads the session once. Frontend: `StudyCompanion` reads the lesson id from `/student/materials/<id>`, sends `page: "lesson"`, and renders `sources` as a "Based on:" group of router links (titles as text); `services/companion.ts` rejects a malformed `sources` as `bad_response`. Residual risk: a reply from general knowledge without the marker is shown with the lesson as its source.

Modules in `src/backend/`: `companion_routes` (route, context lookup, error mapping, metadata-only logging), `companion_service` (mode selection, history trimming, message assembly), `companion_schemas`, `companion_prompts` (fixed rules per mode), `companion_help` (fixed app-help text, written from the user guide: keep them in step), `companion_config` (message 1,000 characters, history 4 messages / 2,000 characters, label 80, output caps hint 100 / explain 200 / help 150 / lesson 200, lesson text cut at 2,000 characters each with the delimiter strings neutralised, the canned reply), `question_match`, `leak_check` and `attempt_store.list_for_student`. A hint, help or lesson reply that `leak_check.find_leak` flags (correct choice by letter or text, or a right/wrong verdict on a choice) is replaced by the canned reply with `withheld: true`. This check is deterministic and limited: paraphrased leaks pass.

`llm_client.py` is the one place the SoC LLM is called. It is generic (no practice or student wording): `SoclaasClient.complete(messages, max_tokens=, caller_id=)` posts to `{SOCLAAS_BASE_URL}/chat/completions` with `Authorization: Bearer`, 15 s timeout, one retry on timeout/5xx, per-caller sliding limits of 20 per minute and 300 per day (in memory, one process), a 12,000-character input ceiling and a 2,000-character reply ceiling. Errors are `LlmError` subclasses with fixed messages; the key is never in a message, `repr` or log. Settings come from `SOCLAAS_BASE_URL`, `SOCLAAS_API_KEY` and `SOCLAAS_MODEL` (names in `src/backend/.env.example`; put real values only in an ignored `src/backend/.env`; the backend does not read that file by itself, so start it with `uv run --env-file .env uvicorn main:app --host 127.0.0.1 --port 8000 --reload` from `src/backend`, or set the variables in the shell). If any is missing the endpoint answers 503 `llm_not_configured` and makes no network call. `httpx` is a runtime dependency for this. `get_llm_client` builds the client once per process on first use: an environment change needs a restart, and a client built while unconfigured stays cached until then. The shared `practice_routes.error_response` adds a `Retry-After` header whenever `retry_after_seconds` is in the error extras. `text_normalise` holds the one normaliser shared by `question_match` and `leak_check`; the leak check also strips markdown, quote marks and Unicode format characters before matching letters.

To fake the model in tests, override the dependency: `app.dependency_overrides[llm_client.get_llm_client] = lambda: fake`, where `fake.complete(messages, *, max_tokens, caller_id)` returns an `LlmReply` or raises an `LlmError`. To test the real client, give `SoclaasClient` an `httpx.MockTransport` and a fake `clock` and `sleep`. No test or CI step reads a key or calls the real service. Live checks are run by hand with approval.

## Authentication and authorisation (SHR-01)

One login for all roles. Accounts are rows of the existing `user` table (additive columns `email`, `password_hash`; migration `20261103_shr01_auth`). Passwords are hashed with stdlib scrypt (`auth/passwords.py`). A login creates a row in `auth_session` (only the SHA-256 of the random cookie token is stored) and sets an HttpOnly cookie; sessions last `SESSION_TTL_SECONDS` (default 43200, absolute). The role comes only from the database and is re-read on every request. Public signup always creates a `student` and rejects unknown body fields. Endpoints: `POST /api/auth/signup` (202, identical reply for a new and an existing email), `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, and `GET /api/courses/{course_id}` (reference use of the course check). Exact contract: `workflow/specs/SHR-01/plan.md`.

Modules in `src/backend/auth/`: `settings` (env read per call, fail-closed `validate()`), `passwords`, `models`, `db` (session per request), `sessions`, `rate_limit` (per-process, on top of `sliding_window.SlidingWindowLimiter`, which moved out of `llm_client.py` with no behaviour change); login attempts are serialised per email and per IP key (`serialised`, locks taken in sorted order and dropped when unused) so parallel wrong guesses see each other's recorded failures, while correct logins are never counted or refused for others (simultaneous logins from one IP queue behind each other's password hash, and each waiting request occupies a worker thread with no timeout, so a flood of correct logins from one IP can stall the app; before deployment add a lock-wait timeout or a cap on waiters, and set `TRUST_PROXY_HEADERS=true` behind a reverse proxy, otherwise every user shares the proxy's IP; expired limiter keys are removed only when the same key is used again, so memory can grow across many distinct IPs or emails), `csrf` (Origin allow-list and per-session token), `dependencies` (public surface), `routes`, `seed`. `main.py` mounts the router, adds credentialed CORS only for the exact `ALLOWED_ORIGINS` (never a wildcard), sets `Cache-Control: no-store` on `/api/auth/*`, and maps `SQLAlchemyError` to a fixed 503.

How a route uses it (teammates: always do this, never read identity from a header, query or body):

```python
from auth.dependencies import AuthUser, current_user, require_course_member
from auth.db import get_session

@router.get("/api/example/{course_id}")
def handler(course_id: UUID, user: AuthUser = Depends(current_user(role="teacher")),
            db: Session = Depends(get_session)):
    course = require_course_member(db, user, course_id)   # 404 not_found for missing or not a member
```

`current_user()` accepts any signed-in role; `role="teacher"` or `role=("teacher", "admin")` restricts it. Failure order: 401 `unauthenticated`, 403 `csrf_failed` (POST/PUT/PATCH/DELETE without a matching `X-CSRF-Token`, or a disallowed `Origin`), 403 `forbidden`. `require_course_member` has no admin bypass. Record-level checks stay in the owning feature and must return the same 404 for missing and not-owned records. Student routes use `practice_routes.require_student`, which wraps `current_user(role="student")` and returns the user id.

Environment (names only; see `src/backend/.env.example`): `SESSION_COOKIE_NAME`, `SESSION_COOKIE_SECURE` (must be true when `APP_ENV=production`), `SESSION_COOKIE_SAMESITE` (`lax`, `strict`, `none`; `none` needs Secure), `SESSION_TTL_SECONDS`, `ALLOWED_ORIGINS`, `TRUST_PROXY_HEADERS` (client IP is the last `X-Forwarded-For` entry only when true), `AUTH_LOGIN_MAX_FAILURES_PER_EMAIL`, `AUTH_LOGIN_MAX_FAILURES_PER_IP`, `AUTH_LOGIN_WINDOW_SECONDS`, `AUTH_SIGNUP_MAX_PER_IP`, `AUTH_SIGNUP_WINDOW_SECONDS`, and the seed-only `SEED_STUDENT_*`, `SEED_TEACHER_*`, `SEED_ADMIN_*` (`_EMAIL`, `_PASSWORD`). Invalid or non-positive numbers use the default. A production misconfiguration (insecure cookie, `SameSite=None` without Secure, bad `DATABASE_URL`) makes the auth routes answer 503 and never falls back to the demo identity.

Seed accounts after `alembic upgrade head` and `python -m teacher_materials.seed`, from `src/backend`: set the `SEED_*` variables in your shell, then `uv run python -m auth.seed` (add `--reset-passwords` to overwrite existing hashes). It is idempotent, prints one status line per role and never the password, skips a role whose variables are unset or whose password breaks the rules, and exits non-zero if an existing user has another role or the email belongs to someone else. Never commit real values.

Frontend: `services/client.ts` `request` sends the cookie (`credentials: same-origin`) and `X-CSRF-Token` on non-GET calls; the token is kept in memory (`setCsrfToken`) and refetched from `/api/auth/me` after reload. `auth/AuthContext.tsx` holds `loading | anonymous | authenticated`; `auth/RequireRole.tsx` is a UX-only route guard. Anonymous visitors see the existing demo mode (sample data, no session) unless the build sets `VITE_ENABLE_DEMO_ACCESS=false`. A 401 `unauthenticated` returns an authenticated client to `/login`; in demo mode the practice and companion areas show a sign-in notice instead. `requestTeacher` also sends the cookie/CSRF token and participates in session-expiry handling; it supports multipart, blob downloads and empty204 deletion responses. Student JSON validation remains strict.

Teacher authentication integration is implemented in this increment. Admin owners should build business routes with `current_user(role="admin")` and explicit access checks; there is no admin course bypass. Existing auth rate-limit limitations remain unchanged.

## Study lessons (STU-01)

Spec and contract: `workflow/specs/STU-01/`. Package `src/backend/study_lessons/`: `models.py` (`PublishedLesson`, `LessonCompletion`, migration `20261104_stu01_lessons`), `access.py` (`visible_lessons`, `get_visible_lesson`), `progress.py` (`completion_counts`, `completed_lessons`, `set_completion`), `schemas.py`, `routes.py` (`/api/study/*`, student role only; `Cache-Control: no-store` comes from the `add_no_store` middleware, which covers `/api/auth/` and `/api/study/` including error responses), `publish.py`, `seed.py`.

- STU-03 must call `get_visible_lesson(db, user, lesson_id)` to fetch lesson text as context; it is the only place that decides who may read a lesson (published, not withdrawn, member of the course; every other case is the same 404).
- STU-04 must read progress through `completion_counts(db, user_id, course_ids=None)` and `completed_lessons(db, user_id)`, not the tables. They count only non-withdrawn lessons in courses the user belongs to.
- TEA-03 publication calls `publish_lesson(db, draft, teacher)` after checking the teacher owns the draft's course; it flushes a new `published_lesson` row (topic copied from the source material) and the caller commits. The teacher publishing workflow below exposes publication. `withdrawn_at` is honoured on read; no code sets it.
- Completion is one row per (user, lesson) written by a single `INSERT ... ON CONFLICT DO UPDATE`; the request carries the wanted state, so repeats and races are safe. The user always comes from the session.
- Dev data: after `teacher_materials.seed`, run `uv run python -m study_lessons.seed` (two sample lessons for `demo-student`'s Software Engineering course). Not for production.
- Frontend: `services/lessons.ts` (shape-checked calls), `services/lessonMessages.ts` (exact error text), `pages/Materials.tsx`, `pages/Lesson.tsx`; the Overview stats are `OverviewStats` in `pages/Student.tsx` (STU-04). Lessons are rendered as text with `white-space: pre-wrap`. Nothing is stored in the browser. Identical in-flight GETs (`services/readOnce.ts`) share one request (StrictMode runs effects twice in development), but only within the same session and completion state: the key includes `getSessionGeneration()` (bumped by every `setCsrfToken` call, i.e. sign-in, sign-out, 401 clear) and a counter bumped before and after each completion PUT, so a request started earlier is never handed to a later page. The old sample lessons and `completed` demo state were removed.
- Known limits: past 500 lessons in a course the list keeps the oldest-published 500 (not topic order) and its count then differs from the Overview, which counts every lesson; a page opened while a completion PUT is still pending can show the earlier state until reload; the PUT body has no size cap; `?course=` matching on the Materials page is case-sensitive; the backend has no formatter; a withdrawal racing a completion PUT can leave the PUT's result visible once.

## State and preview actions

The app stores no tokens, credentials or user data in browser storage. Login submits credentials only to the shared authentication endpoint; passwords and session tokens are never stored in browser storage. Role switching is a demonstration control, not authorisation. Form drafts and selections use local React state. Teacher Materials uploads are validated and transmitted to the private backend store; teacher note generation transmits authorised source text to the SoC LLM through the backend and persists successful drafts. Other upload/generation previews do not transmit files. Preview messages explicitly state that no save, generation, publication, access change or delivery occurs.

Practice uses single-answer MCQs only, including code-reading questions expressed as choices. The Practice page (`pages/Practice.tsx`) renders the set named by the URL (`/student/practice/SETID`, from `GET /api/practice-sets/SETID`; the fixed set id is gone) and keeps one session in `PracticeProvider`, mounted above the student routes so answers and results survive navigation (not reload). The attempt is created on first submit; the page then saves all answers in one PUT, submits and reads the results, each as a separate step so a retry repeats only the failed step. 422 `incomplete` shows the server's missing list, 409 loads the results, and a 404 `attempt_not_found` at the save, submit or results step makes one new attempt and repeats save, submit and results (once per submission; a second one shows "Try again"). Radios stay locked while a retry only has to finish a step after the save. The attempt id is held in memory only and nothing is written to browser storage. The page never computes correctness: score, correct choice and explanations are rendered, as text, from the results response, which the server releases only after a submit. Answer keys live on the backend; CI scans every built frontend JavaScript chunk for fixture explanation text, with the dev seed (`teacher_publications/seed.py`) as a positive control. Teacher answers are fetched only through authorised teacher APIs. Teacher Materials and draft notes use PostgreSQL; source bytes use material_file BYTEA and generation receives only the authorised selected source. Teacher screens use saved records (the Overview report is TEA-05, below); admin screens not yet implemented still use placeholder data. Still to do: deployment configuration and lesson-aware AI context. Tests: the mocked Playwright suite needs no backend; `tests/real-backend.spec.ts` runs only when `REAL_BACKEND=1` (project `real-backend`) against a started backend, and the CI job "Real backend end-to-end" does this: `cd src/backend; uv run uvicorn main:app --port 8000`, then `cd src/frontend; REAL_BACKEND=1 npx playwright test --project=real-backend`.

## Development and verification

Continuous integration (`.github/workflows/ci.yml`) runs on every pull request into `master` and every push to it: backend tests; frontend typecheck, lint, format check, build and Playwright tests; the token tracker's and experiment scripts' unit tests; and a dependency audit that blocks on known vulnerabilities in runtime dependencies and only reports dev-only ones. It uses read-only permissions and no secrets. Plan and decisions: `workflow/specs/CI-01/plan.md`. Deployment is not built yet; options and open decisions are in `workflow/deployment.md`.

Use the startup/check commands in [README.md](../README.md). `package-lock.json` and `uv.lock` pin resolved dependencies. Local PostgreSQL credentials in the Compose file are development-only. Ignore rules exclude local env files, generated output, virtual environments, browser traces and dependency directories. Use `npm run format` to format frontend files and `npm run format:check` to check them.

Playwright exercises real UI behaviour with intercepted health responses. Backend tests independently verify the real API. Visual checks cover desktop/mobile and light/dark modes. Native form validation is used where appropriate; accessible labels, visible focus, a skip link, reduced-motion CSS and a mobile navigation drawer are included. This is not a full accessibility certification.

## Workflow records

`workflow/AppShellPlan.md` records scope, execution decisions and verification. `logs/AppShellSummary.md` summarises the development conversation and tool outcomes. `logs/WorkflowScaffoldingSummary.md` records the design discussion for the multi-agent workflow, including the original plans for comparing A (split verification), B (merged verification) and a single-session baseline. Those experiments have since run; the fair comparison in `workflow/experiments/stu02/fair/` and the decision in `workflow/experiments/results/stu02-decision.md` are the current evidence. Variant B is the chosen workflow. `logs/TrackerAndExperimentSetupSummary.md` covers the token tracker, the STU-02 experiment setup and a review of earlier work. `logs/Stu02FrontendSpecSummary.md` records the frontend spec, build and two fix rounds; its later status update records PR 5 as merged. `logs/PostPr5DocsSummary.md` records the documentation reconciliation. PRs 1–5 are merged; STU-02 backend and frontend work with the signed-in student (SHR-01) and, since STU-04, a PostgreSQL attempt store. Latest recorded checks are 65 mocked browser tests, 60 backend tests and one real-backend test (not re-run in the documentation session). GitHub CI results were not independently checked during that session. Deployment and the remaining student features are unfinished (real login, SHR-01, is built: see the authentication section below; the counts above are historical, and current ones are in `workflow/notes.md`); the shared SoC LLM client and the study companion first slice (STU-03) are built. TEA-01 teacher persistence is implemented as described below. These records do not claim all submission requirements are complete.

## Workflow files

Spec-driven, multi-agent workflow with approved STU-02 specs and completed experiment records; see `workflow/README.md` for the index. Feature specs distinguish implemented slices from future work.

| File | Purpose |
|---|---|
| `CLAUDE.md` | Project rules and read order for Claude Code. |
| `AGENTS.md` | The same rules plus all agent role definitions, for Codex. Keep in sync with `CLAUDE.md` and `.claude/agents/`. |
| `.claude/agents/*.md` | Claude Code agent definitions for the chosen workflow (Variant B): spec-writer, developer, test-designer, verifier. |
| `workflow/coordination.md` | Generator-verifier coordination pattern with an independent test designer, isolation rules, handoffs, revision caps, conflict resolution and how adherence is verified. |
| `workflow/variants/` | The workflow variants that were compared; B was chosen after the fair re-runs (A split verification, B merged verification with a single `verifier`, single-session baseline) and how to switch. |
| `workflow/notes.md` | Handoff log between agents and sessions. |
| `workflow/templates/` | Spec, plan, tasks and handoff templates. |
| `workflow/specs/` | Per-feature spec, plan and tasks. |
| `workflow/experiments/` | Context-engineering experiments, the resource log, and per-run usage summaries under `results/`. |
| `workflow/tools/token-tracker/` | Standard-library Python tool that reads Claude Code and Codex session logs and reports token use and cost. TRK-01 keeps the aggregate view; TRK-02 adds a per-feature-run Markdown report with one row per agent invocation (`workflow/specs/TRK-01/`, `workflow/specs/TRK-02/`). |
| `workflow/tools/speccheck/` | Standard-library Python tool that checks `spec.md`, `plan.md` and `tasks.md` for required sections, the UI states table, UI contract and labelled items before the build phase; run `python -m speccheck --all` there; waivers for pre-existing specs in `workflow/specs/speccheck-waivers.txt` (spec: `workflow/specs/CHK-01/`). |
| `workflow/security/` | Threat model and security test log. |
| `workflow/checklist.md` | Setup and submission checklist. |
| `.github/workflows/ci.yml` | Continuous integration on pull requests and pushes to `master` (plan: `workflow/specs/CI-01/plan.md`). |
| `workflow/deployment.md` | Deployment options, the SoC LLM network question, and open hosting decisions. |
| `docs/Reflections.md` | Evidence-backed reflections on the workflow experiments and frontend run; remaining topics are marked still to do. |

## Acknowledgements

Built with React, TypeScript, Vite, Material UI, Emotion, Lucide, React Router, FastAPI, Uvicorn, HTTPX, pytest, Playwright, ESLint and Prettier. Material UI supplies the controls and theme infrastructure; custom CSS provides layout and decorative code illustrations. No previous MP implementation was copied. Codex assisted implementation; Context7 supplied official library documentation. The decorative login quotation is attributed to B. B. King in the interface. Names, messages, course content and metrics are illustrative fixtures.


### TEA-01 failure and concurrency guarantees

Multipart ingestion enforces the 10 MiB limit in the parser callback before file chunks are spooled, with one file, at most two text fields, 1 KiB text parts and a total request bound of 10 MiB + 64 KiB for headers/fields. Parsed upload resources are closed on success and failure. This callback extends the installed Starlette parser; rerun chunked-ingestion regressions when upgrading FastAPI/Starlette.

Metadata and BYTEA content are flushed and metadata is serialized before one commit. Failure rolls back both; no permanent file or orphaned filesystem bytes exist. Back up/restore PostgreSQL for originals, metadata and drafts together. The 100 MiB upload budget excludes PostgreSQL overhead and other data; monitor the provider allowance. Shared extraction accepts bytes, decoding UTF-8 strictly or wrapping PDF bytes in BytesIO; sessions close before extraction/inference. Topic updates refresh their locked row so even a delayed clear-to-null writes the intended last-committed value. The UI ignores superseded course/filter requests and retries topics/materials together.

Backend `.env` is not loaded implicitly. Use `uv run --env-file .env` for Alembic, seed and Uvicorn as shown in the README. Frontend Vite loads its local `.env`; teacher data screens show the signed-in teacher and anonymous visitors see sign-in guidance without teacher requests.

## Teacher note drafts (TEA-02 notes slice)

Run `uv run --env-file .env alembic upgrade head` before starting this version. The additive revision creates `study_note_draft` and the material composite key. TEA-01's migration is frozen to its original historical schema so both fresh installs and upgrades work. See [SharedDataContract.md](SharedDataContract.md) and [TEA-02 contract](../workflow/specs/TEA-02-notes/plan.md).

The AI content studio now uses generate/list/get endpoints under `/api/teacher`. It reuses shared session authentication, current teacher/course checks and authorised stored bytes. Strict UTF-8 text and pypdf extraction are capped at 8,000 normalised characters/100 pages; no OCR or truncation. An unchanged `llm_client.get_llm_client` dependency supplies exactly one bounded call (`max_tokens=600`, caller `teacher:{id}`); fixed source-only context is separate from trusted instructions. No database transaction remains open during the model call. Session, role, membership and source are rechecked and locked before a new draft is inserted; output must be nonblank and shorter than 2,000 characters; length-finished replies and PostgreSQL-unrepresentable NUL/unpaired-surrogate output are rejected with502 llm_bad_response before persistence. Failed requests preserve sources/older drafts.

Set `SOCLAAS_BASE_URL`, `SOCLAAS_API_KEY`, `SOCLAAS_MODEL` in the ignored backend `.env`, then restart with `--env-file .env`; do not commit credentials. Existing shared per-caller limits/retries apply, with teacher caller IDs separate from student IDs. Browser generation requests use 45 seconds and no automatic retry; a response lost after commit can lead to a second draft on explicit retry (no idempotency yet). The UI renders escaped plain text and preserves line breaks. Drafts persist and remain unpublished. TEA-03 adds explicit editing below, completing the editable-notes portion of US-TEA-02-01.

Tests override the shared dependency with a fake; no provider credentials or live calls are needed. Use the existing isolated `TEA01_TEST_DATABASE_URL` schema fixture and temporary files only where needed, never the development database. Teacher requests use authenticated sessions, and ignore spoofed demo headers. PDF extraction is not process-sandboxed; stronger resource isolation belongs in a production hardening increment.


## Draft note editing (TEA-03)

Apply `uv run --env-file .env alembic upgrade head` from `src/backend` before running against an existing development database. Migration20261102_tea03 backfills immutable source_title, version1, updated_at=created_at and updated_by=created_by without changing content. Downgrade retains titles/content but drops edit metadata; re-upgrade cannot recover the earlier source snapshot after a title edit. TEA-02 merged through PR11 (`040dc07`); the user reported a successful real generation on2026-11-02. This is user-reported evidence, not an automated provider check.

PATCH `/api/teacher/note-drafts/{draft_id}` accepts exactly title, content and a strict positive integer version. It authorises the existing identity/current membership before reading the body, validates/normalises text, then locks user/membership and the current draft through commit. One concurrent version wins; stale writes return409 draft_conflict. Successful edits increment version and update server-resolved editor/time; original attribution and source/course references do not change. PostgreSQL-unrepresentable NUL/unpaired-surrogate text is422. Other invalid fields are422 validation_error and database failures503 service_unavailable. Lists retain creation-time/ID order. No editing operation calls an LLM or publishes a record.

The existing course list/get/create responses add source_title, version, updated_at and updated_by. `NoteDraftEditor` owns the local edit buffer and conflict recovery; the content studio updates persisted list/view state on successful saves. Canonical validation counts Unicode code points and matches Python whitespace trimming; raw differences still trigger unsaved warnings. The entrypoint uses a data router (wildcard App route) so useBlocker guards pathname/search/history changes without rewriting the existing route tree. Pending saves block departure; settled saves cancel any pending navigation and stay on the page. Native unload warnings cannot guarantee persistence and no local edits are stored. Automated tests use isolated schemas/files and fake generation clients, never a live model.


## Teacher MCQ drafts (TEA-02 MCQs)

TEA-03 note editing merged through PR12 (`3069053`). Apply `uv run --env-file .env alembic upgrade head` from `src/backend`; revision `20261102_tea02_mcqs` adds only MCQ batch/question tables. This implements US-TEA-02-02 and MCQ preview, with correction now implemented below; immutable publication is implemented below; student practice attempts/companion integration remains deferred. See [SharedDataContract.md](SharedDataContract.md) and [MCQ contract](../workflow/specs/TEA-02-mcqs/plan.md).

Teacher MCQs reuse the current source extraction, database bytes and access checks. One unchanged shared-client call uses `max_tokens=800`, fixed system/source-only user messages and caller `teacher:{id}`; no transaction stays open during inference. A strict JSON parser rejects duplicate keys, nonfinite values, wrong shapes/types/counts, duplicates, invalid Unicode and clipped/length-finished replies. Exactly three validated questions are saved atomically only after access/source rechecks with locks. Existing sources/notes are untouched. Shared teacher LLM messages now say content; codes/retry semantics and the generic client/student behaviour are unchanged.

The studio uses route-selected Study notes/Practice questions tabs. Question URLs use `/teacher/generate?tab=questions&course={id}&batch={id}`; notes URLs and dirty-editor blockers remain intact. Typed services validate batch responses, generation uses45 seconds and no automatic retry; stale responses cannot replace another selection. Source/course/batch controls disable during MCQ generation. Output is escaped plain text. Published batches now have safe student read APIs; existing attempts and companion are not connected to them. Tests use the isolated PostgreSQL schema/temp-file fixture and fake client only; no live provider calls.


## Shared teacher studio lifecycle

`hooks/useTeacherStudioSources.ts` owns course/source/list loading, retry and stale-GET cleanup for both notes and MCQs; detail fetching and feature-specific editors/viewers remain separate. `hooks/useStudioGeneration.ts` owns duplicate-request prevention and a monotonic navigation/selection lifetime. Any committed navigation or source/course/draft departure permanently invalidates an outstanding success/error, including a Back/Forward round trip to the same selection; leaving the component also invalidates it. These guards suppress obsolete UI changes, not an already-running server generation.

`text_validation.is_postgres_text` shares representability checks across teacher upload titles, generated notes/MCQ fields and manual note edits. `text_validation.normalise_newlines_and_trim` is the one newline and whitespace normaliser for generated notes, generated MCQ fields and manual note edits. Generation failures from the shared client map to API errors in one place, `llm_errors.generation_error` (the study companion keeps its own mapping with different codes). Each caller retains its own limits and error ownership: invalid user titles/edits422, unusable generated content502. Valid Unicode including astral characters remains supported. No database migration or shared LLM-client change is needed for these corrections.


## Authenticated MCQ editing and deletion (TEA-03-mcqs-cleanup)

PR15 merged database file storage; PR16 merged authentication. The current contract is [TEA-03-mcqs-cleanup](../workflow/specs/TEA-03-mcqs-cleanup/plan.md). Apply `uv run --env-file .env alembic upgrade head`; additive revision `20261104_tea03_mcq_edit` follows authentication and backfills batch version1/editor/creation timestamp. Downgrade removes audit columns only; re-upgrade resets their baseline from original creation, without reverting edited question values.

PATCH `/api/teacher/mcq-drafts/{id}` takes exactly version and all three existing question IDs plus question/choices/correct_choice_index/explanation. Each ID occurs once; positions and original attribution are immutable. Strict types, normalized Unicode lengths and casefold duplicates match generation, but manual edits have no aggregate model-reply cap. The batch lock makes three-question updates atomic; stale versions return409 draft_conflict. Complete/list responses add version/updated_at/updated_by; creation ordering is unchanged.

DELETE note-drafts/{id} and mcq-drafts/{id} require one positive ASCII decimal version query; material deletion has no version. Success204 has no JSON. A missing/deleted/inaccessible item is404; stale version409 draft_conflict; referenced source409 material_in_use; restrictive draft references409 draft_in_use. Deletions roll back together on failure, explicitly delete batch questions, and remove original bytes with material metadata. Source deletion shares quota advisory lock32272610 and locks the source against generation's final source check. The logical100MiB original-byte quota is reusable after commit; physical database reclamation is not immediate. Back up PostgreSQL including metadata, originals, drafts and auth records.

All teacher APIs reuse shared auth and course checks. Unsafe transactions hold session/user/membership locks through commit; generation closes its initial transaction before inference and reauthenticates the same cookie in a fresh locked transaction before saving. Expired/revoked sessions, role or membership changes during inference prevent persistence. Session expiry/logout unmounts account-owned teacher views and invalidates old responses; failed logout preserves the editor. MCQ editing shares a focused navigation guard and text helpers with notes, not a generic editor framework. Deletion uses explicit accessible confirmations, no automatic retries, and ownership guards for late responses. Editing/deletion never invokes the model. Published references now block originating draft/question deletion.


## Batch publication scope

PR17 merged authenticated teacher editing/deletion. Teacher publishing now implements the approved [publication specification](../workflow/specs/TEA-03-publishing/spec.md). One reviewed batch becomes exactly one three-question set. The old `/teacher/practice` URL redirects to the questions studio; no assembly workflow exists.

## Teacher publication implementation

The publication migration is `20261105_tea03_publications`, followed by independent ADM-05 `20261106_adm05_access` and STU-04 `20261105_stu04_practice_attempt` branches, joined by `20261106_merge_adm05_stu04`; run `alembic upgrade head` to apply both branches. No historical revisions were rewritten. The migration preserves lessons/completion rows, adds nullable lesson `source_version`, adds batch `(id,course_id)` uniqueness, and creates immutable practice-set/question tables. Downgrade refuses while published sets or nonnull lesson publication provenance exist; it never silently deletes them. Use isolated databases for migration tests.

`teacher_publications.routes` exposes teacher POST publication, per-course catalogue and snapshot detail APIs plus safe student set list/detail reads. It reuses cookie sessions, CSRF, course checks, READ COMMITTED and no-store responses. Origin row locks serialize publish/edit/delete; publication checks existing snapshots before comparing the current draft version. Exactly matching version/title/topic retries return 200; first writes return 201, stale unpublished versions return 409 `draft_conflict`, and different or ambiguous/legacy prior publication returns 409 `already_published`. Both POSTs accept exactly `{version,title,topic_id}`. Titles use trimmed Unicode length 1–200, strict positive integer versions and a required same-course topic. Copies and provenance commit atomically, without inference.

`study_lessons.publish_lesson(db,draft,teacher)` retains its caller-owned transaction and append-snapshot behavior. Optional keyword title/topic overrides affect only the snapshot; new snapshots capture `draft.version`. HTTP publish-once policy lives under the origin lock, not in a lesson uniqueness constraint. Existing nullable-topic/legacy rows retain their semantics. Withdrawn lessons also block republishing.

Teacher GETs share only identical in-flight reads keyed by session generation, mutation epoch, URL, response mode and timeout. Epochs advance before and after mutations; completed reads are not cached. Selection lifetimes invalidate pending sharing before new read effects, so an abandoned A selection cannot rejoin its old request on A→B→A; StrictMode effect replay retains its unchanged lifetime. The studio separately loads publication status and topics; successful POSTs update status locally. Default publication requests use 10 seconds, generation retains 45 seconds, and unsafe requests never retry automatically. Account-owned views, route epochs and effect cleanup ignore stale results. Existing editor blockers continue protecting unsaved work; publishing introduces no additional blocker.

Notes use existing student Materials/completion APIs unchanged. Published MCQs map answer indices to choice IDs a–d and omit keys, explanations and private provenance from student DTOs. Student practice, progress and the companion read published sets through `set_provider` (STU-02-published-sets); STU-04 persists attempts in PostgreSQL. Product help text is in `companion_help.py`.
## ADM-05 account lifecycle and course management

The live admin screens are `/admin/users` and `/admin/courses`. All `/api/admin/*` routes use cookie authentication, the admin role, shared CSRF/Origin checks and `Cache-Control: no-store`. `admin_access/routes.py` owns strict input/API handling; `admin_access/service.py` owns account lifecycle and membership transactions. Creating a course also inserts exactly one General topic in the same transaction so existing teacher publication forms can select it. Existing courses are unchanged. The approved exact API/UI contract is in `workflow/specs/ADM-05/plan.md`.

Account creation success uses a green, dismissible six-second toast; all text/password inputs reset while Account role retains its selection (initially Student). Details open immediately in a scrollable modal, including loading/error states, with nested destructive confirmations and Close/Escape/backdrop dismissal when no write is pending. The shared sidebar keeps its logout footer inside the viewport; navigation scrolls on short windows and long names cannot push logout out. Fresh-context login regressions exercise the saved form password rather than seed credentials.

`tests/real-backend.spec.ts` also has opt-in admin-created student/teacher login checks using independent browser contexts, a real API/database and no API mocks. Run only with an isolated test database and administrator: the real-backend project additionally requires `E2E_ALLOW_ADMIN_ACCOUNT_CREATION=1`, `E2E_ADMIN_EMAIL` and `E2E_ADMIN_PASSWORD` for these cases. They create disposable accounts, verify fresh login and reload, and capture overlay screenshots. Normal mocked runs exclude this file; existing real-backend CI does not create accounts unless explicitly opted in. Never point these creation checks at production data.

### Local admin setup and password reset (PowerShell)

Prerequisites: Git, uv, Node/npm and Docker Desktop as in [README](../README.md). Run commands from inside this checkout. Existing env/database settings must be preserved; no default admin credentials are shipped. Public signup creates students only. No SoC credentials are needed for ADM-05 or mocked tests.

**1. Prepare env files and PostgreSQL.** Start Docker Desktop, then run:

```powershell
Set-Location (git rev-parse --show-toplevel)
docker compose up -d postgres
docker compose exec -T postgres pg_isready -U learnswe -d learnswe
if (-not (Test-Path src\backend\.env)) { Copy-Item src\backend\.env.example src\backend\.env }
if (-not (Test-Path src\frontend\.env)) { Copy-Item src\frontend\.env.example src\frontend\.env }
notepad src\backend\.env
```

The readiness command should report `accepting connections`. If PostgreSQL is still starting, repeat that check before creating a database or running migrations.

**2. Update `src/backend/.env`.** Keep existing database/SoC values and replace existing assignments rather than adding duplicate keys. For a fresh setup, the template uses the database URL below. Credentials here are public **local-test examples**, never shared/production credentials:

```dotenv
DATABASE_URL=postgresql+psycopg://learnswe:learnswe-local-only@127.0.0.1:5433/learnswe_db_files
APP_ENV=development
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=lax
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
SEED_ADMIN_EMAIL=adm05-test@example.com
SEED_ADMIN_PASSWORD='ExampleOnly!7Qm#42vL'
```

Save the file. Quoting keeps `#` literal; do not enter quotes in the login form. `.env` is ignored; never commit credentials. Optional `SEED_STUDENT_EMAIL`/`SEED_STUDENT_PASSWORD` and `SEED_TEACHER_EMAIL`/`SEED_TEACHER_PASSWORD` pairs configure fixed demo accounts; incomplete pairs are skipped. SOCLAAS settings are required only for actual generation/chat, not login.

**Fresh database only:** when using `learnswe_db_files`, create it only if missing. Skip this block when retaining a different existing `DATABASE_URL`; ensure that database is reachable instead. This block preserves any existing database:

```powershell
Set-Location (git rev-parse --show-toplevel)
$adm05DatabaseExists = docker compose exec -T postgres psql -U learnswe -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'learnswe_db_files'"
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect PostgreSQL; check Docker Desktop and the postgres service.' }
if (($adm05DatabaseExists -join '').Trim() -ne '1') {
    docker compose exec -T postgres createdb -U learnswe learnswe_db_files
}
```

**3. Apply migrations and seed, then start the backend.** Apply the additive `20261106_adm05_access` migration before starting the updated backend. Existing users default to enabled; `User.access_status` is enabled/disabled/archived and `archived_at` records irreversible archival. Downgrade refuses while any disabled/archived account exists, rather than silently granting access. Do not edit old migrations. Stop any existing backend with Ctrl+C in its terminal first:

```powershell
Set-Location (git rev-parse --show-toplevel)
docker compose up -d postgres
Set-Location src\backend
uv sync --frozen
uv run --env-file .env alembic upgrade head
uv run --env-file .env python -m teacher_materials.seed
uv run --env-file .env python -m auth.seed
uv run --env-file .env uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

`demo-admin: seeded` means credentials were saved; `unchanged` keeps the previous hash/email; `skipped` identifies missing or invalid settings. Resolve wrong-role/email-conflict errors rather than ignoring them. Seed email is normalised; passwords are not trimmed or printed. Admin-created accounts are not seed targets. Roles remain fixed; no end-user password reset/change flow exists.

**4. Explicitly reset an existing seed password after editing `.env`.** Run in another terminal, or before starting the backend in step 3:

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location src\backend
uv run --env-file .env python -m auth.seed --reset-passwords
```

Changing `.env`, restarting the API, or rerunning the seed without this flag does not replace an existing hash. The flag applies **every configured seed role**, not just admin, and can update configured emails subject to uniqueness. It does not enable disabled accounts, restore archived accounts or revoke sessions. For a password-change test, keep the email unchanged, sign out, check the old password fails once, then check the new password succeeds. Do not infer success from an already-open authenticated session. Repeated failed attempts trigger the login limiter.

After changing backend settings such as `ALLOWED_ORIGINS`, fully stop and restart the `uv run --env-file .env uvicorn ...` command. Uvicorn `--reload` does not refresh the environment loaded by its parent `uv` process. Seed commands are separate processes and read saved `.env` values each time. Vite proxies with `changeOrigin: true`; explicitly allow the frontend origin instead of disabling Origin/CSRF checks.

**5. Configure/start the frontend in a second terminal.** Edit **`src/frontend/.env`**:

```powershell
Set-Location (git rev-parse --show-toplevel)
notepad src\frontend\.env
```

```dotenv
API_PORT=8000
VITE_ENABLE_DEMO_ACCESS=true
```

If `API_PROXY_TARGET` is present, set it to `http://127.0.0.1:8000` or remove it to use `API_PORT`; the target overrides the port. Never put secrets in `VITE_*` variables. Save, stop any running frontend with Ctrl+C, then run:

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location src\frontend
npm.cmd ci
npm.cmd run dev
```

`npm.cmd` avoids PowerShell's `npm.ps1` execution-policy error. Restart the frontend after its `.env` changes. Open **http://127.0.0.1:5173/login**, use Sign in with the configured admin email/password without quotes, and follow the [account/course walkthrough](UserGuide.md#try-account-and-course-management-locally). Demo shortcuts and login role tabs do not grant a real admin session. Account creation sends the password once, confirms it on the client, never returns hashes/passwords/session metadata, and clears secret fields on success/unmount.

**6. Diagnose failures using the Network response, not just the Uvicorn status line.**

| Request/status | Interpretation and recovery |
|---|---|
| Initial `/api/auth/me` 401 | Expected before login. |
| Login 200 and admin workspace | Configured account authenticated successfully. |
| Login 401 `invalid_credentials` | Wrong credentials or inactive account; deliberately indistinguishable. Check seed output/reset flag and account status. |
| Login 403 `csrf_failed` | Origin mismatch. Allow the exact frontend scheme/host/port and restart API. Login validates Origin; it does not need a pre-existing session CSRF token. |
| Login 200 followed by `/api/auth/me` 401 | Inspect cookie retention. Local plain HTTP needs `SESSION_COOKIE_SECURE=false` and a full API restart; production HTTPS keeps Secure enabled. This does not explain an initial login 401. |
| Protected request 403 `forbidden` | Wrong role; selecting the Admin demo tab does not alter the account role. |
| Protected write 403 `csrf_failed` | Invalid session CSRF token or disallowed Origin. Sign in again and check settings. |
| Login 429 `rate_limited` | Wait for retry time. Defaults are 5 failures/email or 20/IP in 900 seconds. The limiter is process-local, so a local restart clears it. |
| API 503 or network error | Check configuration, PostgreSQL/migration head, proxy target and running processes; not proof of a wrong password. |

The [UserGuide sign-in walkthrough](UserGuide.md#set-up-local-admin-sign-in-powershell) provides the user-facing steps. These local settings are not a production deployment configuration.

### Lifecycle implementation and automated verification

Admin writes and login issuance share a transaction advisory lock so concurrent lifecycle changes cannot reactivate/archive users inconsistently or issue sessions after disable commits. The acting admin is rechecked after lock acquisition. Session rows are deleted before account updates, respecting teacher writes' existing session-then-user lock order. Every subsequent protected request rejects inactive users. The same `course_membership` composite key stores student enrolment and teacher management; immutable roles give each row its meaning. Revocation deletes memberships without deleting completion or authorship. Archive retains the user/email/history and deletes sessions/memberships atomically. Repeated grants/removals are idempotent; opposite actions follow transaction lock processing order. Self-disable/archive and removal of the last enabled administrator are rejected.

Teacher generation already closes its initial transaction before the model call and rechecks session/account/course access before saving results. The student companion now rechecks its session/account in a fresh transaction before releasing generated text. Its static practice fixtures do not have course mappings; ADM-05 does not introduce course-grounded retrieval. Any future course context must enforce membership on retrieval and again before output. No live model calls are needed for tests.

For automated backend testing, set `TEA01_TEST_DATABASE_URL` to a disposable PostgreSQL service/database; the existing fixture creates and removes a unique schema. Never point `DATABASE_URL` directly at a developer schema for tests. On Windows use `PGCONNECT_TIMEOUT=2` so the existing unavailable-database test does not wait indefinitely. Example for the repository's documented local Docker service:

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location src\backend
$env:TEA01_TEST_DATABASE_URL = 'postgresql+psycopg://learnswe:learnswe-local-only@127.0.0.1:5433/learnswe'
$env:PGCONNECT_TIMEOUT = '2'
uv run pytest -q --basetemp .pytest_cache/adm05-local-tests
```

Use a fresh dedicated basetemp path for each simultaneous pytest run; pytest owns and clears that directory. The ignored `.pytest_cache` location avoids inaccessible old Windows TEMP directories. To run ADM-05 only instead, replace the last command with:

```powershell
uv run pytest -q tests/test_adm05_access.py tests/test_adm05_migration.py --basetemp .pytest_cache/adm05-focused-tests
```

Frontend tests intercept APIs; no running backend or live SoC service is needed. Run **one browser-test runner at a time** and stop manually started frontend servers first so the harness owns its ports. Do not overlap full/focused runs against shared servers/output directories:

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location src\frontend
npm.cmd ci
npx.cmd playwright install chromium
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npm.cmd test -- --workers=2 --output=test-results/adm05-full
```

For only ADM-05 browser tests, replace the last command with `npm.cmd test -- tests/adm05-access.spec.ts --workers=2 --output=test-results/adm05-focused`. API checks include anonymous/student/teacher rejection, CSRF/Origin, fixed-role creation, disable/fresh-login re-enable, archive/email reservation, cross-course denial, repeated/concurrent assignments, last-admin races and withholding AI after revocation. Mock the SoC client; keep fixtures isolated.

## Progress dashboard (STU-04)

History-test synchronization: wait for the destination page heading before Back or Forward. React Router can update the URL before React commits the view; a URL assertion alone does not establish a page visit. The navigation regression retains exact progress-request counts of 1, 2 and 3.

Spec and contract: `workflow/specs/STU-04/`. `GET /api/progress` (student role only; user from the session; `Cache-Control: no-store`) feeds both the Progress page and the Overview stats.

- Storage: migration `20261105_stu04_practice_attempt` and `attempt_models.PracticeAttempt` (table `practice_attempt`: opaque `id`, creation order `seq`, `status` in_progress or submitted, `answers`, score, `key_version` and `correct_question_ids` stored at submission, `submitted_at`; CHECKs keep submitted rows complete). `attempt_store.DbAttemptStore` replaces the in-memory store. Interface: `create`, `get_owned` (None if unknown or not owned), `list_for_student`, `lock` (see the practice section; an unknown id raises 404 `attempt_not_found`; a row already submitted is never rewritten) and `submitted_summaries(student_id)` (per set: submitted count, best and latest submitted attempt, computed in SQL with window functions; in-progress attempts never appear). The store opens its own short session per call, so routes need no session.
- `practice_data.Question.topic_id` (optional topic UUID); the provider sets it to the published set's topic for every question. If the topic row is missing the topic is reported as "General". `practice_logic.correct_question_ids` is the only place besides scoring that reads the key.
- Rule: `progress_rules.py` holds `MIN_ANSWERS_FOR_TOPIC = 3`, `WEAK_BELOW_PERCENT = 60`, `RECENT_LESSON_LIMIT = 5`, `topic_status` and `accuracy_percent` (integer arithmetic; weak means `correct * 100 < 60 * answered`). The response returns the two numbers as `topics.rule`, and the page text is built from them.
- `progress_service.build_progress(db, student_id, attempts, sets)` reads lesson figures only through `study_lessons.progress` (`completion_counts`, `completed_lessons`, and the new `member_courses`, also used by `GET /api/study/courses`), tallies the latest submitted attempt of each set by topic, resolves topic names with one query and sorts. `progress_schemas.py` holds the response models; none carries answers, question text, choices or ids of attempts. `progress_routes.py` is the thin route.
- Frontend: `services/readOnce.ts` (shared in-flight GET sharing, moved out of `lessons.ts`), `services/progress.ts` (shape-checked `getProgress`), `services/progressMessages.ts` (exact error texts), `pages/Progress.tsx`, `OverviewStats` in `pages/Student.tsx`, `Stat` has `role="group"` named by its label. `weeklyActivity` stays in `data.ts` because the admin sample page still uses it.
- Known limits: progress counts only sets the student can currently access (STU-02-published-sets); there is no cap on attempts per student; attempts made before the migration are lost.

### ADM-05/STU-04 migration integration

The additive no-op merge revision `20261106_merge_adm05_stu04` joins both historical migration heads. Existing installations at either feature head use the same `uv run --env-file .env alembic upgrade head` command; the missing branch applies before the join. Account status and saved practice attempts are preserved. Feature migration tests pin their own revisions, while `test_adm05_stu04_merge_migration.py` verifies one final head and populated upgrades from either parent. Use the merged application after migration.

## Shared shell confirmation and tip dismissal

Sidebar tips remain available in short windows, including the mobile Open companion shortcut;
the navigation list scrolls while the account/logout footer stays in the viewport. Progress loads
depend on the router history-entry key as well as retry state, associating reads with navigation
instead of relying only on a component unmount and remount.

`Shell` owns per-role/account tip dismissal in memory (no browser storage); desktop/sidebar drawer share the same dismissed state until refresh/remount. The X control is labelled Dismiss sidebar tip. Explicit Log out opens Confirm logout, with Cancel and Log out. Opening/cancelling makes no request; confirm sends the existing cookie/CSRF request once. Pending state disables buttons and Escape/backdrop dismissal; network/5xx failure preserves the dialog/session for retry. A logout401 still clears locally, and expired sessions never wait for confirmation. Student, teacher and admin flows share this behaviour. Existing editor/chat/history safeguards run after completed logout, not when the dialog opens. Specs: SHR-01 shared-shell follow-up, ADM-05 AC23-27 and STU-01/STU-04 synchronisation notes.

## Practice on published sets (STU-02-published-sets)

Spec and contract: `workflow/specs/STU-02-published-sets/`. No migration of its own; check that the repository still has exactly one Alembic head with `uv run alembic heads`.

- `set_provider.py` is the only place that reads `published_practice_set` and `published_practice_question` for students and the only place that decides which sets a student can see (one join to `course_membership`). `SetProvider` has `get_for_student`, `get_many_for_student`, `catalog_for_student(student_id, course_id=None, per_course_limit=None)` and `accessible_sets` (newest 200). It maps rows to `practice_data.PracticeSet`: ids are UUID strings, choice ids `a` to `d` in stored order, `correct` from `correct_choice_index`, `code` null, `topic_id` the set's topic, key version `v1`. It returns nothing for an id that is not canonical lowercase UUID text and never falls back to fixture data. Routes receive it with `Depends(get_set_provider)`; `build_progress(db, student_id, attempts, sets)` takes it as `sets`. `auth.db.open_session()` gives it (and `attempt_store`) a short session.
- `practice_routes.py`: set ids from the URL go through `teacher_access.parse_uuid` (422 `validation_error` for a non-UUID, e.g. `intro-se-1`); a set the student cannot access, unknown or not a member, is 404 `set_not_found`. Every attempt endpoint checks ownership (404 `attempt_not_found`) and then the set for the same student (404 `set_not_found`, so removing a membership blocks reads and results). New `GET /api/practice-sets` returns the member courses with their sets and the caller's best score (`practice_schemas.PracticeCatalogOut`, at most 100 sets per course); `practice_schemas.public_set` is the one answer-free view of a set. `/api/practice-sets` and `/api/attempts` responses carry `Cache-Control: no-store`.
- Companion: only the lookup changed. A `set_id` without an attempt must be a UUID (422), a set the student cannot access is 404 before any model call, and the pasted-question match and help-mode leak scope use `accessible_sets`.
- Teacher-folder edits (brief the teacher): `teacher_publications/routes.py`, functions `student_sets` and `student_set` only, now call the provider and `public_set` with unchanged URLs, shapes and errors; new `teacher_publications/seed.py`; `tests/test_tea03_publications.py` gets a rewrite of the part that asserted the old flow (a test-designer task).
- Dev seed (development databases only; refuses unless `APP_ENV=development`): after migrations and `teacher_materials.seed`, run `uv run --env-file .env python -m teacher_publications.seed` from `src/backend`. It adds the set "Software engineering practice" (three questions, with the material and draft rows its foreign keys need) for `demo-student`'s course, idempotently and without overwriting rows. CI runs it in the real-backend job.
- Tests: the fixture set lives in the tests (`tests/fake_sets.py`, a `FakeSetProvider` installed with `app.dependency_overrides[set_provider.get_set_provider]`); database tests insert published rows.
- Frontend: `config.ts` is deleted. `services/practice.ts` has `listPracticeSets`; `services/practiceMessages.ts` holds the exact picker and not-available texts; `pages/PracticePicker.tsx` is the picker; `pages/Practice.tsx` takes `setId` from `/student/practice/SETID` (via `Student.tsx`); `PracticeContext.loadSet(setId)` resets all state when the set id changes and tracks `unavailable` ("load" for a 404 or 422 on load, "later" for a 404 `set_not_found` at save, submit or results) and `forbidden`; `StudyCompanion` sends the URL's set id and the submitted attempt id only when the practice state belongs to that set.

## ADM-07: AI usage recording and report (formerly ADM-06)

### ADM-06 local setup

Prerequisites:

- Git, uv, Node/npm and Docker installed.
- Existing `src/backend/.env` and an enabled admin account.
- Keep your existing database and credentials.
- First-time account? See [local admin setup](#local-admin-setup-and-password-reset-powershell).
- Local HTTP: `SESSION_COOKIE_SECURE=false`; allow the frontend origin in `.env`.
- Frontend `.env`: `API_PORT=8000`. If `API_PROXY_TARGET` exists, use `http://127.0.0.1:8000`.
- SoC credentials are needed only for real chat/generation, not mocked tests.

**1. Stop backend workers with Ctrl+C. Start PostgreSQL and migrate.**

Windows — PowerShell:

```powershell
Set-Location (git rev-parse --show-toplevel)
docker compose up -d --wait postgres
Set-Location src\backend
uv sync --frozen
uv run --env-file .env alembic upgrade head
```

macOS/Linux — bash or zsh:

```bash
cd "$(git rev-parse --show-toplevel)"
docker compose up -d --wait postgres
cd src/backend
uv sync --frozen
uv run --env-file .env alembic upgrade head
```

**2. Start the updated backend. Leave this terminal running.**

Windows:

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location src\backend
uv run --env-file .env uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

macOS/Linux:

```bash
cd "$(git rev-parse --show-toplevel)/src/backend"
uv run --env-file .env uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**3. In a second terminal, activate collection.** Every backend worker must use the updated code first.

Windows:

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location src\backend
uv run --env-file .env python -m ai_usage.activate --feature STU-03 --feature TEA-02
```

macOS/Linux:

```bash
cd "$(git rev-parse --show-toplevel)/src/backend"
uv run --env-file .env python -m ai_usage.activate --feature STU-03 --feature TEA-02
```

Expected: `AI usage coverage activated; existing starts and gaps preserved.` Repeating activation preserves the original start.

**4. In a third terminal, start the frontend.** Stop the old frontend first. Its proxy must point to backend port 8000.

Windows:

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location src\frontend
npm.cmd ci
npm.cmd run dev
```

macOS/Linux:

```bash
cd "$(git rev-parse --show-toplevel)/src/frontend"
npm ci
npm run dev
```

Open **http://127.0.0.1:5173/login**. Open **Feature Analytics** and scroll to the AI usage section (see the ADM-07 User Guide section).

- Initial seven-day results can be **Unavailable**. No backfill.
- For numeric totals, select dates starting after activation's next UTC midnight.
- Do not backdate coverage or clear gaps to manufacture complete data.

### ADM-06 automated tests

Mocks and isolated data. No live AI. No wait for UTC midnight.

**Backend — 77 ADM-06 cases.** Start Docker Desktop/the Docker daemon first. The connection below is for the repository's local Docker service. The fixture creates and removes a unique test schema. Do not add `--env-file .env` to these test commands.

Windows:

```powershell
Set-Location (git rev-parse --show-toplevel)
docker compose up -d --wait postgres
Set-Location src\backend
uv sync --frozen
$env:TEA01_TEST_DATABASE_URL = 'postgresql+psycopg://learnswe:learnswe-local-only@127.0.0.1:5433/learnswe'
$env:PGCONNECT_TIMEOUT = '2'
uv run pytest -q tests/test_adm06_transport.py tests/test_adm06_usage.py tests/test_adm06_migration.py --basetemp .pytest_cache/adm06-guide
```

macOS/Linux:

```bash
cd "$(git rev-parse --show-toplevel)"
docker compose up -d --wait postgres
cd src/backend
uv sync --frozen
export TEA01_TEST_DATABASE_URL='postgresql+psycopg://learnswe:learnswe-local-only@127.0.0.1:5433/learnswe'
export PGCONNECT_TIMEOUT=2
uv run pytest -q tests/test_adm06_transport.py tests/test_adm06_usage.py tests/test_adm06_migration.py --basetemp .pytest_cache/adm06-guide
```

Expected: **77 passed**, with no skipped database tests. Covers attempts/retries, tokens, unavailable data, permissions, concurrency and migration. Use a fresh terminal for normal development afterward.

Browser coverage of the AI usage section lives in `tests/adm07-retained-aiusage.spec.ts` (run with `npm test -- tests/adm07-retained-aiusage.spec.ts --project=mocked` in `src/frontend`).

### ADM-06 implementation notes

- Report layout (hub AI usage section): reasons 14px, caption 16px; the caption text sits in a span capped to the scroll region width (`.analytics-caption-fit`, inline-size container), so table semantics and accessible name are unchanged. The report is read by `services/aiUsage.ts` from `GET /api/admin/ai-usage`.
- `ai_usage`: metadata only. No prompts, replies, credentials or user identifiers.
- Production: `SoclaasClient` + `DatabaseAttemptObserver`. Each retry gets a record. Standalone test clients may omit the observer; production clients must not.
- `usage_feature`: server-owned context; resets after each call. STU-03, TEA-02, ADM-03 and ADM-01 calls are recorded by the shared observer under their own labels; the report shows ADM-03 and ADM-01 as `not_enabled` until their coverage is activated (ADM-01 grading is an allowed label with no activation toggle).
- Mapping: `usage.prompt_tokens` → input; `usage.completion_tokens` → output; `usage.total_tokens` → total. Independent recorded values only; live availability unverified.
- Tokens: nonnegative signed-64-bit integers. Invalid/missing fields stay null; report totals above JavaScript's safe integer range become unavailable.
- Provider 2xx = service success, even if feature validation later fails. 429 = rate-limit failure; other non-2xx/transport errors = other failure.
- Reservation failure blocks dispatch. Finalisation failure leaves pending; all affected totals become unavailable. Domain rollback cannot erase attempts.
- Atomic finalisation: identical replay accepted; conflicting replay cannot overwrite.
- Report: active admins; strict filters; REPEATABLE READ cutoff; private/no-store and Vary: Cookie.
- Limits unchanged. Report throttle: 30 requests/60 seconds/admin, process-local.
- Browser: memory only; clears on session/navigation/new request; 15-second timeout; no automatic retry.
- Coverage: forward-only. No backfill, retention deletion or gap-recovery tool. Downgrade removes usage metadata.
- Production deployment: GitHub Actions; replace every worker before activation.
- Contract: the retained ADM-06 criteria are in `workflow/specs/ADM-07/retained-criteria.md` (the old ADM-06 spec was removed in ADM-07 phase 5).

## TEA-05: teacher learning overview

- Endpoint: `GET /api/teacher/overview?period=7d|30d|all` (`teacher_overview/routes.py`). Order of checks: `teacher_session` (401/403, database failure 503 `service_unavailable`), period validation (422 `invalid_overview_period`; exactly one `period` key, trimmed, case-sensitive), rate limit 30 per 60 s per teacher (429 `overview_rate_limited` with `Retry-After`), then `service.build_overview`. Read-only; no migration, no LLM call.
- `schemas.py`: `PERIODS`, `ReportingPeriod`, `resolve_period` (half-open UTC day range ending 00:00 UTC tomorrow; `all` has no start), `period_json`, `parse_period`. `service.py`: `utc_now()` is the single clock (tests monkeypatch `teacher_overview.service.utc_now`), `build_overview`, `_rate` (reuses `progress_rules.accuracy_percent`; null for a zero denominator) and `_missed_questions` (ranked by exact `missed/answered` fraction, then misses, lower(set title), position, set id; `TOP_MISSED = 5`).
- Additive read helpers (no existing function changed): `study_lessons/progress.py` `course_student_ids`, `lesson_completion_stats`, `LessonCompletionStat`; `attempt_store.py` module function `submitted_in_period` and `PeriodAttempts` (not part of the `AttemptStore` protocol). One roster per course is read first and every count is limited to it, so `completed_students <= student_count` even under concurrent writes. Attempt `set_id` is text and is matched against `str(published_practice_set.id)`, so built-in set ids never match. Answer keys, choices and explanations are never selected.
- Frontend: `services/teacherOverview.ts` (shape-checked `readOverview`, `overviewError`, `periodLine`), `pages/TeacherOverview.tsx` (report section, remounted per history entry, stale and cross-session responses dropped, as `AdminAiUsage.tsx`), used by `Overview` in `pages/Teacher.tsx`, which also shows "Welcome back, {display_name}." from the auth user. Styles are `.teacher-overview-*`.
- Tests: `src/backend/tests/test_tea05_*.py` (`cd src/backend`, `TEA01_TEST_DATABASE_URL=... .venv/bin/python -m pytest -q tests/test_tea05_*.py`) and `src/frontend/tests/tea05-overview.spec.ts`. `mockAuthApi` (`tests/authApi.ts`) registers a default empty overview report, so specs that sign a teacher in need no extra mock; `tests/tea05Api.ts` overrides it for TEA-05 tests.
- Known limit: the report runs about six queries per course and loads every submitted attempt in the period before keeping the latest per student and set. Fine at class size; batch across courses or use `DISTINCT ON` if courses or attempt history grow.

## ADM-02: targeted feedback implementation

Browser fixture maintenance: admin response lists and response details in `tests/adm02Api.ts` describe the same student respondent, independent of the signed-in reviewer. Row navigation tests click the complete name-and-timestamp metadata text, which shares one span.

Apply additive migration `20261107_adm02_feedback` before starting the updated application. It follows `20261106_adm06_ai_usage` and adds `feedback_forms`, `feedback_recipients`, `feedback_responses` and `feedback_response_drafts`. Existing account, course, lesson and AI data are preserved. Use your existing configured database; never point development commands at production.

Windows (from a configured local checkout; both commands load `.env` so migration and API use the same `DATABASE_URL`):

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location src\backend
uv sync --frozen
uv run --env-file .env alembic upgrade head
uv run --env-file .env uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

macOS/Linux:

```bash
cd "$(git rev-parse --show-toplevel)/src/backend"
uv sync --frozen
uv run --env-file .env alembic upgrade head
uv run --env-file .env uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Start the frontend with the existing setup instructions. Sign in as an enabled admin and open `/admin/feedback`; use separate student/teacher browser profiles to check targeted `/student/inbox` and `/teacher/inbox` delivery. Follow the [ADM-02 user walkthrough](UserGuide.md#adm-02-targeted-feedback-forms). No LLM configuration or calls are needed for this feature.

### Storage, access and concurrency

- `feedback_models.py` owns relational records, `feedback_validation.py` validates definitions/answers, `feedback_store.py` serialises snapshots and centralises access/locking, and `feedback.py` owns HTTP routes, strict query/body handling, quotas and fixed error translation. The approved [plan](../workflow/specs/ADM-02/plan.md) is the endpoint/schema contract.
- Reuse cookie sessions, role checks, Origin/CSRF validation and the existing SQLAlchemy session/pool. Before record work, reuse the account lifecycle transaction advisory lock and freshly verify the session/account. Survey operations take that lock before feature records, so account disable/archive, publication, saves, submit and close use a consistent ordering across workers. This simple global ordering favours correctness over throughput.
- Publication freezes definitions/audience and inserts all recipient inbox rows in the same transaction. Partial publication rolls back. Form editing and private draft saving have independent optimistic versions. A unique form/recipient response plus serialised submit/close prevents duplicate completion or late draft resurrection.
- Draft PUT preserves exact text and allows missing required answers. The final POST carries `draft_version` and the complete final answers, validates required fields and atomically inserts the immutable form/question/answer snapshot and removes the private draft. Acknowledgement determines saved/completed UI state; elapsed time alone never does.
- Draft answers are owner-only while open. Admins see submitted responses only. Recipient terminal reads and inbox payloads contain no answer text. Association references are metadata and confer no course/lesson access. The study companion receives no feedback answers or form contents.
- All protected feedback successes/errors use `Cache-Control: no-store`. Render text without HTML interpretation. Strict types reject unknown fields, invalid/foreign IDs, duplicate questions/options/answers and booleans masquerading as scale integers. Body cap is 256 KiB; combined answer text is 20,000 characters. Form and field limits are in the plan.
- Feedback validation currently returns fixed error codes/messages without optional structured field-path details. The browser focuses the relevant invalid control using the entered values and error code.
- Per-account rolling minute quotas: reads 120, general mutations 60, submissions additionally 10, private draft writes separately 120. Shared `auth.rate_limit.admit` is process-local; multiple workers do not share these quota counters. Rate-limit responses include retry timing, and clients do not retry automatically.
- Forms and submissions have no expiry/deletion API; closure retains submitted responses and hidden private drafts. Downgrading this additive migration drops its feedback tables and their contents; back up data before an intentional downgrade.

### Browser lifecycle

`services/feedbackApi.ts` validates public payloads and coalesces only in-flight reads within the same session/write generation. The shared client now accepts an optional AbortSignal without changing existing callers. Feature requests use a 15-second timeout, distinct transport/timeout errors and abort on unmount; late results cannot overwrite a new account's state.

`useResponseDraft` owns the one-second autosave debounce, one in-flight write, coalesced later edits, explicit retry/conflict handling and navigation flushing. Hydration produces no write. Submission cancels debounce, waits for a pending save, then posts once with final answers. A saved draft is recovered server-side after reload or another device; answers never enter localStorage/sessionStorage. Beforeunload warns for unacknowledged edits. Session exit clears the view immediately and does not wait for autosave. Native abrupt termination can lose edits that never reached the server.

Signed-in student/teacher inboxes use persistent request data, with no sample rows or sample unread badge. The inbox shows the real unread count. Anonymous demo previews remain explicitly sample-only. Admin sidebar feedback navigation points to the live form manager; unrelated analytics previews retain their existing labels; authenticated Announcements uses ADM-04 and removes the sample label.

### Verification

Run the existing backend suite with `uv run pytest -q`, plus the frontend `npm run typecheck`, `npm run lint` and `npm test`. Tests need the documented disposable PostgreSQL schema harness. Set process-local `PGCONNECT_TIMEOUT=3` when running the historical unavailable-database test on Windows if a refused port otherwise waits indefinitely; this bounds the test process's libpq connection attempts without changing application configuration. Use `pytest -k adm02` and Playwright `--grep ADM-02` for the independent feature cases after their integration. No live AI calls are required.

Manual checks: save/reopen all six question types; publish to selected student and teacher accounts separately; verify an unselected account cannot open the URL; save partial required answers, navigate away/return and resume; submit once and see Completed; close collection and verify further saves/submits fail; review preserved submitted snapshots as admin. Test two tabs saving the same draft, close racing submission, failure/retry, session change and mobile keyboard access. Deployment remains through the team's GitHub Actions process.


### STU-05-06: student inbox verification notes

`FeedbackInbox.tsx` lists `/api/feedback/inbox` (20 per page, Previous/Next page, status chip from `response_status`) and renders `MessagesInbox.tsx`, which lists `/api/messaging/inbox` with Mark as read and Load more messages. Each message card shows the fixed text `From: Administrator` beside the sent time: the message API returns no sender, and the label is a constant in the component, not data. Both lists publish their unread counts through `publishInboxCount`; `useInboxUnread` combines them in the sidebar badge (hidden at zero, `99+` above 99), refreshes every 60 seconds while visible and on focus, and keeps the last known count if a background read fails. Forms go to named recipients only (no group or class targeting), and there is no email or push delivery. `RecipientFeedback.tsx` owns the draft, submitted and closed states and the privacy copy.

Student form presentation (AC15-AC18) is presentation only. `FeedbackQuestion.tsx` renders the prompt once in a `span` (id `feedback-q-{id}-prompt`) and names the fieldset and each control with `aria-labelledby`; there is no legend or floating label. Required/Optional is a tag on the prompt row. Linear-scale min and max labels sit outside the radiogroup in a three-column grid. `RecipientFeedback.tsx` sets `attempted` after a failed submit with a blank required question and passes `marked` per question, derived from current answers with the shared `isBlankAnswer` (`feedbackApi.ts`), which also drives the focus lookup via `[data-feedback-question]`. All CSS is scoped under `.feedback-form`; the shared `.feedback-question` admin rules are untouched.

### TEA-06: teacher inbox verification notes

Teachers use the same shared components as students: `FeedbackInbox.tsx`, `MessagesInbox.tsx`, `RecipientFeedback.tsx`, `useInboxUnread` and `useFeedbackRead`, against the unchanged ADM-02 and ADM-04 endpoints (roles `student` and `teacher`; admin gets 403). No backend, schema or shared-component change. The only code change is in the `/teacher` block of `App.tsx`: `TeacherFeedbackIndex` replaces the `feedback` index element, redirecting a signed-in teacher from `/teacher/feedback` to `/teacher/inbox` with history replace and keeping the sample `FeedbackForm` for anonymous demo visitors. The student `/student/feedback` route is unchanged. Targeting is by named teacher only (no teacher groups). Evidence: `src/backend/tests/test_tea06_*.py` and `src/frontend/tests/tea06-inbox.spec.ts` plus the ADM-02, ADM-04 and STU-05-06 suites.

Note for the ADM-02 owner (spec Open question 2, deliberately not fixed here): in `src/backend/feedback.py` `inbox`, the list query filters `role_snapshot == actor.role` but the `unread_count` query does not, whereas `messaging_store.unread_summary` does. They can differ only if an account's role changes after delivery, which ADM-05 prevents while roles stay fixed, so it is unreachable today.

## ADM-04: reviewed private feedback follow-up

ADM-04 adds `messaging.py`, `messaging_store.py`, `messaging_validation.py`, `messaging_models.py` and fixed `messaging_errors.py`. Admin endpoints under `/api/admin/messaging` derive a feedback respondent from a submitted ADM-02 response or resolve one role's selected/all-active accounts. Review creates an immutable 15-minute preview; sending uses only that preview ID. The shared account-change advisory transaction lock rechecks the signed-in actor after acquiring the lock and serializes audience validation with account changes. A unique preview/message constraint and unique message/recipient delivery constraint preserve one durable delivery across concurrent sends, retries and process restarts. Sending is all-or-nothing; replay returns the original receipt without resetting read status. No model calls or external delivery occur.

Migration `20261107_adm04_messaging` adds three message tables after ADM-02; it preserves all surveys and existing records. From `src/backend`, apply it only to your intended local database, then start the API with the same environment:

```powershell
uv run --env-file .env alembic upgrade head
uv run --env-file .env uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The equivalent shell commands on macOS/Linux are identical. A serving process must load the intended `.env`; a 503 indicates temporary storage/configuration failure, including an unapplied migration. The implementation session did not migrate the developer database or restart user servers.

`AdminMessaging` connects the submitted-response `Respond to feedback` action and admin `Announcements` navigation. The `?review=<UUID>` URL recovers only the current admin's preview or original sent receipt. Review POST uses its returned data directly; refresh/history performs one recovery GET, never an automatic send. Edit restores reviewed fields and reloads eligibility once. Private drafts are not put in browser storage. `MessagesInbox` appears beneath the unchanged survey section for authenticated students/teachers. New recipient APIs are GET `/api/messaging/inbox?limit=20&offset=0` and POST `/api/messaging/inbox/{delivery_id}/read`; full literal content is inline, so no separate detail endpoint exposes feedback references or audience identities.

Text limits are 120 subject/5000 body Unicode code points, 500 distinct recipients, 128 KiB request bodies and 15 seconds per browser request. Admin quotas per minute: 20 recipient/recovery reads, 10 previews and 5 first-time sends; successful replay is exempt from send quota. Inbox reads and mark-read share 60 requests/minute/account. The reused limiter is process-local; durable uniqueness and access remain database-enforced. Delivery and previews have no automatic retention deletion. No sent-message edit/recall or sent-history browser is included.

Manual verification: sign in as admin, open a submitted response, compose/review/confirm a response, then sign in as its respondent and find exactly one unread Feedback response under Messages. Mark it read and refresh; it stays read. Send a selected-student announcement and check that a different user cannot read its delivery ID. Refresh a review URL before confirming and verify that recovery itself sends nothing. Existing feedback requests, autosave and completion continue independently.


### ADM-04: unread navigation and scoped UI
`GET /api/messaging/unread-count` is an authenticated student/teacher metadata-only endpoint returning `unread_count`, `unread_messages` and `unread_requests`. One aggregate SQL statement counts only the actor's unread deliveries and published/non-draft survey requests matching their role. It reuses the shared session/role/transaction checks, no-store policy and 60/minute recipient quota. No schema migration is needed for this UI follow-up.

`useInboxUnread` loads the summary once per authenticated recipient shell, deduplicates StrictMode reads, refreshes each visible minute and on window focus/visibility return (minimum five seconds apart), and stops when hidden/unmounted or signed out. List loads publish section counts; successful mark-read changes the badge locally. First successful survey-detail read requests a summary refresh. Revisions prevent an older summary from overwriting a more recent local count; in-flight invalidations coalesce into one follow-up. Background failures retain known data and recover on the next refresh without interrupting the current page. No message bodies are polled. Session-generation checks prevent previous-account badge data.

The ADM-04 styles scope input outlines and surfaces to messaging/inbox. Do not reset all nested fieldsets: MUI uses a fieldset for outlined inputs. Header/input contrast, semantic dates, recipient search separation and responsive light/dark screenshots are covered by `tests/adm04-redesign.spec.ts`; private summary semantics by `tests/test_adm04_unread.py`.


### Admin screen design baseline

`workflow/ui-design.md` governs the remaining admin surfaces as well as ADM-04. `Admin.tsx` scopes the live access/course pages and legacy previews with `.admin-surface`; `AdminFeedback.tsx` independently scopes the form routes. Portal dialogs opt into `.admin-dialog`, so input styling also applies outside the page DOM. Do not apply these classes to the ADM-04 composer or recipient inbox.

The scoped rules in `styles.css` define neutral panels, outlined MUI fields, readable metadata and responsive layouts. MUI notched-outline fieldsets receive an explicit border, margin and padding so the global fieldset reset cannot erase them. Account discovery/results precede creation in DOM order and stack below 1100px; recipient lists scroll within 280px. Feedback editor sections retain the native disabled fieldset and existing submission/navigation guards.

`LocalTime.tsx` renders recorded instants with the browser's locale/time zone and preserves the ISO value in `time[datetime]` and the title. Report date filters remain UTC. Response link accessible names retain their exact identifiers and original timestamps, while visible rows lead with human names. Existing endpoints, fetch cadence, error mappings, session clearing and security checks are unchanged; no background requests or live AI are added.

Regression coverage is in `tests/admin-ui.spec.ts`, alongside existing ADM-02/04/05/06 suites. The existing row-layout and timestamp assertions were adapted to the documented taller cards and semantic local dates, retaining full-row navigation, hover, request-count and exact-record assertions. Use isolated Playwright ports when a developer server is running. Check desktop/mobile, both themes, visible input/focus outlines, long content, retained input on failure and keyboard-reachable report scrolling.


### Frontend CI: recipient debounce and shell request counts

The announcement composer schedules its 300ms search debounce only when the trimmed input differs from the applied query. An unchanged initial search must not reset recipient pagination. Debounce browser tests install the Playwright clock before navigation so existing native timers cannot overlap the simulated clock; exact request-count and stale-response assertions remain in place.

The practice picker still loads its catalog once. Its signed-in student shell also makes one metadata-only `GET /api/messaging/unread-count` for the Inbox badge. Integration request assertions explicitly allow those two reads and reject extra catalog, study/course/progress or message-body calls; they must not classify the shell summary as a picker duplicate.


Browser history tests wait for the destination's exact page heading before issuing Back; a URL change plus any visible heading can still describe the previous React screen. Recovered-message tests wait for the expected recipient lookup before asserting its exact count, since the composer input can render before its read effect dispatches. These waits preserve the existing request-count requirements instead of adding sleeps or retries.

When a history test counts completed report loads, wait for the report data on each page before navigating again. The shared reader intentionally coalesces identical requests that are still in flight, so counting one new request per completed visit is different from switching pages while the previous read is pending.

## ADM-03: AI feedback analysis

Admin-only. Spec and contract: `workflow/specs/ADM-03/`. Backend package `src/backend/feedback_analysis/`, frontend pages `AdminFeedbackAnalysis*.tsx`.

- **Two independent parts.** `POST /api/admin/feedback/analyses` stores the analysis and returns the statistics at once (`aggregates.py`, pure functions, no LLM, each response read with its own `form_snapshot`). The AI step then runs in a daemon thread (`jobs.start`, `jobs.run_job`) with its own DB sessions; every write is `UPDATE ... WHERE id = :id AND ai_status = 'running'`, so a job whose row was swept or deleted updates zero rows and ends quietly. The request session is closed before the job starts.
- **Map-reduce.** `entries.py` normalises and de-duplicates free-text answers (short_answer and paragraph only), samples deterministically and packs batches (at most 10); `prompts.py` builds `TASK: MAP` and `TASK: REDUCE` prompts (no identity, no choice or scale answers, no raw answers in reduce); `validate.py` enforces strict JSON and label subsets; `failures.py` holds every exact message and maps shared-client errors. Limits in messages come from `llm_client.Limits()` defaults.
- **One running AI step per admin** (partial unique index); a `running` row older than 780 s becomes `analysis_interrupted` at the next create, list, read or delete (`service.sweep_stale`). Rows are removed only by the owner through `DELETE` (409 while running). No automatic retention.
- **Usage label.** Calls run inside `usage_feature("ADM-03")`, the label ADM-06 already reserves for this feature (the plan named `feedback_analysis`, which the shared whitelist and the ADM-06 database constraint do not accept; see `workflow/notes.md`).
- **Migration.** `20261109_adm03_analysis` (single head after `20261107_adm04_messaging`).
- **Tests.** Use the shared fixture (`TEA01_TEST_DATABASE_URL`) and a fake LLM that tells map from reduce by the first system line (`TASK: MAP` / `TASK: REDUCE`). No live SoC calls.
- **Frontend.** `services/feedbackAnalysisApi.ts` (typed calls, 15 s timeout), `messages/feedbackAnalysis.ts` (exact load, abort, polling and delete messages), `hooks/useAnalysisPolling.ts` (2 s polling only while running and visible, 3 network failures or 810 s stops), `components/QuestionResults.tsx` (table plus CSS bars, no chart library), `components/DeleteAnalysisDialog.tsx`. `services/client.ts` now keeps the error body in `ApiError.detail` and accepts 204 replies.
- **Live tuning (real SoCLaaS, reasoning model).** `LlmClient.complete` takes an optional `timeout_seconds` (default None keeps `Limits.timeout_seconds`; used per request, one retry as before). The reduce call passes `REDUCE_TIMEOUT_SECONDS = 60.0`; map calls use `MAP_TIMEOUT_SECONDS = 30.0`. `MAP_MAX_TOKENS` 1600, `REDUCE_MAX_TOKENS` 3000; reduce caps: summary 400, 5 themes (description 250), 6 suggestions (text 200). Worst case 10 x (2 x 30 + 1) + (2 x 60 + 1) = 731 s, under the 780 s sweep bound. The `ai_timeout` message shows the limit actually used. Test fakes of the client must accept `timeout_seconds`.
- **Response delete.** `DELETE /api/admin/feedback/forms/{form_id}/responses/{response_id}` (in `feedback_analysis/routes.py`, ADM-02 admin dependency including the account-change lock) hard-deletes one `feedback_responses` row with one `DELETE ... RETURNING`; 204, uniform 404 `feedback_response_not_found`. Completion is derived from the row, so recipient and draft rows are untouched. The job checks, before the first call and before each batch, that every selected response still exists; otherwise it stores `ai_responses_deleted` (details missing/selected). The frontend button and dialog live in `AdminFeedback.tsx` and share `components/ConfirmDeleteDialog.tsx` with `DeleteAnalysisDialog`.
- **Shared-client options used by ADM-03.** `complete` also takes `max_reply_chars` (reduce passes 8000; the client otherwise cuts replies at 2000 characters, which would cut the reduce JSON) and `reasoning_effort` (ADM-03 sends `"low"`, which roughly halves hidden reasoning tokens; the field is sent only when set). A reply with no content and `finish_reason` length raises `LlmReplyCutOff` (a subclass of `LlmBadResponse`), stored as `ai_reply_cut_off` with the note that the model used its whole token budget. Fakes must accept all three keywords (`timeout_seconds`, `max_reply_chars`, `reasoning_effort`).
- **Tolerant `reasoning_effort`.** If the gateway answers a 400 or 422 to a request that carries `reasoning_effort` (HTTP 400 or 422 only; some models reject the field), `SoclaasClient` retries once without it, with its own reservation like any other attempt; requests without the field are unchanged. Live run with the final limits (model x-test-2, reasoning effort low): map 11.0 s and 5.3 s valid after one map retry, reduce 19.1 s valid after one retry (a first reduce was rejected by the strict `summary` length rule); 86.9 s total, 5 live calls; model variance is real (about 1 in 3 calls failed: one empty reply at 1600 reasoning tokens, one over-long summary).
- **Job retry (`jobs._run_step`).** One place runs each map and the reduce step: a model-output failure (`ai_reply_cut_off`, `ai_reply_not_json`, `ai_reply_invalid`; `failures.RETRYABLE`) gets one more attempt of the same step Before every attempt, first attempts included, `_run_step` checks the job's age with `jobs._now()` (tests replace this function): from `AI_START_CUTOFF_SECONDS` (600) no call starts and the step fails with `ai_time_limit`. Other failures are final. After two failures the second one is stored with `details.attempts = 2`, `first_attempt_code` and the suffix "The step failed after 2 attempts." (`failures.after_two_attempts`). Progress counts steps. Quota: up to 22 AI calls per analysis, so about 13 analyses a day within the 300-call quota; a call started before 600 s ends within 121 s, so the job ends by 721 s, under the 780 s sweep bound. The reduce prompt asks for a summary of at most 350 characters (validator limit 400).

## ADM-07: backend analytics (formerly ADM-01)

Admin-only. Contract: retained criteria in `workflow/specs/ADM-07/retained-criteria.md` (the old ADM-01 spec was removed in ADM-07 phase 5). Backend package `src/backend/feature_analytics/`, frontend `pages/AdminAnalytics.tsx`, `services/featureAnalytics.ts`, `hooks/useAnalyticsLoad.ts`. Routes under `/api/admin/analytics` (`GET /usage`, `/generation`, `/quality`, `POST /grading-runs`, `GET /grading-runs/{id}`); `Cache-Control: no-store` comes from the existing `/api/admin/*` middleware.

- **Recording hooks** (`recording.py`, re-exported by the package): `record_chat_request_received/outcome`, `record_practice_attempt_started/submitted`, `record_generation_accepted/outcome`. Each uses its own `open_session()`, never raises (logs the hook name and exception class only) and never logs text. Call sites: `companion_routes.post_message` (after validation and context resolution, before `llm.complete`; the outcome is recorded in a `finally`; a refusal reply counts as success; only un-withheld practice-attempt hints are eligible for sanitised grading text; explanations create excluded metadata with NULL text), `practice_routes.start_attempt` (after `store.create` commits) and `submit` (after the `with store.lock(...)` block exits cleanly, using `locked.submitted_at`, which the store fills in before the commit returns), and `teacher_notes` / `teacher_mcqs` `create_*_draft` (after the AI call: an `ApiError` with code `llm_rate_limited` or `llm_busy`, which `llm_errors.generation_error` makes of the client's limiter errors, is not an attempt; every other exit records one attempt and one outcome). MCQ batches create privacy-blocked metadata only; neither stems nor choices enter the scanner or grader. Teacher note requests use the fixed application template; upload/source context is never retained.
- **Tables** (migration `20261109_adm01_analytics`, also extending the ADM-06 `ck_ai_*_feature` constraints and coverage seed for the `ADM-01` usage label): `analytics_meta` (`recording_started_at`; earlier periods are `unavailable/period_before_recording`), `analytics_session`, `analytics_chat_request`, `analytics_practice_attempt`, `analytics_generation_attempt`, `analytics_grading_item`, `analytics_grade`, `analytics_grading_run`. A session is one user and one practice attempt with at most 30 minutes between messages; one open session per user (partial unique index, assigned under `pg_advisory_xact_lock`). Submission takes the same per-user lock before attempt/session row locks; a delayed pre-submission chat attaches to a closed session rather than reopening the completed activity.
- **Privacy and retention.** Approved `privacy.py` policy `adm01-local-dlp-v1` uses local CPU spaCy PERSON recognition and deterministic credentials/identifiers detection, plus authenticated account identity variants. The whole candidate is checked before storage; oversize input (2,000 / 6,000 / 3,000 characters), unsupported Unicode/script/structured input and solution markers are blocked. Only student hints and teacher note output are eligible; context is always empty. A single owned worker accepts no queue, with 500 ms per-item bounds; busy, failed or timed-out scanners fail closed, and timeout requires process restart. Dispatch reloads and rescans a sanitised copy; reasons must pass the scanner without any redaction, schema/markup validation and 30-character private-text-overlap checks. Detected content is replaced with `[REDACTED]`; this bounded English gate cannot guarantee detection of arbitrary names, secrets or paraphrased solutions. No scanner networking or runtime model downloads occur. Analytics text is NULL after grading, and ungraded text expires after seven days. `privacy_blocked` items hold no text, are counted separately, and consume no grading selection slots. `ANALYTICS_PRIVACY_MODE=local_dlp` is the default; `strict` disables all free-text storage/grading. Unready local mode returns 503 before run/quota admission; strict mode returns 409.
- **Reads** (`queries.py`): each metric is its own function (`chat_counts`, `practice_completion`, `generation_rates`, `quality_grades`, `response_times`, `session_stats`, `activity_time_stats`); `routes.py` calls them through the module and turns an exception into `unavailable/read_failed` for that metric only.
- **Provisioning and restore ordering.** Run `uv sync --frozen` at build time (spaCy 3.8.18, official MIT `en_core_web_sm` 3.8.0 wheel SHA256 `1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85`). The model data tree has a fixed platform-independent digest checked before warmup and an offline name-recognition health fixture. Run `uv run --frozen python tools/privacy_smoke.py` on Linux before serving; CI enforces health and 500 ms representative/near-cap scans. Apply `uv run alembic upgrade head` before service start: additive revision `20261110_adm01_privacy` purges all legacy analytics text and grade reasons and blocks old items. After any backup restore, stop serving/worker processes, apply migrations, then run `uv run python -c "from feature_analytics.jobs import purge_legacy_items; purge_legacy_items()"` before restart (also sweeps on analytics run reads/start). This never erases learning/source records. Historical backup retention is operator-owned and unavailable here; application migration does not erase backups. Observed Linux Docker provisioning: representative scans 7.07 / 3.16 / 3.76 ms, near-cap scan 48.93 ms, peak RSS 179,524 KiB (one warm process; performance and detection are workload-dependent). Windows Application Control currently blocks the installed thinc native DLL in this workspace, so the local scanner remains unavailable there; do not bypass that policy.
- **Grading run** (`grading.py`, `jobs.py`): same shape as ADM-03's job. The route takes `llm: LlmClient = Depends(get_llm_client)` (tests fake it with `app.dependency_overrides[llm_client.get_llm_client]`), starts a daemon thread with its own sessions and conditional writes, one call per item inside `usage_feature("ADM-01")` with `caller_id="admin-grading:<admin id>"`, 30 s per call, no call after 200 s of monotonic time (`jobs._now`), job bound 300 s, sweep of runs older than 900 s (`run_expired`, run in the three routes that read runs). Model output must be exactly four `{score, reason}` objects; a reason that repeats 30+ consecutive characters of the data, or any schema deviation, marks the item `grading_failed`. Factual accuracy is always forced to `unassessable` because context is empty. At most 20 items per run, one active run (partial unique index), 10 runs per rolling hour. A global analytics admission advisory lock serializes the active-run and hourly-quota checks through the creation commit, including concurrent starts whose first run finishes immediately.
- **Frontend.** `useAnalyticsLoad` keeps one read per key, shared across React StrictMode's simulated remount, aborted on key change or unmount. The page is wrapped like `LiveAnalysis` so an anonymous visitor goes to `/login` (replace) without any analytics request. The live wrapper immediately unmounts account data when authentication is lost, leaving mid-visit expiry navigation to AuthContext. The quality panel shows assessed, waiting, failed and expired counts. A grading-start 409 triggers one quality reload to discover the active run; if it has already finished, a new run can be started.
- **Tests.** Existing ADM-06 tests and Playwright fixtures list four features (`ADM-01` is a valid usage label); the backend tests are `tests/test_adm01_*.py` (browser tests for the Quality section are `tests/adm07-retained.spec.ts`).
## ADM-07: Feature Analytics hub (phase 2 and phase 4)

Spec: `workflow/specs/ADM-07/`. Phase 2 read existing ADM-01 tables; phase 4 (below) adds the event tables.

- **Backend** (`src/backend/feature_analytics/`): new GET routes `/api/admin/analytics/health`, `/hourly`, `/daily`, `/chatbot-users`; `/usage` takes `include_rows=true|false`. `health.py` holds the pure helpers (`severity`, `percentile_nearest_rank`, `median_half_up`, `round_half_up`, `rate_percent`, `finished_state`). `queries.py` applies the in-progress rule at read time (pending younger than `IN_PROGRESS_EXPIRY_S` = 120 s is excluded and counted as `in_progress`; older is a failure with duration 120000 ms); one timestamp per request is taken by `queries.begin_request()` (tests monkeypatch `queries.utcnow`) and returned as `as_of`. `_cover()` implements partial coverage: metrics are computed from `max(period start, recording start, retention floor)` and carry `data_starts_on`; they are `unavailable` only if the whole period is earlier. Every metric object now has a `data_starts_on` key, and `/usage`, `/generation`, `/quality` also carry a top-level `data_starts_on`. `/generation` entries gain `requests`, `rate_limited` and `rate_limited_state` (see phase 4 below for their sources). Response models in `schemas.py` were not added: responses stay plain dicts like the ADM-01 routes.
- **Phase 4: event collection.** Migration `20261111_adm07_events` (down_revision `20261110_adm01_privacy`) creates `analytics_request_log` (kind chatbot / generation_notes / generation_mcq, `source_id`, `occurred_at`, outcome, `failure_category`, `duration_ms`; no user id, no text; partial unique index `(kind, source_id)`), `analytics_login_event` (user id, role student|teacher, time; no IP or agent), `analytics_practice_draft_started` and `analytics_practice_published` (primary key `practice_set_id`, so once per set under concurrency), and five `analytics_meta` start keys. Backfill: request log from the last 30 days of `analytics_chat_request` / `analytics_generation_attempt` (failures `unclassified`, pending copied as pending); draft-started from `mcq_draft_batch.created_at`, published from `published_practice_set.published_at`, both keyed by the draft batch id (`source_draft_id`). Start keys: `request_log_started_at` = later of `recording_started_at` and migration time minus 30 days (so backfilled history is shown); `request_log_categories_started_at` and `login_events_started_at` = migration time; draft/published keys = earliest backfilled time. The request-log read floor and the purge share `PURGE_REQUEST_LOG_DAYS`. Foreign keys: `analytics_login_event.user_id` cascades on user delete (a hard-deleted user leaves no sign-in history); draft-started and published `teacher_id` do not cascade (they are kept as long as attempts, and the draft/batch tables already restrict deleting those teachers). Downgrade drops the four tables and the five keys; source tables are never touched. There is no unpublish or republish flow today, so a set has one first-publication time. Attempt start and submit times already exist in `analytics_practice_attempt`, so the funnel needs no new collection.
- **Hooks** (`recording.py`, keyword arguments, own session, never raise): `record_chat_request_received` / `record_generation_accepted` also insert the pending log row in the same transaction; the two outcome hooks take `failure_category` and update the log row in the same transaction as the source row (first outcome only; unknown category is stored `unclassified`; success stores none). New: `record_generation_rate_limited(workflow=)` (log row only), `record_login(user_id=, role=)` (student and teacher only), `record_practice_draft_started`, `record_practice_published`, `categorize_llm_error(exc)` (rate limited/busy, timeout, bad response or cut off = invalid output, other `LlmError` = upstream, otherwise unclassified; a host `ApiError` is mapped by its code). Call sites: companion route, TEA-02 notes and MCQ routes (rate-limited branch logs a refusal before re-raising), `auth/routes.py` login after the session is created, MCQ draft creation (first save) and `teacher_publications` publish after commit.
- **Reads:** `/health`, `/hourly`, `/generation` read the request log with the 120-second in-progress rule, the 30-day retention floor and the start keys (`data_starts_on`); the rate-limited tile counts `rate_limited` rows from `request_log_categories_started_at`; `/daily` logins, drafts started and published read their tables. Chatbot per-user counts still come from `analytics_chat_request`.
- **Retention:** `retention.purge_expired()` deletes request-log rows older than `PURGE_REQUEST_LOG_DAYS` (30) and login events older than `PURGE_LOGIN_EVENT_DAYS` (400) in batches of `PURGE_BATCH`; it runs at app startup and at most once per `PURGE_INTERVAL_S` per process after an outcome hook. Draft-started and published rows are kept.
- **AI usage cleanup (one-off, destructive):** `uv run python -m ai_usage.cleanup --dry-run` prints per feature the pending attempts older than 24 hours and the coverage change; `--apply --approved-by <name>` deletes exactly those rows permanently (no archive, no restore) and, for each affected feature, clears `incomplete_since` and sets `covered_since` to the next UTC midnight (never earlier). Terminal rows are never deleted. Run `--dry-run` on the target database and review it before `--apply`; it is not an Alembic revision.
- **Frontend:** `pages/AdminAnalytics.tsx` is the hub; the previous page and its `/admin/feature-analytics-legacy` route were deleted in phase 5, and `/admin/ai-usage` is a `Navigate replace` to `/admin/analytics`; the old `pages/AdminAiUsage.tsx` and its nav entry are gone (the AI usage section is `components/analytics/AiUsageSection.tsx`). Blocks use `hooks/useAnalyticsBlock.ts` (wraps `useAnalyticsLoad`); charts are hand-written SVG (`components/analytics/charts.tsx`); `lib/` has period, local-time bucketing and CSV helpers. Each load sends 7 GETs (6 when AI usage does not apply).
- **SoC LLM limits (observed 2026-11-11, not documented quotas):** with `qwen3.6:35b`, `max_tokens` of 100 to 100 000 were accepted; a 160 000-character prompt (26 687 tokens) was accepted; an 8 000-token completion ended with `finish_reason` "length"; no rate-limit headers; the model list reports a 131 072-token context window. Requests-per-minute and daily quotas were not tested. Unconfirmed hypothesis: reasoning tokens may consume the `max_tokens` budget (the earlier remembered 2 000 or 5 000 limit was not reproduced).
