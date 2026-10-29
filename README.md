# learnSWE

A calmer space to learn, teach and grow in software engineering.

This release is an **interactive app-shell preview**, not a working learning platform. Explore student, teacher and admin workspaces, with Material UI components and light/dark themes. The only backend APIs are process health checks.

## Run locally

Requirements: Node.js 22+, npm 10+, Python 3.12+ and [uv](https://docs.astral.sh/uv/).

In one terminal:

```sh
cd src/backend
uv sync --frozen
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal:

```sh
cd src/frontend
npm ci
npm run dev
```

Open [the local preview](http://127.0.0.1:5173/login). Select a role tab, then **Explore … demo**. No credentials are needed. Sign-in and Create account only display a preview message.

The frontend works without the backend and reports its connection status in the workspace footer. An optional `src/frontend/.env` can override `API_PROXY_TARGET`; see `.env.example`. No secrets are needed.

## What you can explore

- **Student:** overview, topic/search filtering, sample lessons with reversible completion, MCQ-only whole-set practice submission and results, a floating study companion, inbox read status and a feedback-form preview.
- **Teacher:** overview, materials library, file-picker preview, sample AI content studio, editable draft notes/questions/answer keys, practice-set selection and inbox.
- **Admin:** illustrative analytics, feedback-form builder and audience preview, sample feedback and analysis references, announcement preview, role-filtered people table and illustrative AI usage.
- **Shared:** responsive navigation, role switching, light/dark mode, keyboard focus, reduced-motion support and direct browser routes.

Changes exist in memory only and reset on browser refresh. The student companion opens from the bottom-right chat icon on any student page. Close/Escape minimises without losing messages or the unsent draft; its refresh icon clears both without refreshing the page. Chat survives student-page navigation, but returning to login or switching demo roles ends that temporary conversation. Some editor drafts reset when leaving their screen. All figures, records and AI responses are illustrative. There are no AI calls, uploads, messages, registrations, persistence or real permission changes. Browser file selection displays a filename only; the file is not read or uploaded. PostgreSQL is planned but not configured.

**Practice boundary:** complete every question and submit the whole set before scores and solutions are shown. Before submission, the practice hint and companion previews never reveal or confirm answers. The widget displays the current page label and fixed demonstration replies; it does not retrieve page contents or call AI. Authenticated, account-scoped conversation persistence until logout (including browser reload) and secure current-page content retrieval remain future requirements. Sample answer keys ship in frontend code and the demo role switcher is unrestricted; neither is a security boundary. Production answer protection and authorisation must be implemented on the server later.

## Health API

| Endpoint | Response | Meaning |
|---|---|---|
| `GET /api/health` | `200 {"status":"ok"}` | API process can serve a request. |
| `GET /api/health/ready` | `200 {"status":"ready"}` | Process readiness only; does not check PostgreSQL or AI. |

FastAPI's generated API documentation is at [localhost:8000/docs](http://127.0.0.1:8000/docs). No business or authentication endpoints are implemented.

## Verify

```sh
cd src/frontend
npm run typecheck
npm run lint
npm run format:check
npm run build
npx playwright install chromium
npm test
```

```sh
cd src/backend
uv run pytest -q
```

Frontend tests start a local Vite server if port 5173 is free. They cover login preview behaviour, practice submission, completion, inbox, role routes, themes, mobile navigation, focus and backend failure. Tests intercept health responses; the backend suite separately exercises the real ASGI API. Visual review screenshots are generated under `src/frontend/test-results/visual/` and are not committed.

The production build is generated in `src/frontend/dist/`. Hosting it later requires SPA fallback to `index.html` and routing `/api` to FastAPI; deployment is not included in this release.

## Project layout

- `src/frontend/`: React + TypeScript, Vite, Material UI, Emotion, Lucide and React Router. Shared components, in-memory state and sample fixtures are separate from role screens.
- `src/backend/`: FastAPI application and HTTP-boundary tests. Dependencies are locked with uv.
- `docs/`: proposed feature list, user stories and current release guides.
- `workflow/`: spec-driven, multi-agent process: coordination pattern, workflow variants, templates, per-feature specs, experiment and security logs, and execution records. Start at `workflow/README.md`.
- `CLAUDE.md`, `AGENTS.md` and `.claude/agents/`: project rules and agent role definitions for Claude Code and Codex.
- `logs/`: human-readable development interaction summaries.

The feature list and user stories describe the intended product, not completion status. See [the user guide](docs/UserGuide.md) and [developer guide](docs/DeveloperGuide.md) for the boundaries of this preview.
