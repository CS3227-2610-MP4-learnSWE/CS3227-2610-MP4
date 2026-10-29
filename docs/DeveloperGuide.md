# Developer Guide — App Shell Preview

## Architecture and boundaries

The React/TypeScript frontend uses Vite, React Router, Material UI/Emotion and Lucide icons. `src/frontend/src/data.ts` holds fixtures and role navigation; `state.tsx` owns temporary completion, practice and inbox state. Shared layout and visual components live under `components/`; each role has a page module, with shared inbox and feedback pages. The Material UI theme is configured at the root and CSS variables coordinate custom layout/illustrations in both modes.

The student `CompanionProvider` and floating widget live at the student shell boundary, outside individual route screens. Closing hides the panel without unmounting its message/draft state. Leaving the student role or returning to login unmounts it; a browser reload also resets it. No chat is stored in local/session storage or a backend. The legacy `/student/assistant` URL opens the widget and redirects to the overview; navigation and lesson CTAs now open the widget without leaving their page.

The widget derives a current-page label from routes and sample lesson metadata only. Future authenticated sessions must scope conversation history to the signed-in account until logout/clear, restore it on reload, and retrieve bounded, authorised page content on the server. Context must update on navigation, with submission/permission checks excluding protected solutions, drafts and other users’ data. Neither page content nor chat may override fixed instructions; DOM scraping and client-provided context are not security boundaries. No real context pipeline or session persistence is implemented in this preview.

BrowserRouter enables direct URLs and history. For future production hosting, configure SPA fallback and route `/api` to FastAPI. Vite proxies `/api` locally to `API_PROXY_TARGET` (default `http://127.0.0.1:8000`). Only the health indicator fetches backend data; it handles checking, successful JSON, failed/malformed responses and a four-second timeout. No UI action calls an AI or business service.

FastAPI exposes `/api/health` and `/api/health/ready` (process-only semantics) and the STU-02 practice attempt API: `GET /api/practice-sets/{set_id}`, `POST /api/practice-sets/{set_id}/attempts`, `GET /api/attempts/{attempt_id}`, `PUT /api/attempts/{attempt_id}/answers`, `POST /api/attempts/{attempt_id}/submit` and `GET /api/attempts/{attempt_id}/results`. The student is identified by the placeholder `X-Student-Id` header (to be replaced by SHR-01 authentication); other students' attempts return 404. Attempts live in an in-memory store behind the `AttemptStore` interface. Modules in `src/backend/`: `practice_data` (fixture and answer key), `practice_schemas`, `practice_logic` (validation and scoring), `practice_routes` (HTTP, shared header check) and `attempt_store`; `main.py` only wires the router. The key and explanations are released only in results of a submitted attempt. OpenAPI/docs are framework-generated. No database or real authentication dependency is present. PostgreSQL remains the agreed future database. Backend tests use HTTPX ASGI transport against the real application.

## State and preview actions

The app stores no tokens, credentials or user data in browser storage. Login fields are uncontrolled and never read by application code. Sign-in/registration display a notice. Role switching is a demonstration control, not authorisation. Form drafts and selections use local React state. Uploaded files are not read or transmitted. Preview messages explicitly state that no save, generation, publication, access change or delivery occurs.

Practice uses single-answer MCQs only, including code-reading questions expressed as choices. Teachers see sample choices and select a correct option in the review preview. Practice has a single in-memory attempt shared between the practice screen and companion. Incomplete submissions are rejected; successful whole-set submission unlocks local sample results. Starting another attempt resets answers and submission status. Answers are bundled in frontend fixtures; this is display logic only and cannot protect answers from inspection. A server-side attempt API now exists (in-memory, placeholder identity) but the frontend does not use it yet. Production must still connect the frontend to it, add real authentication, role/course access, persistence and filtered AI context before this becomes a real feature.

## Development and verification

Use the startup/check commands in [README.md](../README.md). `package-lock.json` and `uv.lock` pin resolved dependencies. No credentials are required. Ignore rules exclude local env files, generated output, virtual environments, browser traces and dependency directories. Use `npm run format` to format frontend files and `npm run format:check` to check them.

Playwright exercises real UI behaviour with intercepted health responses. Backend tests independently verify the real API. Visual checks cover desktop/mobile and light/dark modes. Native form validation is used where appropriate; accessible labels, visible focus, a skip link, reduced-motion CSS and a mobile navigation drawer are included. This is not a full accessibility certification.

## Workflow records

`workflow/AppShellPlan.md` records scope, execution decisions and verification. `logs/AppShellSummary.md` summarises the development conversation and tool outcomes. `logs/WorkflowScaffoldingSummary.md` records the design discussion for the multi-agent workflow, including the variants (A split verification, B merged verification, single-session baseline) that will be compared in planned experiments; no experiment has been run yet. `logs/TrackerAndExperimentSetupSummary.md` covers the token tracker, the STU-02 experiment setup and a review of earlier work. These are initial process artefacts, not a claim that all assignment requirements for multi-agent SE, context-engineering experiments or reflections have been completed. No deployment automation or product website is created in this phase.

## Workflow files

Spec-driven, multi-agent scaffolding. Contents are templates and drafts until features are specified; see `workflow/README.md` for the index.

| File | Purpose |
|---|---|
| `CLAUDE.md` | Project rules and read order for Claude Code. |
| `AGENTS.md` | The same rules plus all agent role definitions, for Codex. Keep in sync with `CLAUDE.md` and `.claude/agents/`. |
| `.claude/agents/*.md` | Claude Code agent definitions for the chosen workflow (Variant B): spec-writer, developer, test-designer, verifier. |
| `workflow/coordination.md` | Generator-verifier coordination pattern with an independent test designer, isolation rules, handoffs, revision caps, conflict resolution and how adherence is verified. |
| `workflow/variants/` | The workflow variants that were compared; B was chosen (A split verification, B merged verification with a single `verifier`, single-session baseline) and how to switch. |
| `workflow/notes.md` | Handoff log between agents and sessions. |
| `workflow/templates/` | Spec, plan, tasks and handoff templates. |
| `workflow/specs/` | Per-feature spec, plan and tasks. |
| `workflow/experiments/` | Context-engineering experiments, the resource log, and per-run usage summaries under `results/`. |
| `workflow/tools/token-tracker/` | Standard-library Python tool that reads Claude Code and Codex session logs and reports token use and cost per agent and model (spec: `workflow/specs/TRK-01/`). |
| `workflow/security/` | Threat model and security test log. |
| `workflow/checklist.md` | Setup and submission checklist. |
| `docs/Reflections.md` | Reflection skeleton, to be filled from experiment results. |

## Acknowledgements

Built with React, TypeScript, Vite, Material UI, Emotion, Lucide, React Router, FastAPI, Uvicorn, HTTPX, pytest, Playwright, ESLint and Prettier. Material UI supplies the controls and theme infrastructure; custom CSS provides layout and decorative code illustrations. No previous MP implementation was copied. Codex assisted implementation; Context7 supplied official library documentation. The decorative login quotation is attributed to B. B. King in the interface. Names, messages, course content and metrics are illustrative fixtures.
