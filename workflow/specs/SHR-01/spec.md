# Spec: SHR-01 Authentication and authorisation

Status: Draft revision 2, awaiting human approval (spec-writer, 2026-11-03). Decisions in the "Approved decisions" section were made by the user and are not open. Revision 2 keeps the existing demo access, leaves teacher specs and routes unchanged, and records the user's answers to former open questions 1, 2, 3, 5, 7 and 8.

## Goal

Every protected operation requires a signed-in user and is checked on the server for role, course and record access (FeatureList SHR-01; UserStories "Shared acceptance criteria": "Unauthenticated requests are rejected, and server-side checks enforce role, course and record access for every protected operation."). This feature builds the shared auth core for all three roles, a real login and signup UI, and moves the student practice (STU-02) and study companion (STU-03) routes off the placeholder `X-Student-Id` header.

## Approved decisions (not reopened)

1. One login system for student, teacher and admin: accounts live in the existing PostgreSQL `user` table (extended additively); the `role` is set only by the server; one login page; the browser is redirected by role after login; a frontend route guard exists for UX only.
2. Mechanism: password hash plus a server-side session in an HttpOnly cookie, stored in PostgreSQL via SQLAlchemy and an additive Alembic migration. Logout, cookie flags, CSRF protection for state-changing requests and session expiry are included.
3. Accounts: seeded accounts (one per role, from env at seed time, no committed secrets) and public signup. Public signup always creates a `student`; the client can never choose or influence the role. Teacher and admin signup/approval flows are out of scope.
4. Password rules, duplicate-email handling without account enumeration, and rate limiting on login and signup.
5. Shared core: a reusable `current_user` dependency that can require a role, and a course-access check, documented for teammates.
6. In scope: auth core, login/signup UI, migration of the STU-02 and STU-03 routes and their tests to the session user. Not in scope: migrating the teacher routes and building admin routes (listed as a HANDOFF for the teammates). `teacher_materials/demo_identity.py` and its dev gate stay unchanged.
7. Server-side checks are the control; prompts and the frontend are not. Cookie, CORS and secret settings are environment-driven so Render/Neon (undecided) or any host differs from dev by configuration only.
8. (Approved, former open questions) Reuse the existing `user` table (additive columns, no parallel `users`). Admin does not pass course checks implicitly. Password hashing is stdlib `hashlib.scrypt`, no new dependency. Sessions last 12 hours absolute (`SESSION_TTL_SECONDS=43200`), no idle timeout.
9. (Approved) `SlidingWindowLimiter` moves from `llm_client.py` to its own shared module; `llm_client.py` re-imports it, no behaviour change.
10. (Approved) The existing demo access stays: the Demo role switcher, the "Explore demo" buttons and the unauthenticated demo path are kept, as are `demo_identity.py` and its dev gate. Removal is a later, separate change (or the demo may stay for demonstration). The teacher Playwright specs and teacher routes pass unchanged in this feature.

## Behaviour

- A visitor opens `/login`. One form signs in any role. After a successful sign-in the app navigates to `/student/overview`, `/teacher/overview` or `/admin/overview` according to the role returned by the server.
- A "Create account" mode on the same page asks for display name, email and password. Signup creates a student account only. The response is the same whether or not the email was already registered; the user is told to sign in afterwards.
- A signed-in user can log out from the app shell; the session is revoked on the server and the cookie cleared.
- Opening a route of another role while signed in redirects to the user's own home. This is UX only; the server rejects the corresponding API calls regardless.
- Student practice and companion API calls use the session cookie; the user id is the server-resolved `user.id`.

### Coexistence of real login and the demo path

The demo path is the existing client-only shortcut: the "Explore {role} demo" buttons on `/login`, the Shell "Demo role" switcher, and direct navigation to `/student/*`, `/teacher/*`, `/admin/*` without signing in (the teacher Playwright specs do exactly this). It is kept unchanged in this feature.

