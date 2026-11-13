# Tasks: DEPLOY-01 Hosted application and product website

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Resolve account/provider technical gates, obtain human approval of spec/plan, commit approved contract, run speccheck and record start SHA | orchestrator, spec-writer | Draft review | approved; accounts and private database credentials verified |
| 2 | Design deployment/static/health/startup/site/workflow tests from approved contract in isolated worktree; commit by path | test-designer | 1 | done; 108 cases including verifier regressions |
| 3 | Implement Docker/runtime/static/health/migration contracts and automation; preserve auth/AI contracts; update guides and run existing checks | developer | 1 | done; 108 tests and real concurrent PG18 smoke passed |
| 4 | Build responsive static product website and Pages workflow with exact approved copy and verified-origin configuration | developer | 1 | local site complete; live origin pending |
| 5 | Merge run branch into test worktree, run independent suite and distinguish contract/logic defects; orchestrator merges tests | test-designer, orchestrator | 2, 3, 4 | done; 108 independent tests passed |
| 6 | Verify acceptance coverage, security, Docker/runtime and docs; rerun suite; report ranked findings read-only | verifier | 5 | done; code PASS at 164f763, live acceptance pending |
| 7 | Fix findings within two revision rounds and reverify | developer, verifier | 6 | done; three findings fixed in round 1 |
| 8 | Use the dedicated remote deployment branch without master merge; create free dev/prod resources and securely configure secrets; deploy exact CI-passed revision via Actions | orchestrator | 6 or 7; required account access | superseded master PR closed; dedicated-branch amendment in progress, credentials preserved |
| 9 | Verify live app, database, all-role auth, required journeys, restart persistence and background failure recovery; publish Pages after live URL verified | orchestrator, verifier | 8 | pending hosting and deployment |
| 10 | Record URLs, verified/pending checks, limitations, security evidence, session summary and mandatory usage report | orchestrator | every handoff and final closeout | in progress; closeout report required |

Tasks 2 and 3/4 run independently in parallel after contract approval. Deployment adds no new stored record operations; record-mutation concurrency/cross-user tasks from the template are not newly introduced. Existing security/regression suites still apply; migration concurrency and production cross-user smoke checks are mandatory under the plan.

## Dedicated-branch amendment tasks (2026-11-13)

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| A1 | Record user-approved deploy/production-pages direction and fixed CI-wait/tag contracts; run speccheck and record new start SHA | spec-writer, orchestrator | explicit user instruction | contract written |
| A2 | Independently revise workflow branch expectations and add bounded CI-wait/main gate tests; RED before implementation; commit by path | test-designer | A1 | todo |
| A3 | Update CI/deploy/Pages/Render source branch and bounded helper; update operations guides; preserve all existing runtime/UI/security contracts | developer | A1 | todo |
| A4 | Integrate independent tests, run relevant suite/typecheck/lint, inspect workflow permissions/ref guards and exact deployment; read-only verification | test-designer, verifier | A2, A3 | todo |
| A5 | Apply dedicated branch/release tag environment policies, provision only free services, wait exact branch CI, create explicit production/publication tags and verify live results | orchestrator | A4, account access | todo |

A2 and A3 run independently in parallel. This amendment changes deployment sources and triggers, not application features or master. No new human master-merge gate is introduced; release/publication tags remain explicit operator actions, never automatic workflow output.
