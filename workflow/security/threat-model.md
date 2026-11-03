# Threat model

Draft; refine per feature.

## In-app AI features
| Threat | Control | Test |
|---|---|---|
| Prompt injection via uploads, chat or feedback | Treat as untrusted data; separate from instructions; validate output | |
| Answer leakage through hints, sources or output before submission | Server checks submission status; answer keys excluded from AI context | |
| Cross-user or cross-course data access via retrieval | Retrieval filtered by authorised records server-side | |
| Unsafe rendered output (XSS) | Sanitise/escape AI output | |
| Quota exhaustion / abuse of SoC LLM | Per-user limits, input/output caps, backoff, saved generations | |

## Development process
| Threat | Control | Check |
|---|---|---|
| Secrets committed | `.env` ignored, `.env.example` only, secret scanning | |
| Vulnerable dependencies | `npm audit`, pip/uv audit in CI | |
| Over-permissioned CI or deploy tokens | Least-privilege GitHub Actions permissions, environment secrets | |
| Agent runs destructive or unreviewed changes | Human merge gate, read-only reviewers | |

## Authentication and sessions (SHR-01)
| Threat | Control | Test |
|---|---|---|
| Role escalation through signup or any client-controlled field | Signup body is strict (`extra="forbid"`); role is hard-coded to student; role is re-read from the database on every request; `current_user(role=...)` enforces it on the server | SEC-AUTH-01, 02, 03 |
| Session theft or guessing | 256-bit random token; only its SHA-256 is stored; HttpOnly cookie, SameSite, Secure when configured; session rows deleted on logout and expiry; token never in a response body, log or browser storage | SEC-AUTH-04, 09, 10 |
| Cross-site request forgery | Per-session `X-CSRF-Token` on state-changing requests plus an Origin check (also on login, signup and logout) | SEC-AUTH-06 |
| Account enumeration | Generic 401 for wrong password and unknown email; one password hash on every path; signup returns the same 202 for new and existing emails | SEC-AUTH-07 |
| Brute-force password guessing, including parallel guesses | Per-email and per-IP failure limits; login attempts serialised per key so parallel requests cannot pass the check together | SEC-AUTH-08 (sequential and 10-way parallel tests) |
| Login used as a denial of service (one IP holding the per-IP lock with correct logins) | Not fully controlled: correct logins are never counted, and requests wait for the IP lock without a timeout. Open risk; needs a lock-wait timeout or global limit and `TRUST_PROXY_HEADERS` set behind a proxy before deployment | None yet (verifier finding, reading and probe only) |
| Unbounded limiter memory from many distinct emails or IPs | Partly controlled: expired keys are dropped only when reused. Open risk; needs a periodic sweep or size cap | None |
| Misconfiguration silently weakening security in production | Fail closed: production without Secure cookies, SameSite=None without Secure, or a bad database URL returns 503 | SEC-AUTH-12 |
| Demo identity headers accepted on migrated routes | Server never reads `X-Demo-User-Id` or `X-Student-Id` on routes using `current_user` | SEC-AUTH-14 |
| Cross-student or cross-course access after login | Attempts owned by the session user; course checks return the same 404 for missing and non-member courses | SEC-AUTH-05, 13 |
| Failed logout leaves a live server session behind | Client stays signed in and shows an error when the logout call fails, so the user can retry | Playwright logout tests |
