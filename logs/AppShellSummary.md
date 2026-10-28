# App shell development summary — 28 October 2026

## User direction

The user approved a three-role React/TypeScript/Vite shell and a Python/FastAPI backend limited to liveness/readiness. The visual login has three role tabs, display-only authentication/account creation and separate demo links. All content is sample data, with local interactions only. The user subsequently requested Material UI components and light/dark mode. PostgreSQL, real AI, authentication, storage and online deployment remain outside this release. The user authorised verification, commit and push to master.

## Implementation and decisions

- Created source under src/frontend and src/backend; no previous MP code copied.
- Used Material UI for controls/theme infrastructure, Lucide icons, ordinary CSS for layout and decorative code illustrations, and React Router for role routes/history.
- Centralised fixtures and shared transient state. Student whole-set scoring and solution visibility are local demonstrations, explicitly not server-enforced security.
- Added role inboxes and mock survey links, teacher editing/generation/upload previews, and admin sample analytics/forms/analysis/messages/access/usage.
- Backend exposes two process-only health endpoints. Its real HTTP boundary is tested through ASGI; frontend health state is also checked through the running Vite proxy.
- Context7 was used for library documentation. It is not an app dependency. The user asked what it was; the distinction was explained.
- Native browser tooling was unavailable, so rendered visual inspection used screenshots from the requested Playwright test workflow.

## Verification and corrections

Tests were written before the app. The backend initially failed because its module did not exist. Browser test startup initially exposed local server permissions and a missing browser runtime; both were resolved. The first full UI run found a notification-dismissal issue, corrected by ignoring Snackbar clickaway closure. Responsive tests found a hidden table-header label escaping its scroll container; positioning the scroll container established the correct clipping boundary.

An independent read-only review identified unstable teacher material metadata during search, keyboard activation of the file picker, and incorrect lesson-outline anchors. Each was reproduced with a browser test and fixed. A responsive visual pass also improved the mobile companion call-to-action layout. Generated frontend code was formatted with Prettier. Vendor chunking removed the initial bundle-size warning. Backend HTTP tests use ASGI transport to avoid a deprecated upstream TestClient integration.

Frontend tests cover preview authentication, whole-set scoring, incomplete submission, answer visibility, completion reversal/reset, inbox counts/survey links, theme switching, role routes/reload, backend outage, mobile navigation, keyboard focus/history, preview actions, material search, keyboard file selection and lesson anchors. A layout matrix covers 19 routes at desktop/mobile widths in both themes, with screenshots for visual review. This is initial workflow evidence, not the final assignment reflection or full security test suite.

No secrets, real user records or material files were uploaded. No application deployment was performed.
