# Spec: CHK-01 Spec checker

Status: Approved by the user in chat (4 Nov 2026), full table-driven scope

Workflow tooling, not a product feature and not in `docs/FeatureList.md`. Standard library only.

## Goal
Enforce every presence rule of the spec-writer role mechanically before the build phase starts: required sections in `spec.md`, `plan.md` and `tasks.md`; for a spec with a screen, a filled "UI states and copy" table, a "UI contract" section, and the labelled items the role requires. The checker tests presence and non-placeholder text only, never quality or meaning. What it cannot check is listed in its README as "verifier only".

## Approved decisions (fixed by the user; do not reopen)
- Scope is FULL: every presence rule the spec-writer role asks for is enforced.
- CLI: `python -m speccheck <spec-dir>...` checks the given folders; `--all` checks every subfolder of the specs dir; `--specs-dir PATH` (default: `workflow/specs` of the repo that contains the package); `--waivers FILE` (default: `<specs-dir>/speccheck-waivers.txt`); `--list-rules` prints the rule table.
- Exit codes: 0 all pass, 1 at least one finding, 2 usage or waiver-file error.
- Rules live in a table-driven registry (`speccheck/registry.py`, one row per rule); the checker walks the registry.
- Waiver scopes are exactly two: `all` and `added-items` (every labelled item; the section and table rules stay).
- Grandfathering is by an explicit, visible waiver file, not by dates (git dates are unreliable in shallow CI checkouts). Waivers are only for specs that existed before this rule; a new spec must not be added to the file, and reviewers check the diff.

## Behaviour
For each spec folder (the folder name is the spec id) that is not waived with scope `all`, the checker applies the registry rules. Exact codes and messages are in `plan.md`.

1. Files: `spec.md`, `plan.md`, `tasks.md` must exist (SPEC_MISSING, PLAN_MISSING, TASKS_MISSING). Checks that need a missing file are skipped.
2. Tier 1 (every spec, including No-screen specs): each required section exists, has non-blank text, and has no placeholder (SECTION_MISSING, SECTION_EMPTY, PLACEHOLDER).
   - `spec.md`: Goal, Behaviour, Acceptance criteria (also needs at least one checklist item starting `- [ ] AC`, else AC_ITEM_MISSING), Out of scope, Security and AI safeguards, Open questions (text such as "none" is accepted).
   - `plan.md`: Data model, API endpoints, Components and modules, Test plan. "Decisions" is optional (checked for placeholders only if present).
   - `tasks.md`: at least one table data row or list item names an owner role (developer, test-designer, verifier, spec-writer, orchestrator, human, session, user), else TASKS_NO_ROLE.
   - "not applicable" with a reason is accepted for a section that does not apply (for example API endpoints of a command-line tool).
3. No-screen declaration: a line in `spec.md` that starts with "No screen" (case-insensitive, optionally after a list marker or bold) followed by `:` and a reason. A non-empty, non-placeholder reason skips every screen rule (rule 4 and the UI items of rule 5). Tier 1 and the two security items still apply. Empty reason: NO_SCREEN_REASON_EMPTY. Placeholder reason: PLACEHOLDER. A "No screen" line without a colon is not a declaration.
4. Screen rules (spec with a screen): UI_SECTION_MISSING (no heading "UI states and copy" in `spec.md`); UI_TABLE_EMPTY (no table data rows; header and separator rows do not count); UI_TABLE_CELL_EMPTY (a data row has an empty cell; names row number and column header; "not applicable" counts as content); UI_CONTRACT_MISSING (`plan.md` has no heading "UI contract"); UI_CONTRACT_EMPTY (no non-blank text).
5. Labelled items. An item is a labelled entry whose label text (before the first `:`, or the first table cell) matches the item's matcher, case-insensitively. A label is a list item, the first cell of a table row, bold text, or a heading. Content is the text after the label on the same line or row; if empty, the following non-blank lines up to a blank line or heading. No entry: ITEM_MISSING (names the item and accepted labels). Entry with no content: ITEM_EMPTY. Placeholder content: reported once as PLACEHOLDER by the section scan. "not applicable" with a reason is accepted content. A label longer than 80 characters never matches.
   - UI items (screen specs only): REQUESTS, WRONG_ROLE, HISTORY, REFRESH, BACK_FORWARD, EXPIRED_SESSION, BACKEND_DOWN, LONGEST_WAIT, NO_GENERIC_FAILURE. Found in either the "UI states and copy" section of `spec.md` or the "UI contract" section of `plan.md`.
   - Security items (every spec): CONCURRENT_REQUESTS and NORMALISATION, found in the "Security and AI safeguards" section of `spec.md`. Tooling specs write "not applicable: reason".
