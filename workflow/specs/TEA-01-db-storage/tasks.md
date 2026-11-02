# Tasks: TEA-01-db-storage

Status: Approved user implementation request,2026-11-02. No open product decisions.

- [ ] Orchestrator: commit approved contract, record baseline/start SHA and PR13/master6d65273; create independent test worktree.
- [ ] Test-designer: independently write/commit BYTEA/migration/quota/concurrency/API/generation/security/UI tests from recorded contract; update filesystem-era tests preserving intent.
- [ ] Developer: add MaterialFile/schema migration with populated upgrade/downgrade guards; remove current storage_key model dependency.
- [ ] Developer: repurpose upload validation to bounded bytes; atomic metadata/content write with advisory-lock quota; authorised binary downloads; remove permanent file runtime dependency.
- [ ] Developer: migrate shared extraction and note/MCQ source reads to bytes while retaining model transaction/access/output safeguards.
- [ ] Developer: add quota hint/recoverable UI error; update current shared contract/guides/env/deployment/help/CI setup and mark historical storage contracts.
- [ ] Developer: run existing backend/frontend checks as meaningful, report historical fixture mismatches without changing independent tests; commit explicit source/doc paths before test visibility.
- [ ] Test-designer: integrate source in test worktree, run isolated complete suites, distinguish contract mismatch from defects; preserve assertions and report.
- [ ] Orchestrator/verifier: integrate tests; strongest read-only correctness/security/docs review and independent reruns; resolve blocking findings within2 rounds.
- [ ] Orchestrator: record actual evidence/security/session/resources/handoff, verify clean tree and commit locally; no developer data, live calls or publishing.

Fresh database setup is documented for the user; agents do not migrate/reset/seed the existing development database or rewrite .env. No importer/deletion/object storage/authentication feature.
