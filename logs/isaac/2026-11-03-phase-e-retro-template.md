# 2026-11-03 — Phase E: evaluate the workflow — isaac

Branch: `chore/workflow-cleanup-and-refactor`. Model: Claude Sonnet 5.5. Docs only.

## Commit

| Task | Commit message | Change |
|---|---|---|
| E1 | `docs: add a per-feature retro template (E1)` | New `workflow/templates/retro.md` with sections for revision rounds, defects (finder, blocking or not, round fixed), resource use (tracker run, tokens, cost, retries, resource-log row), RED-before-GREEN evidence (test commit and fix commit per criterion), steps done outside the pipeline, and what to change next time. One new row in the `workflow/README.md` index points to it. |

## How it was tested

- Read the template against the E1 list: every required item has a field. The resource-use section uses the same fields as the T12 handoff template.
- The index row is present in `workflow/README.md`. Nothing was run (docs only).

## Not done

- "The ADM-06 pilot produces a filled retro" cannot be met yet: ADM-06 has no spec or code. The template is in place before ADM-06 starts, as the order requires; the filled retro comes with the ADM-06 pilot.