- Two states, decided by the auth status from `GET /api/auth/me`: authenticated (real session) or anonymous. Anonymous plus demo access enabled is "demo mode". There is no third, fake "demo session" and nothing about demo mode is stored on the server or in browser storage.
- Route guard (`RequireRole`, UX only): status loading shows a loading status and renders nothing protected. Authenticated with the matching role renders the route; authenticated with another role redirects to that user's home. Anonymous with demo access enabled renders the route in demo mode, exactly as today. Anonymous with demo access disabled redirects to `/login`. Demo access is enabled unless the frontend build sets `VITE_ENABLE_DEMO_ACCESS=false`; this feature leaves it on by default so existing behaviour and teacher specs are untouched, and a deployed build can switch it off without code change (see Open question 6).
- What a demo user can reach: the static sample-data screens of all three roles (client-only, from `data.ts`/`teacherDemo.ts`), the role switcher, and, only while the backend runs with `APP_ENV=development` and `ALLOW_DEMO_IDENTITY=true`, the existing teacher routes through `X-Demo-User-Id` (unchanged). What a demo user cannot reach: any route that requires `current_user` (the migrated STU-02/STU-03 routes, `/api/auth/me` data, `/api/courses/{id}`). Those return 401 `unauthenticated`. A real-session API route never accepts the demo header or any client-supplied identity.
- Student demo flow consequence: the migrated STU-02/STU-03 routes require a real `student` session, so an anonymous "Explore student demo" user can still browse the sample screens but cannot start a practice attempt or use the live companion. On a 401 while anonymous (demo mode), the client does not redirect; the practice and companion areas show a notice "Sign in to use live practice and the study companion" with a link to `/login`. To try the live flow, sign in with the seeded `demo-student` account (credentials come from the local `SEED_STUDENT_*` environment, never committed, never shown in the UI). Whether to add a one-click demo student sign-in is Open question 7.
- Clear labelling: the existing "Demo · Sample data" pill stays; the Shell shows "Demo (not signed in)" instead of a user name when anonymous; the "Explore demo" buttons are grouped under a heading "Demo shortcut (development): sample data, not signed in, no real account"; the Demo role switcher is shown only in demo mode and is hidden for an authenticated user, whose Shell shows the real display name and role and a Log out button. Demo mode never presents itself as a signed-in state.
- 401 handling: a 401 `unauthenticated` clears client state and returns to `/login` only if the client was authenticated (session expired or revoked). In demo mode it shows the notice above instead. `requestTeacher` (demo header transport) is unchanged and does not trigger the redirect.
- Server enforcement is unchanged by demo mode: every real API route migrated to `current_user` requires a real session, and the demo header gate in `demo_identity.py` is limited to the existing teacher routes and the existing dev flags.

## API summary

