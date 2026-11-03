# Plan: TEA-01 Manage learning materials

> Storage contract update (2026-11-02): filesystem-specific requirements in this historical increment are superseded by [TEA-01 database storage](../TEA-01-db-storage/plan.md). Other feature behaviour remains binding. Current runtime storage uses PostgreSQL BYTEA after that increment is implemented.


## Data model

Implement the `user`, `course`, `course_membership`, `topic`, and `material` tables, constraints, UTC timestamps, and idempotent seed exactly as [SharedDataContract.md](../../../docs/SharedDataContract.md) defines. Use PostgreSQL 16 with synchronous SQLAlchemy 2 and psycopg; create tables through Alembic, not request-time DDL. Material metadata and files are private. A composite topic/course constraint or an equivalent transactionally safe check prevents cross-course assignment. Do not alter existing student data or endpoints.

## API endpoints

The following are the complete TEA-01 paths. All requests require the gated teacher identity and return the exact JSON shapes and error codes in `docs/SharedDataContract.md`.

| Method and path | Role | Request | Success |
|---|---|---|---|
| `GET /api/teacher/courses` | teacher | none | 200 `Course[]` |
| `GET /api/teacher/courses/{course_id}/topics` | managing teacher | none | 200 `Topic[]` |
| `GET /api/teacher/courses/{course_id}/materials` | managing teacher | optional `topic_id` UUID query | 200 `Material[]` |
| `POST /api/teacher/courses/{course_id}/materials` | managing teacher | multipart `file`, `title`, optional `topic_id` | 201 `Material` |
| `PATCH /api/teacher/materials/{material_id}` | managing teacher | JSON `{ "topic_id": <UUID or null> }` | 200 `Material` |
| `GET /api/teacher/materials/{material_id}/file` | managing teacher | none | 200 attachment with original bytes |

Status/code pairs: 401 `unauthenticated`, 403 `demo_identity_disabled` or `forbidden`, 404 `not_found`, 413 `file_too_large`, 415 `unsupported_media_type`, 422 `validation_error`, 503 `service_unavailable`. Error envelope is `{"detail":{"code":"...","message":"..."}}`. The specific condition and check order are in the shared contract. Unknown fields and malformed IDs return 422 after access checks where a resource can be identified.

## Components and modules

- Backend `teacher_materials/models.py`: five ORM models and related migration. Keep the common schema available to later features, but introduce no generic repository framework.
- Backend `teacher_materials/demo_identity.py`: `require_teacher(request, session) -> User` and `require_managed_course(session, teacher, course_id) -> Course`. Both enforce server-side access; the header is development-only and spoofable.
- Backend `teacher_materials/storage.py`: `save_upload(upload, storage_root) -> StoredFile`, `remove_file(storage_root, storage_key) -> None`, and `resolve_file(storage_root, storage_key) -> Path`. Stream and validate before finalizing a generated private path; no public static mount.
- Backend `teacher_materials/routes.py`: FastAPI `router` for six endpoints, synchronous DB sessions and atomic metadata/file cleanup. Keep route responses as shared-contract DTOs, never ORM `storage_key` exposure.
- Backend `teacher_materials/seed.py`: `seed_demo(session: Session) -> None` upserts the named fixture and preserves user-created records. A documented CLI command calls this function explicitly after migrations.
- Existing FastAPI `app`: include `router` once. Existing student routes must behave as before.
- Frontend Teacher Materials page: replace the current preview with a real page. Keep heading `Your materials, all together.`. Expose labeled controls `Course`, `Topic filter`, `Search your materials`, and `Upload material`; upload dialog fields `Title`, `Topic optional`, `Choose a file`, and submit `Upload`. Each material row has `Download` and `Change topic` actions (or a labeled topic selector). Show loading, empty, upload validation, and recoverable errors; a course-load error has a `Retry` button. Search filters currently loaded material titles and filenames on the client; topic filter uses the API query. Default to the first returned course. Show newest material first. Accessibility: programmatic labels, keyboard-operable dialog/actions, visible focus and status text.
- Frontend teacher-materials API client functions: `listTeacherCourses(): Promise<Course[]>`, `listTeacherTopics(courseId: string): Promise<Topic[]>`, `listTeacherMaterials(courseId: string, topicId?: string): Promise<Material[]>`, `uploadTeacherMaterial(courseId: string, input: {file: File; title: string; topicId?: string}): Promise<Material>`, `setTeacherMaterialTopic(materialId: string, topicId: string | null): Promise<Material>`, `downloadTeacherMaterial(materialId: string): Promise<Blob>`. They use the existing shared HTTP client/configuration, preserving all practice calls. The development demo header is sent explicitly for teacher calls only when the demo gate is configured; upload uses `FormData` without a forced JSON content type and download consumes a `Blob` plus attachment filename. Do not add header spoofing to student calls.
- Docs: update `DeveloperGuide.md` with PostgreSQL setup, Alembic, exact seed command, environment gate and private file directory; update `UserGuide.md` with the working Materials page and its unpublished status.

