# Shared data contract for teacher features

This is the shared handoff contract for TEA-01 source materials and the TEA-02 notes-generation slice. These development-only features do not establish production authentication. The API contract is authoritative for black-box tests, so tests need import only the FastAPI `app`.

## Runtime and persistence

- Python backend uses synchronous SQLAlchemy 2, psycopg, PostgreSQL 16, and Alembic. `DATABASE_URL` is a psycopg URL such as `postgresql+psycopg://user:password@localhost:5432/learnswe`. `FILE_STORAGE_DIR` is an absolute private local directory. Both are required for TEA-01; missing/invalid configuration, unavailable database, or unavailable storage yields 503 with `service_unavailable` on TEA-01 requests.
- `APP_ENV` defaults to a non-development value; `ALLOW_DEMO_IDENTITY` defaults to false. The demo header is usable only when `APP_ENV=development` **and** `ALLOW_DEMO_IDENTITY=true`. Production and all other environments reject it with 403 `demo_identity_disabled`, even when the header is present. This header can be spoofed and must not be presented as authentication.
- All records persist in PostgreSQL. IDs are canonical UUID strings except `user.id`, which is a stable string. Timestamps are UTC `timestamptz`; JSON timestamps use ISO 8601 with a `Z` suffix. Database uniqueness and foreign keys enforce membership/topic boundaries.
- `user`: `id` varchar(64) primary key, `display_name` varchar(200) not null, `role` varchar(16) not null constrained to `student`, `teacher`, or `admin`, `created_at` timestamptz not null default current UTC time.
- `course`: `id` UUID primary key default generated UUID, `title` varchar(200) not null, `created_at` timestamptz not null default current UTC time.
- `course_membership`: `course_id` UUID not null foreign key, `user_id` varchar(64) not null foreign key, composite primary key (`course_id`, `user_id`). A teacher may manage a course only if this membership exists and their role is `teacher`.
- `topic`: `id` UUID primary key default generated UUID, `course_id` UUID not null foreign key, `name` varchar(200) not null, `created_at` timestamptz not null default current UTC time; unique (`course_id`, `name`).
- `material`: `id` UUID primary key default generated UUID, `course_id` UUID not null foreign key, `topic_id` UUID nullable, `uploaded_by` varchar(64) not null user foreign key, `title` varchar(200) not null, `original_filename` varchar(255) not null basename, `media_type` varchar(64) not null (`application/pdf` or `text/plain; charset=utf-8`), `size_bytes` bigint not null checked 1–10,485,760, private unique `storage_key` varchar(255) not null, `created_at` and `updated_at` timestamptz not null default current UTC time. Enforce topic in the same course with a composite foreign key or a transactionally equivalent check; `storage_key` is never returned by the API.
- Use an Alembic migration for these tables. From `src/backend`, run `uv run alembic upgrade head`, then `uv run python -m teacher_materials.seed`. The explicit idempotent seed command (not automatic on every request) inserts only missing seed records and memberships. It may be rerun without duplication and must not erase uploads or teacher edits.

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

All paths below start with `/api/teacher`. Send `X-Demo-User-Id: demo-teacher` in the enabled development environment. List responses are bare arrays; courses and topics sort by `created_at` ascending then `id` ascending, materials by `created_at` descending then `id` ascending. There is no pagination in this increment. All UUID path/query/body values must parse as UUIDs. Unknown JSON fields are rejected with 422. There are no optional data wrappers or storage paths.

| Method and path | Request | Success |
|---|---|---|
| `GET /courses` | none | 200 `Course[]` for the teacher's memberships |
| `GET /courses/{course_id}/topics` | none | 200 `Topic[]` for managed course |
| `GET /courses/{course_id}/materials` | optional `topic_id` UUID query | 200 `Material[]` for managed course, filtered to exactly that topic when supplied |
| `POST /courses/{course_id}/materials` | multipart form: required `file` (one binary), required `title` string, optional `topic_id` UUID string | 201 `Material` |
| `PATCH /materials/{material_id}` | JSON object with required `topic_id`: UUID string or `null`; no other fields | 200 `Material` |
| `GET /materials/{material_id}/file` | none | 200 original bytes, `Content-Type` equal to material `media_type` (for text, UTF-8 charset), `Content-Disposition: attachment` with safe original basename |

