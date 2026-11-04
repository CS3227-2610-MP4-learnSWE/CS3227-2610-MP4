# Plan: CHK-01 Spec checker

Status: Approved by the user in chat (4 Nov 2026). Workflow tooling, not a product feature.

## Location and run
`workflow/tools/speccheck/` (package `speccheck`, own `README.md`, `tests/` with `unittest`), laid out like `workflow/tools/token-tracker/`. Run from that folder: `python -m speccheck ...` and `python -m unittest discover -s tests`. Python 3.12+, standard library only. The README states the waiver rule (only for specs that existed before the rule; never add a new spec) and has a section "Verifier only" listing what is not mechanically checkable.

## Data model
```python
@dataclass(frozen=True)
class Section:  heading: str; level: int; line: int; lines: list[tuple[int, str]]   # body lines (line number, text), heading excluded; includes sub-sections
@dataclass(frozen=True)
class Finding:  spec_id: str; file: str; heading: str; code: str; message: str; line: int = 0
@dataclass(frozen=True)
class Waiver:   spec_id: str; scope: str; reason: str       # scope is "all" or "added-items"
@dataclass(frozen=True)
class Rule:     id: str; tier: int; file: str; kind: str; where: str; groups: tuple; skip_no_screen: bool; skip_added_items: bool; source: str
class WaiverError(Exception): line: int; message: str
```
`Rule.kind` is `file`, `section`, `ac-item`, `task-role`, `table`, `item`. `Rule.where` is the heading name (for `item` rules: the heading to search, or `UI` meaning the "UI states and copy" section of `spec.md` plus the "UI contract" section of `plan.md`). `Rule.groups` (item rules only) is the matcher: a tuple of groups, groups are OR'd, regexes inside a group are AND'd, each regex is applied to the lowercased label.

Waiver file `speccheck-waivers.txt`: lines `<spec-id> | <scope> | <reason>`, split on `|` into exactly 3 non-empty trimmed fields (a reason may not contain `|`). Shipped at `workflow/specs/speccheck-waivers.txt`.

## Modules (one job each)
| Module | Job |
|---|---|
| `registry.py` | The rule table: `RULES: tuple[Rule, ...]`, one row per rule. Data only. |
| `parse.py` | Markdown to sections, tables, labelled entries, placeholder scan. No file access. |
| `rules.py` | `check_spec_dir`: reads the three files, walks `RULES`, returns findings. |
| `waivers.py` | `load_waivers`: parse and validate the waiver file. |
| `cli.py` | Argument parsing, folder discovery, `--list-rules`, output formatting, exit code. |
| `__main__.py` | Calls `cli.main(sys.argv[1:])` and exits with its result. |

## Rule registry (what the checker walks)
Source column names where the rule comes from. Tier 1 rules apply to every non-waived spec; "screen" rules are skipped by a No-screen declaration; "labelled" rules are skipped by waiver scope `added-items`.

| Rule id (code) | Tier | File | Where | Check | Skip no-screen | Skip added-items | Source |
|---|---|---|---|---|---|---|---|
| SPEC_MISSING | 1 | spec.md | file | exists | no | no | spec-writer: output spec.md |
| PLAN_MISSING | 1 | plan.md | file | exists | no | no | spec-writer: output plan.md |
| TASKS_MISSING | 1 | tasks.md | file | exists | no | no | spec-writer: output tasks.md |
| SECTION Goal | 1 | spec.md | Goal | section exists, non-empty | no | no | template spec.md |
| SECTION Behaviour | 1 | spec.md | Behaviour | same | no | no | template spec.md |
| SECTION Acceptance criteria | 1 | spec.md | Acceptance criteria | same, plus AC_ITEM_MISSING (needs a `- [ ] AC` item) | no | no | template spec.md |
| SECTION Out of scope | 1 | spec.md | Out of scope | same | no | no | template spec.md |
| SECTION Security and AI safeguards | 1 | spec.md | Security and AI safeguards | same | no | no | template spec.md |
| SECTION Open questions | 1 | spec.md | Open questions | same | no | no | template spec.md; role: flag ambiguities |
| SECTION Data model | 1 | plan.md | Data model | same | no | no | template plan.md |
| SECTION API endpoints | 1 | plan.md | API endpoints | same | no | no | template plan.md |
| SECTION Components and modules | 1 | plan.md | Components and modules | same | no | no | template plan.md |
| SECTION Test plan | 1 | plan.md | Test plan | same | no | no | template plan.md |
| TASKS_NO_ROLE | 1 | tasks.md | table rows or list items | one names an owner role | no | no | role: tasks tagged with owning role |
| NO_SCREEN | 1 | spec.md | line "No screen: reason" | reason non-empty | no | no | design decision |
| UI_SECTION_MISSING, UI_TABLE_EMPTY, UI_TABLE_CELL_EMPTY | 2 | spec.md | UI states and copy | heading, data rows, no empty cell | yes | no | role: UI states table |
| UI_CONTRACT_MISSING, UI_CONTRACT_EMPTY | 2 | plan.md | UI contract | heading, non-blank text | yes | no | role: plan UI contract |
| PLACEHOLDER | 1 and 2 | all | Tier 1 sections, screen sections, items, first heading line | no placeholder text | partly (screen sections only) | no | role: a state not written down is a guess |
| UI items (nine, below) | 2 | spec.md or plan.md | UI | labelled item | yes | yes | role: every visible state |
| Security items (two, below) | 2 | spec.md | Security and AI safeguards | labelled item | no | yes | template spec.md security note |

