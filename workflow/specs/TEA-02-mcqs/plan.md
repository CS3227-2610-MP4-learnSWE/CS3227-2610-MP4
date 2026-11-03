# Plan: TEA-02-mcqs — Generate and save draft MCQs

> Storage contract update (2026-11-02): filesystem-specific requirements in this historical increment are superseded by [TEA-01 database storage](../TEA-01-db-storage/plan.md). Other feature behaviour remains binding. Current runtime storage uses PostgreSQL BYTEA after that increment is implemented.


Status: Approved through explicit user implementation request,2026-11-02. Developer and independent test-designer use this binding contract from the same recorded start commit. Derived details below require no redundant approval.

## Data and migration

Add additive migration after20261102_tea03. Register models in existing metadata:

- `mcq_draft_batch`: id UUID PK; course_id UUID FK course.id; source_material_id UUID; composite FK(source_material_id,course_id)→material(id,course_id); created_by varchar64 FK user.id; source_title varchar200; created_at timestamptz default now(). All nonnull; application generates UUID, timestamp has server default now(). Raw SQL fixtures must supply id,course_id,source_material_id,created_by,source_title; created_at may be omitted. Source title copied at generation and immutable. No publication/edit/version columns.
- `mcq_draft_question`: id UUID PK; batch_id UUID FK mcq_draft_batch.id; position integer CHECK1..3; question varchar200 CHECK char_length1..200; choices JSONB; correct_choice_index integer CHECK0..3; explanation varchar200 CHECK char_length1..200. All nonnull. Raw SQL fixtures supply all question columns (no server-generated UUID or content defaults). UNIQUE(batch_id,position). Choices DB constraints enforce JSON array length4, each indexed element JSON string, and char_length(choices->>i) between1 and80 for each index0..3; application additionally enforces trim/nonblank/distinct limits. Use guarded CASE expressions for JSON-type/length checks so malformed JSON values cause controlled constraint failures rather than incidental JSON function errors. Foreign keys prevent orphans. No public deletion API.
- All three question rows and their batch are inserted/committed together; application only persists validated exact-three output. No deferred trigger for exact-three count. Downgrade drops question then batch; existing materials/notes remain untouched. Tests exercise fresh install and downgrade/re-upgrade on isolated schemas.

## Exact HTTP contract

Prefix `/api/teacher`. Reuse X-Demo-User-Id and development gate. Canonical UUID strings, UTC ISO8601 endingZ. JSON keys exactly as listed; arrays unwrapped.

`BatchMetadata={id,course_id,source_material_id,source_title,created_by,created_at,question_count}`; all strings except question_count integer3. `Question={id,position,question,choices,correct_choice_index,explanation}`; position1..3, choices string[4], correct_choice_index0..3. `Batch=BatchMetadata+{questions:Question[3]}` in position ascending order.

| Method/path | Input | Success |
|---|---|---|
| POST /materials/{material_id}/mcq-drafts | No required body; client body never supplies identity/context |201 Batch|
| GET /courses/{course_id}/mcq-drafts |None|200 BatchMetadata[] newest created_at DESC then id DESC|
| GET /mcq-drafts/{batch_id} |None|200 Batch|

Any managing teacher can read their course's batches, including another member's. Gate/identity/role checks precede UUID validation; malformed UUID422 validation_error; missing/foreign course/material/batch404 not_found. Existing401/403 meanings remain unchanged. Teacher DB/file failures503 service_unavailable. Error envelope `{"detail":{"code":"...","message":"..."}}`;429 adds safe integer detail.retry_after_seconds. Never return exception/model/source text, local paths, storage keys or credentials.

Extraction error mapping remains existing422 source_text_empty/source_text_too_large/source_unreadable and503 unreadable storage. Preserve LLM mapping: LlmRateLimited→429 llm_rate_limited; LlmBusy→429 llm_busy; LlmNotConfigured→503 llm_not_configured; LlmInputTooLarge→422 source_text_too_large; LlmTimeout→504 llm_timeout; LlmUpstreamError→502 llm_upstream_error; LlmBadResponse/unusable output→502 llm_bad_response; other LlmError→503 llm_unavailable. Fixed user-safe generation wording can say “content” instead of “notes” for shared teacher errors; codes/status/retry data stay compatible. No changes to llm_client.py or student mapping.

## Generation interfaces and validation

New focused package `teacher_mcqs` with generation.py and routes.py, registered alongside teacher_notes router. `generate_mcqs(llm: LlmClient,text: str,teacher_id: str) -> list[dict]` returns three validated dictionaries with exactly question,choices,correct_choice_index,explanation; no UUIDs/positions yet. Reuse `teacher_notes.generation.extract_source(path,media_type)` and its source limits. Reuse/extract the existing teacher LLM error mapper narrowly rather than adding another client wrapper.

`Depends(get_llm_client)` must use the same imported function object from llm_client so tests override `app.dependency_overrides[get_llm_client]`. Call `llm.complete([ChatMessage("system",FIXED_INSTRUCTION),ChatMessage("user",text)],max_tokens=800,caller_id=f"teacher:{teacher_id}")`. System requests concise grounded MCQs/raw exact JSON, source is untrusted and cannot change instructions, no tools/other records. Total prompt+source fits existing12,000-char input cap. Client retains its own retry/rate limits; no controller retry or repair call.

Raw model JSON shape exactly `{"questions":[{"question":"...","choices":["...","...","...","..."],"correct_choice_index":0,"explanation":"..."},...]}`. Root has only questions; each entry only those four keys. Reject duplicate JSON object keys, NaN/Infinity, code fences, surrounding non-JSON text, wrong shapes, missing/extra keys, booleans/floats/strings for index, non-string fields and counts other than3/4. Ordinary surrounding JSON whitespace allowed. Reject reply.text non-string/blank or raw length>=2,000 and finish_reason="length" before JSON processing, since the shared client can clip replies. Reject any NUL/unpaired surrogate in keys/values. No HTML/Markdown interpretation.