6. Placeholders: a word-bounded `TBD`, `TODO`, `TBC`, `FIXME`, `XXX`, the string `???`, or an unfilled angle-bracket template slot (case-insensitive) in a Tier 1 section, a screen section, an item, a No-screen reason, or the first heading line of a file gives PLACEHOLDER naming the text. Backtick code spans and fenced code blocks are ignored, so a spec can quote such words. In `tasks.md` the word `todo` is a valid status and is not a placeholder.
7. Waivers: lines `<spec-id> | <scope> | <reason>`; blank lines and `#` comments allowed. Scope `all`: skip every check and print WAIVED. Scope `added-items`: skip every labelled item (rule 5), keep all other rules. Reason required. Malformed line, unknown scope, or duplicate id: exit 2 with WAIVER_BAD_LINE naming the line number. A waiver for a folder that does not exist: warning WAIVER_UNKNOWN_ID (under `--all`), not a failure.
8. `--list-rules` prints one line per registry rule (format in `plan.md`) and exits 0.
9. Output is plain text, one finding per line, then a summary line. Findings are sorted by spec id, then file, then order in the file.

## UI states and copy
No screen: command-line tool, output contract in plan.md

## Acceptance criteria
- [ ] AC1: Placeholder detection: each of `TBD`, `TODO`, `TBC`, `FIXME`, `XXX`, `???` and an angle-bracket slot (any case) in a cell, section line, item content or No-screen reason gives PLACEHOLDER naming the text and line; the same words in backticks, in a fenced block, or inside a longer word (for example "TODOS") give none; in `tasks.md` a status of `todo` gives none; an unfilled angle-bracket slot in the first heading line of a file gives PLACEHOLDER.
- [ ] AC2: A spec with a screen and no "UI states and copy" heading gives UI_SECTION_MISSING; a section with only a header and separator row gives UI_TABLE_EMPTY.
- [ ] AC3: A data row with an empty cell gives UI_TABLE_CELL_EMPTY naming the row number and column header; a cell reading "not applicable" passes.
- [ ] AC4: A plan with no "UI contract" heading gives UI_CONTRACT_MISSING; a heading with no text under it gives UI_CONTRACT_EMPTY.
- [ ] AC5: For each UI item (REQUESTS, WRONG_ROLE, HISTORY, REFRESH, BACK_FORWARD, EXPIRED_SESSION, BACKEND_DOWN, LONGEST_WAIT, NO_GENERIC_FAILURE): no label gives ITEM_MISSING naming the item and the accepted labels; a label with no content gives ITEM_EMPTY; a label with placeholder content gives PLACEHOLDER; a label with content passes.
- [ ] AC6: Each UI item passes when placed only in the spec's "UI states and copy" section, or only in the plan's "UI contract" section; it fails when placed in neither (for example under another heading).
- [ ] AC7: Labels are accepted as a list item, a table first cell, bold text and a heading; content may follow on the same line or on the next non-blank lines up to a blank line or heading; matching is case-insensitive; "wrong-role" and "wrong role" both match; a label over 80 characters does not match.
- [ ] AC8: CONCURRENT_REQUESTS and NORMALISATION are required in the "Security and AI safeguards" section of every non-waived spec, including No-screen specs: missing gives ITEM_MISSING, no content gives ITEM_EMPTY, "not applicable: reason" passes; an entry placed outside that section does not satisfy them.
- [ ] AC9: A spec with a "No screen" line (plain, in a list, or bold) and a reason skips the UI section, UI contract and UI items but still gets Tier 1 and the security items; an empty reason gives NO_SCREEN_REASON_EMPTY; a placeholder reason gives PLACEHOLDER.
- [ ] AC10: Missing `spec.md`, `plan.md` or `tasks.md` gives SPEC_MISSING, PLAN_MISSING or TASKS_MISSING naming the spec id.
- [ ] AC11: For each required `spec.md` section (Goal, Behaviour, Acceptance criteria, Out of scope, Security and AI safeguards, Open questions): absent gives SECTION_MISSING naming it; heading with no text gives SECTION_EMPTY; text such as "none" passes; Acceptance criteria without a `- [ ] AC` item gives AC_ITEM_MISSING; headings match case-insensitively at any level.
- [ ] AC12: For each required `plan.md` section (Data model, API endpoints, Components and modules, Test plan): absent gives SECTION_MISSING, empty gives SECTION_EMPTY, "not applicable: reason" passes; a missing "Decisions" section gives nothing, but a placeholder in a present one gives PLACEHOLDER.
- [ ] AC13: `tasks.md` with no table row or list item naming one of the accepted owner roles gives TASKS_NO_ROLE; a row naming any one of them passes; role words match whole words, case-insensitively.
- [ ] AC14: Waiver scope `all` prints WAIVED with scope and reason and produces no findings for that spec; scope `added-items` still reports Tier 1, table and contract findings but no ITEM_* findings (UI or security).
- [ ] AC15: A malformed waiver line, unknown scope, empty reason, or duplicate id exits 2 and stderr names WAIVER_BAD_LINE and the line number; comments and blank lines are ignored; a waiver for a non-existent folder under `--all` prints WARN WAIVER_UNKNOWN_ID and does not change the exit code.
- [ ] AC16: `--all` checks every subfolder of the specs dir (ignoring plain files such as `README.md` and the waiver file); `--specs-dir` and `--waivers` override the defaults; a missing default waiver file means no waivers, a missing explicit one exits 2.
- [ ] AC17: Exit code is 0 when all specs pass or are waived, 1 when any finding exists, 2 for usage errors (no arguments, `--all` combined with folders, unknown option, folder that does not exist) and waiver-file errors.
- [ ] AC18: Output lines follow the exact formats in `plan.md`, findings are sorted by spec id, file, then order in file, and the last line is `speccheck: <n> checked, <f> failed, <w> waived`.
- [ ] AC19: `--list-rules` exits 0 and prints one `RULE` line per registry row in the format in `plan.md`, with every rule id and item code named in this spec present.
- [ ] AC20: The README of the tool has a section "Verifier only" naming what the checker cannot check (quality, acceptance criteria matching the user stories, completeness of the contract, accuracy of copy, whether a stated behaviour is sensible).
- [ ] AC21: `python -m speccheck workflow/specs/CHK-01` passes (the checker passes its own spec).
- [ ] AC22: `python -m speccheck --all` run on this repo with the shipped `workflow/specs/speccheck-waivers.txt` exits 0, and every waiver in that file is for a spec that predates this rule (CHK-01 is not listed).
- [ ] AC23: Binary, very large (5 MB), or non-UTF-8 files do not crash the checker (read as UTF-8 with errors replaced); the checker writes no files, opens no network connection, and never executes spec content.
- [ ] AC24: Headings inside fenced code blocks are not headings; a section runs to the next heading of the same or higher level, so sub-headings belong to their parent section.

