# Shared data contract for teacher features

This is the shared handoff contract for TEA-01 source materials and the TEA-02 generation/TEA-03 draft-note editing slices. Teacher APIs now use PR16 shared session authentication; publication remains deferred. The current original-file storage contract is [TEA-01-db-storage](../workflow/specs/TEA-01-db-storage/plan.md); filesystem requirements in earlier feature specifications are historical and superseded. The API contract is authoritative for black-box tests, so tests need import only the FastAPI `app`.

## Runtime and persistence

- Python backend uses synchronous SQLAlchemy 2, psycopg, PostgreSQL 16, and Alembic. `DATABASE_URL` is a psycopg URL such as `postgresql+psycopg://user:password@localhost:5432/learnswe`. Original bytes also live in PostgreSQL; `FILE_STORAGE_DIR` is unused. Missing/invalid database configuration or unavailable database yields 503 with `service_unavailable` on teacher requests.
- All teacher requests require a live session cookie and teacher role; unsafe requests require Origin/CSRF validation. `X-Demo-User-Id` and legacy demo flags are ignored. Current course membership controls access, regardless of creator.
- All records persist in PostgreSQL. IDs are canonical UUID strings except `user.id`, which is a stable string. Timestamps are UTC `timestamptz`; JSON timestamps use ISO 8601 with a `Z` suffix. Database uniqueness and foreign keys enforce membership/topic boundaries.
- `user`: `id` varchar(64) primary key, `display_name` varchar(200) not null, `role` varchar(16) not null constrained to `student`, `teacher`, or `admin`, `created_at` timestamptz not null default current UTC time. SHR-01 adds nullable `email` varchar(254) (stored trimmed and lower-case, CHECK `email = lower(email)`, unique index `ux_user_email`) and nullable `password_hash` varchar(255) (`scrypt$n$r$p$salt$hash`; NULL means the user cannot sign in). Existing seed users keep their ids; `auth_session` (id UUID, `token_hash` unique SHA-256 hex, `user_id` FK cascade, `csrf_token`, `created_at`, `expires_at`) holds server-side sessions.
- `course`: `id` UUID primary key default generated UUID, `title` varchar(200) not null, `created_at` timestamptz not null default current UTC time.
- `course_membership`: `course_id` UUID not null foreign key, `user_id` varchar(64) not null foreign key, composite primary key (`course_id`, `user_id`). A teacher may manage a course only if this membership exists and their role is `teacher`.
- `topic`: `id` UUID primary key default generated UUID, `course_id` UUID not null foreign key, `name` varchar(200) not null, `created_at` timestamptz not null default current UTC time; unique (`course_id`, `name`).
- `material`: `id` UUID primary key default generated UUID, `course_id` UUID not null foreign key, `topic_id` UUID nullable, `uploaded_by` varchar(64) not null user foreign key, `title` varchar(200) not null, `original_filename` varchar(255) not null basename, `media_type` varchar(64) not null (`application/pdf` or `text/plain; charset=utf-8`), `size_bytes` bigint not null checked 1–10,485,760, `created_at` and `updated_at` timestamptz not null default current UTC time. Enforce topic in the same course with a composite foreign key or a transactionally equivalent check. `size_bytes` is the validated original-byte count.
- `material_file`: `material_id` UUID primary/foreign key to material.id with ON DELETE CASCADE; `content` BYTEA NOT NULL checked `octet_length(content)` between 1 and 10,485,760. One matching content row is inserted atomically with each material. Bytes are not base64 and never appear in metadata JSON. No ORM relationship eagerly loads content.
- Use an Alembic migration for these tables. For local setup with the fresh database URL in `.env`, from `src/backend` run `uv run --env-file .env alembic upgrade head`, then `uv run --env-file .env python -m teacher_materials.seed`. The explicit idempotent seed command (not automatic on every request) inserts only missing seed records and memberships. It may be rerun without duplication and must not erase uploads or teacher edits.

## Seed fixture

