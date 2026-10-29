# Run B (Variant B, merged verification): run record

- Branch `claude/stu02-run-b-223ec1`, start commit `70ab114` plus the Variant B switch `540293c`, final commit `46bf41d`. Session `local_ac7f604b`, sonnet orchestrator.
- Hidden grader: 18/18. Own tests: 42/42 (3 health, 39 STU-02).
- Revision rounds: 1 of 2 (docs only). The verifier re-checked after the fix round.
- Cost by session (tracker, API list prices): 1.56 USD over 54 requests, about 8 minutes wall time. Orchestrator 0.52, verifier (general-purpose agent on opus) 0.68, developer 0.18, test-designer 0.19.
- Interventions: 0.
- Process deviations: the `verifier` agent type was not registered, because agent definitions load from the main project folder, which held the grader branch's older agent files (see below); the orchestrator ran a general-purpose opus agent told to follow `verifier.md`. The developer's definition does not mention docs, so the docs defect cost the revision round. The resource-log row on the run branch has estimates only.
- Verification found no code or security defects. Left open (non-blocking): no lock between save and submit (a race that Run A's security-reviewer found and fixed); student id not trimmed; malformed PUT body gives 422 before the ownership 404.

## Setup flaw affecting Runs A and B
Claude Code loads subagent definitions from the main project folder, not from the run's worktree. During both runs the main folder was on `exp/stu02-grader`, whose `.claude/agents/` were older copies (before worktree isolation and the pilot fixes). Logs confirm both runs' developer and test-designer received the old text. The orchestrators read the current `coordination.md` in their own worktrees and passed the key rules on (for example the start-commit reset), so isolation still worked. A's reviewers ran with old definitions; B's verifier ran with the current `verifier.md` via a general-purpose agent. The build step is comparable; the verification step is not perfectly equal.
