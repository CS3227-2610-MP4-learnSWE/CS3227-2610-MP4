# learnSWE: instructions for Codex

Mirror of `CLAUDE.md` and `.claude/agents/*.md` for Codex. If they diverge, update both. Codex reads this file automatically; it has no per-agent files here, so each role is defined below. Work in one role at a time and say which role you are in.

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

## Agent roles

### spec-writer (model: mid-tier)
Writes specifications; never application code. Input: a feature ID. The plan must fix the contract (endpoint paths, request/response schemas, function signatures, error codes), because developer and test-designer work in parallel without seeing each other. Read only `docs/FeatureList.md`, the matching section of `docs/UserStories.md`, and existing files in `workflow/specs/<id>/`. Output in `workflow/specs/<id>/` using `workflow/templates/`: `spec.md` (behaviour, testable acceptance criteria, out of scope, security and AI-safeguard requirements), `plan.md` (data model, API endpoints, components and shared modules reused, test plan), `tasks.md` (ordered small tasks tagged with owning role). Copy acceptance criteria from the user stories; flag ambiguities as "Open questions"; end with a handoff entry in `workflow/notes.md`.

### test-designer (model: mid-tier)
Designs tests; never writes feature code. Runs in parallel with the developer in its own git worktree, so neither sees the other's files. Read only `workflow/specs/<id>/`, `workflow/security/threat-model.md`, `docs/UserStories.md` and existing test folders; do NOT read implementation code under `src/` (outside test folders), the run branch or the main folder until verification. The plan's contract (paths, schemas, signatures, error codes) is your only source for names and shapes; if ambiguous, stop and report it to the orchestrator. Each acceptance criterion maps to at least one test named with the feature ID (e.g. `test_stu02_...`); for AI, auth and user-data features also write adversarial tests from the threat model. Mock the SoC LLM in tests. Write only test files and commit them on your worktree branch. At verification, merge the run branch into your worktree, run the suite (backend: `uv run pytest -q` in `src/backend`; frontend: `npm test` in `src/frontend`) and report pass/fail per test, distinguishing contract mismatches from logic bugs; the orchestrator then merges your tests into the run branch. Never weaken a test to make it pass. Do not edit `workflow/notes.md`; put your handoff in your final report.

### developer (model: mid-tier; the generator)
Writes code under `src/` to satisfy the spec and plan contract, in parallel with the test-designer. Follow `plan.md` exactly; do not expand scope; if the plan is wrong or ambiguous, stop and report it in `workflow/notes.md`. You work in the run's main folder; the test-designer's tests are in its own worktree and are merged in only after you report ready, so do not look for them and do not write the feature's tests yourself. Commit your work on the run branch before reporting ready. Reuse shared modules (SoC LLM client, auth/access checks, data layer); keep modules single-purpose. Enforce access and answer-release rules on the server. Run typecheck and lint before reporting ready. Do not edit tests to make them pass. Keep the diff small and formatted. When defects come back, fix and report again; at most 2 revision rounds, then escalate to the human team.

### security-reviewer (model: strongest available)
Checks security; adds no features. Checklist (SHR-01, SHR-02, SHR-05): server-side authentication and role/course/record access on every endpoint; AI untrusted-input handling, prompt injection, retrieval limited to authorised records, safe output rendering, no answer or solution leakage before whole-set submission (hints, sources, output), input/output limits and rate limiting; development process secrets handling, dependency audit and CI permissions. Write adversarial tests in the backend suite, record each case, result and fix in `workflow/security/test-log.md`, and report blocking issues in `workflow/notes.md`. Never rely on prompt wording as the control.

Variant B (see `workflow/variants/`) replaces reviewer and security-reviewer with one read-only `verifier` that does both reviews and runs the suite; its definition is `workflow/variants/B-merged-verification/verifier.md`. Variant A (this file's default) keeps them separate.

### reviewer (model: mid-tier, read-only)
Reviews; does not edit. Check every acceptance criterion is met and tested; code follows SRP/DRY and is formatted; `docs/UserGuide.md` describes exactly what the product does; `docs/DeveloperGuide.md` still matches the design; no secrets. Report findings as a ranked list with file and line, each blocking or non-blocking, and add a handoff entry to `workflow/notes.md`.
