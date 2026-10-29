# Run A (Variant A, split verification): run record

- Branch `claude/stu02-run-a-eba95d`, start commit `70ab114`, final commit `17a5169`. Session `local_e99f55d5`, sonnet orchestrator.
- Hidden grader: 18/18. Own tests: 44/44 (3 health, 41 STU-02).
- Revision rounds: 1 of 2.
- Cost by session (tracker, API list prices): 2.76 USD over 87 requests. Orchestrator 0.89, security-reviewer (opus) 1.13, developer 0.39, test-designer 0.28, reviewer 0.08.
- Intervention: 1. The security-reviewer stalled after one of its own scratch tests failed (last activity 10:56 UTC); at the user's request it was nudged at about 12:37 UTC and resumed. Requests after the nudge cost 1.26 USD, but that includes the fix round and final docs that would have happened anyway; the stall's own overhead is roughly the resumed security review (0.55 USD) plus an expired prompt cache rewritten after the 1 h 40 min gap. The exact overhead cannot be separated.
- Process deviations: the orchestrator told the security-reviewer not to touch `src/`, so its 14 adversarial tests stayed in a scratch file and were not committed; neither reviewer re-ran after the fix round (the orchestrator checked the race fix itself with a threaded test); the resource-log row on the run branch has estimates only.
- Findings fixed in round 1: a save/submit race (now one store lock, score stored at submit); untrimmed student id; stale docs; an `assert`.
- Left open (non-blocking): no rate limit or id length cap; malformed PUT body gives 422 before the ownership 404; invalid JSON without header gives 422 not 401; `/docs` public.
- Still to record by the user: review minutes and quality score (1-5) in `stu02-A-notes.json`.