| Record | Stable ID | Value/access |
|---|---|---|
| Teacher A | `demo-teacher` | role `teacher`; member of Course A |
| Teacher B | `demo-teacher-other` | role `teacher`; member of Course B |
| Student | `demo-student` | role `student`; member of Course A |
| Course A | `11111111-1111-4111-8111-111111111111` | title `Software Engineering` |
| Course B | `22222222-2222-4222-8222-222222222222` | title `Programming` |
| Topic A | `33333333-3333-4333-8333-333333333333` | Course A, name `Testing` |
| Topic B | `44444444-4444-4444-8444-444444444444` | Course B, name `Basics` |

## API contract

All paths below start with `/api/teacher`. Send the shared session cookie and `X-CSRF-Token` on unsafe methods. List responses are bare arrays; courses and topics sort by `created_at` ascending then `id` ascending, materials by `created_at` descending then `id` ascending. There is no pagination in this increment. All UUID path/query/body values must parse as UUIDs. Unknown JSON fields are rejected with 422. There are no optional data wrappers or storage paths.

| Method and path | Request | Success |
|---|---|---|
| `GET /courses` | none | 200 `Course[]` for the teacher's memberships |
| `GET /courses/{course_id}/topics` | none | 200 `Topic[]` for managed course |
| `GET /courses/{course_id}/materials` | optional `topic_id` UUID query | 200 `Material[]` for managed course, filtered to exactly that topic when supplied |
| `POST /courses/{course_id}/materials` | multipart form: required `file` (one binary), required `title` string, optional `topic_id` UUID string | 201 `Material` |
| `PATCH /materials/{material_id}` | JSON object with required `topic_id`: UUID string or `null`; no other fields | 200 `Material` |
| `GET /materials/{material_id}/file` | none | 200 original bytes, `Content-Type` equal to material `media_type` (for text, UTF-8 charset), `Content-Disposition: attachment` with safe original basename |

`Course = {id, title, created_at}`. `Topic = {id, course_id, name, created_at}`. `Material = {id, course_id, topic_id, uploaded_by, title, original_filename, media_type, size_bytes, created_at, updated_at}`. IDs except `uploaded_by` are canonical UUID strings; `uploaded_by` is the user ID string; `size_bytes` is an integer; timestamps are UTC ISO 8601 strings ending in `Z`; other values are strings except nullable `topic_id`. Use these exact snake_case keys; `topic_id` is `null` when unassigned. No file contents, absolute paths, `storage_key`, publishing state, or teacher-private records are included in JSON. On POST, `uploaded_by` is the resolved server-side user, never client input.

Title is trimmed of leading/trailing Unicode whitespace, then must have 1–200 Unicode code points. NUL and unpaired surrogate characters are rejected with 422 validation_error before file storage; valid astral Unicode is supported. File extension uses the final basename and case-insensitive `.pdf`/`.txt`; a missing/empty filename or unsupported extension is 415. The upload must contain 1 through 10,485,760 bytes. PDF parsing with pypdf must succeed and find at least one page; encrypted, corrupt, or unreadable PDFs are 422. Text must be valid UTF-8; empty/invalid text is 422. Accepted `media_type` is derived from the validated extension/content, not a client MIME claim. Original basename is retained for download after removing any path components and control characters. Material IDs are generated server-side and unique for simultaneous uploads.

Errors use exactly `{"detail":{"code":"...","message":"..."}}` with an HTTP status. The message is human-readable; for file_too_large it must mention `10 MiB`, and storage_quota_exceeded states `Upload would exceed the 100 MiB total storage limit.`, and for 415 it must mention `PDF` and `UTF-8 text`. No stack trace, SQL error, storage key, or path is exposed.

| Status | `detail.code` | Condition |
|---|---|---|
| 401 | `unauthenticated` | Missing, expired, revoked or unknown session |
| 403 | `csrf_failed` | Unsafe request fails shared Origin/CSRF validation |
| 403 | `forbidden` | Current session user is not a teacher |
| 404 | `not_found` | Missing or inaccessible course/material; topic absent, inaccessible, or in another course |
| 413 | `file_too_large` | Stream exceeds 10,485,760 bytes, regardless of `Content-Length` |
| 413 | `storage_quota_exceeded` | Original bytes plus this upload would exceed 104,857,600 bytes (100 MiB) |
| 415 | `unsupported_media_type` | Filename has no supported extension |
| 422 | `validation_error` | Bad UUID, fields, title, empty/invalid file, encrypted/corrupt PDF, or invalid UTF-8 |
| 503 | `service_unavailable` | Missing/invalid config, DB unavailable, upload processing failure, or missing material content |

