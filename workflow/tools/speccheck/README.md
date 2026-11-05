# Spec checker

Checks that a feature's `spec.md`, `plan.md` and `tasks.md` contain what the spec-writer role must produce: required sections, a filled "UI states and copy" table and "UI contract" for a spec with a screen, and the labelled items listed below. It tests presence and non-placeholder text only, never quality or meaning. Python 3.12+, standard library only. Not product code. It reads files and writes nothing; it never runs spec content. Spec, plan and tasks: `workflow/specs/CHK-01/`.

## Run (from this folder)

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location workflow\tools\speccheck
python -m speccheck ..\..\specs\CHK-01
python -m speccheck --all
python -m speccheck --list-rules
```

Give the spec folder as an explicit path, not `.`: from inside a folder link the operating system reports the link target's name, so `.` can be checked (or waived) under the wrong id. Folder links named on the command line are not followed.

Options: `--specs-dir PATH` (default: `workflow/specs` of the repo that holds this tool), `--waivers FILE` (default: `<specs-dir>/speccheck-waivers.txt`; a missing default file means no waivers, a missing explicit file is an error). `--all` checks every subfolder of the specs dir. `--list-rules` prints one `RULE` line per row of the rule table in `speccheck/registry.py` and cannot be combined with folders or `--all`.

Output is plain text: one `FAIL <spec-id> <file>: section "<heading>": <message> [<CODE>]` line per finding (or `OK <spec-id>`, or `WAIVED <spec-id> (<scope>): <reason>`), then `WARN` lines, then `speccheck: <n> checked, <f> failed, <w> waived`.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | All specs pass or are waived. |
| 1 | At least one finding. |
| 2 | Usage error (no arguments, `--all` with folders, unknown option, folder that does not exist) or waiver-file error (`WAIVER_BAD_LINE` with the line number on stderr). |

## Waivers

`workflow/specs/speccheck-waivers.txt` lists specs that existed before this check, one per line: `<spec-id> | <scope> | <reason>`. Blank lines and `#` comments are allowed. Scopes:

- `all`: skip every check for that spec and print `WAIVED`.
- `added-items`: skip only the labelled items (the eleven below); every other rule stays.

Rule: a waiver is only for a spec that existed before the rule. Never add a new spec to the file; reviewers check the diff. A waiver for a folder that does not exist gives `WARN ... [WAIVER_UNKNOWN_ID]` under `--all` and does not change the exit code.

## Item labels

Each item needs a labelled entry (a list item, a table first cell, bold text or a heading). The label is the text before the first `:` (or the first table cell); matching ignores case and a label of more than 80 characters never matches. Content is the rest of the line, or the following lines up to a blank line or heading (at most 20 lines per label and 100,000 per section). Write `Label: not applicable: reason` when an item does not apply. The first nine are searched in the spec's "UI states and copy" section or the plan's "UI contract" section (screen specs only; a `No screen: reason` line in `spec.md` skips them); the last two in the spec's "Security and AI safeguards" section (every spec).

| Item code | Example label to write | Label must contain |
|---|---|---|
| REQUESTS | Requests per load and per retry | "requests", "per" and "load" or "retry" |
| WRONG_ROLE | Wrong role | "wrong role" or "wrong-role" |
| HISTORY | Link history: push or replace | "push" and "replace", or start with "link history" |
| REFRESH | Refresh | "refresh" |
| BACK_FORWARD | Back and Forward | "back" and "forward" |
| EXPIRED_SESSION | Expired session or logout | "expired session" or "logout" |
| BACKEND_DOWN | Backend down | "backend down" |
| LONGEST_WAIT | Longest wait before an error | "longest wait" or "timeout" |
| NO_GENERIC_FAILURE | No generic failure message | "generic" |
| CONCURRENT_REQUESTS | Concurrent requests (same time) | "concurrent" or "same time" |
| NORMALISATION | Normalisation | "normalise" or "normalize" |

## Verifier only

The checker cannot judge these; the verifier still reads every spec:

- Quality of the spec and plan, and whether a stated behaviour is sensible.
- That the acceptance criteria are actually copied from the user stories.
- Completeness of the contract (every path, schema, signature and error code is present and consistent).
- That the `notes.md` handoff entry exists.
- That the content of each label is correct (the checker sees that "Refresh" has text, not that the text is right).
- A required section that holds only a sub-heading or an empty code fence still passes.
- Template guidance sentences and an HTML-comment item count as content.
- One label can satisfy several items (for example "Back and Forward, refresh").
- A `No screen:` line anywhere in `spec.md` disables the screen rules.
- Code fences are a simple toggle (three backticks or `~~~`), not full CommonMark.
- Comparisons such as `a < b and c > d` and `<https://...>` look like placeholders; put them in backticks.

## Measurement

Idea only, not built: to compare the effect of the check on spec gaps, classify each first-run integration failure per feature as UI-detail (a visible state, label, count or history behaviour the spec did not state), other contract (paths, schemas, codes), logic bug or test bug, and record the four counts in the feature's first-run results file. An example of such a file is `workflow/experiments/results/stu01-first-run.md`, which exists on branch `feat/stu01-spec` and is not yet in `master`.

## Tests

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location workflow\tools\speccheck
python -m unittest discover -s tests
```
