# Continuous integration setup summary — 30 October 2026

## User direction
After choosing workflow B, the user decided to design CI/CD next, then finish STU-02 with B once PR 3 merges, before other features. The user restated that work never happens on `master`: a new branch is cut from the latest `master` and changes reach it only through an approved PR. The user was unsure about CI/CD; the AI explained CI (automatic checks on every PR, no decisions needed) and CD (automatic deployment to dev and prod, which needs hosting decisions), and the user approved building CI and checking the SoC LLM guide.

## What was done
- Branch `chore/ci` from the latest `master`. Plan `workflow/specs/CI-01/plan.md`; workflow `.github/workflows/ci.yml` with four jobs (backend tests; frontend typecheck, lint, format, build and Playwright; workflow tool tests; dependency audit).
- Each step was run locally before writing it into the workflow. Runtime dependencies have no known vulnerabilities; pytest 8.4.2 (dev only) has an advisory fixed in 9.0.3, so dev-only findings are reported but not blocking.
- Two test-reliability changes: the layout-matrix Playwright test now has a 180 s timeout (it takes over a minute), and CI runs Playwright with 2 workers and one retry, after a route test failed once under parallel load and passed alone and on re-run.
- The SoC LLM guide could not be fetched: its host resolves to a private NUS address. Recorded in `workflow/deployment.md` with the hosting options and open decisions.

## Not done
The workflow has not run on GitHub yet; it runs once the branch is pushed and a PR is opened, which waits for the user's review. Deployment is not built. This summary was written by the AI and should be checked by a team member.
