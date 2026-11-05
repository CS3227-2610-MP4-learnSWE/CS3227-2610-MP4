Implement feature ADM-01 (backend-complete slice only; the admin report page is out of scope) yourself in this single session. Do not start any subagents.

Spec, plan and tasks are approved: workflow/specs/ADM-01/. Do not edit them. If something is ambiguous, stop and ask me.

Process: read the spec and plan first, write the tests first (mock the SoC LLM; follow the plan's contract), then the code, then run the backend suite (`uv run pytest -q` in src/backend). Then review your own diff against every acceptance criterion in spec.md (met and covered by a test), security (admin-only 401/403, no message text/answers/user ids/file content stored, concurrent safety) and update docs/DeveloperGuide.md and docs/UserGuide.md (only claim what works). At most 2 revision rounds.

Rules: skip the token-tracking lifecycle. Do not read or write anything under workflow/experiments/, workflow/usage/ or other worktrees. Do not push or open a PR. Commit only on this branch, staging by path. Tell me when you are done: PASS with the suite result, or what is still failing.