## Integration
- CI: a job in `.github/workflows/ci.yml` runs `python -m speccheck --all` and the tool's unit tests (`python -m unittest discover -s tests`, run from `workflow/tools/speccheck/`) on pull requests that change `workflow/specs/**` or `workflow/tools/speccheck/**`. Blocking. Read-only permissions as in CI-01.
- `workflow/coordination.md` gets a short "Spec check gate" subsection: the build phase (test-designer and developer) starts only after `speccheck` passes for the feature's spec folder.
- The verifier's handoff line records that the check passed (or the waiver in force).

## Measurement (idea only)
To compare the effect of the check on first-run spec-gap failures per feature, classify each first-run integration failure as one of: UI-detail (a visible state, label, count or history behaviour the spec did not state), other contract (paths, schemas, codes), logic bug, or test bug. Each feature's own first-run results file records the four counts. This spec does not build that tooling.

## Out of scope
Judging quality or meaning of a spec; fixing specs; checking the content of `tasks.md` beyond one owner role; checking STU-/TEA- code; editing templates, user stories, agent definitions or `docs/`; date-based grandfathering; a third waiver scope.

## Security and AI safeguards
- Read-only: reads files under the given folders and the waiver file; writes nothing; no network; never imports, evaluates or executes spec content.
- Files are read as UTF-8 with errors replaced; a huge or binary file yields findings or OK, never a crash.
- Regexes avoid catastrophic backtracking (linear patterns, no nested quantifiers).
- No AI or LLM call.
- Concurrent requests (same time): not applicable: the tool stores no records and runs are independent and idempotent; the same input gives byte-identical output.
- Normalisation: spec ids are folder names compared exactly (case-sensitive); waiver fields are trimmed of whitespace; headings and labels are compared case-insensitively after trimming and stripping trailing punctuation.

## Open questions
1. The item labels are fixed here (table in `plan.md`). The STU-01 branch's templates and spec-writer text must use the same labels, or its specs will fail.
2. STU-01 specs will be enforced when merged. They must comply; waivers are only for specs that existed before this rule.
3. Which existing specs need `all` and which `added-items` is decided by running the checker; the developer records the result in the waiver file with reasons. Most older specs lack the new items, so expect many `added-items` waivers and some `all`.
4. The code for the refresh item is REFRESH (not REFRESH_BACK) to avoid confusion with BACK_FORWARD; confirm.
