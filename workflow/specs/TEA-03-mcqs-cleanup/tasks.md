# Tasks: TEA-03-mcqs-cleanup

Status: Approved through explicit user implementation request, 2026-11-04.

| Task | Owner | Deliverable | Status |
|---|---|---|---|
|1|spec-writer|Approved spec/plan/tasks and requirement stories; record PR15/16|Complete|
|2|orchestrator|Record same start SHA and create isolated independent test worktree|Complete|
|3|test-designer|Independent auth/edit/delete/migration/security/UI tests from contract; explicit test commit before source visibility|Complete|
|4|developer|Migrate teacher endpoints/transport to shared cookie+CSRF auth, retaining READ COMMITTED and postmodel rechecks|Complete|
|5|developer|Add batch audit migration/strict atomic versioned MCQ editing|Complete|
|6|developer|Atomic authenticated note/batch/source deletion, locks/quota/references/errors and topic-race handling|Complete|
|7|developer|MCQ editor/dirty guards, confirmation/recovery/204 integration, guides/help and existing checks; commit source|Complete|
|8|test-designer|Merge implementation into test worktree and report tests without weakening assertions|Complete: 727 backend / 245 browser PASS|
|9|orchestrator|Integrate tests; shared contract/session/security/resource/handoff records|Complete|
|10|verifier|Strongest read-only full acceptance/code/security/docs review and fresh suites|Complete: PASS at5df6934|
|11|developer/test-designer|Resolve findings with regressions, maximum two correction rounds|Complete: 2 rounds; all findings resolved|
|12|orchestrator|Final local commits/evidence/handoff; retain human push/PR/merge gate|Complete: PostgreSQL16 728 PASS; local commit only|
