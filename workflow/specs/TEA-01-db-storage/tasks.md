# Tasks: TEA-01-db-storage

Status: Approved user implementation request,2026-11-02. No open product decisions.

- [x] Orchestrator: commit approved contract, record baseline/start SHA and PR13/master6d65273; create independent test worktree.
- [x] Test-designer: independently write/commit BYTEA/migration/quota/concurrency/API/generation/security/UI tests from recorded contract; update filesystem-era tests preserving intent.
- [x] Developer: add MaterialFile/schema migration with populated upgrade/downgrade guards; remove current storage_key model dependency.
- [x] Developer: repurpose upload validation to bounded bytes; atomic metadata/content write with advisory-lock quota; authorised binary downloads; remove permanent file runtime dependency.
- [x] Developer: migrate shared extraction and note/MCQ source reads to bytes while retaining model transaction/access/output safeguards.
- [x] Developer: add quota hint/recoverable UI error; update current shared contract/guides/env/deployment/help/CI setup and mark historical storage contracts.
- [x] Developer: run existing backend/frontend checks as meaningful, report historical fixture mismatches without changing independent tests; commit explicit source/doc paths before test visibility.
- [x] Test-designer: integrate source in test worktree, run isolated complete suites, distinguish contract mismatch from defects; preserve assertions and report.
- [x] Orchestrator/verifier: integrate tests; strongest read-only correctness/security/docs review and independent reruns; resolve blocking findings within2 rounds.
- [x] Orchestrator: record actual evidence/security/session/resources/handoff, verify clean tree and commit locally; no developer data, live calls or publishing.

Fresh database setup is documented for the user; agents do not migrate/reset/seed the existing development database or rewrite .env. No importer/deletion/object storage/authentication feature.

Completion: strongest verifier PASS at1c7483370a02ccc6ae31c08e8416b81c5a7ba254, one correction round;499backend/159browser/types/lint/format/build verified. User fresh DB setup remains manual and documented.
