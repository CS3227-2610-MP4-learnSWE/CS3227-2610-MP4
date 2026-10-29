# Reflections

Concrete examples backed by results in `workflow/experiments/`, `workflow/security/` and `logs/`. Sections not yet backed by an experiment are marked as still to do.

## Multi-Agent SE

### The experiment: two coordination patterns on one feature
We built the same feature, the server-side core of STU-02 (practice attempts, with answers released only after whole-set submission), three times from one approved spec and one start commit, each in a fresh Claude Sonnet session:

- **Variant A, split verification (5 agents):** spec-writer, then developer and test-designer in parallel, then a reviewer and a separate security-reviewer.
- **Variant B, merged verification (3 build agents):** developer and test-designer in parallel, then one verifier doing code, docs and security review together.
- **Baseline, single session:** no subagents, as a reference. The assignment requires multi-agent SE, so it could not be chosen.

Each result was graded with an 18-test acceptance and security suite that the runs never saw (checked beforehand against a reference implementation and four planted bugs), and token use was measured per agent from the local logs with our tracker, priced at API list prices.

![A vs B comparison](images/stu02-a-vs-b.png)

| | A (5 agents) | B (3 agents) | Baseline |
|---|---|---|---|
| Hidden grader | 18/18 | 18/18 | 18/18 |
| Cost | 2.76 USD | 1.56 USD | 0.52 USD |
| Requests | 87 | 54 | 14 |
| Wall time | 2 h 37 min (1 h 40 min stalled) | 8 min | 3 min |
| Revision rounds | 1 | 1 | 0 |
| Human interventions | 1 | 0 | 0 |
| Save/submit race | found and fixed | found, left open | double-submit fixed |

### Why we chose B over A
Both multi-agent variants produced correct code (18/18), and a blind API usability review found them behaviourally identical against the contract. B cost 43% less, finished without a stall, and re-verified after its fix round, which A did not. Our pre-registered decision rule (qualify on at least 90% of the grader with no leakage or ownership failure, then choose the cheapest unless within 15%) therefore picked B.

The price of B is real, and we accepted it knowingly. B's single verifier noticed the save/submit race and an untrimmed student id but rated both non-blocking, while A's dedicated security-reviewer insisted the race be fixed. One agent covering code quality, docs, security and tests in one pass spreads its attention; a specialist focused on one concern pushes harder. We compensate by fixing B's two defects before merging, adding a severity rule to the verifier (anything that can break an acceptance criterion, including two simultaneous requests, is blocking), and adding concurrency and input normalisation to the spec template.

### Coordination pattern design and verification
The pattern is generator-verifier with an independent test designer: the developer and test-designer work in parallel from a fixed HTTP contract in `plan.md`, so tests are not shaped by the code. A two-endpoint pilot (1.46 USD) before the real runs exposed five process defects, all fixed: the test-designer's worktree started from a branch without the spec; a reviewer's instructions said both "read-only" and "write to notes.md"; an agent staged another agent's file with `git add -A`; a "lint green" trigger could not be checked because the backend has no linter; and the security-reviewer created its own log file. Isolation became enforced by separate git worktrees rather than by instruction.

We verified adherence from evidence, not from the agents' reports: git timestamps show tests and code committed independently seconds apart; the tracker's per-agent breakdown showed every agent ran; and reading the subagent logs revealed a setup flaw we would otherwise have missed. Claude Code loads subagent definitions from the main project folder, not from the run's worktree, so Runs A and B received older instructions and B's verifier ran as a general-purpose agent. The orchestrators had read the current `coordination.md` and passed the key rules on themselves, so the runs still worked. Lesson: verify which instructions an agent actually received, not which ones you wrote.

### Idle, blocked and overloaded agents
In Run A the security-reviewer stalled after one of its own tests failed and never reported back; the orchestrator sat idle for 1 h 40 min until a human nudged it. Because the gap exceeded the prompt-cache lifetime, resuming also rewrote the orchestrator's cache. Neither B nor the baseline stalled. A pattern with more hand-offs has more places to block.

### Retries, repeated analysis and overhead
Coordination itself is expensive: the orchestrator alone cost 0.89 USD in A (32%) and 0.52 USD in B (33%). Opus verification was the single largest cost in both (A security-reviewer 1.13 USD, B verifier 0.68 USD). Each variant used one revision round: A to fix the race and small issues, B only to update stale documentation.

### Conflicts between agents
Two conflicts surfaced. In A, the orchestrator told the security-reviewer not to touch `src/`, contradicting its definition, so its 14 adversarial tests stayed in a scratch file and were never committed. In B, the verifier and the developer did not disagree, but the verifier's severity call meant a real defect shipped. Both point to the same fix: instructions must state precedence and severity explicitly.

### Did multi-agent coordination outweigh its costs?
For this small, tightly specified feature, not on correctness: the single-session baseline also scored 18/18, at 19% of A's cost and 33% of B's. What the extra agents bought was review: independent tests from the contract, and findings beyond the grader (the race, id trimming, documentation gaps). Multi-agent coordination pays off when a feature carries risk that a single author is likely to overlook (security, concurrency, AI behaviour) or when the spec is less precise; for small fixes and docs we use a single session, as `workflow/coordination.md` already allows.

## Context Engineering and Resource-aware Use

### Measured observations so far
- **Model switching invalidates the cache.** After switching one long session from Sonnet to Opus, 5 requests cost 2.69 USD, mostly from rewriting about 280,000 tokens of context at the Opus cache-write price. Keep one model per session; start a new session for a different model.
- **Cache reads dominate volume, output and cache writes dominate cost.** Every run read millions of cached tokens, cheaply; the expensive parts were output and cache writes.
- **Reasoning share.** Reasoning tokens were 11% of output in A, 9% in B and 5% in the baseline; the Opus security-reviewer spent 21% of its output on reasoning.
- **Context organisation decides which instructions are followed.** Agents followed the definitions loaded from the main folder, not the newer files in their own worktree; the orchestrators followed the newer `coordination.md` they read directly.
- **Measure, don't estimate.** Run sessions wrote token estimates into the resource log; the tracker's measured figures differed and replaced them.

### Still to do
- System prompts and skills for the agents; upfront versus retrieve-on-demand context; when more context hurt.
- What belongs in notes and handoff documents (beyond the handoff template in use).
- Model choice per task beyond the Sonnet/Opus split used here.
- Other token-monitoring and reduction approaches, and the most token-hungry task types once more features are built.
