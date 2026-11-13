# Deployment: Render application, Neon PostgreSQL and GitHub Pages

Implementation: DEPLOY-01. No live URLs are claimed until the checks below pass. The user explicitly selected the dedicated remote branch deploy/production-pages for hosting and instructed that master stay untouched. No merge into master is required; keep independent verification and exact-commit CI gates. GitHub Actions owns deployment; leave Render automatic deployment off.

## Architecture and free-tier limits

A multi-stage Dockerfile builds React/Vite and a Python 3.12 FastAPI server. Render serves both from one HTTPS origin, preserving same-site session cookies and relative /api calls. Separate learnswe-dev and learnswe-prod free web services use separate empty Neon projects/databases and database roles. Both hosted services run APP_ENV=production for production security; environment isolation comes from services, credentials and data, not disabling security in dev.

The product site is static website/ content, independently published to GitHub Pages. It makes no API requests, stores no session data and links to the real application login.

Render free services sleep after 15 minutes idle, can restart at any time, and share 750 instance hours per workspace/month. They offer neither persistent disks nor shell/one-off jobs. Avoid paid resources and payment methods when a strict zero-cost ceiling is required; service suspension is preferable to overage billing. Neon free capacity and retention limits must be checked in its dashboard. Provider free tiers are suitable for this assignment/demo, without an always-on production SLA. Sources: https://render.com/docs/free and https://neon.com/pricing.

Teacher originals are PostgreSQL material_file.content BYTEA, not persistent local files. Existing per-file/total raw-byte limits do not describe full database consumption; monitor tables/indexes/backups too. FILE_STORAGE_DIR remains ignored. Never clear old databases or files to bypass migration guards.

## One-time secure setup

1. Create Render and Neon accounts in the owner's name, free plans only. Connect Render to this public GitHub repository. Prefer matching Singapore regions if supported. Create independent empty dev and production databases/roles; never point either service at local or existing real-user data.
2. After verification and successful dedicated-branch push CI, create the two Git-backed Docker services from deploy/production-pages using render.yaml (plan free, autoDeployTrigger off). Creation may initiate the first build; do not treat it as an approved production release. Use GitHub Actions for subsequent deploys and verify exact commit.
3. In each Render service's secure environment settings, set DATABASE_URL to the corresponding Neon **direct/unpooled** TLS URL with the SQLAlchemy postgresql+psycopg:// prefix. Turn Connection pooling off when obtaining the URL: session advisory migration locks require one stable PostgreSQL connection, so startup rejects recognizable Neon -pooler endpoints. Set ALLOWED_ORIGINS to that service's exact https:// origin. Set SOCLAAS_BASE_URL, SOCLAAS_API_KEY and SOCLAAS_MODEL only server-side. Never paste secrets into chat, website variables, Git, Docker build arguments or logs.
4. The image fixes APP_ENV=production, SESSION_COOKIE_SECURE=true, SESSION_COOKIE_SAMESITE=lax, TRUST_PROXY_HEADERS=false, FRONTEND_DIST_DIR=/app/frontend-dist and disables demo access at frontend build. Keep these values. Render supplies PORT. Session cookies remain HttpOnly through the shared auth module; unsafe requests retain origin/CSRF checks.
5. Create GitHub environments development and production. Store RENDER_API_KEY and RENDER_SERVICE_ID as environment secrets for the corresponding service. Require a teammate review for production environment deployments when repository policy supports it. Use separate production credentials; grant minimum provider scope available. Do not commit secret exports.
6. Verify the SoC endpoint is reachable from Render using a separately approved bounded request. Do not substitute another LLM provider. Missing/unreachable AI configuration remains an explicit limitation; never claim AI verified without a successful hosted request.

## Proxy and rate-limit boundary

