# Handoff notes

Newest entry first. Use `templates/handoff.md`.

## 2026-10-28: scaffolding (session)
- Done: CLAUDE.md, AGENTS.md, agent definitions, coordination pattern, variants A and B, templates, reflection skeleton, checklist.
- Design decisions: generator-verifier with an independent test-designer running in parallel and isolated from `src/`; the spec step is shared and excluded from the comparison; revision loop capped at 2 rounds; changes go to `master` by PR only; experiments run on separate branches cut from the same `master` commit and are not merged.
- Next: build the token tracker (separate from learnSWE, with a copy under `workflow/tools/`), define the experiment task candidates and rubric, assign team members and roles, write the first spec.
- Open: SoC LLM access and quota; deployment target; subject and learner level; the Codex `AGENTS.md` pickup is untested; where the Codex model name is logged.
