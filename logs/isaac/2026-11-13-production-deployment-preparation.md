# Production deployment preparation ? 2026-11-13

User requested production hosting, a live link and a separate GitHub Pages product website, free tiers only and a separate branch. Created `deploy/production-pages`; no master changes committed/pushed. Read workflow/deployment/runtime files; GitHub connection confirms public repository/admin access. Docker engine responds. Local SoC settings presence checked without displaying secrets. Render/Neon not connected; integrations offered; user needs accounts.

Independent spec-writer created DEPLOY-01 spec/plan/tasks, all Draft. Speccheck: 1 checked, 0 failed, 0 waived. Requested human approval required by AGENTS.md before application code. No app changes, new tests, resources, database mutations, live LLM calls or deployment. No hosted URLs exist yet. Existing untracked .claude/worktrees/ preserved.

Plan: same-origin Render app, isolated free dev/prod PostgreSQL, secure sessions, locked migrations, process/database health distinction, exact-commit CI deployment and static product site. Existing daemon AI job interruption and stale recovery documented as limitations. Pending: approval, accounts, secrets via secure settings, provider API/proxy verification, implementation/testing, PR review and live verification.

Usage: [run report](../../workflow/usage/runs/2026-11-13-DEPLOY-01/report.md). Both invocation rows and total verified; tokens/cost unavailable because normal export rejects historical parent-session usage outside run interval. Report generated with empty temporary export source, explicitly documented. Command recovery: initial wrong relative path/required effort, then exporter attribution failure. Resume same run.

## Implementation and hosting preparation after approval

Isaac approved spec/plan. Developer and isolated independent test-designer implemented/tested contracts; test dependencies clarified before affected work. Strongest verifier code PASS164f763 after one revision.108 deployment cases passed, latest Docker+isolatedPG18 startup/routing smoke passed, four desktop/mobile light/dark screenshots inspected. Prior configuredCI43308029098: backend3313/frontend1369 plus realE2E/spec/tools/audits passed; only product source-copy formatting failed and fixed. LatestCI43358710922 pending. Full local runs interrupted; handles unavailable and localfrontend last-run failures cannot be called green. No-DB run invalid prerequisites.

Pushed separate branch and opened draftPR46; GitHub connector403 resolved using existing Git credentials in memory, no credential output. Created GitHub development/production environments with master-only branch policy, enabled Pages Actions source. Reserved URL https://cs3227-2610-mp4-learnswe.github.io/CS3227-2610-MP4/ is not published. Inspected dashboards; user already had free Neon production, root created free learnswe-development project in Singapore. Render valid private key saved by user, verified via read-only API and encrypted into both environment secrets. No Render services or production app deployment yet. Neon unpooled URLs pending secure file entry; keep file ignored and never print values.

Read-only review overlapped regression runs, with release gates retained. Optional cleanup/test-add command rejected by automatic review; no rejected action executed and generated fixtures left; later tests added with apply_patch. CUA recovered changed window IDs and opened QuickOpen path for user credential entry; no automated credential creation or Codex-extension interaction. No SoC inference calls. Same usage run resumed; report recovery before work continuation; regenerate/link at handoff.

## Credential and concurrency checkpoint

User saved both Neon URLs privately. Verified valid separate direct TLS hosts/passwords and read-only connectivity (zero public tables in each); no Neon migrations/data changes. DATABASE_URL values normalized to psycopg scheme in memory and encrypted in matching GitHub environments. Render key also encrypted earlier; no secret values logged/committed. Real concurrent migration startup on new isolated PG18 test DB passed both containers, one head,38tables,zero invalidindexes; temporary containers8092/8093 left. Strongest verifier codePASS164f763; latestCI43358710922 deploymentcontracts/E2E/spec/audits/tools green, fullbackend/frontend still pending at last check. Render provisioning/live URLs and teammate review/merge remain pending.

PR46 marked ready for teammate review after code PASS and all local checks; latest branch CI remains required before merge. No master merge, Render service or application/Pages publication performed. Awaiting teammate review/merge per AGENTS.md before deployment continuation.

## Production admin email maintenance
User requested admin-production@example.com in place of the personal login email. Updated the existing production account and ignored credentials file, preserving password and account ID. Live generic-email login and identity check passed; former-email login returned 401. No application code or deployment change. No live AI requests. Model: gpt-6.1-sol; token usage unavailable.

## 2026-11-13: production password maintenance
- User requested passwords at most 12 characters. Rotated all three seeded production accounts to distinct randomly generated 12-character passwords satisfying existing rules; updated the ignored production credentials file. Revoked their prior sessions.
- Verified live sign-in and identity for admin, teacher and student; each former password returned 401. No secrets printed, application code or deployment changes, or live AI calls. Model gpt-6.1-sol; token usage unavailable.

## 2026-11-13: smoke-test credential documentation maintenance
- Updated UserGuide local-example wording and hosted-access tables, production URL, current local student/teacher emails and ignored password-file/key locations. DeveloperGuide distinguishes local, hosted development and production credential files. Production administrator values and all real passwords omitted.
- Checked local configured student/teacher emails against the ignored backend environment file; production role logins were verified during password rotation. Documentation-only change; git diff --check passed. No new application tests or live AI calls. Role: developer (documentation maintenance); model gpt-6.1-sol; token usage unavailable.