Request processing order is configuration, live session, unsafe Origin/CSRF, teacher role, accessible resource, then mutation input. Writes lock session/user/membership and target through commit. Topic PATCH accepts topic_id UUID or null only, changing topic/timestamp with last-committed-write semantics; a concurrently deleted material returns404.

## Storage and transaction boundary

Validate bounded upload bytes before insertion, then acquire transaction advisory lock `pg_advisory_xact_lock(32272610)` and issue a fresh `SUM(octet_length(material_file.content))` query. Teacher sessions use READ COMMITTED isolation. Reject totals above 104,857,600 bytes; hold the lock through commit/rollback so concurrent uploads cannot oversubscribe. The budget counts original bytes across all courses/users, not PostgreSQL overhead or other tables; monitor provider storage headroom. Administrative raw SQL is outside application quota enforcement.

Metadata and original bytes commit atomically; failure rolls both back. Lists query metadata only. Downloads and generation fetch bytes only after current teacher/course authorisation. An externally missing content row returns 503 service_unavailable, `Stored material content is unavailable.`, before inference; metadata can still be listed without loading/checking bytes. No permanent files/public file URLs are created. Multipart may use temporary spooled files which are closed after each request.

Alembic explicitly uses READ COMMITTED before its first query, independent of the database default; this prevents a pre-lock repeatable-read snapshot from hiding concurrent uploads. Revision `20261102_tea01_db_storage` refuses upgrade before any DDL when material rows exist; create a separately named fresh database, keep old data/files untouched and re-upload. Downgrade also refuses while any material exists. Empty downgrade restores the old storage_key column, but never reconstructs files. Existing IDs, references and metadata fields are preserved by current operations; there is no cross-database import. See README setup instructions.

## Integration test setup

Tests use a real isolated PostgreSQL schema, not SQLite: read `TEA01_TEST_DATABASE_URL` as the base database URL, create a unique schema for the run, set the app `DATABASE_URL` with psycopg `options=-csearch_path=<schema>` before importing/configuring the app, run `uv run alembic upgrade head` and `uv run python -m teacher_materials.seed`; no permanent file directory is needed. Configure local session settings and authenticate test users. Drop the test schema in teardown. Temporary files may check that no permanent files are created. The only application import required for black-box tests is `app`; HTTP requests and the seed CLI/SQL fixture can establish state. Student API tests authenticate through the session cookie (SHR-01); also run `uv run python -m auth.seed` with test-only `SEED_*` values after the teacher seed. Configure environment before app import, or provide a documented app factory/config reset if the application loads settings at import time.

## Internal handoff interfaces

Keep module boundaries single-purpose; these names are the shared implementation interface, while HTTP tests rely only on the API above:

- `src/backend/teacher_materials/models.py`: SQLAlchemy `User`, `Course`, `CourseMembership`, `Topic`, `Material`, `MaterialFile` models with the columns above.

- `src/backend/teacher_materials/storage.py`: `validate_upload(upload) -> ValidatedUpload` with `original_filename`, `media_type`, `size_bytes`, `content: bytes`; `MAX_BYTES` 10 MiB and `MAX_TOTAL_BYTES` 100 MiB. No permanent filesystem storage.
- `src/backend/teacher_access.py`: `teacher_session(request)` (shared cookie authentication/CSRF and READ COMMITTED database session), `owned_material(session, teacher, material_id)` and `parse_uuid(value)`. `src/backend/timestamps.py`: `utc_timestamp(value)`.
- `src/backend/teacher_materials/routes.py`: source operations including guarded deletion, authorised content retrieval and atomic metadata/content writes.
- `src/backend/teacher_materials/seed.py`: `seed_demo(session: Session) -> None` and the exact rerunnable CLI `uv run python -m teacher_materials.seed` from `src/backend`; document its invocation in `docs/DeveloperGuide.md`.

