# 2026-11-03 — Phase A: hard-coded paths and values (docs only) — isaac

Branch: `chore/workflow-cleanup-and-refactor`. Model: Claude Sonnet 5.5. One commit per task (T1–T4).

## Commits

| Task | Commit message | Change |
|---|---|---|
| T1 | `docs: make rule-file commands portable (T1)` | `CLAUDE.md` and `AGENTS.md` Commands section: replaced the `cd "C:\Users\yikbi\..."` lines with `Set-Location (git rev-parse --show-toplevel)` then `Set-Location src\backend` / `src\frontend`. Heading now says "first go to the repo root". |
| T2 | `docs: remove absolute user paths from workflow docs (T2)` | `workflow/README.md` and `workflow/tools/token-tracker/README.md`: same relative pattern. `workflow/experiments/stu02/procedure.md`: the experiment finished on 29 Oct, so a "Historical" note was added and its paths were left as the record. |
| T3 | `chore: define the API port once (T3)` | `src/frontend/.env.example` (and the ignored local `.env`): `API_PROXY_TARGET=http://127.0.0.1:8000` became `API_PORT=8000`. `vite.config.ts` proxies to `` `http://127.0.0.1:${env.API_PORT}` ``. `.github/workflows/ci.yml` real-backend job defines `API_PORT: "8000"` in `env:` and uses `$API_PORT` for uvicorn and the health check. README and DeveloperGuide point to `.env.example` instead of repeating the number. |
| T4 | `docs: point rule files to the checklist for deadline and owners (T4)` | `CLAUDE.md` and `AGENTS.md` say "Deadline and owners: see `workflow/checklist.md`". The checklist already holds the date and names and is unchanged. |

## How each was tested

- T1: ran `Set-Location (git rev-parse --show-toplevel)` then `Set-Location src\backend` and `src\frontend` in PowerShell; both landed in the right folder. `grep` for `yikbi` and `C:\Users` in the two files finds nothing.
- T2: ran the tracker's `python -m tracker report --branch ...` from the new relative commands; it produced a table. grep for `yikbi`/`C:\Users` under `workflow/` finds only `procedure.md` (marked historical), `notes.md`, `checklist.md` and `results/stu02-try-it.md` (records, out of scope).
- T3: started the Vite dev server with `API_PORT=8000` and fetched `http://127.0.0.1:5173/api/health`, which returned `{"status":"ok"}` through the proxy (port 8000 was already served by another backend process, so my own uvicorn start was refused; the proxied reply came from that one). `npm run typecheck` and `npm run lint` passed. Vite also starts with no `.env` (the CI frontend job has none). `ci.yml` parses as valid YAML. The CI health check itself was not run on GitHub.
- T4: grep for a person's name or a date in the two rule files finds nothing; the checklist still has both.

## Problems found and fixed

- My first T1 edit used a Python regex replacement string, which turned `\b` and `\f` in `src\backend` / `src\frontend` into control characters (`srcackend`). I noticed this during T3, fixed both files and folded the fix into the T1 commit with a fixup and autosquash, so the history has no bad commit. Control-character grep over every edited file is now clean.

## Open points for the user

- Port 8000 still appears in the backend start command in `CLAUDE.md`, `AGENTS.md` and `README.md` line 30, because the task listed only the frontend, CI and the two doc lines. Changing the port would touch those too. Say if you want them to use `$API_PORT`.
- The rule files no longer say the deadline is on `master`; the Git section already says `master` must be gradeable.
- Not run: the full backend suite (docs-only phase), GitHub CI.
