# Tasks: TEA-02-mcqs

Status: Approved,2026-11-02. User implementation request approves spec/plan; no open product decisions.

- [x] Orchestrator: record approved spec start commit and TEA-03 PR12/master3069053 merge; create independent worktree from that SHA.
- [x] Test-designer: independently write/commit backend migration/API/generation/security/persistence cases and browser cases mapped to AC1–10, fake LLM only; do not read implementation until test commit/integration.
- [x] Developer: add additive batch/question schema/migration with structural constraints; preserve existing schema/data and register models.
- [x] Developer: implement strict bounded MCQ JSON validation/shared-client generation; reuse extraction/error/access/storage helpers and transactional post-model recheck/atomic persistence.
- [x] Developer: implement exact POST/list/get contracts and typed frontend service; no student/publication endpoint or shared-client changes.
- [x] Developer: add content-studio tabs and questions selection/list/read-only preview with45-second timeout, duplicate/stale guards, safe rendering, recoverable states and preserved note navigation protection.
- [x] Developer: update shared data contract, developer/user guides and app help; run existing backend/browser checks as available plus type/lint/format/build; commit explicit owned paths before independent-test visibility.
- [x] Test-designer: merge implementation into test worktree, run isolated backend/browser suites, report contract mismatches separately from defects; never weaken assertions.
- [x] Orchestrator: integrate independent tests; strongest verifier read-only evaluates all acceptance/security/docs and reruns suites. Resolve findings with independent RED regressions, maximum2 rounds.
- [x] Orchestrator: inspect mobile/desktop light/dark evidence; record actual counts, security/session/resource logs, handoff and deferred features; verify clean tree and commit locally. Human gate remains before push/PR/master merge.

Completion: independent verifier PASS at3ebc6462b65c09e71a7fa141763409c402e2f9c4 after one correction round;478 backend,149 full browser, frontend types/lint/format/build. Final verifier reran17 focused MCQ cases. Human publishing gate retained.
