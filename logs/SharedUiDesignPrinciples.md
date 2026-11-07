# Shared UI design principles ? 2026-11-07

User liked the ADM-04 redesign and requested permanent reusable guidance for future screens/specs, with a local Git commit.

Created workflow/ui-design.md covering the accepted layout, input distinction, restrained theme tokens, spacing/type defaults, desktop/mobile/light/dark behavior, readable list/date/status hierarchy, accessible unread badges, private metadata polling/session lifecycle and the MUI fieldset-reset regression. Added a concrete screen-spec/plan checklist and source/reference examples; ignored screenshots are not permanent assets.

Linked the guide from workflow/README.md and both spec/plan templates. AGENTS.md now requires relevant screen work to read the guide; updated the spec-writer allowed-read list in AGENTS.md and its Claude definition so the rule is usable by both agents. Updated handoff/resource records. No application code, existing feature contract, dependencies, environment/database or user processes changed.

Validation: local Markdown links and required guide references checked, current spec suite checked and git diff whitespace checked. No runtime suites necessary for documentation-only maintenance. No delegated agents or explicit feature-workflow run; token/cost attribution unavailable. Commit locally only; no remote push or PR update.
