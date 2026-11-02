# Approved teacher review corrections — 2026-11-02

User requested fixes for the Ponytail full review in logs/PonytailTeacherReview.md. This is an approved corrective extension to TEA-01/TEA-02-notes/TEA-03/TEA-02-mcqs, not a new feature. Existing HTTP shapes, permissions, limits and visible controls remain binding.

## Contract

1. Notes and MCQ generation must permanently ignore success/error after any committed navigation or course/source/draft selection departure, including A→B→A. No stale result may navigate or display a message. Keep duplicate-click prevention, pending guards and no automatic POST retry. Existing draft-editor unsaved/pending-save guards remain intact.
2. Generated note text containing NUL or unpaired surrogate code points is unusable model output: return502 detail.code llm_bad_response using existing fixed safe message, before opening persistence transaction. No draft/file change. Normal Unicode including astral characters remains supported; existing raw<2000, nonblank, finish-length checks unchanged. Shared llm_client.py unchanged.
3. Material title containing NUL/unpaired surrogate is invalid user input:422 validation_error, safe title-validation message, before file creation or metadata work. Gate/identity/course checks still precede validation. Valid trimmed1–200-codepoint titles unchanged; no new filename/content constraints or endpoints.
4. Remove duplicated course/source/list loading and generation freshness ownership with focused shared frontend hooks/helpers used by both studio views. Keep feature-specific detail fetching, note editor, MCQ validation/viewer and labels separate. Preserve loading/retry/empty behaviour, direct URLs, stale GET suppression and existing route blockers. No generic configurable editor/framework/dependencies. Reuse narrow backend text-representability validation across upload, note generation/editing and MCQ validation if it reduces duplicate checks without changing error ownership.

## Verification and workflow

Independent test-designer first writes/commits regression tests from this contract in separate worktree at recorded start; reproduce RED before application fixes. Fake LLM only, isolated PostgreSQL schema/tempfiles. Browser tests for stale note success/failure after course A→B→A and draft back/forward; existing MCQ regressions stay unchanged. HTTP tests fake generated NUL/high/low surrogate→502, invalid material title→422 with no files/rows, accepted astral Unicode. Preserve source/previous drafts. Shared refactor must retain course loading/retry/material/list/detail staleness and dirty editor guards; existing suite is regression evidence.

Developer then implements, commits source/product docs before test integration. Designer integrates/runs backend+browser+types/lint/format/build; parent integrates tests; strongest independent verifier read-only checks every review finding, docs and regressions. At most2 review correction rounds. No migration, provider call, developer data, push/PR/master merge. Parent owns workflow/session/security/resource logs; developer owns source/product docs. Final local commits permitted by existing feature workflow.
