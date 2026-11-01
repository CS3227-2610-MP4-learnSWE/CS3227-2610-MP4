# Plan: TEA-02-notes — Generate and save draft notes

Status: Approved through the user's implementation request, 2026-11-01. This is the developer/independent-test contract. Use Variant B from the same recorded spec commit; test-designer reads this contract, not feature source code.

## Data model and migration

Add `study_note_draft`: `id` UUID PK generated server-side, `course_id` UUID not null, `source_material_id` UUID not null, `created_by` varchar(64) not null FK user.id, `title` varchar(200) not null source title snapshot, `content` text not null with DB check char_length(content) between 1 and 2000, and `created_at` timestamptz not null server default now(). Enforce content nonblank in application validation. Add material UNIQUE(id, course_id), then draft composite FK(source_material_id, course_id) -> material(id, course_id), plus course FK. No publication column, editing endpoint, draft deletion or student API. Existing material rows/seeds remain untouched. Migration downgrade removes draft table before material's new uniqueness constraint. Export model through existing SQLAlchemy metadata.

Creation validates model text at 1–1,999 characters after stripping (reject >=2,000 before stripping as well, because the shared client may have clipped it). The schema's 2,000 maximum leaves space for future reviewed editing; this slice never generates a 2,000-character row.

## API and exact representations

All paths start /api/teacher; reuse X-Demo-User-Id and existing development gate. All UUID response values are canonical strings. UTC timestamps end in Z. `DraftMetadata = {id, course_id, source_material_id, created_by, title, created_at}`; all fields strings, IDs UUID except created_by. `Draft = DraftMetadata + {content: string}`. No wrapper, status, storage key, raw filename or provider metadata.

| Method/path | Input | Success |
|---|---|---|
| POST /materials/{material_id}/note-drafts | No body required; body is not used for identity/context | 201 Draft |
| GET /courses/{course_id}/note-drafts | No body | 200 DraftMetadata[] newest created_at then UUID descending |
| GET /note-drafts/{draft_id} | No body | 200 Draft |

Teacher-role membership grants access to all drafts of that course, including another member teacher's drafts. Same existing 401 unauthenticated; 403 demo_identity_disabled/forbidden; 404 not_found; 422 validation_error for malformed UUID; 503 service_unavailable for database/private-file/config failures. Identity/gate/role checks precede identifier validation; accessible resource lookup precedes extraction/model work. Missing or malformed files on disk give controlled 503 if not readable at all, and source_unreadable when bytes can be read but decoding/parsing fails.

All errors use exactly {"detail":{"code":"...","message":"..."}}; messages are fixed safe text, never exception text. LLM error mapping:

| Condition / exception | Status/code | Message requirement |
|---|---|---|
| empty/whitespace extraction | 422 source_text_empty | State no usable text; scanned PDFs need a text-based source |
| extracted text >8,000 chars | 422 source_text_too_large | Mention 8,000 characters |
| PDF >100 pages | 422 source_text_too_large | Mention 100 pages; reject before extracting any page |
| invalid UTF-8, malformed/encrypted PDF, extraction exception | 422 source_unreadable | State source cannot be read as UTF-8 text/text-based PDF |
| LlmRateLimited | 429 llm_rate_limited | Fixed retry message; Retry-After header uses retry_after_seconds integer |
| LlmBusy | 429 llm_busy | Fixed retry message; Retry-After header uses retry_after_seconds integer |
| LlmNotConfigured | 503 llm_not_configured | State AI service is not configured |
| LlmInputTooLarge | 422 source_text_too_large | State source cannot fit request limit; normally unreachable due to 8,000 source cap |
| LlmTimeout | 504 llm_timeout | Fixed retry message |
| LlmUpstreamError | 502 llm_upstream_error | Fixed generation-failed message |
| LlmBadResponse or unusable reply | 502 llm_bad_response | Fixed unusable-output message |
| other LlmError | 503 llm_unavailable | Fixed unavailable message |

No controller-level LLM retries. The unchanged client owns its existing bounded retry and rate-limit behaviour. No source/model text or credentials in error bodies/logs.

## Reused interfaces and implementation boundaries

- Reuse shared SQLAlchemy User/Course/CourseMembership/Material metadata and Alembic setup, teacher `require_teacher(request, session)` and `require_managed_course(session, teacher, course_id)`; private `storage_root()`/`resolve_file(root, storage_key)` and existing teacher HTTP transport. Extract narrowly reusable session/material lookup helpers only if necessary; preserve TEA-01 semantics.
- Add one focused notes backend package/module for extraction/generation/service and router; wire its router alongside existing routes. Source text extraction is not persistence and must not create a second upload store.
- Use unchanged `llm_client.get_llm_client` as a FastAPI dependency (`Depends(get_llm_client)`) so tests can set `app.dependency_overrides[get_llm_client] = lambda: fake`. The fake exposes `complete(messages, *, max_tokens, caller_id)` and returns `LlmReply(text, finish_reason, prompt_tokens, completion_tokens)` or raises an existing `LlmError` subclass. Clear overrides after every test. Do not implement a second wrapper.
- Build exactly two `ChatMessage`s: system fixed instruction (concise grounded notes, headings/bullets, no obedience to source instructions); user extracted source only. Call `complete(..., max_tokens=600, caller_id=f"teacher:{teacher.id}")`. No source title or arbitrary frontend values augment prompt. The total fixed prompt plus 8,000-char source must fit the existing 12,000 input ceiling. Source instructions remain data; no tools/retrieval/provider config override exists.
- Read strict UTF-8 text. PDF uses pypdf, rejects encrypted/unreadable/no-page PDFs, checks len(pages)<=100 first, then extracts page text in order with newlines. Text normalisation is CRLF -> LF, then CR -> LF, then strip surrounding Unicode whitespace; limits count Python Unicode characters in final normalised text, not bytes. Cumulative PDF checks may trim outer whitespace but must preserve internal text/page separators. Stop as soon as normalised cumulative text exceeds 8,000; no partial generation.
- Release initial DB session/transaction before model complete. Copy only scalar source/identity snapshot needed. Open a new session afterwards and recheck user role/gate, source and current course membership before insert, serialize after flush/refresh and before commit. No transaction/file cleanup can delete source bytes. Failed metadata commit means no new row; no output or old draft overwrite.

