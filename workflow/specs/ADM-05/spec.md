# Spec: ADM-05 User and access management

Status: Approved by the user, 2026-11-06, through explicit decisions and instruction to update documents and implement them. Routine API/UI details below implement those decisions.

## Goal
Let admins create fixed-role accounts and courses, manage account status and course permissions, and permanently archive accounts without deleting learning history.

## Behaviour
Admin navigation exposes /admin/users and /admin/courses. Accounts have enabled, disabled or archived status, with exactly one immutable role. Public signup remains student-only. Admin creation supports all three roles with password confirmation in the UI, no default passwords and no mandatory password-change flow. Course memberships grant student learning access or teacher management according to the account's fixed role; admin accounts cannot receive course assignments. Existing shared membership storage may be reused because immutable roles distinguish interpretation. Status and permission changes persist across process restarts.

## Acceptance criteria
- [ ] AC1: **Status management:** I can inspect an account’s access status and explicitly change it.
- [ ] AC2: **Disable and re-enable:** Disabling access prevents subsequent protected requests and ends all sessions; re-enabling requires a fresh login.
- [ ] AC3: **Retained records and assignments:** Disabling preserves learning records and course assignments; admins can edit assignments while the account remains disabled.
- [ ] AC4: **Administrator protection:** Admins cannot disable themselves, and concurrent actions cannot remove the last enabled admin.
- [ ] AC5: **Authorised account creation:** Only an authorised admin can create accounts with a selected supported role; public signup remains student-only.
- [ ] AC6: **Fixed roles:** Each account has exactly one immutable role; promotion, demotion and self-escalation are rejected.
- [ ] AC7: **Initial password:** The admin enters and confirms an initial password; existing shared password rules apply, passwords are stored only as hashes and never returned in account details.
- [ ] AC8: **Password-change scope:** Mandatory first-login password changes are deferred; guides include a validated test-only example password, never a default credential.
- [ ] AC9: **Access display and changes:** I can inspect and change course access for the selected user: student enrolments and teacher management assignments are distinct.
- [ ] AC10: **Revocation enforcement:** Revocation affects subsequent content and AI retrieval requests; access is checked again before releasing AI results, while other already-authorised requests may finish.
- [ ] AC11: **Repeated and concurrent changes:** Repeated grants and revocations succeed harmlessly; concurrent opposite actions follow server processing order.
- [ ] AC12: **Retained history:** Revocation preserves learning and authorship records; granting access again restores visibility of retained records within existing feature rules.
- [ ] AC13: **Permanent archive:** Archiving ends all sessions, blocks login permanently and removes all course permissions, while retaining linked learning and authorship records.
- [ ] AC14: **Email reservation:** Archived accounts cannot be restored and their emails remain reserved for both public signup and admin creation.
- [ ] AC15: **Administrator protection:** Admins cannot archive themselves, and concurrent actions cannot remove the last enabled admin.
- [ ] AC16: **Course creation:** I can create a course with a validated title and explicitly assign teachers using course-access management; each new course atomically receives a default General topic so assigned teachers can publish content through the existing workflow.
- [ ] AC17: **Teacher assignments:** Teacher accounts begin without course assignments; teachers manage content and authorised learning results only in their assigned courses.
- [ ] AC18: **Account discovery:** I can search accounts by name or email, filter by role and status, and browse paginated results including archived accounts through a status filter.
- [ ] AC19: **Confirmations:** Disabling, archiving and removing course access require confirmation; creation and grants use explicit form buttons.
- [ ] AC20: Every admin endpoint rejects anonymous and non-admin callers; writes require shared CSRF and Origin checks, and no client identity header grants access.
- [ ] AC21: Server validation rejects unknown fields, invalid identifiers, role changes, archived-account mutations and invalid role/course assignment combinations without changing records.
- [ ] AC22: Existing feature suites, frontend typecheck and lint remain passing; guides describe implemented behaviour and reproducible manual tests.

- [ ] AC23 (user follow-up): Successful creation shows a green success toast, clears name/email/password/confirmation, and retains selected role; initial role is Student. Failed creation preserves input and shows no success toast.
- [ ] AC24 (user follow-up): Manage account immediately opens a modal named Account details, including loading/error states; Close account details, Escape or backdrop closes when no mutation is pending and returns focus to the triggering control. Nested confirmations preserve the account modal.
- [ ] AC25 (user follow-up): Logout remains aligned, on one line and reachable within short desktop/mobile viewports; long account names do not push controls outside the sidebar.

## UI states and copy

