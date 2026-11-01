# Tasks: TEA-02-notes — Generate and save draft notes

Status: Approved plan requested for implementation on 2026-11-01.

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Commit spec, contract and test interfaces; record shared start commit | spec-writer, orchestrator | approved user plan | done |
| 2 | Write independent backend/browser/security tests in isolated worktree from recorded start; no feature-source reads | test-designer | 1 | todo |
| 3 | Add draft schema/migration and authorised generate/list/get pipeline using unchanged shared LLM client | developer | 1 | done |
| 4 | Replace notes preview with real course/source generation, persisted list/view, query navigation and bounded retry/error UI | developer | 3 | done |
| 5 | Update shared handoff/user/developer guides and app-help truthfulness; run existing checks and commit source | developer | 3, 4 | done |
| 6 | Integrate developer branch in test worktree; run independent cases then merge tests into run branch | test-designer, orchestrator | 2, 5 | todo |
| 7 | Independent read-only code/docs/security verifier re-runs all required checks | verifier | 6 | todo |
| 8 | Fix blocking findings, max two rounds, and verifier rechecks | developer, verifier | 7 | todo |
| 9 | Record security/results/resources/session handoff and commit reviewed feature; retain human publishing gate | orchestrator | 7, 8 | todo |

Tasks 2 and 3 start in parallel from the same recorded spec commit. No live model calls. No push/PR publication/merge without approval.
