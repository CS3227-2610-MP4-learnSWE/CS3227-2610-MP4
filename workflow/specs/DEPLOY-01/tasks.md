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
| 8 | Open PR; obtain teammate review/merge; create free dev/prod resources and securely configure secrets; deploy exact CI-passed revision via Actions | orchestrator, human reviewer | 6 or 7; required account access | review-ready PR 46, GitHub environments/Pages and encrypted key/database secrets configured; teammate review/merge and Render provisioning pending |
| 9 | Verify live app, database, all-role auth, required journeys, restart persistence and background failure recovery; publish Pages after live URL verified | orchestrator, verifier | 8 | pending hosting and deployment |
| 10 | Record URLs, verified/pending checks, limitations, security evidence, session summary and mandatory usage report | orchestrator | every handoff and final closeout | in progress; closeout report required |

Tasks 2 and 3/4 run independently in parallel after contract approval. Deployment adds no new stored record operations; record-mutation concurrency/cross-user tasks from the template are not newly introduced. Existing security/regression suites still apply; migration concurrency and production cross-user smoke checks are mandatory under the plan.