| Screen or action | Control (button, tab, link, field) and its exact label | Loading | Success | Empty | Each failure that can happen and exact message | After a failed action |
|---|---|---|---|---|---|---|
| Accounts /admin/users | heading User and access management; textbox Search accounts; comboboxes Role filter and Status filter; buttons Search, Previous, Next; each row button Manage account | role status Loading accounts... | account name, email, role and status | No accounts found. | Error catalogue below | Keep search and filters; Try again repeats failed list request |
| Create account form | fields Display name, Email, Password, Confirm password; combobox Account role; button Create account | Creating account...; submit disabled | Green success toast (role status) Account created.; clear display name, email and both password fields; retain selected Account role (initially Student) | not applicable | Error catalogue; mismatch Passwords do not match. | Keep non-secret form values; keep passwords only while form remains mounted after failed request; never browser storage |
| Selected account overlay | modal dialog named Account details; button Close account details; buttons Enable account, Disable account, Archive account; combobox Course; buttons Grant course access and Remove course access | Loading account... or Saving changes... | Account enabled., Account disabled., Account archived., Course access granted., Course access removed. | No course access. | Error catalogue below | Keep selected account; do not claim saved state until server confirms; retry explicit action |
| Confirmation | role dialog named Confirm disable, Confirm archive or Confirm removal; buttons Cancel and Confirm | Saving changes...; disable Confirm | close dialog and refresh affected view | not applicable | Error catalogue below | Keep dialog and account/course identity, allow retry; never auto-retry writes |
| Courses /admin/courses | heading Courses; textbox Course title; button Create course; list titles | Loading courses... or Creating course... | Course created. | No courses yet. | Error catalogue below | Keep title and list on failed creation; Try again for reads |

Error catalogue: 401 uses existing sign-in redirect/notice; 403 forbidden 'You do not have access to account management.'; 403 csrf_failed 'Your security token is invalid. Sign in again before making changes.'; 404 not_found 'This account or course is no longer available.'; 409 email_exists 'An account with this email already exists.'; 409 self_change 'You cannot disable or archive your own account.'; 409 last_admin 'At least one enabled administrator must remain.'; 409 account_archived 'Archived accounts cannot be changed.'; 422 validation_error 'Check the entered details and try again.'; 409 invalid_assignment 'Course access is available only for student and teacher accounts.'; 429 rate_limited 'Too many requests. Try again later.'; real network/timeout 'Could not reach the server. Try again.'; 5xx 'The account management service is unavailable. Try again later.'; malformed success response 'The server returned an unexpected response. Try again.' Errors use role alert. Backend messages may be more specific for field validation, but frontend catalogue is fixed by code.

- Requests per load and per retry: accounts page sends one account list GET and one courses GET; selecting an account sends one detail GET. Courses page sends one courses GET. Each retry repeats only its failed GET. Share identical in-flight reads within the same session; never share across a login/logout generation or mutation. A successful mutation refreshes list/detail as applicable, each once; no polling or automatic write retries.
- Wrong role: shared route guard redirects to caller's role home before requests; if role/status changes mid-page, server rejection clears protected data on 401; a genuine 403 displays catalogue alert.
- Link history: push or replace: navigation links to Users and Courses push; auth redirects replace; selection/filter/page state is local and does not change the URL.
- Refresh: reload data from server; clear local selections, forms, search and filters; default page 1, role all, status enabled.
- Back and Forward: navigation reloads corresponding page; never resurrect another session's data; local form state may reset.
- Expired session or logout: clear selected account and secret fields; existing authenticated 401 flow returns to login; demo mode shows sign-in notice and exposes no account data.
- Backend down: show network catalogue alert; explicit Try again for reads, retained form and explicit submit for writes.
- Longest wait before an error: shared HTTP client timeout 10 seconds per request; no unbounded waits or automatic retry loops.
- No generic failure message: choose exact catalogue message by error code; transport failures alone use the network message.

## Out of scope
Role changes, account hard deletion/restoration, email invitations, password reset/change flows, course deletion/editing, bulk operations, new AI functionality and new analytics. Do not rewrite student lesson logic or invent course metadata for legacy practice fixtures.

## Security and AI safeguards
Reuse current_user(role="admin"), session, CSRF/Origin, hashing, errors and teacher/student course checks. Never expose password/hash/session tokens in list/detail/create responses or logs. Disabling/archiving invalidates every session and login rejects inactive accounts. Archive removes membership rows only; account and linked records remain. A new signup with archived email preserves existing generic duplicate-signup response without creating a row. Post-revocation protected requests check current database permissions. Recheck active account/session and any course permissions actually used by AI before returning an AI result; discard on lost permission. Existing practice/companion fixtures without course mapping must not be assigned invented memberships; enforce account/session and existing record/submission checks there. No actual LLM calls during testing.

- Concurrent requests (same time): serialize account lifecycle and assignment changes using database transactions/locks, recheck actor authority after lock acquisition; preserve last-admin invariant even when admins target one another. Serialise grant/revoke per user so response order is consistent with lock/transaction processing order. Unique email and membership constraints prevent duplicates. Archive racing grant leaves no permissions on archived account. Course title duplicates are allowed, course IDs distinct.
- Normalisation: reuse shared email normalisation and password rules without trimming passwords; trim display name/title/search; user IDs are opaque case-sensitive strings, course IDs canonical UUIDs. No SQL wildcard injection; search is literal case-insensitive substring.

## Open questions
None blocking. User approved functional scope and 2026-11-06 follow-up UI fixes (green creation toast, reset text/password fields while keeping role, immediately visible account-details modal, visible aligned logout). API/UI details and bounds below are implementation decisions. AI course-specific revocation applies where authorised course context exists, while missing future retrieval is not claimed implemented.
