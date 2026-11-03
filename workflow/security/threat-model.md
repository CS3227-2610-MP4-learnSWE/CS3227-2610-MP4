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

## Admin features (none built yet)
| Threat | Control | Test |
|---|---|---|
| Self-escalation through a role change (ADM-05) | The acting user comes from the server session, never the request; only an admin may change roles or course access; a user cannot change their own role; the last admin cannot be removed | not yet (planned `test_adm05_*`) |
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
