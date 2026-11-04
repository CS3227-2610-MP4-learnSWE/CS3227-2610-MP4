# learnSWE

A calmer space to learn, teach and grow in software engineering.

This release includes server-backed student practice, the student study companion, private teacher source materials and persisted AI-generated draft notes and MCQ batches. Teacher notes use the shared SoC LLM client for generation; teachers can explicitly edit/save drafts without AI calls. Publication remains deferred. Other teacher and admin screens remain demonstrations.

## Run locally

Requirements: Node.js 22+, npm 10+, Python 3.12+, [uv](https://docs.astral.sh/uv/) and Docker Desktop for PostgreSQL 16. Start Docker Desktop first.

From the repository root, start the local database:

```sh
docker compose up -d postgres
# Once, create a fresh database; keep any previous database unchanged.
docker compose exec postgres createdb -U learnswe learnswe_db_files
```

In the backend terminal:

```sh
cd src/backend
uv sync --frozen

# Only if .env does not already exist:
cp .env.example .env
```

Edit `.env`: point `DATABASE_URL` at the fresh `learnswe_db_files` database on loopback port 5433, as in `.env.example`. Preserve an existing `.env` and change only the needed values. Keep `APP_ENV=development` and configure the session settings for local HTTP testing. Teacher APIs require a real teacher sign-in; demo identity headers are ignored. No permanent file directory is required. Then run:

```sh
uv run --env-file .env alembic upgrade head
uv run --env-file .env python -m teacher_materials.seed
uv run --env-file .env python -m auth.seed
uv run --env-file .env python -m study_lessons.seed
uv run --env-file .env uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Before `auth.seed`, set the `SEED_*` email and password variables in `.env` (names in `.env.example`; choose your own passwords, never commit them). `ALLOWED_ORIGINS` (also in `.env.example`) must list the frontend origin, or the browser's login is refused with a 403 and the login page says it could not reach the server. Restart the backend after editing `.env`; `--reload` does not re-read it.

The storage conversion refuses migration when existing materials are present; use a fresh database rather than clearing the previous one. Old uploads and drafts do not appear in the fresh database; upload sources again. Populated downgrade is also refused because originals cannot be reconstructed as old filesystem files. To return to the old version, restore its code, database configuration and original files together.

The seed can be rerun; it does not erase uploads. Teacher APIs ignore legacy identity headers and require a signed-in teacher account. The `--env-file` option is important: the API does not automatically load the backend `.env`.

In another terminal, from the repository root:

```sh
cd src/frontend
npm ci

# Only if .env does not already exist:
cp .env.example .env
npm run dev
```

In PowerShell, use `Copy-Item .env.example .env` instead of `cp` if preferred. Preserve any existing `.env` rather than overwriting it; add the values from `.env.example` manually.

Open [the local preview](http://127.0.0.1:5173/login). Sign in using the account configured by `auth.seed`. Public Create account creates students only. Role tabs choose an anonymous sample-data shortcut; they do not assign the signed-in role. Teacher materials and content studio require teacher sign-in.

Preview screens work without the backend, but Student Practice, the study companion, Teacher Materials and Teacher AI content studio require it. Copy `src/frontend/.env.example` to `src/frontend/.env` for the local proxy settings. `API_PORT` in that file is the backend port the Vite dev server proxies `/api` to. AI calls also require the backend `SOCLAAS_BASE_URL`, `SOCLAAS_API_KEY` and `SOCLAAS_MODEL` settings; keep the key in the ignored backend `.env`.

## What you can explore

- **Student:** overview, topic/search filtering, sample lessons with reversible completion, MCQ-only whole-set practice submission and results, a floating study companion, inbox read status and a feedback-form preview.
- **Teacher:** overview, working private materials library with PDF/UTF-8 uploads, topic assignment and download, working AI content studio with saved draft notes, explicit note and three-MCQ batch editing/conflict recovery, confirmed unpublished draft deletion and deletion of unreferenced sources; sample publication screens, practice-set selection and inbox.
- **Admin:** illustrative analytics, feedback-form builder and audience preview, sample feedback and analysis references, announcement preview, role-filtered people table and illustrative AI usage.
- **Shared:** responsive navigation, role switching, light/dark mode, keyboard focus, reduced-motion support and direct browser routes.

Remaining preview state and the current student practice session are temporary. Teacher Materials records and file bytes persist in PostgreSQL across browser/backend restarts and redeploys. Uploads are limited to 10 MiB each and 100 MiB total original bytes; database overhead and other records need additional capacity. The student companion opens from the bottom-right chat icon on any student page. Close/Escape minimises without losing messages or the unsent draft; its refresh icon clears both without refreshing the page. Chat survives student-page navigation, but returning to login or switching demo roles ends that temporary conversation. Some editor drafts reset when leaving their screen. Dashboard figures remain illustrative. The student companion and teacher notes/MCQs make real AI calls when configured; publication and message delivery remain unimplemented. Login and student registration use the shared authentication service. Teacher Materials original bytes and metadata persist together in PostgreSQL; uploading never publishes student-facing content. Other preview actions remain in memory.

**Practice boundary:** complete every question and submit the whole set before scores and solutions are shown. The student companion uses server-selected hint mode before submission and explain mode for eligible submitted attempts. It calls the SoC LLM; its documented deterministic leak check has residual risks (see the user guide). It does not retrieve lesson content yet. Authenticated account-scoped conversation persistence until logout remains future work. Student practice gets questions without keys and reads answers only from the server after submission. Separate teacher sample answers load only in the lazy teacher screen. The demo role switcher is not authentication. Teacher source/draft endpoints require a live teacher session, CSRF on mutations and current course membership; identity headers are ignored.

## Health API

| Endpoint | Response | Meaning |
|---|---|---|
| `GET /api/health` | `200 {"status":"ok"}` | API process can serve a request. |
| `GET /api/health/ready` | `200 {"status":"ready"}` | Process readiness only; does not check PostgreSQL or AI. |

FastAPI's generated API documentation is at `/docs` on the backend (the port in `src/frontend/.env.example`). Teacher Materials endpoints and BYTEA storage are specified in [the shared data contract](docs/SharedDataContract.md).

The frontend proxy uses `API_PORT` (default `8000`). Existing `API_PROXY_TARGET` URLs remain supported and take precedence. After changing frontend environment settings, restart `npm run dev`.

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

Frontend tests start a local Vite server if port 5173 is free. They cover login preview behaviour, practice submission, completion, inbox, role routes, themes, mobile navigation, focus and backend failure. Teacher browser tests mock authenticated sessions; no teacher identity-header flags are required. PostgreSQL integration tests require `TEA01_TEST_DATABASE_URL` pointing to a dedicated test database; they create/drop only their unique schema. Without that variable, teacher integration tests are explicitly skipped. Never point it at production. Tests intercept health responses; the backend suite separately exercises the real ASGI API. Visual review screenshots are generated under `src/frontend/test-results/visual/` and are not committed.

The production build is generated in `src/frontend/dist/`. Hosting it later requires SPA fallback to `index.html` and routing `/api` to FastAPI; deployment is not included in this release.

## Project layout

- `src/frontend/`: React + TypeScript, Vite, Material UI, Emotion, Lucide and React Router. Shared components, in-memory state and sample fixtures are separate from role screens.
- `src/backend/`: FastAPI application and HTTP-boundary tests. Dependencies are locked with uv.
- `docs/`: proposed feature list, user stories and current release guides.
- `workflow/`: spec-driven, multi-agent process: coordination pattern, workflow variants, templates, per-feature specs, experiment and security logs, and execution records. Start at `workflow/README.md`.
- `CLAUDE.md`, `AGENTS.md` and `.claude/agents/`: project rules and agent role definitions for Claude Code and Codex.
- `logs/`: human-readable development interaction summaries.

The feature list and user stories describe the intended product, not completion status. See [the user guide](docs/UserGuide.md) and [developer guide](docs/DeveloperGuide.md) for the boundaries of this preview.
