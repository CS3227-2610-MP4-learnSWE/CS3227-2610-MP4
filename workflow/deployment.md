# Deployment (CD): options and open decisions

Not built yet. Continuous integration is in place (`.github/workflows/ci.yml`, plan in `specs/CI-01/plan.md`); deployment waits for the decisions below.

## What the assignment requires
- The app is deployed online, with a separate **dev** and **production** environment.
- The team manages deployment with its own automation (for example GitHub Actions). Build-and-host environments provided by Codex or Claude are not allowed.
- AI features must use the SoC LLM.

## The deciding question: where can the SoC LLM be reached from?
The SoC documentation host (`dochub.comp.nus.edu.sg`) resolves to a private address (172.18.x.x) and could not be reached from outside the NUS network on 30 Oct 2026. If the SoC LLM endpoint is internal too, a backend hosted outside NUS cannot call it, and the backend would have to run inside the NUS network (or reach it through an approved route). To confirm from the NUS network or VPN: the SoC LLM guide linked in the assignment (endpoint, authentication, rate limits, and whether it is reachable from the internet).

## Options
| Option | Fits if | Notes |
|---|---|---|
| SoC-provided server or VM for dev and prod | SoC offers project hosting, or the LLM is internal-only | GitHub Actions deploys over SSH or a self-hosted runner inside NUS; secrets in GitHub environments |
| External host for both (static frontend host plus a Python app host) | The SoC LLM is reachable from the internet | Free tiers exist; separate dev and prod services; deploy from Actions |
| Split: frontend on a static host, backend inside NUS | Frontend can be public, backend must be internal | Needs CORS and a public route to the backend |

## Pipeline shape once hosting is chosen
- Merge to `master` deploys to **dev** automatically after CI passes.
- A version tag (for example `v1.0.0`) or a manual approval deploys the same build to **prod**, using a protected GitHub environment.
- Secrets (LLM key, database URL) live in GitHub environment secrets, never in the repository; the job has least-privilege permissions.

## Open decisions
1. Is the SoC LLM reachable from outside the NUS network?
2. Does SoC provide servers or VMs for course projects?
3. Database hosting for PostgreSQL (dev and prod).
