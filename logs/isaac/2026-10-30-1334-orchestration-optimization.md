# 2026-10-30 13:34 — Multi-Agent Orchestration Optimization Discussion — isaac

## Summary

Discussed the current spec-driven multi-agent workflow and how to reduce token usage, orchestration time, and revision cycles without weakening correctness or security.

## Conversation outcomes

- Mapped the responsibilities of the spec-writer, developer, test-designer, and verifier.
- Identified the main context handoff mechanisms: specifications, git commits/worktrees, `workflow/notes.md`, resource logs, and session logs.
- Identified an architectural risk: the spec-writer may define models, schemas, endpoints, or shared modules without enough knowledge of the existing implementation.
- Concluded that the spec-writer should receive a compact, maintained architecture reference rather than the entire codebase.
- Concluded that the developer must still inspect reevant implementation files because architecture summaries can become stale and may omit behavioral invariants.
- Recommended adding explicit reuse/extend/adapt/create decisions for models, schemas, endpoints, and shared modules.
- Recommended mapping the project threat model to OWASP categories and LLM-specific risks, while keeping project-specific controls and tests.
- Recommended front-loading architecture, contract, security, and requirements checks while preserving independent verifier review.
- Recommended risk-based orchestration so low-risk work can use a reduced workflow and security-sensitive work retains the full workflow.
- Recommended recording token proxies, elapsed time, tool calls, retries, revision rounds, and test durations.

## Artifact created

Created [`workflow/optimization-plan.md`](../../workflow/optimization-plan.md), containing:

- implementation steps;
- architecture and feature context packets;
- requirements-matrix guidance;
- security/threat-model improvements;
- risk-based routing;
- front-loaded automated checks;
- five baseline-versus-optimized experiments;
- adoption criteria and a human verification checklist.

## Follow-up

Run the proposed experiments on representative low-risk, normal endpoint/data, and security-sensitive or AI features before changing the default orchestration process.
