# Workflow scaffolding summary — 28–29 October 2026

## User direction

The user asked for a review of the existing app shell, then to set up spec-driven, multi-agent scaffolding on a separate branch before project work, using the assignment brief (MP4 requirements) as the structure. Claude Code was used for this session. All changes go to `master` by pull request only.

## What was discussed and decided

- **Multi-agent design.** The first draft was a five-role sequential pipeline written without discussion. The user questioned it because of token cost. After discussion, the design became a generator-verifier pattern with an independent test designer that works in parallel with the developer, from the spec and plan contract only, without reading `src/`.
- **Variants to compare.** Variant A: developer, test-designer, reviewer, security-reviewer (split verification, the default in `.claude/agents/`). Variant B: developer, test-designer and one verifier combining code and security review (merged verification). Baseline: a single session, still spec-first and tests-first. The spec-writer step is shared and excluded from the comparison, so the spec is written and approved once per experiment task. Revision loops are capped at 2 rounds.
- **Why a plan contract.** Parallel isolated agents can disagree on names and shapes, so `plan.md` must fix endpoint paths, schemas, signatures and error codes.
- **Evaluation approach.** Judge cost per accepted outcome rather than tokens alone: tokens, rework rounds, defects found, a fixed quality rubric and the user's review time. Results will be single runs, so they are anecdotal, not statistical.
- **Experiments.** Run on separate branches cut from the same `master` commit, not merged; only results are copied into `workflow/experiments/`.
- **Codex.** `AGENTS.md` mirrors `CLAUDE.md` and the agent roles for Codex. Whether Codex reads it was not tested.

## Token-tracking findings

Both tools write local session logs with token usage. Claude Code: `~/.claude/projects/<project>/<session>.jsonl`, with per-message `usage` (input, output, cache read and creation tokens). The same message appears multiple times (63 usage lines for 22 distinct message ids in one session), so a tracker must dedupe by message id. Codex: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`, with `token_count` events carrying input, cached, output and reasoning tokens plus rate-limit percentages. Only field names were inspected; no conversation content was read or stored. The tracker itself is not built yet, and where Codex records the model name is unconfirmed.

## Changes made

Added `CLAUDE.md`, `AGENTS.md`, five agent definitions, `workflow/` (coordination, variants, templates, experiment and security logs, checklist, notes), `docs/Reflections.md` skeleton, and a workflow-files table in `docs/DeveloperGuide.md`. Merged the latest `master` (floating study companion and MCQ-only practice) into the branch with no conflicts. Opened PR 1.

## Verification and corrections

Backend pytest (3), typecheck, lint and build passed on the merged branch. Playwright: 17 passed, 1 timed out at the default 30s (the layout matrix test, about 1.3 minutes on this machine) and passed with a longer timeout. Prettier flagged files only due to local CRLF line endings. No application code was changed by this work.

Corrections during the session: the first role drafts lacked the generator-verifier loop (the "verifier" was initially just the test runner); the Git section first said "merge to master" and was corrected to PR-only; the spec-writer was moved out of the comparison to avoid confounding.

## Not done

No experiments, token tracker, CI/CD, hosting decision, security tests or team role assignments yet. The agent isolation rules are written instructions and are not enforced. This summary was written by the AI from the session and should be checked by a team member.
