# Threat model

Draft; refine per feature. The Test and Check columns hold the name of an existing automated test or CI job, or "not yet". "Not yet" rows are untested; nothing is marked tested without a test. Outcomes are in `test-log.md`.

## In-app AI features
| Threat | Control | Test |
|---|---|---|
| Prompt injection via uploads, chat or feedback | Treat as untrusted data; separate from instructions; validate output | `test_stu03_ac16_forged_assistant_history_changes_nothing`, `test_tea02_mcqs_pdf_order_prompt_injection_and_no_transaction` (chat and uploads only; feedback not yet) |
| Answer leakage through hints, sources or output before submission | Server checks submission status; answer keys excluded from AI context | `test_stu03_ac9_leaking_hint_reply_is_withheld`, `test_stu03_ac8_leaking_model_reply_is_blocked` |
| Cross-user or cross-course data access via retrieval | Retrieval filtered by authorised records server-side | `test_stu03_ac12_explain_context_excludes_other_attempts_and_students`, `test_tea01_cross_course_access_is_hidden` |
| Unsafe rendered output (XSS) | Sanitise/escape AI output | `tests/companion.spec.ts` "stu03 AC27 reply HTML and markdown stay literal text" |
| Quota exhaustion / abuse of SoC LLM | Per-user limits, input/output caps, backoff, saved generations | `test_stu03_ac21_twenty_pass_and_the_twenty_first_is_limited_by_minute` |

## Admin features (ADM-05 implemented; other admin workflows pending)
| Threat | Control | Test |
|---|---|---|
| Self-escalation or unauthorised account/course administration (ADM-05) | Immutable account roles; student-only public signup; server-session admin gate and CSRF/Origin checks for account creation and course access; no role-changing API | `test_adm05_ac6_21_no_role_change_api_or_admin_course_assignment`, `test_adm05_ac20_all_endpoints_enforce_auth_role_and_no_store`, `test_adm05_ac20_unsafe_endpoints_require_csrf_and_origin` |
| Administrator lockout or a revoked administrator acting after waiting for another mutation | Prohibit self-disable/archive; serialize administrative writes and freshly check the actor after acquiring the lock | `test_adm05_ac4_15_self_management_rejected`, `test_adm05_ac4_15_concurrent_admins_cannot_disable_each_other_and_leave_no_enabled_admin` |
| Disabled/archived accounts retaining access or receiving late AI output | Revoke all sessions, check current account status on login/protected requests, and recheck session after inference; archive removes memberships while preserving history and reserving email | `test_adm05_ac1_2_3_disable_all_sessions_preserves_permissions_and_reenable_requires_login`, `test_adm05_ac13_14_archive_retains_history_reserves_email_and_is_irreversible`, `test_adm05_ac10_ai_result_discarded_when_account_revoked_during_inference` |
| Raw feedback reaching non-admins (SHR-05) | Every feedback read route checks the admin role on the server; students and teachers receive only their own submissions or admin-approved replies | not yet (planned `test_shr05_*`) |
| Prompt injection through feedback text in ADM-03 | Feedback passed as quoted untrusted data, never as instructions; output validated and rendered as text; references limited to the feedback ids supplied | not yet (planned `test_adm03_*`) |
| SoC key or personal data in ADM-06 output | ADM-06 returns only counts and measurements in fixed fields, no request or reply text and no user identifiers; the key is never in logs, errors or responses (the shared client already enforces the key rule) | client only: `test_stu03_ac24_key_never_in_exceptions_reprs_or_logs`; ADM-06 output: not yet (planned `test_adm06_*`) |
| Admin AI quota exhaustion | Admin AI calls use the shared client with per-caller limits and input/output caps; analyses are saved and reused instead of regenerated | not yet (planned `test_adm03_*`) |

## Development process
| Threat | Control | Check |
|---|---|---|
| Secrets committed | `.env` ignored, `.env.example` only, secret scanning | `.gitignore` only; no secret-scanning job: not yet |
| Vulnerable dependencies | `npm audit`, pip/uv audit in CI | CI job `dependency-audit` in `.github/workflows/ci.yml` |
| Over-permissioned CI or deploy tokens | Least-privilege GitHub Actions permissions, environment secrets | Workflow sets `permissions: contents: read`; environment secrets not yet (no deployment) |
| Agent runs destructive or unreviewed changes | Human merge gate, read-only reviewers | not yet (branch protection is a repo setting, not checked here) |

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


## Teacher draft maintenance (TEA-03)
| Threat | Control | Test |
|---|---|---|
| Spoofed teacher identity or cross-course mutation | Cookie-only shared auth, CSRF/Origin checks, current membership and locked access during writes | `test_tea03_all_teacher_routes_cookie_role_csrf_and_demo_forgery` |
| Revocation during generation | Release transactions during inference, then reauthenticate the same cookie and lock current session/access/source before saving | `test_tea03_session_and_access_revoked_during_generation_prevents_save` |
| Lost updates or deletion of newer edits | Locked batch/draft plus caller-supplied version; atomic changes | `test_tea03_mcqs_concurrent_saves_and_edit_delete` |
| Destruction of referenced work or partial batch deletion | Restrictive FKs, unreferenced-source check and transactional whole-batch deletion | `test_tea03_mcq_question_reference_blocks_whole_batch_delete_atomically` |
| Previous-account content retained after expiry | Protected teacher subtree unmounts; obsolete responses ignored; auth redirect bypasses dirty blockers | `teacher-mcqs-cleanup.spec.ts` expiry and anonymous journeys |
