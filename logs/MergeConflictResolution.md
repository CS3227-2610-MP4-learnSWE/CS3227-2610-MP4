# Merge conflict resolution ? 2026-11-07

Resolved the in-progress merge of master into feat/adm04-feedback-follow-up.

- src/backend/auth/routes.py: combined both branches' no-store prefixes, preserving messaging and adding practice-sets/attempts.
- workflow/notes.md: retained both conflict sides and added the maintenance handoff.
- Frontend typecheck and lint passed using npm.cmd after PowerShell blocked npm.ps1.
- Direct execution of the actual middleware function passed 11 private-route checks, the AI-usage override and health exclusion. The first harness attempt lacked the Request annotation binding; corrected and rerun successfully.
- git diff --check passed. Full backend and browser suites were not run.
- Resolutions and this record staged; no commit or push. Existing untracked worktrees untouched.

Small maintenance, no invoked project workflow or delegated agents. Model/effort inherited; exact tokens, cost and elapsed unavailable.