Item table (labels the spec-writer, the templates and the spec-writer text must use; matching is on the lowercased label text, before the first `:` or the first table cell; a label of 80 characters or more never matches):

| Item code | Matcher (AND within a group; groups OR'd) | Example label to write | Where searched | Source rule |
|---|---|---|---|---|
| REQUESTS | `requests` AND `per` AND `load\|retry` | Requests per load and per retry | UI | requests sent per load and per retry |
| WRONG_ROLE | `wrong[ -]role` | Wrong role | UI | what a wrong-role user sees |
| HISTORY | `push` AND `replace` ; or `^link history` | Link history: push or replace | UI | push versus replace for each link |
| REFRESH | `refresh` | Refresh | UI | what a user sees on refresh |
| BACK_FORWARD | `back` AND `forward` | Back and Forward | UI | Back and Forward |
| EXPIRED_SESSION | `expired session` ; or `logout` | Expired session or logout | UI | after logout or an expired session |
| BACKEND_DOWN | `backend down` | Backend down | UI | with the backend down |
| LONGEST_WAIT | `longest wait` ; or `timeout` | Longest wait before an error | UI | the longest time any screen waits before showing an error |
| NO_GENERIC_FAILURE | `generic` | No generic failure message | UI | no failure hides behind a generic message |
| CONCURRENT_REQUESTS | `concurrent` ; or `same time` | Concurrent requests (same time) | spec.md Security and AI safeguards | what must hold when two requests for the same record arrive at the same time |
| NORMALISATION | `normalis` | Normalisation | spec.md Security and AI safeguards | how identifiers and inputs are normalised |

"UI" means the "UI states and copy" section of `spec.md` or the "UI contract" section of `plan.md`; either place satisfies the item. Tooling or record-free specs write `Label: not applicable: reason`.

## Contract (importable)
- `speccheck.parse.sections(text: str) -> list[Section]`: ATX headings (1 to 6 `#`, then a space), outside fenced code blocks (lines starting with three backticks or `~~~` toggle a fence). A section runs from after its heading to the next heading of the same or higher level (sub-headings are inside it). Document order, one entry per heading. Heading key: text trimmed, lowercased, `**` and backticks removed, trailing punctuation (`. : ; , ! ?`) stripped.
- `speccheck.parse.find_section(secs: list[Section], name: str) -> Section | None`: first section whose key equals `name` lowercased.
- `speccheck.parse.tables(section: Section) -> list[Table]`; `Table(header: list[str], rows: list[tuple[int, list[str]]])`. A table is a run of consecutive lines starting with `|` whose second line is a separator row (every cell matches `:?-{1,}:?`). Cells split on `|` not preceded by a backslash, outer pipes dropped, trimmed. Data rows exclude header and separator; row numbers are 1-based among data rows.
- `speccheck.parse.placeholders(line: str) -> list[str]`: matched placeholder text in a line after removing backtick code spans. Case-insensitive: `\b(TBD|TODO|TBC|FIXME|XXX)\b`, the literal `???`, and `<[^<>\n]+>` (except `<br>`, `<br/>`). The caller skips fenced-block lines. `rules.py` passes a flag so that in `tasks.md` `TODO` is ignored.
- `speccheck.parse.labelled_entries(section: Section) -> list[Entry]`; `Entry(label: str, content: str, line: int)`. Forms: list item (`-`, `*`, `+`, `1.`), table data row (label = first cell; content = other cells joined with a space, trimmed), bold at line start (`**label**` or `**label:**`), heading (its text). Label = text before the first `:`, with `*`, backticks and list marker stripped. Content = text after the colon; if empty (and not a table row), the following non-blank lines up to a blank line or heading, joined with a space. A list item without `:` uses its whole text as label under the same rule. Sub-headings of the section are scanned.
- `speccheck.registry.RULES: tuple[Rule, ...]`.
- `speccheck.rules.check_spec_dir(path: Path, waivers: dict[str, Waiver]) -> list[Finding]`: spec id is `path.name`. Returns `[]` when waived with `all` (the CLI prints WAIVED); omits all ITEM_* findings (and their searches) when waived with `added-items`. Findings sorted by `(file, line, rule order)`; the CLI sorts across specs by spec id.
- `speccheck.waivers.load_waivers(path: Path) -> dict[str, Waiver]`: raises `WaiverError(line, message)` on malformed line (not three fields, empty field), unknown scope, or duplicate id. A missing file raises `FileNotFoundError` (the CLI decides). Blank lines and lines starting (after spaces) with `#` are ignored.
- `speccheck.cli.main(argv: list[str]) -> int`: returns the exit code; findings to stdout, usage and waiver errors to stderr.

Check order in `check_spec_dir`: missing-file checks; No-screen detection (first matching line in `spec.md` outside fences); Tier 1 section rules for spec.md, plan.md; `tasks.md` role rule; if a screen is declared absent (no valid No-screen line), the screen rules (UI section, table, contract); then the placeholder scan over Tier 1 sections, screen sections (if applicable), tasks.md, and each file's first heading line; then the item rules. PLACEHOLDER is one finding per line, naming the first match, `line` = file line. Item findings: UI items on `plan.md`, heading "UI contract" (heading `(file)` if that section is missing); security items on `spec.md`, heading "Security and AI safeguards" (`(file)` if missing). Items are reported in registry order. Items are searched only in their "where" sections.

## CLI
`python -m speccheck [--specs-dir PATH] [--waivers FILE] (--all | --list-rules | SPEC_DIR...)`.
- Default specs dir: `Path(__file__).resolve().parents[3] / "specs"` (`cli.py` is at `workflow/tools/speccheck/speccheck/cli.py`, so `parents[3]` is `workflow`).
- Explicit `SPEC_DIR` arguments are used as given (spec id = folder name). `--all`: every direct subfolder of the specs dir, sorted by name.
- Waivers: default `<specs-dir>/speccheck-waivers.txt`; if absent and not given explicitly, no waivers. An explicit missing `--waivers` file is a usage error.
- WAIVER_UNKNOWN_ID warning: a waiver id that matches no subfolder of the specs dir. Only under `--all`.
- Counting: `checked` = spec folders examined and not waived with `all`; `failed` = checked folders with at least one finding; `waived` = folders waived with `all`. A folder waived `added-items` counts as checked.
- `--list-rules` combined with folders or `--all` is a usage error.

## Output contract
Stdout, one line each: per-spec lines sorted by spec id (FAIL lines sorted by file then order in file, or `OK`, or `WAIVED`), then warnings, then the summary.

| Line | Format |
|---|---|
| Finding | `FAIL <spec-id> <file>: section "<heading>": <message> [<CODE>]` (`<file>` is `spec.md`, `plan.md` or `tasks.md`; `<heading>` is the section's original heading text, or `(file)` for whole-file problems) |
| Waived | `WAIVED <spec-id> (<scope>): <reason>` (for `added-items` it is followed by the spec's normal FAIL or OK lines) |
| Pass | `OK <spec-id>` |
| Warning | `WARN <spec-id>: waiver for a spec folder that does not exist [WAIVER_UNKNOWN_ID]` |
| Summary | `speccheck: <n> checked, <f> failed, <w> waived` |
| Rule listing (`--list-rules`) | `RULE <id> tier=<1 or 2> file=<file> where="<where>" skip_no_screen=<yes or no> skip_added_items=<yes or no> source="<source>"`, one per registry row, registry order |
| Usage error (stderr, exit 2) | `speccheck: error: <text>` |
| Waiver error (stderr, exit 2) | `speccheck: error: <waiver file>: line <n>: <text> [WAIVER_BAD_LINE]` |

Messages and codes. Tests should assert the code, the spec id, the file and key words, not the full prose.

| Code | File, heading | Message |
|---|---|---|
| SPEC_MISSING | `spec.md`, `(file)` | `spec.md not found` |
| PLAN_MISSING | `plan.md`, `(file)` | `plan.md not found` |
| TASKS_MISSING | `tasks.md`, `(file)` | `tasks.md not found` |
| SECTION_MISSING | the file, `(file)` | `no "<section>" section` |
| SECTION_EMPTY | the file, the section | `section has no text` |
| AC_ITEM_MISSING | `spec.md`, `Acceptance criteria` | `section has no "- [ ] AC" checklist item` |
| TASKS_NO_ROLE | `tasks.md`, `(file)` | `no table row or list item names an owner role (accepted: developer, test-designer, verifier, spec-writer, orchestrator, human, session, user)` |
| NO_SCREEN_REASON_EMPTY | `spec.md`, `(file)` | `line <n>: "No screen" has no reason after the colon` |
| UI_SECTION_MISSING | `spec.md`, `(file)` | `no "UI states and copy" section and no "No screen: reason" line` |
| UI_TABLE_EMPTY | `spec.md`, `UI states and copy` | `section has no table data rows` |
| UI_TABLE_CELL_EMPTY | `spec.md`, `UI states and copy` | `row <n>, column "<header>" is empty` |
| PLACEHOLDER | file and section where found (`(file)` for a No-screen reason or a first heading line) | `line <n>: placeholder text "<match>"` |
| UI_CONTRACT_MISSING | `plan.md`, `(file)` | `no "UI contract" section` |
| UI_CONTRACT_EMPTY | `plan.md`, `UI contract` | `section has no text` |
| ITEM_MISSING | see check order | `item <NAME> missing; accepted labels: <labels>` |
| ITEM_EMPTY | see check order | `item <NAME> has a label but no content` |
| WAIVER_BAD_LINE | stderr only | `line <n>: <reason>`; reasons: `expected "spec-id \| scope \| reason"`, `unknown scope "<s>"`, `duplicate id "<id>"` |
| WAIVER_UNKNOWN_ID | warning | see Warning row |

`<NAME>` is an item code from the item table. `<labels>` text is `a label with` the matcher words joined as in the item table, then `, e.g. "<example label>"`; for example for REQUESTS: `a label with "requests", "per" and "load" or "retry", e.g. "Requests per load and per retry"`. The example label is the "Example label to write" column.

Exit codes: 0 no FAIL lines; 1 at least one FAIL line; 2 usage or waiver error (only the stderr line is printed).

## UI contract
No screen: command-line tool, output contract in plan.md

## API endpoints
Not applicable: command-line tool with no HTTP endpoints; the CLI and output contract are above.

## Components and modules
New: the six modules above. Reused: none (standard library only). Changed files outside the tool: `.github/workflows/ci.yml` (new job `spec-check`: checkout, setup-python 3.12, `python -m unittest discover -s tests` and `python -m speccheck --all` run in `workflow/tools/speccheck`, path-filtered to `workflow/specs/**` and `workflow/tools/speccheck/**`, `contents: read`, blocking); `workflow/coordination.md` ("Spec check gate" subsection); `workflow/specs/speccheck-waivers.txt` (new); `workflow/README.md` index line.

## AI usage
None.

## Test plan
Tests build synthetic spec folders in temporary directories (a helper writes a complete passing spec, plan and tasks, then each test breaks one thing); the only repo-level tests are the two on this repo. One test file per module (`test_parse.py`, `test_registry.py`, `test_rules.py`, `test_waivers.py`, `test_cli.py`), each test named with `chk01` and the AC number (for example `test_chk01_ac1_placeholder_tbd`).

| AC | Test |
|---|---|
| AC1 | `placeholders()` and `check_spec_dir`: each word, `???`, a slot; negatives (backticks, fence, "TODOS", `todo` status in tasks.md, slot in the first heading) |
| AC2, AC3, AC4 | rules: no heading, header-only table, empty cell (row and column named), "not applicable", contract missing and empty |
| AC5, AC6, AC7 | for every UI item: missing, empty, placeholder, ok; each label form; spec-only, plan-only, wrong heading; case; 80-character label |
| AC8 | both security items: missing, empty, "not applicable: reason", wrong section, No-screen spec |
| AC9 | No-screen forms; empty and placeholder reason; Tier 1 and security items still enforced |
| AC10, AC11, AC12, AC13 | missing files; each Tier 1 section missing and empty; "none" in Open questions; no AC item; optional Decisions; role words |
| AC14, AC15 | waivers module and CLI: both scopes, bad lines (line number), unknown ID warning |
| AC16, AC17, AC18 | CLI via `main(argv)` with captured output: `--all`, overrides, exit codes, line formats, sorting, summary |
| AC19, AC20 | `--list-rules` lines and ids; README contains a "Verifier only" heading |
| AC21, AC22 | repo-level: `main` on `workflow/specs/CHK-01`, and `--all` on the real specs dir |
| AC23 | binary bytes, 5 MB file, invalid UTF-8; no files created in the temp dir |
| AC24 | fenced heading ignored; sub-headings belong to the parent |

Security: spec text containing shell-like or Python-like content is only read (assert no side effects); a path argument that is a file, or missing, exits 2.

## Decisions
- Presence only: the checker cannot judge quality, so the verifier still reads every spec (README "Verifier only" list).
- Rules are data in `registry.py`, so adding a rule is a one-row change and `--list-rules` always matches behaviour.
- Explicit waiver file over dates, so grandfathering is visible in review.
- Placeholder words are ignored inside backticks and fences so specs can quote them; `todo` is a valid status in `tasks.md`.
- UI items may live in the spec or the plan, since spec-writers already split copy between the two; security items are in the spec only.