The test-designer must not import these internals or implementation files. The seed CLI path is fixed because the independent test fixture invokes it.

## Cross-role integration and authentication handoff

- These PostgreSQL users, courses, memberships and topics are the common foundation. Later student/admin work should reuse their IDs and relationships rather than create parallel teacher-specific copies.
- A source `material` is private teacher input, **not** a published lesson or a student practice set. Generated content references its material ID through separate records. TEA-01 introduced sources only; TEA-02 now creates unpublished study-note drafts as described below. MCQ drafts are implemented below; publication and student answer release remain future work.
- Current student practice still reads the server fixture `intro-se-1` and stores attempts in the in-memory `AttemptStore`. Since SHR-01 the attempt owner is the signed-in `user.id` (the old `X-Student-Id` header is gone and ignored), but attempts are not rows in these tables. Nothing automatically migrates attempts, enrolls students or changes the existing scoring flow.
- SHR-01 implements real authentication: `POST /api/auth/signup|login|logout`, `GET /api/auth/me`, an HttpOnly session cookie, a per-session CSRF token (`X-CSRF-Token` on POST/PUT/PATCH/DELETE) and the reusable `auth.dependencies.current_user(role=...)` and `require_course_member(db, user, course_id)` (see `workflow/specs/SHR-01/plan.md` and the Developer Guide). Student practice and companion routes already use it. Teacher routes also use these shared checks via teacher_access; demo identity is retired for all teacher APIs. Seeded demo accounts get credentials only from the `SEED_*` environment through `uv run python -m auth.seed`; nothing real is committed.
- Back up and restore PostgreSQL: it now contains both originals and metadata/drafts. No coordinated file-directory backup is required in the new mode. Returning to the historical filesystem version requires its prior code/configuration/database and original files; do not downgrade a populated database. Future object storage must retain private access and stable material references.

## TEA-02-notes integration contract

See [TEA-02 notes contract](../workflow/specs/TEA-02-notes/plan.md) for exact endpoints, representations, errors, limits and test interfaces. This is an implemented additive draft-generation slice; editing is implemented through the TEA-03 extension below; publication remains deferred.

- `study_note_draft`: UUID `id` PK; UUID `course_id` and `source_material_id` not null, composite FK to material `(id, course_id)` and course FK; `created_by` varchar(64) user FK; `title` varchar(200) not null snapshot; `content` text not null with length 1–2,000 DB constraint; `created_at` timestamptz not null default now(). Add material uniqueness `(id, course_id)`. All UUIDs generated server-side; no nullable fields. Generation accepts only nonblank output shorter than 2,000 chars to reject potential clipping. NUL/unpaired-surrogate model output is rejected before persistence with 502 llm_bad_response. Append-only generation never overwrites drafts.
- Metadata JSON is `{id, course_id, source_material_id, created_by, title, created_at}`; retrieve/create adds `content`. UUIDs are strings and timestamps UTC Z. Course lists omit content, newest first then ID descending. Current teacher-role membership controls every read/create, not creator ownership. Source uploads remain private; drafts are not lessons and have no student endpoint/publication state.
- POST `/api/teacher/materials/{material_id}/note-drafts`, GET `/api/teacher/courses/{course_id}/note-drafts`, GET `/api/teacher/note-drafts/{draft_id}` use shared cookie authentication and the safe error envelope. TEA-02 introduced read-only drafts; TEA-03 adds explicit PATCH editing below.
- Reuse **`src/backend/llm_client.py`** for Teacher and Admin AI. `get_llm_client()` supplies `complete(messages, max_tokens=, caller_id=)`; keep access checks, selected context, prompts and feature-specific output validation in the calling service. The client itself knows nothing about roles, practice sets or leak checks. Teacher notes use `teacher:{resolved_user_id}` caller IDs, fixed system instructions and one authorised source only. Do not change client limits or student behaviour for this increment.
- Notes accept strict UTF-8/plain PDF extraction, maximum 100 PDF pages and 8,000 normalised characters. No truncation, OCR, extraction persistence or multi-source retrieval. Draft editing retains these IDs/course checks; future publication must do so too; never publish by merely exposing this teacher API.