`Course = {id, title, created_at}`. `Topic = {id, course_id, name, created_at}`. `Material = {id, course_id, topic_id, uploaded_by, title, original_filename, media_type, size_bytes, created_at, updated_at}`. IDs except `uploaded_by` are canonical UUID strings; `uploaded_by` is the user ID string; `size_bytes` is an integer; timestamps are UTC ISO 8601 strings ending in `Z`; other values are strings except nullable `topic_id`. Use these exact snake_case keys; `topic_id` is `null` when unassigned. No file contents, absolute paths, `storage_key`, publishing state, or teacher-private records are included in JSON. On POST, `uploaded_by` is the resolved server-side user, never client input.

Title is trimmed of leading/trailing Unicode whitespace, then must have 1–200 characters. File extension uses the final basename and case-insensitive `.pdf`/`.txt`; a missing/empty filename or unsupported extension is 415. The upload must contain 1 through 10,485,760 bytes. PDF parsing with pypdf must succeed and find at least one page; encrypted, corrupt, or unreadable PDFs are 422. Text must be valid UTF-8; empty/invalid text is 422. Accepted `media_type` is derived from the validated extension/content, not a client MIME claim. Original basename is retained for download after removing any path components and control characters. The material ID and `storage_key` are generated server-side and unique for simultaneous uploads.

Errors use exactly `{"detail":{"code":"...","message":"..."}}` with an HTTP status. The message is human-readable; for 413 it must mention `10 MiB`, and for 415 it must mention `PDF` and `UTF-8 text`. No stack trace, SQL error, storage key, or path is exposed.

| Status | `detail.code` | Condition |
|---|---|---|
| 401 | `unauthenticated` | Enabled gate, but header absent or user ID unknown |
| 403 | `demo_identity_disabled` | Demo gate not fully enabled |
| 403 | `forbidden` | Known identity is not a teacher |
| 404 | `not_found` | Missing or inaccessible course/material; topic absent, inaccessible, or in another course |
| 413 | `file_too_large` | Stream exceeds 10,485,760 bytes, regardless of `Content-Length` |
| 415 | `unsupported_media_type` | Filename has no supported extension |
| 422 | `validation_error` | Bad UUID, fields, title, empty/invalid file, encrypted/corrupt PDF, or invalid UTF-8 |
| 503 | `service_unavailable` | Missing/invalid config, DB unavailable, or private storage unavailable |

Request processing order is: check the development gate; require the header; look up identity in the database; check teacher role; check course/material ownership; validate fields and file; then store/mutate. Thus a caller cannot use malformed input to probe inaccessible records. For list filtering and topic assignment, a valid UUID from another course yields 404. A missing `topic_id` on PATCH is 422; JSON `null` unassigns it. PATCH changes only `topic_id` and `updated_at`; if two updates race, the last committed value wins. Settings may be read once at app startup in production, but tests that vary gate values must create a fresh app/config context or reset cached settings per case.

## Storage and transaction boundary

Create a unique staged file below `FILE_STORAGE_DIR` while streaming, cap byte count, validate content, and atomically move it to its generated final private key before committing the metadata transaction. If validation, move, or commit fails, roll back metadata and remove staged/final files created for that request. Do not serve files directly from a public static mount. A read after a successful 201 must find the file; if a previously committed file is externally missing, respond 503 rather than exposing a path. Downloads check current teacher/course access before opening it. File access must remain within the storage root even if a database key is malformed.

## Integration test setup

Tests use a real isolated PostgreSQL schema, not SQLite: read `TEA01_TEST_DATABASE_URL` as the base database URL, create a unique schema for the run, set the app `DATABASE_URL` with psycopg `options=-csearch_path=<schema>` before importing/configuring the app, run `uv run alembic upgrade head` and `uv run python -m teacher_materials.seed`, and use a temporary `FILE_STORAGE_DIR`. Set `APP_ENV=development`, `ALLOW_DEMO_IDENTITY=true`. Drop the schema and remove files in teardown. The only application import required for black-box tests is `app`; HTTP requests and the seed CLI/SQL fixture can establish state. Existing student API tests must still pass unchanged. Configure environment before app import, or provide a documented app factory/config reset if the application loads settings at import time.

## Internal handoff interfaces

Keep module boundaries single-purpose; these names are the shared implementation interface, while HTTP tests rely only on the API above:

