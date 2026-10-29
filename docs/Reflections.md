# Reflections

Draft skeleton. Fill with concrete examples backed by results from `workflow/experiments/`, `workflow/security/` and `logs/`.

## Multi-Agent SE
- Coordination pattern design and implementation (see `workflow/coordination.md`)
- Verifying triggering, context management, resource sharing and handoffs
- Idle, overloaded or blocked agents
- Retries, repeated analysis and unnecessary tool calls
- Resolving disagreements between agents
- Benefits versus costs; when to use and when not to use multi-agent coordination

## Context Engineering and Resource-aware Use
- System prompts and skills for the agents
- Upfront versus retrieve-on-demand context
- How context organisation affects instruction following
- What belongs in notes/handoff documents
- When more context hurt, and the signals
- Model choice and configuration per task
- Reducing cache misses and the measured token effect
- Share of tokens spent on reasoning, and persisted reasoning
- Other token-monitoring and reduction approaches
- Most token-hungry task types and reductions achieved
