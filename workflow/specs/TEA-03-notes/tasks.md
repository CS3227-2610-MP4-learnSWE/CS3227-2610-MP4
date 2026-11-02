# Tasks: TEA-03-notes — Edit draft notes

Status: Approved implementation request,2026-11-02.

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
|1|Commit approved spec/plan/API+UI contract and record start commit|spec-writer,orchestrator|user approval|done|
|2|Write independent backend/browser/security tests in isolated worktree|test-designer|1|done|
|3|Add migration/backfill/response fields and transactional versioned PATCH|developer|1|done|
|4|Add editor/validation/recovery and data-router unsaved navigation protection|developer|3|done|
|5|Update shared contract/guides/help and TEA02 merge/live-test handoff; run existing checks, commit source|developer|3,4|done|
|6|Integrate developer source in test worktree, run tests, merge independent tests|test-designer,orchestrator|2,5|done|
|7|Read-only independent code/docs/security verifier reruns checks|verifier|6|done|
|8|Fix findings and verifier recheck, max two rounds|developer,verifier|7|done (two rounds)|
|9|Record session/security/resource/handoff evidence and commit local branch; retain human publishing gate|orchestrator|7,8|done|

Tasks2/3 run in parallel from one recorded contract commit. No live model calls, developer-data tests, push, PR publication or master merge.
