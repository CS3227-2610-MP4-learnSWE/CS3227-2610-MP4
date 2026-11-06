# ADM-05 local login/testing documentation — 2026-11-06

Developer role, documentation maintenance only; no new application feature or multi-agent run. The user requested copyable commands and env-file instructions after experiencing login Origin rejection and confusion about changing a seed password.

Updated UserGuide with backend/frontend env setup that preserves existing files, test-only quoted credentials, Docker/migration/seed commands, seed output interpretation, all-configured-role reset semantics, full process restarts, real sign-in instead of demo access, old/new password testing and 401/403/429/503 recovery. Existing account/course walkthrough remains available.

Updated DeveloperGuide with standalone setup/reset instructions, conditional fresh-database creation, backend Origin/CSRF versus credential failure details, fixed demo identity and session limitations, frontend proxy precedence, and focused/full automated test commands using dedicated pytest temp and browser output directories with one browser runner at a time.

Validation: all 15 PowerShell fenced command blocks parsed using the PowerShell AST parser. Quoted sample env parsed through uv, shared password validator and local Origin value passed using a disposable temporary env file, then removed. Initial absolute-backslash temporary env argument was rejected by uv; the check succeeded with a slash-normalised temporary path. Documented commands use relative `.env` paths. No application suites rerun because no runtime code/tests changed. Diff whitespace check passed. No developer env values, passwords, database, seeds, processes, live AI or remote Git changed during this documentation task.

Resource use: single inherited Codex session; exact per-task tokens/model/cost not measured; tracker not run for this documentation-only follow-up; no agents or application revision rounds. One temporary-env validation command retried as described above.
