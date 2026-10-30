# Setup and submission checklist

Deadline: 13 Nov 2026, 2pm SGT, `master` as pulled. Student owner: yikbi; teammates own Teacher and Admin. Shared login, persistence and SoC LLM client ownership still needs team agreement.

Current state (30 Oct): PRs 1–5 merged. STU-02 works with placeholder identity and server-memory storage; this does not complete real authentication, persistence or any AI feature. Latest recorded local checks: mocked browser suite 65, backend 60, real-backend test 1. Not re-run during this docs update; GitHub CI status not independently checked here. Remaining technical follow-ups include pytest, OpenAPI errors, six malformed-body check-order cases, the loose locked-state assertion and an eye check of dark-mode practice colours. The historical verifier copy is now labelled. Reflection records include the frontend run; other reflection topics and final guide checks remain open.

## Setup
- [x] Role split confirmed by the user: yikbi owns Student; teammates own Teacher and Admin
- [ ] GitHub organisation created; repo named `CS3227-2610-MP4`, public
- [ ] Submit organisation name on Canvas (was due 23 Oct; confirm status)
- [ ] SoC LLM access obtained; quota and rate limits documented
- [ ] Decide subject and learner level
- [ ] Choose hosting and set up dev and production environments
- [x] GitHub Actions CI: tests, lint, format, build, browser tests, dependency audit (`.github/workflows/ci.yml`)
- [ ] Deployment: dev on merge, gated prod (blocked on hosting and SoC LLM reachability; see `workflow/deployment.md`)
- [ ] Upgrade pytest past the dev-only advisory (pinned below 9; fix in 9.0.3)
- [ ] Secrets in GitHub environments, not in repo

## Deliverables
- [ ] `src/` formatted and reviewed
- [ ] `workflow/` organised and each file described in the developer guide
- [ ] `docs/UserGuide.md` accurate to the product (peer-tested)
- [ ] `docs/DeveloperGuide.md` with design, process and acknowledgements
- [ ] `docs/Reflections.md` with experiments and results
- [ ] Product website on GitHub Pages
- [ ] `logs/` summaries verified for every session
- [ ] At least one LLM feature per role
- [ ] Security tests for AI features and the dev process
- [ ] Evidence of context engineering and resource-aware use
- [ ] Final check: `master` up to date, no changes after deadline
