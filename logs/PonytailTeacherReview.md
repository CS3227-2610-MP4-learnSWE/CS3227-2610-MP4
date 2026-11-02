# Ponytail full teacher review — 2026-11-02

Reviewed TEA-01 materials, TEA-02 notes/MCQs, TEA-03 editing and connected guides/shared contract at2c36951. Read-only review of application code; no fixes or test changes. Parent inspected materials/access/storage/docs; independent strongest verifier inspected note/MCQ pipelines and UI lifecycles.

## Confirmed findings

1. Note generation can revive obsolete success/failure after navigating away and back to the same selection. TeacherNotes.tsx:170–184 compares a selection string only, while MCQs use a monotonic navigation epoch. Independent browser probes reproduced obsolete success opening the generated draft and obsolete failure showing an alert. Apply permanent request invalidation to notes and add regression cases.
2. Generated notes do not reject NUL/unpaired surrogates before PostgreSQL. Independent isolated fake-LLM probes: NUL reply returns503 service_unavailable, surrogate reply raises unhandled UnicodeEncodeError. Reject unusable output as502 llm_bad_response before persistence; preserve earlier drafts. This breaks the documented safe model-output/error contract.
3. Upload title validation checks length only. Parent isolated probe with title Unit\x00testing returned503 service_unavailable, zero material rows; bad title should be422 validation_error under SharedDataContract.md:56. Reject PostgreSQL-unrepresentable text before file storage/DB work.

## Conciseness and documentation

The main duplication is teacher studio course/source fetching, request lifecycle and post-model access rechecks. The different stale-response behaviour in notes versus MCQs demonstrates maintenance drift. Prefer a small shared pending-generation guard and narrowly shared lifecycle/access helpers; keep distinct note editor and MCQ parser/viewer logic. Avoid a generic configurable editor framework. Most guides correctly distinguish persistent teacher records, previews, unpublished drafts, spoofable local identity and deferred production features; correct the behaviour above instead of weakening those promises.

## Evidence and limits

Five targeted probes used mocked responses, isolated PostgreSQL schemas and temporary files; no live provider or developer data. Two browser history cases and two generated Unicode cases were independently reproduced; parent ran one invalid-title HTTP probe. Prior implementation verification at unchanged code:478 backend/149 browser/types/lint/format/build; those full suites were not repeated for this review and missed these cases. No deployment, live-model factual-quality or production-authentication testing. Exact resource/cost totals unavailable. No application changes, push or PR.