The entrypoint uses --no-proxy-headers and rejects TRUST_PROXY_HEADERS=true. It does not trust client-supplied X-Forwarded-For. Explicit ALLOWED_ORIGINS permits the HTTPS frontend even though the upstream connection uses HTTP. Secure cookies are still sent by browsers over the public HTTPS origin. Until Render's trusted proxy boundary is verified, per-IP quotas can group visitors under a proxy IP; per-email and authenticated caller limits remain. Do not set wildcard proxy trust to bypass a login/rate-limit issue. A future trusted-proxy configuration requires a reviewed security contract.

## Builds, migration and startup

From the repository root:

```powershell
docker build -t learnswe:local .
```

The image installs locked dependencies with uv sync --frozen --no-dev and npm ci, builds the frontend and starts as UID 10001. It includes no local env files, worktrees, logs or database files. Runtime binds 0.0.0.0:$PORT, default 8000, with one Uvicorn worker and no development reload. Startup validates secure settings and the built index before migration.

Before accepting traffic, python -m deployment.start runs Alembic upgrade head while holding PostgreSQL advisory lock 3227261001. Concurrent starts serialize; lock acquisition stops after 60 seconds. Configuration or migration errors exit nonzero with a redacted diagnostic; Render must report the failed release rather than serving the new build. Restarts check head but do not reapply completed revisions. Explicit operator migration uses python -m deployment.start --migrate-only, with the same lock and secure DATABASE_URL. Startup never seeds accounts or sample data. Avoid manually running raw Alembic concurrently with release startup.

Only backward-compatible schema changes can safely coexist with old serving processes during a rolling deployment. First deployment uses an empty database. An incompatible schema release requires a separately reviewed maintenance/backup plan.

## Account provisioning

After successful migration, run these commands from a trusted operator machine or an ephemeral container against the intended database, passing secrets through an ignored env file/secure environment, never command-line literals:

```powershell
uv run --env-file .env.production python -m teacher_materials.seed
uv run --env-file .env.production python -m auth.seed
```

Run from src/backend. The ignored operator file must specify APP_ENV=production, the intended DATABASE_URL and six SEED_ email/password fields. Use strong unique private credentials; do not use public README examples. The first command creates the starting courses/users; the second sets sign-in credentials. Provisioning is idempotent by default and does not reset existing passwords; --reset-passwords is an explicit account operation. Remove provisioning secrets from service runtime after use. Use admin Users/Courses screens to manage access after initial provisioning. No production sample_data.py, development analytics/feedback seeds or environment-label workaround.

## GitHub Actions releases

.github/workflows/ci.yml preserves existing master/PR checks and additionally runs on pushes to deploy/production-pages. .github/workflows/deploy.yml starts on that branch or explicit deploy-development-* / deploy-production-* tags, using github.sha. Branch pushes target development; deploy-development-* retries an eligible development commit after initial provisioning or failure; deploy-production-* manually promotes a chosen eligible ancestor to production. No release tag is created automatically. The script validates ancestry on origin/deploy/production-pages, waits at most 900 seconds for the newest eligible ci.yml push run for that exact SHA/branch, then immediately verifies success again before any Render request. Each in-flight request has a 30-second timeout; total CI wait can reach 930 seconds. Failure/cancellation fails closed, and older successes cannot override a newer pending/failed eligible run. No default-branch workflow_run or workflow_dispatch is required. The application job has a 35-minute timeout to cover CI waiting and provider deployment polling.

Render's POST /v1/services/{serviceId}/deploys accepts {commitId: SHA} for Git-backed services, including Docker. The script polls for at most 15 minutes, rejects returned commit mismatches, fails on provider terminal failure and verifies process health, database health and /login HTML. Per-environment Actions concurrency does not cancel a running migration. Source: https://render.com/docs/deploys and https://api-docs.render.com/reference/create-deploy.

The workflow checks out the exact event SHA with full history and validates the fixed deployment branch before any hosting request; only trusted maintainers should push deployment code or create release tags. GitHub development policy permits deploy/production-pages plus deploy-development-* tags; production permits only deploy-production-* tags. Keep custom environment branch policies and existing protections/secrets. Tokens are environment variables and provider response bodies are not logged. A successful release smoke is not a substitute for the user journeys below.

