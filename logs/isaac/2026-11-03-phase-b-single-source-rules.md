# 2026-11-03 — Phase B: one source for the shared rules — isaac

Branch: `chore/workflow-cleanup-and-refactor`. Model: Claude Sonnet 5.5. One commit per task (T5–T7).

## Commits

| Task | Commit message | Change |
|---|---|---|
| T5 | `docs: keep the token-measuring steps in the tracker README only (T5)` | `workflow/tools/token-tracker/README.md` gained a "Use in the workflow" section (when to run, save the summary, add the resource-log row, what is committed). `workflow/README.md` "Measuring token usage" is now three lines and a link to that section. |
| T6 | `docs: make AGENTS.md the single source of shared rules (T6)` | `AGENTS.md`: new title and a header saying it is the single source (Codex reads it, `CLAUDE.md` imports it); the old "mirror of CLAUDE.md" text is gone; a one-line intro added under "Agent roles". `CLAUDE.md`: now `@AGENTS.md` plus a short "Claude Code only" note about `.claude/agents/`. `.claude/agents/` unchanged. |
| T7 | `docs: fix coordination and README contradictions after T6 (T7)` | `workflow/coordination.md` Handoff: "Only the developer and the orchestrator write `notes.md`" now includes the spec-writer, because its own definition ends with a `notes.md` entry. `workflow/README.md`: replaced "Edit all three places together" with the new arrangement. Nothing else contradicted the rules (Context management, Handoff, agent table models match `.claude/agents/` frontmatter). |

## How each was tested

- T5: grep shows `python -m tracker report` no longer appears in `workflow/README.md` and appears in the tracker README; the link anchor `#use-in-the-workflow` matches the new heading; `resource-log.md` still points at "Measuring token usage", which still exists. Checked line endings (both files CRLF) and control characters after my first attempt wrote a stray carriage return (`\r` in `experiments\results`); that was caught before commit and redone.
- T6 import check (first step): Claude Code is 2.1.317. In a throwaway folder, `CLAUDE.md` containing only `@AGENTS.md` and an `AGENTS.md` with a codeword: a fresh `claude -p` session returned the codeword, so imports load. After the change, a fresh `claude -p` in the repo, told to use only its instructions, stated the branch/PR rule and listed the four roles with models. No fallback (sync check) was needed. Not tested: Codex itself (not installed here); it reads `AGENTS.md` by convention, and that file still contains everything it did before.
- T7: read both sections and the agent table against `AGENTS.md` and `.claude/agents/*.md` frontmatter and bodies.

## Notes

- The "no duplicated rule text" check is by inspection: `CLAUDE.md` has no rule text. Role text still appears in both `AGENTS.md` and `.claude/agents/*.md`; that was explicitly out of scope.
- Not run: backend or frontend suites (docs only).