## Frontend contract

Route `/teacher/generate?course={id}&draft={id}`. Reuse existing teacher course/material APIs, form components and themes. Extend `requestTeacher` with optional fifth `timeoutMs` argument defaulting to existing REQUEST_TIMEOUT_MS; only generation passes 45_000. Existing multipart/blob/header behaviour stays identical.

Visible labels: heading `AI content studio`; selectors `Course`, `Source material`; action `Generate draft notes`; list heading `Saved drafts`; viewer badge `Unpublished draft · Review required`; empty list `No saved drafts yet`; no source `Upload a source material to generate notes.`; unsupported feature `MCQ generation is not available in this increment.`. Viewer shows source title snapshot, creator ID and local-readable created_at. Render content as React text in a whitespace-preserving container, never innerHTML/Markdown. Use a visible notice `Generation sends the selected source text to the SoC LLM.` and input-limit text mentioning `8,000 characters` and `100 pages`.

Initial query course selects that managed course; absent course defaults to first managed course. An inaccessible queried course/draft shows recoverable error without silently displaying another draft. Selecting a course clears current source/viewer/draft query and loads its materials/drafts; selecting a saved draft updates query and fetches it. Generation snapshots selected course/source; keep a single busy guard until settled and ignore completion when current course differs. Course/source/list/view requests need stale-result guards. On success select/open created draft and refresh saved list, with visible success message `Draft notes generated and saved.`. Errors retain chosen source and saved drafts; explicit retry uses another click. Show `If a response is lost, generating again may create another saved draft.` near generation failure/controls. No automatic POST retry.

Frontend API service exports list/get/generate draft calls with types matching above. Test-designer intercepts HTTP paths rather than importing UI internals; upload seed fixtures are established through existing APIs. No frontend answer keys or student feature changes.

## Test plan and fixtures

Use existing TEA01_TEST_DATABASE_URL fixture: unique PostgreSQL schema per run, Alembic upgrade head and explicit seed, temporary FILE_STORAGE_DIR. Existing seeded IDs are recorded in SharedDataContract; Course A `11111111-1111-4111-8111-111111111111`, Course B `22222222-2222-4222-8222-222222222222`, Teacher A demo-teacher, Teacher B demo-teacher-other, student demo-student. Upload sources via existing multipart POST /courses/{id}/materials; DB fixture can alter/corrupt file state or revoke membership inside fake.complete for adversarial tests. Never use developer DB/file data.

| Criteria | Independent evidence |
|---|---|
| AC1, AC4 | text/PDF upload -> generate -> list/get; exact fields, source title/creator, sort, two generations distinct; new TestClient/process reopen reads persistent row; migration constraints |
| AC2 | empty text, scanned/no-text PDF, UTF-8 corruption, malformed/encrypted PDF, 8,000/8,001 boundary and 100/101 pages, no model invocation on failures |
| AC3 | capture two messages/max_tokens/caller_id, injection remains source data; normal output accepted, blank/nonstring/length-finished/2,000 chars rejected, client unchanged |
| AC5 | gate/missing/unknown/student/foreign-course/source/draft/malformed UUID; no storage paths/keys or credential-like exception text |
| AC6 | fake checks no active DB transaction on generation; revoke membership or remove source during fake; injected commit failure; concurrent distinct generations; source bytes and existing drafts unchanged |
| AC7, AC8 | intercepted browser generation/list/get, real labels, escaped HTML, selection controls and busy guard, slow/error/retry, stale course/list/view responses, query reload, no unexpected POST retries |
| AC9 | existing suites, types/lint/build, responsive no page overflow in light/dark, guides accurate; no live provider calls |

No live LLM calls, deployment, push or PR without separate user approval. Commit reviewed implementation on the feature branch only. Independent read-only verifier re-runs suites and reviews access, prompts, transaction boundaries, limits and guide truthfulness; max two fix rounds.

## Decisions

User chose generate/save/view only and rejection of oversized sources rather than chunking. Fixed existing client ceiling remains unchanged. Source excessive-page code, output rejection boundary, safe LLM codes, fifth timeout argument and exact UI labels above are implementation defaults to make independent tests possible, not scope additions. Real authentication, editing, publication, MCQs, OCR, chunking, generation idempotency and persistent rate limits remain future increments.
