# Developer Guide — App Shell Preview

## Architecture and boundaries

The React/TypeScript frontend uses Vite, React Router, Material UI/Emotion and Lucide icons. `src/frontend/src/data.ts` holds fixtures and role navigation; `state.tsx` owns temporary completion, practice and inbox state. Shared layout and visual components live under `components/`; each role has a page module, with shared inbox and feedback pages. The Material UI theme is configured at the root and CSS variables coordinate custom layout/illustrations in both modes.

BrowserRouter enables direct URLs and history. For future production hosting, configure SPA fallback and route `/api` to FastAPI. Vite proxies `/api` locally to `API_PROXY_TARGET` (default `http://127.0.0.1:8000`). Only the health indicator fetches backend data; it handles checking, successful JSON, failed/malformed responses and a four-second timeout. No UI action calls an AI or business service.

FastAPI exposes `/api/health` and `/api/health/ready`, with process-only semantics. OpenAPI/docs are framework-generated. No database or authentication dependency is present. PostgreSQL remains the agreed future database. Backend tests use HTTPX ASGI transport against the real application.

## State and preview actions

The app stores no tokens, credentials or user data in browser storage. Login fields are uncontrolled and never read by application code. Sign-in/registration display a notice. Role switching is a demonstration control, not authorisation. Form drafts and selections use local React state. Uploaded files are not read or transmitted. Preview messages explicitly state that no save, generation, publication, access change or delivery occurs.

Practice has a single in-memory attempt shared between the practice screen and companion. Incomplete submissions are rejected; successful whole-set submission unlocks local sample results. Starting another attempt resets answers and submission status. Answers are bundled in frontend fixtures; this is display logic only and cannot protect answers from inspection. Production must implement server-side attempt verification, role/course access and filtered AI context before this becomes a real feature.

## Development and verification

Use the startup/check commands in [README.md](../README.md). `package-lock.json` and `uv.lock` pin resolved dependencies. No credentials are required. Ignore rules exclude local env files, generated output, virtual environments, browser traces and dependency directories. Use `npm run format` to format frontend files and `npm run format:check` to check them.

Playwright exercises real UI behaviour with intercepted health responses. Backend tests independently verify the real API. Visual checks cover desktop/mobile and light/dark modes. Native form validation is used where appropriate; accessible labels, visible focus, a skip link, reduced-motion CSS and a mobile navigation drawer are included. This is not a full accessibility certification.

## Workflow records

`workflow/AppShellPlan.md` records scope, execution decisions and verification. `logs/AppShellSummary.md` summarises the development conversation and tool outcomes. These are initial process artefacts, not a claim that all assignment requirements for multi-agent SE, context-engineering experiments or reflections have been completed. No deployment automation or product website is created in this phase.

## Acknowledgements

Built with React, TypeScript, Vite, Material UI, Emotion, Lucide, React Router, FastAPI, Uvicorn, HTTPX, pytest, Playwright, ESLint and Prettier. Material UI supplies the controls and theme infrastructure; custom CSS provides layout and decorative code illustrations. No previous MP implementation was copied. Codex assisted implementation; Context7 supplied official library documentation. The decorative login quotation is attributed to B. B. King in the interface. Names, messages, course content and metrics are illustrative fixtures.