## GitHub Pages product website

Set repository variable PRODUCT_APP_URL to the verified production HTTPS origin (no /login, query, fragment or credentials). Settings > Pages > Build and deployment > Source: GitHub Actions. The public repository supports Pages. No custom domain is needed.

.github/workflows/pages.yml starts on relevant deploy/production-pages changes or an explicit publish-site-* tag (for first publication/retry once the app is live). It checks out github.sha, fails fast on invalid/unset PRODUCT_APP_URL, builds to build/product-site, waits for and immediately verifies exact-SHA dedicated-branch push CI, checks /login availability, then uses official configure/upload/deploy Pages actions. Its build timeout is 20 minutes; the github-pages environment permits only the dedicated branch or publish-site-* tags. Publication tags do not replace branch CI or permit unrelated source commits. Generated CSS links are relative, so the repository subpath works. Never upload website/index.html directly: it is a template containing __APP_LOGIN_URL__.

Local preview example (public placeholder is only for local validation):

```powershell
$env:PRODUCT_APP_URL='https://example.com'
python scripts/build_product_site.py --output build/product-site
python -m http.server 8088 --directory build
```

Open http://127.0.0.1:8088/product-site/ for subpath, keyboard and responsive checks. The real public site link will be recorded only after publication and live verification.

## Background work, restart and recovery

Feedback analysis and analytics quality grading use existing in-process daemon threads. They are not durable workers and may stop during Render restart, deploy or idle shutdown. Existing feedback-analysis stale sweeping marks interrupted old runs failed during subsequent authorized service reads/actions; existing grading sweep marks expired runs run_expired. Review the failure in the admin UI and initiate an explicit new analysis/grading run; never assume a lost thread resumes or automatically replay AI calls. Existing privacy initialization/scanning threads restart with the app and retain fail-closed behavior. A single Uvicorn worker avoids multiplying process-local jobs/rate limits. No paid worker, cron, Redis or queue is introduced.

## Backup, rollback and restore

Before later production releases, make an encrypted/off-repository PostgreSQL backup with pg_dump using provider-required TLS and private credentials. Originals are included in the database, so restore as one unit. Verify a restore into a separate empty recovery database before trusting the backup. Never commit dumps or print connection URLs. Retention and point-in-time recovery depend on the actual provider plan; a free tier is not a backup policy.

For app-only rollback, select an earlier verified ancestor of deploy/production-pages with successful push CI and create a new explicit deploy-production-* tag at that SHA to redeploy through Actions. Render free native rollback history is limited. Check schema compatibility first: rolling back code does not reverse migrations. Do not automatically downgrade or delete material data. For incompatible failure, stop writes, preserve failed deployment/database evidence, restore a tested backup to a new database, deploy compatible code, verify all journeys, then switch secure configuration and redeploy. Keep the old database/files until recovery is confirmed.

## Verification record (pending live access)

- Local validation results: see the DEPLOY-01 handoff/session log; do not infer live hosting from a passing build.
- Live application URL: pending. Product website URL: pending.
- Required live checks: /api/health and /api/health/ready report process state; /api/health/database performs a SELECT 1 probe with a 5-second response bound and redacted 503 failures. Unknown API routes/methods and missing static files must not become HTML.
- Sign in/out as student, teacher and admin with private operator credentials. Verify Secure/HttpOnly/SameSite=Lax cookies, CSRF rejection, unauthenticated/wrong-role/cross-course denial and expired-session behavior.
- Teacher uploads an original, reads it back, reviews/publishes content; student reads a lesson, submits a full practice set and sees answers only afterward, then checks progress; admin reviews feedback. Use controlled test records.
- Approve a bounded SoC request before testing hosted AI generation/analysis. Confirm background completion and explicit recovery of an interrupted job.
- Restart the application and verify accounts, originals, published content and results persist. Verify Pages assets and real application link from its repository subpath on desktop/mobile light/dark and keyboard navigation.
- Mark every check passed, failed or pending with evidence; never publish credentials, private content or an unverified live URL.
