# Spec: DEPLOY-01 Hosted application and product website

Status: Draft; human approval required before implementation.

## Goal
Deploy learnSWE online with separate development and production environments, managed by the team through GitHub Actions, and publish a separate GitHub Pages product website. This implements the delivery requirements in docs/FeatureList.md; it does not introduce new learning features.

## Behaviour
Render serves the built React frontend and FastAPI API under the same HTTPS origin. Separate managed PostgreSQL databases hold development and production data, including uploaded originals. A static product website explains the three roles and links to the verified production application's login page. Deployments use reviewed repository changes and successful CI, never a direct push to master or an independent host auto-deploy.

## Acceptance criteria
- [ ] AC1 A multi-stage Dockerfile builds locked frontend/backend dependencies and starts a non-root production server on 0.0.0.0 using PORT (default 8000); APP_ENV=production and demo access disabled are required for production. Secrets and local artifacts are excluded from the build context and image.
- [ ] AC2 The app serves frontend assets and client-side routes on one origin. Unknown /api routes, unsupported API methods, missing assets and path traversal never receive index.html. Existing protected API status codes, bodies and security controls remain unchanged.
- [ ] AC3 Development and production have separate Render services, database credentials/data and GitHub environments. Only GitHub Actions deploys after successful CI for the exact selected commit. Production promotion is manual, of a commit with successful master CI, and cannot deploy an unreviewed feature branch.
- [ ] AC4 Release preparation runs Alembic upgrade head once under a PostgreSQL advisory lock before accepting traffic. Migration failure prevents starting the new release and is visible without leaking credentials. Provisioning is an explicit operator action, never automatic per restart; public example credentials/sample data are excluded from production.
- [ ] AC5 HTTPS session authentication works on the application origin with Secure, HttpOnly, SameSite=Lax cookies, explicit allowed origins and CSRF validation. No secret enters the frontend, product website, image or Git. Proxy headers are trusted only using a documented Render-compatible boundary.
- [ ] AC6 Health reporting distinguishes process liveness from database readiness. Database readiness returns bounded, redacted failure without an LLM request. Restart/redeploy preserves database records and original files. Background activity and recovery limitations are documented and verified where present.
- [ ] AC7 GitHub Pages publishes only the product website via GitHub Actions on relevant master changes or manual dispatch. The published site contains no credentials/private data, loads under the repository subpath, and links to the verified HTTPS production application; publication fails when the application URL is unset or invalid.
- [ ] AC8 Product copy describes only working features, meets the shared responsive/accessibility baseline and does not claim uptime, AI availability or unverified capabilities. The live link is verified before publication.
- [ ] AC9 Deployment documentation covers required repository/hosting settings, secrets entered through provider or GitHub secure settings, migrations, explicit account provisioning, backup/restore, rollback compatibility, worker/restart behavior, free-tier limitations, and live verification results versus pending checks.
- [ ] AC10 Existing shared acceptance criteria remain enforced: unauthenticated requests are rejected; server-side role/course/record checks protect operations; AI context contains only authorised records; whole-set submission is verified before answers/solutions are released; user/generated text is safely rendered; limits and quotas prevent uncontrolled retries; private progress/feedback remain restricted. Production smoke checks include all three roles and at least one persisted upload/read/practice/feedback journey, without publishing credentials or student data.

## UI states and copy
Apply ../../ui-design.md. The product website has a header, one hero/title, three role panels, a short workflow section and footer. It reuses neutral surfaces, restrained blue, the shared theme token names, 8px spacing, readable typography and visible keyboard focus. There are no editable fields, notifications, counts, API reads or dynamic loading states. Layout stacks on 320-390px mobile and respects light/dark preference and reduced motion. The application UI and its existing state contracts are unchanged.