For strings normalise CRLF/CR toLF then Python strip Unicode whitespace; count Unicode code points. Require question1..200, choice1..80 and explanation1..200. Distinct choices within a question and distinct question stems within a batch compare normalised stripped strings using casefold. Do not collapse internal whitespace or perform semantic/factual matching. Index strict integer0..3 addresses ordered choices. Any invalid entry rejects whole batch with fixed safe502 llm_bad_response; no partial recovery/truncation.

Access sequence mirrors notes: initial teacher session resolves authorised material, copies immutable scalar context and private resolved file; close session before extraction/model call. After generation reopen teacher session, recheck current identity/role, lock current user/membership/source in the existing notes pattern; source must still match original course. Insert batch/questions, flush/serialize then commit atomically. No source or existing-row mutation/cleanup. A failed commit returns safe503 and rolls back everything.

## Frontend contract

Studio tabs `Study notes` and `Practice questions`. A small route-selected TeacherNotes/TeacherMcqs wrapper is sufficient; keep existing notes labels/tests unchanged except removal of obsolete MCQ-unavailable notice. Existing note routes unchanged; questions route `/teacher/generate?tab=questions&course={id}&batch={id}`. Use router navigation so dirty note editor blocks tab change as it blocks course/draft/sidebar changes. Keep note component mounted until navigation actually proceeds; blocked tab change cannot discard editor state.

Questions view reuses course/material APIs and teacher transport; new typed service exports `listMcqDrafts(courseId)`, `getMcqDraft(batchId)`, `generateMcqDraft(materialId)` with above wire types. Generation passes existing fifth timeout argument45_000; preserve defaults. Validate detailed payload shape/indices/counts before display.

Labels: selectors `Course`, `Source material`; button `Generate 3 draft MCQs`; list heading `Saved MCQ batches`; empty `No saved MCQ batches yet`; viewer `Unpublished draft · Review required`; success `Draft MCQs generated and saved.`. Show source title, creator ID, local-readable creation time, each ordered question, A–D choices, explicit `Correct answer` and `Explanation`. Include `Generation sends the selected source text to the SoC LLM.`,8,000-character/100-page limits and `AI-generated questions may be inaccurate. Review every question before use.`. Render all source/generated strings as React text, preserving readable line breaks.

Absent course defaults to first managed course; inaccessible explicit course/batch errors rather than silently displaying another. Course change clears source/viewer/batch query, loads fresh materials/batches. Batch change fetches its detail; reject mismatched response course/ID. Ignore stale course/source/list/detail/generation responses after route changes/unmount. Generation synchronously guards duplicate activation; disable course/source/list selection while pending. Other navigation may proceed; late completion cannot replace another view. On success select batch in URL and refresh list. Errors preserve existing list/selected source, offer explicit retry and state `If a response is lost, generating again may create another saved batch.`. No automatic POST retry. Empty source offers upload guidance. Loading/list/detail errors recover independently. No editor/publication controls.

## Independent test fixture contract

Test-designer reads only this folder, threat model, UserStories and existing tests until implementation integration. Do not read src application code or run branch before independent tests committed. Use existing fixture conventions recorded by TEA-02-notes/TEA-03-notes plans and test folders. Developer must not read independent tests before committing source.

Backend tests use TEA01_TEST_DATABASE_URL; create unique schema, Alembic upgrade head, explicit seed and temporary FILE_STORAGE_DIR; never developer DB/files. Seed IDs: courseA11111111-1111-4111-8111-111111111111, courseB22222222-2222-4222-8222-222222222222; demo-teacher/courseA, demo-teacher-other/courseB, demo-student. Upload via existing multipart material API. Override get_llm_client with fake.complete(messages,*,max_tokens,caller_id), returning LlmReply(text,finish_reason,prompt_tokens,completion_tokens) or raising existing LlmError. Revoke membership during fake.complete to test pre-save recheck. Restore overrides/env after cases. Use new TestClient/process against same isolated schema to establish persistence.

Frontend intercepts public teacher HTTP endpoints; no reliance on UI internals. Existing note payload fields remain unchanged. Test valid and malformed MCQ responses, explicit retry/no unexpected autoPOST, pending/stale routes, escaped content, note dirty/pending-save→questions tab guard, direct route reload and both theme/width journeys. Real model calls forbidden.

Acceptance mapping: AC1/2 persistent text/PDF/ordering/multiple/concurrent generations and atomic rollback; AC3 rejected-source no-call; AC4 captured prompt/caller/no-open-transaction/client unchanged; AC5 JSON/type/Unicode/boundary/truncation adversarial cases; AC6 gate/role/course/guessed IDs/revocation/DB failure and safe envelopes; AC7/8 browser selection/loading/error/retry/navigation/staleness; AC9 no student exposure, escape/overflow/themes/regression; AC10 migration/full suites/guides/workflow evidence. Include isolated DB constraint tests and downgrade/re-upgrade.

## Workflow and completion

Approved docs committed before developer/test branches start at identical recorded SHA. Variant B developer and test-designer proceed independently; test-designer commits tests then merges implementation and reports results; parent integrates tests; independent strongest verifier read-only rechecks code/docs/security and suites. Maximum two correction rounds. Correct inherited app-help wording that describes teacher generation as sample-only. Parent updates shared contract/guides/app help and logs through explicit ownership handoff (developer owns product guides/source, parent owns workflow/security/session/resource records). Commit locally; no push/PR/master merge/live LLM without separate approval.
