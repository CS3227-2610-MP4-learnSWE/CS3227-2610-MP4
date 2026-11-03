# Spec: TEA-02-mcqs — Generate and save draft MCQs

> Storage contract update (2026-11-02): filesystem-specific requirements in this historical increment are superseded by [TEA-01 database storage](../TEA-01-db-storage/plan.md). Other feature behaviour remains binding. Current runtime storage uses PostgreSQL BYTEA after that increment is implemented.


Status: Approved through the user's explicit implementation request, 2026-11-02. This specification fixes implementation defaults within that approved plan; no additional approval is pending before application code.

## Goal and story

Implement US-TEA-02-02: “As a teacher, I want to generate practice questions from selected source material so that I can prepare practice activities more quickly.” Original acceptance criteria:

- Generated drafts contain MCQs only, with answer choices, exactly one correct choice and an explanation per question; no free-text answer questions.
- Unusable output is identified clearly and failed requests preserve existing work.
- Generated questions remain unpublished until reviewed and explicitly published.

This increment also supplies the MCQ preview portion of US-TEA-03-01. Correction, approval, publication, practice-set assembly and student access are deferred. TEA-03 note editing was merged through PR 12 at master3069053; existing notes generation/editing remains operational.

## Acceptance criteria

- [x] AC1: A managing teacher selects one authorised UTF-8/text-based-PDF source and generates exactly three single-answer MCQs, each with four choices, one correct index and an explanation. Each success creates a separate persistent batch; reopening after restart shows the same ordered content.
- [x] AC2: POST returns201, list/get200 with the exact contract in plan.md. Course/source consistency, creator/source snapshot and newest-first ordering are preserved. Creation is atomic: no partial batch or orphan question survives failure.
- [x] AC3: Reuse existing extraction: normalised source maximum8,000 Unicode characters and100 PDF pages; reject empty/scanned, unreadable, oversized and excessive-page sources without calling the model. Never truncate source text.
- [x] AC4: Exactly one application-level shared-client call uses two fixed-role messages, max_tokens800 and server-derived teacher caller ID. Source instructions remain untrusted data, not instructions. No tools, retrieval, other records or shared-client behaviour changes.
- [x] AC5: Strictly validate raw JSON against plan.md. Malformed/extra/duplicate fields, invalid Unicode/types/answers/counts/limits, repeated questions, empty or truncated replies return502 llm_bad_response and create nothing. Structural validation does not promise factual correctness.
- [x] AC6: Gate/identity/teacher/course checks precede file/model work. Missing/unknown identity401, disabled gate/nonteacher403, foreign/missing resources404. Recheck access/source before atomic save; revoked access or database failure leaves source bytes and existing drafts unchanged. No transaction remains open during the model call.
- [x] AC7: Studio Study notes/Practice questions tabs retain note routes/editing and unsaved-change protections. Questions expose source/course selectors, real-request notice, supported limits, Generate 3 draft MCQs, persistent list and read-only preview of choices, answer and explanation with attribution and Unpublished draft · Review required.
- [x] AC8: Explicit loading/empty/success/recoverable errors, no duplicate click or automatic POST retry,45-second generation timeout and uncertain-response duplicate warning. Stale responses cannot replace current course/batch. Direct-route refresh reopens selected batch.
- [x] AC9: Generated strings render escaped as text. Drafts have no student endpoint/publication path. Notes/student/material/health behaviour and note-edit navigation safeguards remain compatible. Both themes/mobile/desktop remain readable without overflow.
- [x] AC10: Migration upgrade/downgrade and isolated fake-LLM tests pass. Shared contract/guides/app help and session/security/resource/handoff records state actual behaviour. Variant B review and two-round correction limit apply; commit locally only.

## Security and scope

The server is the access boundary; development identity remains spoofable/local-only. Never expose private keys/paths/provider exceptions. Batch creation includes current membership/source checks after generation. Teacher-only responses may include answers; students cannot retrieve them. Generated content is unreviewed and never publishes automatically. No live model call, push, PR publication or merge without separate approval.

## Open questions

None. Three questions, four choices, read-only batches and fixed shared-client limits are approved defaults. No editing, MCQs in student practice, autosave, question history or production authentication in this increment.

Verification: PASS at3ebc6462b65c09e71a7fa141763409c402e2f9c4; evidence in logs/TEA02McqsSession.md and workflow/security/test-log.md. No live provider calls.
