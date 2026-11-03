# Spec: TEA-01-db-storage — Persist original uploads in PostgreSQL

Status: Approved through the user's explicit implementation request, 2026-11-02. This replaces the filesystem portions of TEA-01/TEA-02 storage contracts; it does not change authentication, publication or AI behaviour. Baseline master6d65273 includes PR13 (MCQ generation and teacher review fixes).

## Goal and stories

Teachers' original uploads must survive backend restarts/redeploys without a persistent application disk. PostgreSQL stores metadata and original bytes atomically. The user chose a fresh database rather than importing old uploads, a100MiB deployment-wide original-byte budget and the existing10MiB per-file limit. Existing local databases/files remain untouched and are not automatically visible in the fresh database.

US-TEA-01-01 acceptance criteria:
- Supported files within configured size limits are saved to the selected course.
- Rejected uploads explain the accepted formats and limits.
- Uploading does not publish student-facing content.

US-TEA-01-02 acceptance criteria:
- I can assign a material to a topic in its course and find it under that topic.
- I cannot organise or retrieve materials for courses I do not manage.

The existing note/MCQ stories remain operational: authorised source generation, failure preservation and unpublished output. No new student endpoint or publication path.

## Acceptance criteria

- [x] AC1: PDF/UTF-8 text originals and existing metadata are persisted in PostgreSQL in one transaction;201 immediately downloads byte-identical original bytes. Restart/redeploy requires no permanent filesystem directory.
- [x] AC2: Existing paths, metadata shapes, list ordering, topic assignment/filter/search, filename handling, title/Unicode checks and development identity/course checks stay compatible. Bytes/internal keys never appear in metadata responses or lists.
- [x] AC3: File content is1–10,485,760 bytes; validate actual PDF/UTF-8 content and preserve multipart ingress caps. Rejection/failure creates neither metadata nor binary rows and changes no earlier work.
- [x] AC4: A transaction advisory lock serialises deployment-wide quota admission. Actual stored bytes cannot exceed104,857,600 through concurrent uploads; exact-boundary upload succeeds, excess413 storage_quota_exceeded. UI explains100MiB total and10MiB per file with recoverable quota errors.
- [x] AC5: Downloads and note/MCQ generation resolve current teacher/course access before fetching binary content. Missing content/DB failure yields safe503; no inaccessible source bytes or paths leak.
- [x] AC6: Shared extraction accepts bytes, strict UTF-8/text-based PDFs and existing100page/8,000character limits. Model prompts/output checks/client unchanged; no DB transaction open during inference; post-model role/membership/source rechecks remain.
- [x] AC7: New migration creates binary table and removes storage_key only when materials are empty. Populated upgrade/downgrade refuses safely with fresh-database guidance, preserving existing rows/schema/files; empty downgrade/reupgrade works.
- [x] AC8: Runtime/endpoints need no FILE_STORAGE_DIR, storage keys, generated private paths, permanent-file writes or cleanup. Temporary multipart spooling is permitted and closes on every outcome. Health/student APIs remain usable without teacher DB configuration.
- [x] AC9: Shared contract, guides, environment examples, deployment/setup/help and tests describe PostgreSQL storage accurately, including fresh-data boundaries, quotas, DB backup and provider capacity monitoring. Historical specifications are clearly identified as superseded for storage.
- [x] AC10: Variant B independent tests/verifier, backend/browser suites, types/lint/format/build and mobile/desktop both themes pass using isolated schemas/fakes. Commit locally only; human publishing gate retained.

## Boundaries and safety

No importer, deletion/replacement endpoint, object storage, production auth, new model wrapper, live LLM call or deployment. Never reset, migrate, seed or alter the developer's existing database/files/.env. Implementation/testing uses isolated data only; configuring the user's fresh database is documented, not silently performed. Old-data rollback uses previous code/config/database/files; no downgrade reconstructs originals. Byte quota is not total PostgreSQL disk usage or a guarantee of provider free-plan capacity.

## Open questions

None. Exact contracts and independent fixture details are fixed in plan.md.

Verified PASS at1c7483370a02ccc6ae31c08e8416b81c5a7ba254; evidence in logs/TeacherDatabaseStorage.md. All acceptance criteria complete after one correction round; no live provider/deployment check.