| Screen or action | Control (button, tab, link, field) and its exact label | Loading | Success | Empty | Each failure that can happen (wrong input, 401, 403, 404, 409, 422, 429, network, timeout) and the exact message | After a failed action (what stays, what is retried) |
|---|---|---|---|---|---|---|
| Product homepage | Link "Open learnSWE"; link "How it works"; link "View source"; link "Skip to content" | Static HTML; no loading message | H1 "Learn software engineering. Build understanding."; introductory text "Study published lessons, practise with feedback, and get guided AI support." | Not applicable: static editorial content | No runtime API failures. A failed website/document navigation uses the browser or GitHub Pages error page; no fabricated application status. Unset/invalid app URL fails the build with "PRODUCT_APP_URL must be an HTTPS origin." | Browser navigation leaves the static site recoverable through Back; no local user data exists |

- Requests per load and per retry: zero application API requests on the product website; normal HTML/CSS asset requests only. No automatic retry, polling or availability probes.
- Wrong role: not applicable: public static product website has no account/role checks. Open learnSWE navigates to the application's /login route, which retains existing authenticated routing.
- Link history: push or replace: all links use standard same-tab anchor navigation, adding normal browser history; How it works is #how-it-works, Skip to content is #main. No replaceState or SPA router on the product site.
- Refresh: product website reloads the same static document. Application client routes return the SPA shell; its auth guards restore existing behavior.
- Back and Forward: browser history restores static page/anchor or application route normally; no website authentication state is stored.
- Expired session or logout: product website is unchanged; application retains its existing login/logout and expiration contract.
- Backend down: product website remains readable. Open learnSWE performs a normal navigation; browser/host error state is authoritative, and Back returns to the website. No fake live indicator or website retry button.
- Longest wait before an error: not applicable to static website application requests: none are sent. Browser navigation timing belongs to the browser. Database readiness has the bounded server timeout in the plan.
- No generic failure message: static website has no runtime API error handler. Build configuration failures use the exact validation message above; existing application failure messages are preserved.

## Out of scope
New role features, new account policies, real-user data migration, custom paid domains, paid resources without approval, replacing SoC LLM, redesigning the app UI, email/push delivery, invented worker infrastructure, and automatic destructive database downgrades. Concurrent-record and cross-user mutation behavior is not newly introduced; existing regression tests and production smoke checks preserve those contracts.

## Security and AI safeguards
Keep auth/access/CSRF checks and answer-release boundaries server-side. Static fallback must not bypass API routing or expose files outside the build directory. Server-only secrets go into secure provider/GitHub configuration, never chat, Git, public logs, frontend variables or Docker layers. Production uses fresh credentials and an empty dedicated database; do not clear existing databases to bypass migration guards. SoC LLM remains the sole AI provider, with the existing shared client and safeguards. Live SoC calls require explicit approval per coordination rules; otherwise record AI verification as pending.

- Concurrent requests (same time): application record invariants remain unchanged; concurrent release starts on one database serialize migrations using the same advisory lock. No automatic provisioning or duplicate worker starts per request. Deployment concurrency is per target environment, with running releases not cancelled mid-migration.
- Normalisation: PRODUCT_APP_URL is trimmed and must be an HTTPS origin without credentials, path, query or fragment; a trailing slash is removed and /login appended. Static request paths are resolved beneath the configured frontend directory and traversal is rejected. Existing identifier normalization is unchanged.

## Open questions
1. Human approval of this Draft spec and plan is required before feature code/tests begin.
2. Free tiers only is confirmed; no Render/Neon accounts exist yet. User account creation/authentication is needed; no billable resources are authorized.
3. Public GitHub repository and admin access are confirmed. Actual production/development HTTPS origins and provider service access remain pending. Pages settings must be configured. Do not request credentials in chat.
4. Confirm SoC endpoint public reachability from Render and approve a bounded live SoC smoke request if required. Existing docs record reachability as unresolved.
5. Hosting discovery must confirm the pinned-commit deployment API and available migration execution mechanism for the chosen Render tier before the build phase. If unavailable, amend the plan rather than deploy a moving branch.
6. Existing implementation inventory must establish actual background jobs, production restrictions and proxy trust requirements. Escalate incompatible contracts before implementation; do not bypass restrictions by labelling production development.
7. Assignment decisions about subject/learner level, upload policies, scoring, feedback retention and SoC quota remain owned by their feature specs; deployment must preserve them and report any unresolved release blocker.
