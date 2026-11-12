# Production deployment preparation ? 2026-11-13

User requested production hosting, a live link and a separate GitHub Pages product website, free tiers only and a separate branch. Created `deploy/production-pages`; no master changes committed/pushed. Read workflow/deployment/runtime files; GitHub connection confirms public repository/admin access. Docker engine responds. Local SoC settings presence checked without displaying secrets. Render/Neon not connected; integrations offered; user needs accounts.

Independent spec-writer created DEPLOY-01 spec/plan/tasks, all Draft. Speccheck: 1 checked, 0 failed, 0 waived. Requested human approval required by AGENTS.md before application code. No app changes, new tests, resources, database mutations, live LLM calls or deployment. No hosted URLs exist yet. Existing untracked .claude/worktrees/ preserved.

Plan: same-origin Render app, isolated free dev/prod PostgreSQL, secure sessions, locked migrations, process/database health distinction, exact-commit CI deployment and static product site. Existing daemon AI job interruption and stale recovery documented as limitations. Pending: approval, accounts, secrets via secure settings, provider API/proxy verification, implementation/testing, PR review and live verification.

Usage: [run report](../../workflow/usage/runs/2026-11-13-DEPLOY-01/report.md). Both invocation rows and total verified; tokens/cost unavailable because normal export rejects historical parent-session usage outside run interval. Report generated with empty temporary export source, explicitly documented. Command recovery: initial wrong relative path/required effort, then exporter attribution failure. Resume same run.
