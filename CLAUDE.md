# learnSWE: project instructions

Programming/SE learning web app with three roles (student, teacher, admin), each with at least one SoC-LLM feature. CS3227 MP4: spec-driven, multi-agent, security-tested, deployed with separate dev/prod. Deadline: 13 Nov 2026, 2pm SGT, on `master`.

## Read first (in this order, only what the task needs)
1. `workflow/README.md`: index of process files and the agent roster.
2. `docs/FeatureList.md`: feature IDs (STU/TEA/ADM/SHR/OPT). `docs/UserStories.md`: acceptance criteria.
3. `workflow/specs/<feature-id>/`: spec, plan, tasks for the feature you are working on.
4. `workflow/notes.md`: latest handoff state. Update it before ending a task.

## Rules
- Spec first: no feature code without an approved `spec.md` and `plan.md`. Tests are written before code.
- One agent role per task; hand off through `workflow/notes.md` using `workflow/templates/handoff.md`. See `workflow/coordination.md`.
- Security is enforced on the server (auth, role/course access, answer release after submission). Prompts are never the only control. Log security tests in `workflow/security/`.
- AI calls go through the SoC LLM only, via one shared client with rate limiting, input/output caps and error handling. No other LLM provider.
- Keep shared logic single-purpose and not duplicated (SRP, DRY). Keep the UI simple.
- Do not claim a feature in `docs/UserGuide.md` unless it works; inaccuracies count as bugs.
- Record resource use (model, rough tokens, retries) for notable tasks in `workflow/experiments/resource-log.md`.
- Add a summary to `logs/` after each working session. Verify it against what actually happened.
- No build-and-host tools for deployment; use GitHub Actions in the team's repo.
- Never commit secrets. Use `.env` files (ignored) and `.env.example`.

## Commands (PowerShell 5.1: no `&&`; one command per line, start with the full `cd`)
- Backend: `cd "C:\Users\yikbi\NUS\CS3227\MP4\CS3227-2610-MP4\src\backend"` then `uv sync --frozen`, `uv run pytest -q`, `uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload`.
- Frontend: `cd "C:\Users\yikbi\NUS\CS3227\MP4\CS3227-2610-MP4\src\frontend"` then `npm ci`, `npm run dev`, `npm run typecheck`, `npm run lint`, `npm test`.

## Git
Work on a feature branch and open a pull request into `master`; never commit or push directly to `master`. A teammate reviews and merges after tests pass. `master` must always be gradeable.