## TEA-03 editable draft contract

The current study_note_draft record additionally stores source_title varchar(200) NOT NULL (immutable source snapshot), version integer NOT NULL default1 CHECK>=1, updated_at timestamptz NOT NULL defaultnow(), and updated_by varchar(64) NOT NULL FK user.id. Existing rows backfill from title/created_at/created_by; new generation sets both timestamps to one instant, both creator/editor to the resolved teacher, version1 and both initial titles to the source title. Editable title remains varchar(200); content remains text with1–2000 character DB check. All fields live in PostgreSQL. No source files are rewritten. Downgrade removes only the four new fields/check/FK; re-upgrade backfills anew and does not recover dropped historical attribution.

Current metadata JSON is `{id, course_id, source_material_id, created_by, title, created_at, source_title, version, updated_at, updated_by}`; create/get/PATCH adds content, list omits it. UUIDs/string user IDs and UTC-Z timestamps retain their prior representation; version is an integer. Lists remain created_at DESC,id DESC after edits. Prior TEA-02 metadata above is historical; these fields are additive for all current responses.

PATCH `/api/teacher/note-drafts/{draft_id}` requires exactly `{title, content, version}`. Title is stripped and limited1–200 code points; content normalises CRLF/CR toLF, strips surrounding Unicode whitespace and permits1–2000. Null, wrong types, boolean/string/float/nonpositive version, unknown fields, NUL and unpaired surrogates return422 validation_error. Gate/identity/role/resource/course checks precede body validation; a locked current version mismatch returns409 draft_conflict. Successful updates change only title/content/version/updated_by/updated_at, with server-resolved current teacher and current UTC save time, and increment version once. New generation remains append-only; editing addresses an existing record. No body claim can change IDs/source/title snapshot/original creator/time. Concurrent same-version writers yield one200 and one409; commit failures roll back with safe503. Reusing an old version after a lost response cannot overwrite a committed change.

Any current teacher member of the course may edit, irrespective of creator. Role/membership locks hold access stable through commit; the cookie session is authenticated and locked for mutations. Editing never calls llm_client.py, and students have no draft endpoint. Future publication must create a separate immutable published representation so later draft edits cannot mutate a published version; no such records are introduced in TEA-03.


## TEA-02 MCQ draft integration contract

Implemented on the generation-only slice of US-TEA-02-02; see [exact MCQ contract](../workflow/specs/TEA-02-mcqs/plan.md). TEA-03 note editing merged through PR12. PostgreSQL stores these records; original source bytes live in material_file BYTEA. All fields below are nonnull, with no publication status or student access; batch version/audit fields are extended below.

| Entity | Fields, constraints and defaults |
|---|---|
| `mcq_draft_batch` | `id` UUID PK generated by application; `course_id` UUID FK course; `source_material_id` UUID with composite FK `(source_material_id,course_id)` to material; `created_by` varchar64 FK user; `source_title` varchar200 immutable source snapshot; `created_at` timestamptz default now(), UTC. |
| `mcq_draft_question` | `id` UUID PK generated by application; `batch_id` UUID FK batch; `position` integer1–3, unique within batch; `question` varchar200 (1–200 code points); `choices` JSONB array of exactly four strings, each1–80 code points; `correct_choice_index` integer0–3; `explanation` varchar200 (1–200 code points). No other defaults. |

Application normalises CRLF/CR toLF and strips strings; rejects blank/NUL/unpaired-surrogate values. Choices are distinct and question stems unique within a batch under trimmed casefold comparison. Complete model JSON must be shorter than2,000 characters with exactly three questions; raw JSON must contain exactly the expected keys without duplicates/nonfinite numbers. Every generation inserts a new complete batch and three questions in one transaction. Database checks constrain indices, positions, text lengths and JSON choices; exact-three/trim/distinct validation is application-enforced. Downgrade drops only the two new tables, discarding MCQ drafts but retaining sources/notes. PostgreSQL backups include these records and original material_file bytes.

