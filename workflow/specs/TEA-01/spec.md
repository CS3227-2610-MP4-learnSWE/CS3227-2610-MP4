# Spec: TEA-01 Manage learning materials

> Storage contract update (2026-11-02): filesystem-specific requirements in this historical increment are superseded by [TEA-01 database storage](../TEA-01-db-storage/plan.md). Other feature behaviour remains binding. Current runtime storage uses PostgreSQL BYTEA after that increment is implemented.


Status: Approved (human plan approval, 2026-10-30; details below are implementation defaults within that approval)

## Goal

A teacher can upload private source material to a course they manage, browse it by course and topic, assign or remove a topic, and download the original file for lesson preparation.

## Behaviour

- A teacher sees only courses they manage and the topics and source materials within those courses. Materials can be filtered by one topic; unassigned materials appear in the unfiltered list.
- A teacher uploads one PDF or UTF-8 text file of at most 10 MiB with a title. A topic in the same course is optional. A successful upload returns metadata and leaves the original file available for authorised download.
- A teacher may change a material's topic to another topic in its course or set it to `null`. A later successfully committed assignment wins if updates race.
- The teacher Materials page replaces its preview with a working course selector, topic filter, search, upload dialog, per-row download and topic assignment. It shows loading/empty/error states and a Retry action for course loading failures.
- Source materials are private inputs for later drafting. Uploading does not create or publish a student-facing lesson.
- Errors explain accepted formats and the 10 MiB limit where relevant. The demo identity header works only in an explicitly enabled development environment; it is not production authentication.

## Acceptance criteria

The first five bullets preserve the two TEA-01 user stories' acceptance criteria:

- [ ] AC1: Supported files within configured size limits are saved to the selected course.
- [ ] AC2: Rejected uploads explain the accepted formats and limits.
- [ ] AC3: Uploading does not publish student-facing content.
- [ ] AC4: I can assign a material to a topic in its course and find it under that topic.
- [ ] AC5: I cannot organise or retrieve materials for courses I do not manage.
- [ ] AC6: A managing teacher can list their courses/topics/materials and download an uploaded original; an unassigned material remains discoverable in its course.
- [ ] AC7: An unknown identity, a student identity, a disabled demo gate, a missing course/material, and a foreign-course topic produce the contract's errors without exposing private metadata or file bytes.
- [ ] AC8: Rejected or interrupted uploads leave no committed metadata or staged/final file; successful metadata never points to a missing file as a result of upload failure.
- [ ] AC9: Concurrent uploads receive distinct material IDs/storage keys; concurrent topic changes only alter `topic_id` and `updated_at`, with the last committed update winning.

## Out of scope

Real login/account approval, student-facing publication, lesson reading, AI generation, OCR, file conversion, virus scanning, material deletion, pagination, and unrelated teacher preview screens. The Materials page is in scope. Existing student endpoints remain unchanged.

## Security and AI safeguards

- Every teacher endpoint checks a server-side teacher identity and course membership before reading or changing a course, topic, material, or file. An inaccessible record returns 404. No storage path or raw content appears in metadata JSON.
- Demo identity is explicitly limited to `APP_ENV=development` and `ALLOW_DEMO_IDENTITY=true`; default is disabled. `X-Demo-User-Id` is spoofable, so it must never be treated as real authentication or enabled outside development.
- Accept only `.pdf` and `.txt` filenames (case-insensitive) and verify contents: pypdf must parse a non-encrypted readable PDF; text must decode as UTF-8. Reject empty files. Stream with a hard 10 MiB limit rather than trusting `Content-Length`. Treat filenames, titles, text, and PDF contents as untrusted. Files remain under a private local directory; downloads are attachments.
- Normalize the title by trimming outer whitespace before checking its 1–200 character length. Compare UUIDs in canonical parsed form; compare user IDs exactly to seeded IDs. A topic must belong to the material/course, independent of the client-supplied ID. Concurrent topic updates commit atomically and affect no other material fields.
- No AI calls or retrieval are part of TEA-01. Later AI work must use only authorised materials and treat extracted content as data, not instructions.

## Open questions

No blocking questions for this increment. Production authentication, storage migration/backup, and user-managed course enrollment belong to later shared work.
