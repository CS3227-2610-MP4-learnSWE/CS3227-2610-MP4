You are the orchestrator for a build of feature ADM-01 (backend-complete slice only; the admin report page is out of scope). Follow AGENTS.md and workflow/coordination.md (Variant B: developer and test-designer in parallel, then the verifier).

Spec, plan and tasks are approved: workflow/specs/ADM-01/. Do not edit them. If something is ambiguous, stop and ask me.

Rules for this run:
- Skip the token-tracking lifecycle (no run manifest, no invocations.csv); the experiment coordinator measures usage from session logs.
- Record the start commit with `git rev-parse HEAD`, start the developer and the test-designer (worktree isolation, given the start commit) together, merge the tests after both report, then run the verifier.
- At most 2 revision rounds. After that stop and tell me.
- Do not read or write anything under workflow/experiments/, workflow/usage/ or other worktrees. Do not push or open a PR. Commit only on this branch, staging by path.
- Tell me when you are done: PASS with the suite result, or what is still failing.
