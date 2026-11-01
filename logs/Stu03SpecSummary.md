# STU-03 spec summary: 30 October 2026

## Direction and completed work
After the cap experiments were merged (PR 7), `master` was pulled and `feat/stu03-spec` created. The spec-writer agent drafted `workflow/specs/STU-03/spec.md`, `plan.md` and `tasks.md` for the first slice of the AI study companion (hint, explain and help through one endpoint, the server choosing the mode). After discussion, the orchestrator updated all three to the user's decisions: stem-only hint context, a fixed reply shape as a prompt instruction, a hard leak rule (stating or confirming the answer, or ruling on a specific choice), a deterministic server leak check with no judge call, a canned reply on a block, per-student limits of 20 per minute and 300 per day with no shared limit, and a generic `llm_client.py` with no required teammate coordination.

## Verification and limits
No code was written, no tests were run and no live LLM call was made. The edits were checked by searching for leftover old limits and open-question references, not by a full re-read. The 20/300 limits and the 80% pasted-question threshold are our choices, not measurements. Items a to j were confirmed by the user and recorded in the spec, together with a planned post-build iterative live-testing step (AC35); the spec itself is not yet approved.

## Resources and summary verification
Spec-writer subagent: about 89k tokens, 41 tool uses, about 5.5 minutes (as reported by the harness). Total session tokens and cost were not measured. This summary was checked against the files on the branch and the commands run. Human review pending.
