# Setup and submission checklist

Deadline: 13 Nov 2026, 2pm SGT, `master` as pulled. Owners to be assigned.

## Setup
- [ ] Decide team members and one role each (student/teacher/admin); N roles for N students
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