All endpoints require current teacher membership through shared cookie authentication and CSRF validation. Identity/role checks occur before IDs/file/model work; membership/source are rechecked and locked before save. Any current managing teacher may read a batch regardless of creator. No client identity/course claims are used. No storage keys, local paths or provider metadata appear in responses.

- POST `/api/teacher/materials/{material_id}/mcq-drafts`: no required body;201 complete batch.
- GET `/api/teacher/courses/{course_id}/mcq-drafts`:200 metadata array ordered created_atDESC/idDESC.
- GET `/api/teacher/mcq-drafts/{batch_id}`:200 complete batch.

Metadata: `{id,course_id,source_material_id,source_title,created_by,created_at,question_count,version,updated_at,updated_by}` (question_count integer3, other fields strings, UUID IDs and UTC Z timestamp). Detail adds `questions` ordered by position, each `{id,position,question,choices,correct_choice_index,explanation}`. Choices preserve order; index0 corresponds to the first. These are unreviewed teacher-only answers, not approved student practice records. Future question editing/practice-set/publication must reuse these IDs and enforce server-side release rules through separate endpoints.

Source limits/errors match note generation (8,000 characters/100 pages, no OCR/truncation). Safe existing identity401/403/resource404/validation422/service503 envelopes apply. Model errors preserve429 retry information,503 unconfigured/unavailable,504 timeout and502 upstream/bad-response. Invalid/truncated output returns502 `llm_bad_response` and creates nothing; failed persistence rolls back the entire new batch. Reuse `src/backend/llm_client.py` unchanged for teacher/admin AI; MCQs use800 tokens and the same teacher caller identity, so note/MCQ requests share its per-teacher quota. Strict structure does not ensure factual accuracy; review is required. No automatic generation retry or idempotency: an explicit retry after a lost response can create another saved batch.


## SHR-01 authentication contract

Exact rules: [SHR-01 plan](../workflow/specs/SHR-01/plan.md). Real sessions replace the placeholder student header; teacher routes also require the shared authenticated session and ignore demo headers.

- `user` additions (nullable, additive): `email` varchar(254), stored trimmed and lower-case (CHECK `email = lower(email)`), unique index `ux_user_email`; `password_hash` varchar(255), format `scrypt$n$r$p$salt$hash`. NULL `password_hash` means the user cannot sign in. New signups get id `u-` plus 32 hex characters and role `student`.
- `auth_session`: `id` UUID PK; `token_hash` varchar(64) not null unique (SHA-256 hex of the cookie token, the raw token is never stored); `user_id` varchar(64) not null FK `user.id` ON DELETE CASCADE, indexed; `csrf_token` varchar(64) not null; `created_at` timestamptz not null default now; `expires_at` timestamptz not null, indexed (created plus `SESSION_TTL_SECONDS`, default 43200).
- Cookie `learnswe_session` (name from `SESSION_COOKIE_NAME`): HttpOnly, Path `/`, Max-Age equal to the session lifetime, SameSite from `SESSION_COOKIE_SAMESITE` (default Lax), Secure by default (required when `APP_ENV=production`).

| Method and path | Auth | Request | Success |
|---|---|---|---|
| `POST /api/auth/signup` | none | exactly `{display_name, email, password}` | 202 `{"status":"accepted"}`, no cookie; same reply for an already registered email; always creates a student |
| `POST /api/auth/login` | none | exactly `{email, password}` | 200 `{"user":{id,email,display_name,role},"csrf_token"}` and `Set-Cookie` |
| `POST /api/auth/logout` | session optional | none | 200 `{"status":"ok"}`, cookie cleared, session row deleted; a live session needs `X-CSRF-Token` |
| `GET /api/auth/me` | any session | none | 200 `{"user":{...},"csrf_token"}` |
| `GET /api/courses/{course_id}` | any role, course member | none | 200 `{id, title, created_at}` |

Every `/api/auth/*` response has `Cache-Control: no-store`. State-changing requests (POST, PUT, PATCH, DELETE) that use a session must send `X-CSRF-Token` equal to the session's token, and a present `Origin` must be in `ALLOWED_ORIGINS` or the server's own origin. Existing `/api/practice-sets/*`, `/api/attempts/*` and `POST /api/companion/messages` now require a `student` session; `X-Student-Id` is ignored.