The backend `teacher_materials` module and seed CLI paths are fixed for the test fixture. Independent backend tests import only `app`. Frontend browser tests mock the business API at the HTTP boundary, not implementation functions.

## AI usage

None. Uploaded content is stored as untrusted source input. TEA-01 neither invokes the SoC LLM nor creates student-facing output.

## Test plan

Use a real PostgreSQL 16 test instance via `TEA01_TEST_DATABASE_URL`, create a unique schema per test run, set the app `DATABASE_URL` to that schema, migrate and seed, and use a temporary `FILE_STORAGE_DIR`. Set the development demo gate only for positive-path cases. A disposable local example is `postgresql+psycopg://learnswe:learnswe-local-only@127.0.0.1:55432/learnswe_test`. The fixture must not assume this URL is available in CI. Keep existing student tests in the suite.

CI must provide a PostgreSQL 16 service and a private temporary file directory for these tests. Tests may skip locally with a clear reason when `TEA01_TEST_DATABASE_URL` is absent; they must execute in CI. Configure gate values so negative tests can vary them safely without cross-test leakage. Test schema creation and migration occur before importing the app when settings are import-time cached.

| Criterion | Minimum independent test evidence |
|---|---|
| AC1 | `test_tea01_upload_pdf_and_text_persists_metadata_and_bytes`: upload each format, assert 201 metadata, DB row, byte-identical download and persistence across requests. |
| AC2 | `test_tea01_rejects_file_types_sizes_and_bad_content`: 415 extension, 413 streamed over-limit, 422 empty/invalid UTF-8/encrypted or corrupt PDF/title, messages state formats/limit, no residue. |
| AC3 | `test_tea01_upload_does_not_publish`: existing student content endpoint/result unchanged after upload; no publication record created. |
| AC4 | `test_tea01_assign_filter_and_unassign`: initial unassigned list, assign same-course topic, filter, unassign, assert timestamps and only topic field changes. |
| AC5 | `test_tea01_cross_course_access_is_hidden`: Teacher B cannot list, upload, assign or download Course A records; foreign topic rejected 404. |
| AC6 | `test_tea01_teacher_lists_and_downloads`: courses/topics/materials shapes, sort order, attachment headers, file content. |
| AC7 | `test_tea01_demo_gate_and_roles`: absent/unknown header, disabled or non-development gate, student role; malformed UUID and missing record; exact envelope/status/code. |
| AC8 | `test_tea01_failed_upload_cleans_files_and_rows`: injected move/commit failure and invalid upload leave no row or staged/final file; 503 where appropriate. |
| AC9 | `test_tea01_concurrent_uploads_and_assignments`: unique IDs/keys/files from simultaneous uploads; two topic updates yield one complete valid topic value and only timestamp/topic change. |

Frontend browser tests, with mocked TEA-01 HTTP responses, must cover course/topic selection, newest-first material rows, title/filename search, upload form and success refresh, assignment/unassignment, attachment download, empty state, and error/retry behavior. Assert the exact visible labels above and that existing practice navigation and API calls still work. A separate real-backend smoke check covers API integration; frontend mocks do not establish backend correctness.

Security cases: path-traversal filename and tampered storage key cannot escape the private directory; wrong role/foreign course gets no metadata or bytes; a supplied MIME label cannot bypass extension/content validation; a spoofed header is rejected outside the explicit development gate. Log cases in `workflow/security/test-log.md` during verification. Tests should not import implementation internals to avoid coupling to the developer branch.

## Decisions

- Approved scope on 2026-10-30: PDF and UTF-8 text, 10 MiB maximum, trimmed 1–200 character title, private files, course/topic listing, topic assignment, authorised download, PostgreSQL persistence, gated demo identity. These details fill in the format/limit and enrollment questions identified in the original stories for this increment.
- A membership is an explicit row, not an inferred teacher ownership field. The seed grants two teachers separate courses and a student one course to support isolation tests.
- List endpoints return bare arrays without pagination; materials are newest-first, courses/topics oldest-first with ID tie breakers.
- Store generated file keys privately; move a validated file into place before metadata commit, then clean files on any failure. This makes a successful 201 immediately downloadable.
- Reject malformed or cross-course topic references; `PATCH` requires `topic_id` but accepts `null` to unassign. The last committed update wins without modifying unrelated fields.
- Production authentication, student publication and AI behavior are separate features; the demo header is only a development fixture.
