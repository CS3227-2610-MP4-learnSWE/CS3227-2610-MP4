# Plan: CI-01 Continuous integration on every pull request

Status: Approved by the user in chat (30 Oct 2026). Process infrastructure, not a product feature.

## Goal
Every pull request into `master`, and every push to `master`, runs the project's checks automatically on GitHub Actions, so `master` stays gradeable and reviewers see a pass or fail before merging.

## Jobs (`.github/workflows/ci.yml`)
| Job | Steps | Blocking |
|---|---|---|
| backend | `uv sync --frozen`; `uv run pytest -q` | yes |
| frontend | `npm ci`; typecheck; lint; Prettier check; build; Playwright (Chromium) | yes |
| workflow-tools | unit tests of the token tracker and the experiment scripts (standard library only) | yes |
| dependency-audit | backend runtime deps with `pip-audit`; frontend runtime deps with `npm audit --omit=dev --audit-level=high` | yes |
| dependency-audit (dev deps) | backend dev deps with `pip-audit`; frontend all deps | no, reported only |

## Security of the pipeline
- `permissions: contents: read` for the whole workflow; no secrets are used by CI.
- Third-party actions pinned to major versions from their official publishers (`actions/*`, `astral-sh/setup-uv`).
- Runs on `pull_request`, never `pull_request_target`, so code from a pull request never runs with write access.
- Newer pushes cancel older runs of the same branch (concurrency group).

## Decisions
- Dev-only advisories (pytest 8.4.2, fix in 9.0.3, pinned below 9) are reported, not blocking: they never ship. Upgrading pytest is a separate change.
- Playwright on CI uses 2 workers and 1 retry. Locally, the route test failed once under parallel load and passed alone and on a re-run; a retry is reported as "flaky" in the log, not hidden.
- The layout-matrix test (19 routes x 2 widths x 2 themes) gets a 180 s timeout; it takes over a minute and failed the 30 s default.

## Out of scope (CD)
Deployment needs a hosting decision first; see `workflow/deployment.md`.
