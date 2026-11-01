# Spec: TEA-02-notes — Generate and save draft notes

Status: Approved by the user's explicit implementation request on 2026-11-01. The contract below records that approved plan and implementation defaults; no additional product scope is introduced.

## Goal

A teacher selects an authorised uploaded source, generates concise study notes through the shared SoC LLM client, and reopens the persisted unpublished draft later.

Original US-TEA-02-01 acceptance criteria are: “I can select an authorised source and receive editable draft notes” and “Generation does not publish content; failure preserves the source and existing drafts.” This slice implements generation, persistence and read-only viewing only. **Editable notes remain deferred to TEA-03**; do not mark the whole story complete. MCQs, approval, publication, OCR and student access remain out of scope.

## Behaviour and acceptance criteria

- [ ] AC1: A development teacher selects one managed course and one existing source material. POST generation returns HTTP 201 with a new saved draft, source title snapshot and server-resolved creator. Repeated successes create distinct drafts without overwriting existing ones.
- [ ] AC2: Strict UTF-8 text and text-based PDF sources work. PDF pages are extracted in order, with a newline between pages. Reject over 100 PDF pages before text extraction. Normalise CRLF and CR to LF and trim surrounding Unicode whitespace; the resulting source must contain 1–8,000 Unicode characters. Stop accumulating PDF text when the limit is exceeded; never truncate and generate. Empty/scanned sources, unreadable content and excessive text/pages return the specified 422 and make no model call.
- [ ] AC3: The model receives a fixed system instruction and a separate user message containing only the selected source text. Invoke the unchanged shared client using max_tokens=600 and caller_id="teacher:{resolved_user_id}". No arbitrary prompts, tools, other records or student answer keys enter context. Reject blank, non-string, finish_reason="length", or >=2,000-character output; save accepted stripped plain text only.
- [ ] AC4: PostgreSQL stores draft IDs, source/course/creator references, title, content and UTC creation time. Isolated fresh and existing-schema migrations and downgrade/re-upgrade succeed; drafts survive new app requests/process restart. Lists omit content, sort created_at descending then ID descending, and retrieve returns content. Drafts never appear in student materials/practice or become published.
- [ ] AC5: All operations enforce the existing demo gate, resolved teacher role and current managed-course membership. Missing/unknown identities return 401, disabled gate/nonteacher 403, and guessed/foreign/missing records 404. Invalid UUIDs return 422 after identity checks. No private path, storage key, SQL detail or key is exposed.
- [ ] AC6: No database transaction remains open during the model call. Recheck source existence, teacher role and course membership before inserting. A teacher losing access while generation runs cannot save. Database/model/extraction failures preserve source bytes and all existing drafts; concurrent successful generation creates separate valid rows.
- [ ] AC7: The real AI content studio replaces the sample notes generator with labelled Course and Source material selectors, generation action and notices. Its saved draft list and read-only viewer show source title, creator ID and timestamp. Generated strings are escaped text with line breaks, including HTML-like output. MCQ generation is explicitly unavailable.
- [ ] AC8: Browser route /teacher/generate?course={id}&draft={id} reopens an authorised saved draft on reload. Course/draft changes ignore stale responses; no repeated clicks can issue overlapping generation. Loading, empty, error, success and explicit retry states work. Frontend generation timeout is 45 seconds; no automatic POST retry. A lost-response warning explains another attempt may create another draft.
- [ ] AC9: Existing health/student/material APIs and shared llm_client.py remain compatible. Teacher screens work on mobile/desktop in both themes. Guides/contract describe actual implemented behaviour, local spoofable identity and deferred editing. Tests use fake model replies, isolated DB schema and temporary private files; no live LLM calls or deployment occur without separate approval.

## Security and concurrency

Access and data selection are server-enforced. Uploaded source text and model output are untrusted; fixed instructions are defence-in-depth, not authorisation. UUID strings parse to UUID values; user ID comes exclusively from the existing resolver. Generation has no side-effect tool access. Only teacher-managed source text goes to the provider; all output is plain text. Each generation uses a unique UUID and append-only row. A single frontend generation stays busy until settled even if course selection changes; stale completion cannot replace a newer course/draft view. Source snapshots are read before the model call and access is checked again before commit. Draft queries use current membership, not who originally created the draft.

## Open questions

None for this slice. Editing/publication, long-document chunking/OCR, idempotent generation, authentication replacement and stronger process-isolated PDF resource limits are future work. Existing process-local LLM rate limits apply; failed/lost responses may still consume a model call and an explicitly retried POST can create another draft.