Exact contract in `plan.md`. Endpoints: `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `GET /api/courses/{course_id}` (reference use of the course-access check). Existing `/api/practice-sets/*`, `/api/attempts/*` and the companion route now require a `student` session.

## Acceptance criteria

The first group copies the story-level criterion. The rest are the testable decomposition of it and of the approved decisions.

Story-level (copied from UserStories "Shared acceptance criteria"):

- [ ] AC1: Unauthenticated requests are rejected, and server-side checks enforce role, course and record access for every protected operation. (Verified for the routes in this scope by AC12 to AC20.)

Accounts, signup and passwords:

- [ ] AC2: `POST /api/auth/signup` with valid `display_name`, `email`, `password` returns 202 `{"status":"accepted"}`, creates exactly one user with `role="student"`, stores only a password hash (never the password), and sets no cookie.
- [ ] AC3: Signup accepts only `display_name`, `email`, `password`. Any other field, including `role`, `id`, `is_admin` or `course_id`, returns 422 `validation_error` and creates no user. A request that sends `role:"admin"` or `role:"teacher"` therefore never produces a privileged account, and a successful signup is always a student.
- [ ] AC4: Email is trimmed and lower-cased before storage and comparison (1 to 254 characters, one `@`, non-empty local part, domain containing a dot, no whitespace or control characters). `Alice@Example.com ` and `alice@example.com` are the same account. Invalid email returns 422 with `fields` containing `email`.
- [ ] AC5: Password rules: 10 to 128 Unicode code points, not stripped or otherwise altered, no NUL or unpaired surrogate, not equal (case-insensitive) to the email or its local part, and not in the built-in common-password list. A violation returns 422 `validation_error` with `fields` containing `password`. No composition rules (upper/digit/symbol) are required. `display_name` is trimmed, 1 to 100 code points, no control characters.
- [ ] AC6: Duplicate email without enumeration: signing up with an already registered email returns the identical status and body as a new email (202 `{"status":"accepted"}`), changes nothing for the existing account (password and role unchanged), and sends no distinguishing header. Both paths perform one password hash so response time does not reveal the difference. Concurrent signups with the same email create at most one user and both return 202.
- [ ] AC7: Seeded accounts: `uv run python -m auth.seed` (from `src/backend`) gives `demo-student`, `demo-teacher` and `demo-admin` an email and password hash from the environment variables listed in `plan.md`. It is idempotent, never overwrites an existing password hash unless `--reset-passwords` is passed, skips a role whose variables are unset or whose password breaks the rules, refuses to change the role of an existing user, and the repository contains no real password.

Login, session, logout:

- [ ] AC8: `POST /api/auth/login` with correct credentials returns 200 `{"user":{id,email,display_name,role},"csrf_token":"..."}` and sets the session cookie. The `role` is read from the database; the response never contains the password hash, session token hash or any other user's data.
- [ ] AC9: Wrong password, unknown email and malformed-but-well-typed credentials all return the identical 401 `invalid_credentials` response (same body, same status); the unknown-email path still performs a password-hash comparison. A user without a password hash (for example an unseeded demo user) cannot log in and gets the same 401.
- [ ] AC10: The session cookie is `HttpOnly`, has `Path=/`, a `SameSite` value from configuration (default `Lax`), `Secure` when configured (required when `APP_ENV=production`), and a `Max-Age` equal to the session lifetime. The cookie value is a random token of at least 256 bits; the database stores only its SHA-256 hash. Each login issues a fresh token (no reuse, no client-supplied session id is accepted).
- [ ] AC11: Session expiry: a session older than `SESSION_TTL_SECONDS` (default 43200) is rejected with 401 `unauthenticated` and its row is deleted. `POST /api/auth/logout` deletes the server-side session, clears the cookie, and the old cookie value then yields 401 on `GET /api/auth/me` and on protected routes. Logout without a session returns 200 and is harmless. `GET /api/auth/me` with a valid session returns 200 `{"user":{...},"csrf_token":"..."}`; without one, 401 `unauthenticated`.

Shared dependency and route protection:

- [ ] AC12: `current_user(role=...)` returns the authenticated user or raises, in this order: 401 `unauthenticated` (no cookie, unknown token, expired session, or user row gone), 403 `csrf_failed` (state-changing method without a matching `X-CSRF-Token`, or a disallowed `Origin`), 403 `forbidden` (user role not allowed). Role is re-read from the database on every request, so a role change takes effect immediately.
- [ ] AC13: State-changing requests (POST, PUT, PATCH, DELETE) authenticated by session require header `X-CSRF-Token` equal to the session's token; GET/HEAD/OPTIONS do not. A request whose `Origin` header is present but is neither in `ALLOWED_ORIGINS` nor the request's own origin is rejected with 403 `csrf_failed`, including on login, signup and logout.
- [ ] AC14: The course-access check `require_course_member` returns the course for a user with a `course_membership` row and raises 404 `not_found` otherwise; a non-member cannot distinguish a nonexistent course from one they may not see. `GET /api/courses/{course_id}` returns 200 `{id,title,created_at}` for a member of any role, 404 for a non-member or unknown id, 401 when signed out, 422 `validation_error` for a non-UUID (after authentication). Admin has no automatic course access through this check (see Open questions).

Student route migration:

- [ ] AC15: All STU-02 and STU-03 routes (`GET /api/practice-sets/{set_id}`, start/save/submit/results/get attempt routes, `POST` companion route) require a `student` session. Signed out returns 401 `unauthenticated`; teacher or admin returns 403 `forbidden`. The `X-Student-Id` header is ignored: sending it never selects or changes the user, and nothing reads it.
- [ ] AC16: Attempt ownership uses the session user's `id`. Student A cannot read, save, submit or fetch results of student B's attempt; the response is the same 404 `attempt_not_found` as for a nonexistent id (unchanged STU-02 behaviour). Companion context built from an attempt id is restricted to the session student's own attempt, and the companion's `caller_id` for the LLM client is the session user id.
- [ ] AC17: Answer release is unchanged and still server-enforced (SHR-02): correct choices, explanations and results are not returned before a successful whole-set submission, not in direct requests, and not in companion context. Migrating identity must not weaken any existing STU-02/STU-03 test; all of them pass after being updated only to authenticate via the session.

Rate limiting and failure handling:

- [ ] AC18: Login is rate limited per normalised email (default 5 failures per 15 minutes) and per client IP (default 20 failures per 15 minutes). Over the limit returns 429 `rate_limited` with `retry_after_seconds` (integer greater than 0) and a `Retry-After` header, before any password check, for existing and nonexistent emails alike. Signup is limited per IP (default 10 per hour) with the same 429 shape. Limits are configured by environment and fail closed (an invalid value uses the default).
- [ ] AC19: If the database is unavailable or cookie/secret configuration is invalid for the environment (for example `APP_ENV=production` without Secure cookies, or `SameSite=None` without Secure), auth endpoints return 503 `service_unavailable` and never fall back to unauthenticated or demo access. Errors never contain a stack trace, SQL, token, hash or file path.
- [ ] AC20: `Cache-Control: no-store` is set on all `/api/auth/*` responses. Passwords, tokens and cookies are not logged. Health endpoints stay public; `/openapi.json` and `/docs` remain schema only.

Frontend:

- [ ] AC21: `/login` shows one form with labelled Email and Password fields (correct `autocomplete` values), a Sign in button, and a switch to Create account (Display name, Email, Password with the rules shown). Submit buttons are disabled while a request is in flight; errors are announced (`role="alert"`) with a recovery action; a 429 shows the wait time. After sign-in the browser goes to the role's home; after signup the page shows the generic accepted message and switches to sign in. The existing "Explore {role} demo" buttons remain on the page, visually separate under the development-shortcut heading (AC25).
- [ ] AC22: The route guard behaves as in "Coexistence of real login and the demo path": while the session check is pending a loading status is shown and no protected content is rendered; a signed-in user of the wrong role is sent to their own home; an anonymous visitor reaches `/student/*`, `/teacher/*`, `/admin/*` in demo mode exactly as before when demo access is enabled (default), and is sent to `/login` when the build sets `VITE_ENABLE_DEMO_ACCESS=false`. A 401 `unauthenticated` clears client session state and returns to `/login` only when the client was authenticated; in demo mode it shows the "Sign in to use live practice and the study companion" notice and does not redirect. Logout clears client state and returns to `/login`.
- [ ] AC23: The client sends the CSRF token on state-changing requests and sends no `X-Student-Id`; neither the session token nor the password is stored in `localStorage`, `sessionStorage` or any readable cookie. The CSRF token is kept only in memory and re-fetched from `GET /api/auth/me` after a page reload.
- [ ] AC25: Demo coexistence. The "Explore demo" buttons, the Demo role switcher, the "Demo · Sample data" pill and direct anonymous navigation to every role route keep working unchanged. Demo mode is clearly labelled (Shell shows "Demo (not signed in)"; buttons sit under the development-shortcut heading; the switcher is hidden when authenticated). Demo mode creates no session, no cookie and no browser storage entry, and gives access to no `current_user` route: an anonymous call to a migrated student route returns 401 `unauthenticated` and the demo header (`X-Demo-User-Id`, `X-Student-Id`) never authenticates it. `demo_identity.py`, its dev gate, `requestTeacher`, the teacher routes and the existing `teacher-*.spec.ts` files are unchanged and still pass without edits.

Documentation and migration:

- [ ] AC24: The Alembic migration is additive (new revision after `20261102_tea02_mcqs`; historical migrations untouched), works on a fresh and a populated database, and downgrade removes only what it added. Existing demo users keep working for the teacher dev gate (teacher routes and specs unchanged). `docs/SharedDataContract.md`, `docs/DeveloperGuide.md` (usage of `current_user` and `require_course_member`, seed command, env vars) and `docs/UserGuide.md` (sign in, sign up, log out; only what works) are updated; `.env.example` files list the new variables with no real values.

## Out of scope

- Teacher and admin self-signup, approval, invitation or role-change flows (left to the teacher/admin owners).
- Migrating the teacher routes (`/api/teacher/*`, `demo_identity.py`, `X-Demo-User-Id`) and building admin routes: HANDOFF to teammates (see plan.md "Handoff for teammates"). The demo identity and its `APP_ENV=development` plus `ALLOW_DEMO_IDENTITY=true` gate stay as they are and must not be removed. The teacher Playwright specs are not edited in this feature.
- Removing the demo access (buttons, switcher, anonymous demo path, `demo_identity.py`): a later, separate change, or the demo may stay for demonstration.
- A one-click demo student sign-in or any server-side demo session (see Open question 7).
- Email verification, password reset, password change, account deletion, multi-factor authentication, OAuth/SSO, "remember me", session listing, concurrent-session limits, idle timeout, account lockout beyond rate limiting.
- Course enrolment/join flows (how students join courses; decision still open in the user stories); the seed memberships are used.
- Multi-instance shared rate limiting or a distributed session cache (limits are per process).
- Changes to `llm_client.py` limits or behaviour.

## Security and AI safeguards

- Authentication, role and course checks run on the server in a shared dependency; the frontend guard and prompts are not controls. There are no AI calls in this feature; the existing companion keeps its safeguards, and the session user id replaces the header value as `caller_id` and attempt owner (SHR-02: cross-user access and answer leakage tests continue to apply; SHR-05: individual progress stays private to the owning user).
- Role is stored server-side and is never accepted from any request body, header, query or cookie. Signup rejects unknown fields (AC3).
- Passwords: hashed with salted scrypt (stdlib), compared in constant time, never logged or returned. Session tokens: 256-bit random, only the SHA-256 is stored. A database leak therefore exposes neither passwords nor usable session tokens.
- Cookies: HttpOnly, SameSite configurable, Secure enforced in production. CSRF: synchroniser token in the session plus `Origin` check on unsafe methods (needed especially if the frontend and API end up on different sites and SameSite=None is required).
- Enumeration: generic `invalid_credentials`, identical signup responses, dummy hash on unknown emails, rate limits before verification.
- Concurrency: two simultaneous signups with the same email are serialised by a unique index on the normalised email (one row, both get 202). Two simultaneous logins create two independent sessions. Logout and expiry delete the row; a request that races a delete either sees the session (and completes) or gets 401. Rate-limit counters are updated under a lock.
- Normalisation: email trimmed and lower-cased before limiter keys, uniqueness and lookup; display name trimmed; passwords untouched. Rate-limit keys use the normalised email, so case or whitespace variants cannot bypass the limit.
- Known accepted limitation: per-email login limiting lets an attacker temporarily lock a known victim's login attempts (denial of service); the window is short and the IP limit and generic errors still apply.
- Security tests to log in `workflow/security/test-log.md`: SEC-AUTH-01 role escalation via signup body (AC3); SEC-AUTH-02 unauthenticated access to every migrated route (AC15); SEC-AUTH-03 wrong-role access to student routes (AC15); SEC-AUTH-04 forged/unknown/expired/logged-out cookie (AC11); SEC-AUTH-05 cross-student attempt access via session and via leftover `X-Student-Id` (AC15, AC16); SEC-AUTH-06 CSRF missing/wrong token and foreign Origin (AC13); SEC-AUTH-07 login and signup enumeration, response and timing parity (AC6, AC9); SEC-AUTH-08 brute-force rate limits (AC18); SEC-AUTH-09 cookie flags and token storage (AC10, AC23); SEC-AUTH-10 no hash/token in responses, logs or DB plaintext (AC8, AC10, AC20); SEC-AUTH-11 answer release unchanged after migration (AC17); SEC-AUTH-12 production misconfiguration fails closed (AC19); SEC-AUTH-13 course-access non-member indistinguishable from nonexistent (AC14); SEC-AUTH-14 demo mode grants no server access: anonymous request with `X-Demo-User-Id: demo-teacher`, `X-Demo-User-Id: demo-student` or `X-Student-Id` to every migrated student route and to `/api/courses/{id}` returns 401, and an authenticated student session plus `X-Demo-User-Id` still resolves to the session user only (AC15, AC25).

## Test interface (for the test-designer, no src/ access needed)

- Only `from main import app` is imported. Environment is set before import: isolated PostgreSQL schema (same pattern as the shared contract: `TEA01_TEST_DATABASE_URL`, unique schema, `search_path` option), `uv run alembic upgrade head`, `uv run python -m teacher_materials.seed`, then `uv run python -m auth.seed` with `SEED_*` variables set to test-only passwords. `APP_ENV=development`, `SESSION_COOKIE_SECURE=false`, `SESSION_COOKIE_SAMESITE=lax`, `ALLOWED_ORIGINS=http://localhost:5173`, `TRUST_PROXY_HEADERS=true`.
- Seeded fixtures: `demo-student` (member of Course A `11111111-1111-4111-8111-111111111111`), `demo-teacher` (member of Course A), `demo-admin` (no memberships), each with the email from `SEED_<ROLE>_EMAIL`. Course B `22222222-2222-4222-8222-222222222222` has no student member.
- The test client keeps a cookie jar per simulated user. New students for isolation are created through `POST /api/auth/signup` then `POST /api/auth/login`. Direct SQL is permitted only to read the tables named in `plan.md` (hash and expiry checks) and to set `auth_session.expires_at` for expiry tests.
- Rate-limit tests send a distinct `X-Forwarded-For` per test (honoured only when `TRUST_PROXY_HEADERS=true`, last entry used) and read limits from the `AUTH_*` environment variables, which are read on each request, so a test can set a low limit with `monkeypatch.setenv`.
- No live LLM calls: the companion tests keep using the existing fake LLM client.

## Open questions

Closed (decided by the user, recorded in "Approved decisions" 8 to 10): 1 reuse the `user` table; 2 admin does not pass course checks implicitly; 3 stdlib scrypt; 5 12-hour absolute session, no idle timeout; 7 `SlidingWindowLimiter` moves to its own module; 8 teacher specs and routes stay unchanged, demo access kept (old question 6 is superseded by the same decision). Question numbers below are kept for reference.

4. Deployment topology: same-site (API behind the same host or a reverse proxy, `SameSite=Lax`) is assumed. If the static frontend and API are on different registrable domains on Render, `SameSite=None; Secure` and `ALLOWED_ORIGINS` plus a frontend API base URL are needed; the code supports this by configuration, but the frontend API base URL setting is not designed here. Decide when hosting is chosen.
6. Closed (user, 2026-11-03): demo access stays on for now (`VITE_ENABLE_DEMO_ACCESS` unset). Whether the deployed build sets it to `false` is decided at deployment; server enforcement is the same either way.
7. Closed (user, 2026-11-03): accepted the student demo limitation. Migrated STU-02/STU-03 routes need a real session, so anonymous demo students see a "Sign in" notice and can use the seeded `demo-student` login or sign up. A dev-only, server-gated demo sign-in endpoint remains a possible later follow-up, not part of this feature.
