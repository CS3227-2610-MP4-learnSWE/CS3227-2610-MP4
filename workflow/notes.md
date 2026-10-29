# Handoff notes

Newest entry first. Use `templates/handoff.md`.

## 2026-10-30: continuous integration (CI-01)
- Done: `.github/workflows/ci.yml` on branch `chore/ci` from `master`: backend tests, frontend checks and Playwright, workflow tool tests, dependency audit (runtime blocking, dev reported). Read-only permissions, no secrets. Every step was run locally first. Playwright: 180 s timeout for the layout-matrix test, 2 workers and 1 retry on CI (the route test failed once under parallel load). Plan: `specs/CI-01/plan.md`.
- Found: the SoC docs host resolves to a private NUS address, so the SoC LLM may be reachable only inside NUS; this decides hosting (`deployment.md`).
- Next: user reviews, then push and PR; confirm SoC LLM reachability and hosting, then build deployment; upgrade pytest past the dev advisory.
- Not verified: the workflow has not run on GitHub yet (it runs once the branch is pushed and a PR is opened).

## 2026-10-28: scaffolding (session)
- Done: CLAUDE.md, AGENTS.md, agent definitions, coordination pattern, variants A and B, templates, reflection skeleton, checklist.
- Design decisions: generator-verifier with an independent test-designer running in parallel and isolated from `src/`; the spec step is shared and excluded from the comparison; revision loop capped at 2 rounds; changes go to `master` by PR only; experiments run on separate branches cut from the same `master` commit and are not merged.
- Next: build the token tracker (separate from learnSWE, with a copy under `workflow/tools/`), define the experiment task candidates and rubric, assign team members and roles, write the first spec.
- Open: SoC LLM access and quota; deployment target; subject and learner level; the Codex `AGENTS.md` pickup is untested; where the Codex model name is logged.
