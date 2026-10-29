# App shell execution record

Approved scope: three-role React/TypeScript preview, Material UI with light/dark modes, separate FastAPI health endpoints, no persistence/authentication/AI/business APIs, no deployment. Source is under src/. Commit and push to master after verification are explicitly authorised.

## Tasks
- Scaffold dependencies and write browser/backend behaviour tests.
- Build shared themes, login, navigation, sample data and three role workspaces.
- Add health endpoints, setup instructions and preview limitations.
- Verify tests, lint, types, build and desktop/mobile visuals; review and push.

## Decisions
- Work in the existing clean checkout: user approved implementation and push to master; no extra worktree needed.
- User amended the plan to Material UI and light/dark themes. Themes start with OS preference and remain in memory.
- API health is the only network integration. Other interactions use isolated sample state, reset on refresh.
- Content subject is illustrative software-engineering basics, not a settled curriculum.

## Execution results

- Shared Material UI themes, login and role navigation implemented.
- Student, teacher and admin screens implemented with explicit sample/preview boundaries.
- Health-only backend, lockfiles, environment examples and release-specific guides added.
- Independent reviewer findings reproduced and fixed: filtered-index status drift, keyboard file-picker activation and section anchors.
- Browser regression suite includes desktop/mobile, light/dark and reduced-motion checks. Screenshots visually reviewed for login, student overview, teacher studio and admin overview.
- Production boundaries remain explicit: no auth, LLM integration, database, uploads, persistent state or delivery.

Final verification: 14 Playwright tests passed; 3 backend tests passed. TypeScript, ESLint, Prettier check and Vite production build passed. Both live health endpoints returned the expected JSON through the Vite proxy. Dependencies audited with zero npm vulnerabilities. Browser runner emitted an environment colour-setting warning only; no app runtime errors were observed in the layout matrix. No full accessibility or production-security certification is claimed.

## Follow-up: floating student companion and MCQ-only practice

- Replace the dedicated assistant screen/navigation entry with a shared non-modal bottom-right widget. Legacy URL redirects to overview and opens it.
- Local messages and unsent draft survive route changes/minimise; clear resets both. Student provider unmount at login/role switching ends the demo chat. Browser reload remains a documented preview reset.
- Current-page label is illustrative; real contents and account-scoped persistence until logout/reload restoration are future authenticated-app requirements.
- Change the last free-text sample question to MCQ and show choices/correct-choice selection in teacher previews.

Follow-up verification: 18 browser tests and 3 backend tests passed, with TypeScript, lint, formatting and production build passing. Mobile drawer-to-chat regression was reproduced and fixed. New tests cover draft/history retention, clear, login and role-switch resets, current-page label, Escape focus return and mobile sizing. Dark mobile widget screenshot inspected. No backend functionality added.
