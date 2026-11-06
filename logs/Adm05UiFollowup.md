# ADM-05 user-reported UI/login follow-up — 2026-11-06

Developer-role scoped maintenance after the original feature closed. User requested green creation toast, clearing all creation text/password fields while retaining role, aligned visible logout, immediate modal account details, and investigation of created-account login failures. User explicitly authorised the updated UI behaviour; spec/plan amended and regression tests committed before implementation in `99c3c23`. Single-session follow-up; no new multi-agent feature run.

## Changes

- Green filled success Alert in a dismissible six-second Snackbar, retaining accessible status text. Name/email/password/confirmation reset on successful creation; selected role stays, default Student. Failure preserves inputs.
- Account details mounts a labelled Dialog immediately, including loading/error states. Close/Escape/backdrop dismiss when no mutation is pending; nested destructive confirmations and existing APIs/security checks remain. Original late-401 regression now closes the modal before sidebar logout, keeping the old GET pending and all session-isolation assertions.
- Sidebar navigation scrolls independently in short windows; footer does not shrink or leave the viewport, long names truncate, and logout stays on one line. Short-window helper tip hides to preserve room. Desktop/mobile tests cover viewport bounds.
- Guides explain the revised UI, form passwords versus seeded passwords, and login credential rejection versus later cookie/session loss.

## Login investigation

Read-only inspection confirmed recent student/teacher records persisted, were enabled and contained password hashes; no passwords/hashes were printed or exported. The local development configuration had Secure cookies enabled on plain HTTP. Changed only ignored `.env` setting `SESSION_COOKIE_SECURE=false` after checking APP_ENV=development; no passwords or seeded/user accounts reset. Existing production Secure-cookie defaults and authentication code remain unchanged.

User reported the login form's incorrect-credentials message even after a restart/retry, then subsequently confirmed **it works now**. Do not claim Secure cookies explain that initial credential rejection: cookie retention happens after login, and a specific cause of the reported401 was not reproduced. Independent actual browser tests prove admin form creation and fresh-context sign-in/reload for both roles using the exact form passwords, including mixed case, spaces and #. No seed-password substitution or auth bypass. User confirmed their own login working; no further secret input requested.

## Evidence

- Initial three UI regressions RED: success was plain text, details lacked a modal, and logout bottom reached770px in a500px viewport.
- Admin UI suite17PASS; auth/admin browser selection82PASS. Added mobile footer coverage afterwards: all four follow-up cases PASS (desktop1100px/mobile390px, both500px high).
- Backend227PASS: ADM-05 access/creation plus shared login/account/authorisation, including two independent cookie-jar regressions.
- Actual no-mock browser integration2PASS against isolated PostgreSQL schema, dedicated FastAPI8011/Vite5181 and independent Chromium contexts. Password cases include case/#/spaces; login and authenticated reload succeed for student and teacher. Test servers stopped and disposable schemas removed after each run.
- Actual screenshots of green toast, visible sidebar logout and account overlay inspected at1100x600. Initial overlay image caught the MUI fade; final capture waits for completed opacity transition. Screenshot artifacts are ignored under test-results/adm05-live-isolated.
- Typecheck/lint/build PASS. Final all-file line-ending-aware formatting, typecheck/lint and whitespace checks PASS; speccheck7checked/0failed/12existingwaivers. No entire post-follow-up application suite or independent verifier pass claimed.

An initial run retained the old late-401 test's background logout action, which the new modal correctly blocks; updated only that interaction (close overlay first), then all17passed. First isolated live runner used a TypeScript config under node_modules, rejected by Node's type-stripping rules; switched the disposable config to CommonJS and reran successfully. Additional live runs captured final visual artifacts. No live LLM, developer database mutations, user password changes, remote push or deployment. The intentional ignored local cookie-setting change is described above; user restarted their backend.

Resource use: inherited Codex session, per-task tokens/cost unavailable; no agents or tracker for this scoped maintenance task. No extension of the original closed feature's two revision rounds. Test/harness recoveries are documented above.