- `src/backend/teacher_materials/models.py`: SQLAlchemy `User`, `Course`, `CourseMembership`, `Topic`, `Material` models with the columns above.
- `src/backend/teacher_materials/demo_identity.py`: `require_teacher(request, session) -> User`, which enforces the gate, resolves the header, and checks role; `require_managed_course(session, teacher, course_id) -> Course`, which returns 404 for absent or inaccessible courses.
- `src/backend/teacher_materials/storage.py`: `save_upload(upload, storage_root) -> StoredFile`, where `StoredFile` has `storage_key`, `original_filename`, `media_type`, `size_bytes`; `remove_file(storage_root, storage_key) -> None`; `resolve_file(storage_root, storage_key) -> Path` rejects escape paths.
- `src/backend/teacher_materials/routes.py`: `router` containing the six operations above. It uses one synchronous SQLAlchemy session per request, checks access before querying records, and handles file/DB cleanup at the transaction boundary.
- `src/backend/teacher_materials/seed.py`: `seed_demo(session: Session) -> None` and the exact rerunnable CLI `uv run python -m teacher_materials.seed` from `src/backend`; document its invocation in `docs/DeveloperGuide.md`.

The test-designer must not import these internals or implementation files. The seed CLI path is fixed because the independent test fixture invokes it.

## Cross-role integration and authentication handoff

- These PostgreSQL users, courses, memberships and topics are the common foundation. Later student/admin work should reuse their IDs and relationships rather than create parallel teacher-specific copies.
- A source `material` is private teacher input, **not** a published lesson or a student practice set. Generated content references its material ID through separate records. TEA-01 introduced sources only; TEA-02 now creates unpublished study-note drafts as described below. MCQ generation, publication and student answer release remain future work.
- Current student practice still reads the server fixture `intro-se-1` and stores attempts in the in-memory `AttemptStore`. Its placeholder `X-Student-Id` is not a foreign-key integration with these new tables. Nothing automatically migrates attempts, enrolls students or changes the existing scoring flow.
- Real authentication must resolve the signed-in account to the shared user ID on the server and replace the demo-header resolver. Keep the teacher-role and course-membership checks; the demo role switcher/header is not proof of identity. Demo seeds are for development only, with no credentials or passwords.
- Back up PostgreSQL and the private file directory together. A database-only restore cannot recover uploaded bytes. Storage keys remain opaque server-owned references; future object storage can replace local file resolution without exposing local paths or turning private uploads into public URLs.

## TEA-02-notes integration contract

See [TEA-02 notes contract](../workflow/specs/TEA-02-notes/plan.md) for exact endpoints, representations, errors, limits and test interfaces. This is an implemented additive draft-generation slice; editing and publication remain deferred.

- `study_note_draft`: UUID `id` PK; UUID `course_id` and `source_material_id` not null, composite FK to material `(id, course_id)` and course FK; `created_by` varchar(64) user FK; `title` varchar(200) not null snapshot; `content` text not null with length 1–2,000 DB constraint; `created_at` timestamptz not null default now(). Add material uniqueness `(id, course_id)`. All UUIDs generated server-side; no nullable fields. Generation accepts only nonblank output shorter than 2,000 chars to reject potential clipping. Append-only generation never overwrites drafts.
- Metadata JSON is `{id, course_id, source_material_id, created_by, title, created_at}`; retrieve/create adds `content`. UUIDs are strings and timestamps UTC Z. Course lists omit content, newest first then ID descending. Current teacher-role membership controls every read/create, not creator ownership. Source uploads remain private; drafts are not lessons and have no student endpoint/publication state.
- POST `/api/teacher/materials/{material_id}/note-drafts`, GET `/api/teacher/courses/{course_id}/note-drafts`, GET `/api/teacher/note-drafts/{draft_id}` use the existing demo gate/header and safe error envelope. No editable fields in this increment.
- Reuse **`src/backend/llm_client.py`** for Teacher and Admin AI. `get_llm_client()` supplies `complete(messages, max_tokens=, caller_id=)`; keep access checks, selected context, prompts and feature-specific output validation in the calling service. The client itself knows nothing about roles, practice sets or leak checks. Teacher notes use `teacher:{resolved_user_id}` caller IDs, fixed system instructions and one authorised source only. Do not change client limits or student behaviour for this increment.
- Notes accept strict UTF-8/plain PDF extraction, maximum 100 PDF pages and 8,000 normalised characters. No truncation, OCR, extraction persistence or multi-source retrieval. Draft editing/publication later must reference these IDs and retain course checks; never publish by merely exposing this teacher API.