| Status | `detail.code` | Condition |
|---|---|---|
| 401 | `unauthenticated` | no, unknown or expired session cookie, or user gone (replaces the student routes' `missing_student`) |
| 401 | `invalid_credentials` | login failed for any reason |
| 403 | `forbidden` | signed in but role not permitted |
| 403 | `csrf_failed` | missing or wrong `X-CSRF-Token`, or a disallowed `Origin` |
| 404 | `not_found` | course missing or caller not a member (same reply) |
| 422 | `validation_error` | invalid body or path; `fields` lists names only |
| 429 | `rate_limited` | login or signup limits; includes `retry_after_seconds` and `Retry-After` |
| 503 | `service_unavailable` | database or auth configuration unavailable or invalid |

Check order for a protected route: 401, then 403 `csrf_failed` (unsafe methods), then 403 `forbidden`. Role is re-read from the database on every request.

Shared handoff (`src/backend/auth/dependencies.py`): `current_user(role=None | "teacher" | ("teacher","admin")) -> Callable[..., AuthUser]` is a FastAPI dependency factory returning `AuthUser(id, email, display_name, role)`; `require_course_member(db, user, course_id) -> Course` raises 404 `not_found` unless a `course_membership` row exists (no admin bypass). Never read identity from a header, query or body. Seed login credentials with `uv run python -m auth.seed` after the teacher seed, using the `SEED_*` environment variables; nothing real is committed.


## TEA-03 MCQ editing and unpublished deletion

Authoritative extension: [TEA-03-mcqs-cleanup](../workflow/specs/TEA-03-mcqs-cleanup/plan.md). Migration20261104_tea03_mcq_edit follows20261103_shr01_auth. mcq_draft_batch gains nonnull version integer default1 CHECK>=1, updated_at timestamptz defaultnow(), updated_by varchar64 FK user.id. Backfill uses created_at/created_by; new generation uses identical original/edit timestamps and creator/editor. All original IDs, positions and attribution remain immutable. Downgrade drops additive audit fields only; edited question values remain.

PATCH /api/teacher/mcq-drafts/{id}: exactly {version,questions}, with exactly three objects {id,question,choices,correct_choice_index,explanation}. Existing question IDs must appear once each; array order does not reorder positions. Strict integer version>=1 and answer0..3 (no bool/string/float), four distinct choices, normalized nonblank question/explanation1–200 codepoints, choices1–80, no NUL/surrogates, duplicate stems/choices compared by casefold. No manual aggregate2000 ceiling. Lock batch, compare version, update all three/audit/version atomically, return200 complete batch; stale409 draft_conflict. Valid API no-ops still increment version; UI sends changed values only. List order stays created_atDESC/idDESC. Complete and metadata responses include version/updated_at/updated_by.

DELETE /api/teacher/note-drafts/{id}?version=N and /api/teacher/mcq-drafts/{id}?version=N require exactly one positive ASCII decimal query (no signs/whitespace/decimals). DELETE /api/teacher/materials/{id} has no version. Authorize before validating mutation input; success204 empty; inaccessible/already deleted404. Draft version conflicts409 draft_conflict. Delete MCQ children+batch atomically; restrictive future references409 draft_in_use. Sources with any note/MCQ reference return409 material_in_use; otherwise metadata and BYTEA disappear in one transaction. Quota lock32272610 serializes byte-removing deletion with uploads; source locks serialize with final generation checks, preventing orphan drafts. Any managing teacher may act. SQL failures503 and rollback; metadata never exposes bytes/keys/paths. Physical database space may not shrink immediately after logical quota recovery. PostgreSQL backups contain all original bytes and drafts; no filesystem backup is needed.

Every current draft is unpublished; there are no published/student references in this model. Future practice-set/publication integration must add restrictive references or deletion guards before exposing these records. No cascade from a source to drafts, no unpublish, no individual-question deletion and no student attempt deletion are introduced.
