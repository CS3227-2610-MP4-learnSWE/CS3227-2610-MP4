# Plan: TRK-03 Per-invocation usage from Claude Code and Codex logs

Status: Original contract approved by user in chat (2026-11-05); Codex run-report and mandatory workflow attribution follow-up approved by the user's request (2026-11-06).

All paths are under `workflow/tools/token-tracker/` unless stated. Python 3.12+, standard library only. Metric formulas are in `spec.md` ("Metric definitions"); this plan fixes names, shapes, texts and layouts. The test-designer and developer both rely only on this contract.

## Data model

### Value conventions (used by every row dict and renderer)
- A row is a `dict[str, object]` keyed by CSV column name. Value `None` = blank (not applicable). Value `UNAVAILABLE` (the string `"unavailable"`, constant in `tracker/invocation_metrics.py`) = data missing. `int` for counts and tokens, `float` for durations, ratios, means and USD, `str` otherwise. Timestamps are `str` already formatted by `timeutil.format_utc` (`2026-10-29T01:00:00.123Z`, UTC, milliseconds).
- `format_value(column, value)`: `None` gives empty text; `UNAVAILABLE` gives `unavailable`; an `int` gives `str(value)`; a `float` gives `format(value, spec)` where spec is `.1f` for `elapsed_s, active_s, tool_time_s, wait_before_start_s, context_mean`; `.4f` for `reasoning_share, cache_hit_ratio`; `.6f` for `cost_usd, cost_input, cost_cache_read, cost_cache_write_5m, cost_cache_write_1h, cost_output`. Python round-half-even on the binary float, no thousands separators. A column whose value is an `int` is never given a decimal point (for example a cost of integer 0 from an empty sum is converted with `float()` first by the producer).
- `prices.json` extension (backward compatible). A model entry is either flat (unchanged: keys `input, cache_read, cache_write_5m, cache_write_1h, output`, USD per million tokens) or tiered:

```json
"claude-haiku-5-5": {
  "match_variants": true,
  "as_of": "2026-11-05",
  "source": "Provider pricing page (user-supplied screenshot, 2026-11-05); per-request tiers by prompt size (input + cache read + cache write 5m + cache write 1h); the tier rule is an unverified assumption",
  "tiers": [
    {"max_prompt_tokens": 100000, "input": 0.10, "cache_write_5m": 0.125, "cache_write_1h": 0.20, "cache_read": 0.01, "output": 0.50},
    {"input": 0.50, "cache_write_5m": 0.625, "cache_write_1h": 1.00, "cache_read": 0.05, "output": 2.50}
  ]
}
```
  Rules: `tiers` must be a non-empty list of objects; a tier applies to a request when `max_prompt_tokens` is absent or the prompt size is less than or equal to it; the first applicable tier in list order is used; a tier lists the five price keys like a flat entry; if `tiers` is present, flat keys on the same entry are ignored. A malformed `tiers` (not a list, empty, an element that is not an object, a `max_prompt_tokens` that is not an int) or no applicable tier gives no price (`None`). Per-model `as_of` and `source` are optional documentation keys inside an entry. Model lookup (new function `pricing.resolve_model_prices(prices: dict, model: str) -> dict | None`, used by `cost_breakdown`): (1) an exact key match wins; (2) otherwise among entries with `"match_variants": true` (the value must be the JSON `true`), the longest key `K` such that `model.startswith(K)` and `len(model) > len(K)` and `model[len(K)]` is not an ASCII letter or digit; (3) otherwise `None`. Only the Haiku entry carries `match_variants`, so Sonnet and Opus stay exact-match and no historical result changes. Examples: `claude-haiku-5-5-20261105` and `claude-haiku-5-5[1m]` resolve to Haiku; `claude-haiku-5-50`, `claude-haiku-5-5x`, `claude-haiku-4-5`, `anthropic.claude-haiku-5-5`, `claude-sonnet-5-5-20261105` do not resolve. The top-level `as_of` (`2026-10-29`) and `source` stay as they are and keep meaning "for models that have no `as_of`/`source` of their own"; Sonnet 5.5 and Opus 5.5 entries are not edited.
- `UsageRow` gets one read-only property in `tracker/model.py`: `prompt_tokens -> int` = `input_tokens + cache_read_tokens + cache_write_5m_tokens + cache_write_1h_tokens`. No field is added or changed (`COLUMNS` and `as_csv_dict` unchanged).

### Dataclasses
```python
# tracker/log_session.py
@dataclass(frozen=True)
class RequestInfo:
    row: UsageRow                 # unpriced (cost_usd None), from claude_logs.row_from_line
    order: int                    # line index where this message id first appeared in its file
    requested_model: str          # top-level requestedModel of the kept line, "" if absent
    reasoning_reported: bool      # kept line has output_tokens_details.thinking_tokens as an int

@dataclass(frozen=True)
class ToolCallInfo:
    tool_use_id: str
    name: str
    use_time: datetime | None     # time of the first line holding this tool_use
    result_time: datetime | None  # time of the first user line with a tool_result for this id
    is_error: bool                # any matching tool_result block has is_error is True
    read_path: str | None         # normalised path when name == "Read" and input.file_path is a non-empty str

@dataclass(frozen=True)
class WindowLog:                  # one prompt (subagent) or the whole file (main session)
    requests: tuple[RequestInfo, ...]      # sorted by order
    tool_calls: tuple[ToolCallInfo, ...]   # sorted by first appearance
    first_time: datetime | None            # earliest line time in the window
    last_time: datetime | None             # latest line time in the window
    human_messages: int

@dataclass(frozen=True)
class FileLog:
    path: Path
    agent_id: str                 # "" for the main file; for agent-X.jsonl it is X
    meta: dict | None             # claude_logs.agent_meta(path) for subagent files, None for main
    windows: tuple[WindowLog, ...]         # one per prompt, in file order; the main file has exactly one
    agent_calls: Mapping[str, str | None]  # tool_use id -> subagent_type, for tool_use blocks named "Agent"; the value is the input.subagent_type text only if it passes ^[A-Za-z0-9._:-]{1,64}$, else None. No other input field is kept

# tracker/invocations.py
@dataclass(frozen=True)
class InvocationRecord:
    invocation_id: str
    run_id: str
    role: str
    session_id: str
    agent_id: str                 # "" for orchestrator
    prompt_number: int | None     # 1-based for subagents, None for orchestrator
    launched_by: str | None       # orchestrator invocation id; None for a subagent means no Agent call matched (rendered "unavailable"); None for the orchestrator (agent_id "") is rendered blank
    requested_agent_type: str | None   # subagent_type of the matching Agent call; same None rules as launched_by
    window: WindowLog
    rows: tuple[UsageRow, ...]    # priced (cost_usd set via pricing.cost_usd), in request order

@dataclass(frozen=True)
class BuildResult:
    records: tuple[InvocationRecord, ...]   # in numbering/output order
    warnings: tuple[str, ...]
```

### Metadata sidecar (R4)
CSV, UTF-8 (BOM allowed), header exactly `invocation_id,role_label,arm,phase,revision_round,trigger,start_commit,end_commit,agent_definition_hash` (9 columns), one row per invocation (not every invocation needs a row). Rules: `role_label` free text (display only; it never changes the invocation ID or `role`); `trigger` blank or one of `first`, `retry`, `revision`, `resume`; `revision_round` blank or a non-negative integer (digits only); other cells free text, trimmed; `invocation_id` compared exactly. Lines are numbered from 1 for the header. Output rows copy the cells as text; an invocation with no sidecar row, or a run without `--meta`, gets blank cells.

### Output columns
`CSV_COLUMNS` (57, in this order) in `tracker/invocation_render.py`:

`record, run_id, invocation_id, role, role_label, session_id, agent_id, prompt_number, launched_by, requested_agent_type, requested_model, observed_models, model_match, started_at, finished_at, elapsed_s, active_s, tool_time_s, tool_calls_timed, wait_before_start_s, requests, input_tokens, cache_read_tokens, cache_write_5m_tokens, cache_write_1h_tokens, output_tokens, reasoning_tokens, reasoning_share, cache_hit_ratio, zero_cache_read_after_first, cache_writes_after_gap, cache_write_tokens_after_gap, context_first, context_max, context_mean, cost_usd, cost_input, cost_cache_read, cost_cache_write_5m, cost_cache_write_1h, cost_output, tool_calls, failed_tool_calls, tool_calls_by_name, files_read, files_distinct, files_repeated, repeated_paths, human_messages, arm, phase, revision_round, trigger, start_commit, end_commit, agent_definition_hash, likely_agent_inferred_guess`

Row kinds (`record` column): `invocation`; `run_total` (`invocation_id` blank, `role` = `TOTAL`, `role_label`, `session_id`, `agent_id`, `prompt_number`, `launched_by`, `requested_agent_type`, metadata and `likely_agent_inferred_guess` blank); `unattributed` (`invocation_id` blank, `role` = `UNATTRIBUTED`; filled: `record, run_id, role, requests`, the five token columns, `reasoning_tokens`, `cost_usd` and `likely_agent_inferred_guess`; every other cell blank). Orchestrator rows: `agent_id`, `prompt_number`, `launched_by` and `requested_agent_type` blank. Subagent rows: `launched_by` is the orchestrator invocation ID or `unavailable`; `requested_agent_type` is the type name or `unavailable`. `role_label` comes from the sidecar (blank when none) and is blank on every other row kind. `likely_agent_inferred_guess` is filled only on the `unattributed` row and is blank on every invocation row (it is an inference, never a measurement, and the column name says so). `run_total` per-column rules are in the spec table; every column not listed there as a sum, ratio or merge is blank on the total row, except `requests` and the token and cost columns, which are sums (cost columns `unavailable` if any invocation's is). Row order: invocation rows in numbering order, then `run_total`, then `unattributed`.

CSV encoding: UTF-8 without BOM, `\n` line endings, `csv.writer` default quoting (minimal), header row first, trailing newline.

## API endpoints
Not applicable: local CLI tool (no server, no network).

## Codex invocation usage in the multi-agent workflow
No new parser is required for the routine report: `tracker.codex_logs.read_codex_rows` already emits request-level `UsageRow` values, and `tracker.run_report.render_report` already attributes both `tool=codex` and `tool=claude` rows by exact `(tool, session_id, agent_id)` and invocation time window. The manifest contract is the existing `workflow/usage/templates/invocations.csv` header and `run-report` CLI above; no schema or output changes.

Codex manifest mapping is fixed: `tool=codex`; `session_id` is exactly `session_meta.payload.id`; `agent_id` is the session ID for a log with `parent_thread_id` and blank for a main session; timestamps are timezone-aware invocation start/finish. The Markdown report contains model(s), request count, input, cache read/write, output, reasoning, and cost for each matching invocation. If a Codex source ID is missing or the local logs do not match it, the run closeout is incomplete and the resource log records attribution unavailable; no ID is invented and no missing total is called zero. The detailed `invocations-from-logs` path stays Claude-only.

The orchestrator invokes `python -m tracker run-report --manifest <manifest>` at every completed or stopped multi-agent run close, then commits the manifest and report and links the report from the resource log. This is a required workflow action, not a provider hook. Local logs from another machine must be contributed before the report can be considered complete.

## Components and modules

### CLI contract
```
python -m tracker invocations-from-logs --run-id RUN_ID [--meta PATH] [--claude-dir PATH]
    [--codex-dir PATH] [--prices PATH] [--out-md PATH] [--out-csv PATH] SESSION_ID [SESSION_ID ...]
```
- `--run-id` required. Valid: starts with a letter or digit, then only letters, digits, `.`, `_`, `-`.
- Positional `SESSION_ID` one or more (argparse `nargs="+"`).
- `--meta PATH` optional sidecar. `--claude-dir` default `~/.claude`. `--codex-dir` default `~/.codex` (used by aggregate report cross-check; this Claude-specific reconstruction command does not cut Codex invocations). `--prices` default `prices.json` in the tool folder (a missing file means no prices, as for the other commands).
- `--out-md` default `<workflow>/usage/runs/<RUN_ID>/report-v2.md`; `--out-csv` default `<workflow>/usage/runs/<RUN_ID>/metrics-v2.csv`, where `<workflow>` is `TOOL_DIR.parents[1]` (the repo's `workflow` folder), independent of the current directory. Parent folders are created. Existing files are overwritten only after every check has passed.
- Success: stdout one line `Wrote invocation report for run {run_id} ({n} invocations) to {md_path} and {csv_path}`, where `n` counts invocation rows including orchestrator rows; exit 0. Warnings go to stderr, one per line, before any other output, and do not change the exit code.
- Failure: stderr one or more lines starting `error: ` (exact texts below), exit code as listed, no output file written or changed. Every message says what is wrong and names the input that caused it. Argparse usage errors (missing `--run-id`, no session ID) exit 2 with argparse's own text.

| Condition | Exit | stderr text (exact; `{x}` filled in) |
|---|---|---|
| invalid `--run-id` | 2 | `error: --run-id "{value}" is invalid: it must start with a letter or digit and contain only letters, digits, '.', '_' and '-'` |
| empty session ID | 2 | `error: session ID argument {n} is empty: give a non-empty Claude Code session ID` (`n` = 1-based position among the session ID arguments) |
| duplicate session ID | 2 | `error: session ID "{id}" is given more than once (arguments {a} and {b}): list each session once` (`a` and `b` = 1-based positions of the first two occurrences) |
| session has no log file | 2 | `error: no Claude Code logs found for session ID "{id}" under {projects}: expected {id}.jsonl or {id}/subagents/agent-*.jsonl in a project folder (check the session ID and --claude-dir)` (`projects` = `str(Path(claude_dir) / "projects")`; tests match the pieces, not the path separators) |
| `--meta` unreadable or not UTF-8 | 2 | `error: --meta file "{path}" cannot be read: {reason}` (`reason` = the OS error text, or `not valid UTF-8 text`) |
| sidecar header wrong | 2 | `error: --meta file "{path}" line 1: header is "{found}" but must be exactly: invocation_id, role_label, arm, phase, revision_round, trigger, start_commit, end_commit, agent_definition_hash` (`found` = the cells joined by `, `) |
| sidecar row has a wrong field count | 2 | `error: --meta file "{path}" line {n}: expected 9 fields but found {k}` |
| unknown invocation ID | 2 | `error: --meta file "{path}" line {n}: invocation ID "{id}" is not in this run; the run's IDs are: {ids}` (`ids` = all IDs in output order, joined by `, `) |
| duplicate invocation ID | 2 | `error: --meta file "{path}" line {n}: invocation ID "{id}" already appears on line {m}` |
| bad trigger | 2 | `error: --meta file "{path}" line {n}: trigger "{value}" is not allowed; use one of: first, retry, revision, resume` |
| bad revision round | 2 | `error: --meta file "{path}" line {n}: revision_round "{value}" is not a non-negative integer` |
| invocation rows not in report rows | 1 | first line (only when `k` is above 0): `error: cross-check failed for session(s) {sessions}: {k} invocation request(s) have no identical row in the report (affected sources: {sources}); report rows: {m}, invocation rows plus unattributed rows: {i}` |
| a compared quantity differs | 1 | one line per differing quantity, in the order `requests, input_tokens, cache_read_tokens, cache_write_5m_tokens, cache_write_1h_tokens, output_tokens, reasoning_tokens, cost_usd`: `error: cross-check failed for session(s) {sessions}: {quantity}: invocations plus unattributed = {a}, report = {b}, difference (report minus invocations plus unattributed) = {d}` (ints plain, `d` signed with `+` or `-`; cost as `.6f` with signed difference, `unavailable` for `a`, `b` or `d` when a cost is unknown) |
| (last line of every cross-check failure) | 1 | `error: cross-check failed for session(s) {sessions}: likely cause: {cause}` where `cause` is, when `k` is above 0, `a message ID is logged in more than one file for these sessions (for example a copy of a log outside the session folder layout) with a larger output_tokens, so the report keeps a different line than the invocation reader`, and otherwise `a log line is counted differently by the invocation reader and by the report (a parsing difference); treat this as a tracker defect` |
| output path cannot be written | 2 | `error: cannot write the {kind} to {option} "{path}": {reason}` (`kind` = `report` with `option` = `--out-md`, or `metrics CSV` with `--out-csv`; `reason` = the OS error text) |

In the cross-check lines: `sessions` = the listed session IDs sorted, joined by `, `; `sources` = distinct `{session_id}/{agent_id}` of the invocation rows that have no identical report row (`main` replaces an empty agent ID), sorted, joined by `, `; `m` = number of report rows for the listed sessions; `i` = number of invocation rows plus unattributed rows. These lines hold only IDs, counts and numbers, never log text.

Checks run in this order: run ID, session IDs (empty, then duplicates in argument order), logs found (argument order), build, sidecar, cross-check, render, write. The first failing check stops the run; the cross-check failure prints all its lines. `{path}` and `{value}` are as given on the command line or in the sidecar. Warning text (stderr), one per subagent file without usable meta: `warning: agent {agentId} in session {sessionId}: no usable meta.json (file missing, unreadable or without a text agentType); role set to unknown`.

### Markdown layout (`invocation-v2`)
Written by `render_markdown(run_id, session_ids, rows, total, unattributed, meta_rows) -> str`. Exact text and order, `\n` line endings, ending with one trailing newline:

```
# Invocation report: {run_id}

Format: `invocation-v2`

Sessions: {session IDs sorted ascending, joined by ", "}

Costs are tracker list-price estimates, not billed. `unavailable` means the logs do not contain the data; no metric is estimated. The only inference is `likely_agent (inferred guess)` on the unattributed line, which is a guess and is never added to any invocation. A blank cell means not applicable. Elapsed values are wall-clock durations; the run total is latest finish minus earliest start. Wait before start is a wall-clock gap, not proof that one stage depended on another. Role is the agent type logged by Claude Code; Requested agent type is the type named in the launching Agent call; Role label is the label from the metadata file and never changes an invocation ID. Claude Code logs only; Codex sessions are not included.

## Invocations

{table A}

Unattributed usage (rows in the listed sessions that no invocation claims): requests={n}, input={n}, cache_read={n}, cache_write_5m={n}, cache_write_1h={n}, output={n}, reasoning={n}, cost_usd={x}; likely_agent (inferred guess, not measured): {text}

## Cache and context

{table B}

## Tools, files and time

{table C}

## Cost by token type (USD)

{table D}

## Metadata

{table E}
```
`cost_usd={x}` is `format(value, ".6f")` or `unavailable`. `{text}` is the likely-agent text defined in the spec (entries `{invocation ID} (rule: window; requests: {k})`, `{invocation ID} (rule: nearest; requests: {k})` or `unavailable (rule: none; requests: {k})`, joined by `; `), or `none` when there are no unattributed rows. Each table is `| h1 | h2 |` header, `| --- | --- |` separator, then one row per invocation (numbering order) and, for tables A to D, a last row whose first cell is `TOTAL` (table E has no total row). Cells are `format_value` text passed through `mdtable.escape_cell`. Column headers (exact) and the CSV column each shows:

| Table | Headers in order (CSV column) |
|---|---|
| A | `Invocation ID` (invocation_id), `Role` (role), `Role label` (role_label), `Session ID` (session_id), `Agent ID` (agent_id), `Prompt` (prompt_number), `Launched by` (launched_by), `Requested agent type` (requested_agent_type), `Requested model` (requested_model), `Observed model(s)` (observed_models), `Model match` (model_match), `Started` (started_at), `Finished` (finished_at), `Elapsed (s)` (elapsed_s), `Requests` (requests), `Input` (input_tokens), `Cache read` (cache_read_tokens), `Cache write (5m)` (cache_write_5m_tokens), `Cache write (1h)` (cache_write_1h_tokens), `Output` (output_tokens), `Reasoning` (reasoning_tokens), `Cost (USD)` (cost_usd) |
| B | `Invocation ID`, `Reasoning share` (reasoning_share), `Cache hit ratio` (cache_hit_ratio), `Zero cache read after first` (zero_cache_read_after_first), `Cache writes after gap` (cache_writes_after_gap), `Cache write tokens after gap` (cache_write_tokens_after_gap), `First context` (context_first), `Max context` (context_max), `Mean context` (context_mean) |
| C | `Invocation ID`, `Tool calls` (tool_calls), `Failed tool calls` (failed_tool_calls), `Tool calls by name` (tool_calls_by_name), `Files read` (files_read), `Distinct files` (files_distinct), `Repeated reads` (files_repeated), `Human messages` (human_messages), `Active (s)` (active_s), `Tool time (s)` (tool_time_s), `Tool calls timed` (tool_calls_timed), `Wait before start (s)` (wait_before_start_s) |
| D | `Invocation ID`, `Input` (cost_input), `Cache read` (cost_cache_read), `Cache write (5m)` (cost_cache_write_5m), `Cache write (1h)` (cost_cache_write_1h), `Output` (cost_output), `Total` (cost_usd) |
| E (role_label is shown in table A, not repeated here) | `Invocation ID`, `Arm` (arm), `Phase` (phase), `Revision round` (revision_round), `Trigger` (trigger), `Start commit` (start_commit), `End commit` (end_commit), `Agent definition hash` (agent_definition_hash) |

### New and changed modules
New (each single-purpose):

| File | Contents |
|---|---|
| `tracker/errors.py` | `class TrackerError(Exception)`: `__init__(self, message: str, exit_code: int = 2)`; attributes `message`, `exit_code`; `message` has no `error: ` prefix and may hold several lines separated by `\n`; the CLI prints each line prefixed with `error: ` to stderr |
| `tracker/timeutil.py` | `parse_utc(value: object) -> datetime \| None` (ISO text, `Z` accepted, returns UTC-aware datetime; non-string, unparseable or timezone-less gives `None`); `format_utc(value: datetime) -> str` |
| `tracker/log_session.py` | `find_session_files(claude_dir: Path, session_id: str) -> tuple[Path \| None, list[Path]]` (main file or None; subagent files sorted by path; scans every folder under `<claude_dir>/projects`; main = file named `{session_id}.jsonl` whose parent folder is not `subagents`; subagent = `agent-*.jsonl` whose parent is `subagents` and whose grandparent folder is named `session_id`); `read_file_log(path: Path, agent_type: str, split_prompts: bool) -> FileLog`; `normalise_read_path(raw: str) -> str` |
| `tracker/invocations.py` | `validate_run_id(run_id: str) -> None`; `build_invocations(run_id: str, claude_dir: Path, session_ids: Sequence[str], prices: dict) -> BuildResult` (raises `TrackerError`) |
| `tracker/invocation_metrics.py` | `UNAVAILABLE = "unavailable"`; `metric_rows(records: Sequence[InvocationRecord], prices: dict) -> list[dict[str, object]]` (same order as `records`; includes `wait_before_start_s` because it needs all records); `total_row(records, rows, prices) -> dict[str, object]`; `unattributed_row(run_id: str, rows: Sequence[UsageRow], likely_agent: str \| None) -> dict[str, object]` (fills `likely_agent_inferred_guess` with `likely_agent`) |
| `tracker/unattributed.py` | `likely_agent_text(rows: Sequence[UsageRow], records: Sequence[InvocationRecord]) -> str \| None`: `None` when `rows` is empty; otherwise the grouped guess text of the spec (rules `window`, `nearest`, `none`; times from `record.window.first_time/last_time`; only records with the same `session_id` as the row; the row time from `timeutil.parse_utc(row.timestamp)`; distance in seconds to the nearer of start and finish; ties and ordering by position in `records`); it reads no other data and changes no record |
| `tracker/invocation_meta.py` | `META_COLUMNS: list[str]` (the 9 sidecar columns); `read_metadata(path: Path \| None, known_ids: Sequence[str]) -> dict[str, dict[str, str]]` (empty dict for `None`; `known_ids` is in output order for the unknown-ID message; raises `TrackerError` per the table); `apply_metadata(rows: list[dict[str, object]], meta: dict[str, dict[str, str]]) -> None` (sets `role_label` and the seven metadata columns on each invocation row, `None` for a missing or empty cell) |
| `tracker/crosscheck.py` | `cross_check(invocation_rows: Sequence[UsageRow], report_rows: Sequence[UsageRow], session_ids: Sequence[str]) -> list[UsageRow]` returns the unattributed rows (report rows left after removing the invocation rows, as a multiset) or raises `TrackerError(message, exit_code=1)` whose message holds the descriptive lines of the CLI table |
| `tracker/mdtable.py` | `escape_cell(text: str) -> str` (backslash to `\\`, `|` to `\|`, CRLF/LF to `<br>`; the exact chain `run_report._cell` uses today); `table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str` |
| `tracker/invocation_render.py` | `CSV_COLUMNS`, `format_value(column: str, value: object) -> str`, `render_csv(rows: Sequence[dict]) -> str` (rows in output order: invocations, total, unattributed), `render_markdown(run_id: str, session_ids: Sequence[str], invocation_rows: Sequence[dict], total: dict, unattributed: dict, likely_agent: str \| None) -> str` |
| `tests/helpers_trk03.py` | synthetic log builders (owned by the test-designer; `tests/helpers.py` is not edited) |
| `tests/test_trk03_*.py` | tests below |

Changed (behaviour of existing commands unchanged):
- `tracker/pricing.py`: add `cost_breakdown(row: UsageRow, prices: dict) -> dict[str, float] | None` returning keys `input, cache_read, cache_write_5m, cache_write_1h, output` (0.0 for a type with 0 tokens, whatever its price) or `None` if the model has no entry, no tier applies, or a type with tokens above 0 has no price; `cost_usd(row, prices) -> float | None` keeps its signature and returns the sum of the breakdown values in that key order starting from 0.0, or `None` (the sum order and arithmetic are the same as today, so existing results are identical to the last bit). Tier choice uses `row.prompt_tokens`. Model lookup uses the new `resolve_model_prices(prices, model)` described under "Data model"; `cost_usd` and `cost_breakdown` both go through it.
- `tracker/model.py`: the `prompt_tokens` property.
- `tracker/claude_logs.py`: rename `_row_from_line` to public `row_from_line`, `_agent_type` logic split into public `agent_meta(path: Path) -> dict | None` (parsed meta JSON object of a subagent file, `None` when missing, unreadable, not an object, or the file is not in a `subagents` folder) plus the existing `_agent_type`; add `keep_largest(best: dict, key: tuple, row: UsageRow) -> None` (the keep rule `kept is None or row.output_tokens >= kept.output_tokens`) used by `read_claude_rows` and by `log_session`. `read_claude_rows` output is unchanged.
- `tracker/run_report.py`: `_cell` calls `mdtable.escape_cell` for its escaping (output unchanged).
- `tracker/cli.py`: new subparser and branch; existing branches untouched. The branch collects report rows as `rows = [r for r in collect_rows(claude_dir, codex_dir, prices) if r.tool == "claude" and r.session_id in sessions]`, builds invocations, runs `cross_check(all invocation rows, rows, session_ids)` (it uses `summarise(...)[-1]`, the TOTAL group, for the compared sums), computes `likely_agent_text(unattributed, records)`, merges the sidecar with `apply_metadata`, renders and writes with `run_report.write_report(text, path)` (reused: writes UTF-8 with `\n`).
- `prices.json`: add the Haiku entry (with `"match_variants": true`).
- `README.md` and `workflow/usage/README.md`: see R8 below.

### Algorithms the contract fixes
- `read_file_log`: reads objects in order with `jsonl.read_objects`. Lines are indexed 0,1,2,... over the objects yielded. Tracks the current window; `pending_handback` is set when a user line has a `tool_result` block whose `tool_use_id` names a `tool_use` called `SubagentHandback` earlier in the file. A user line whose `message.content` is a `str` is a prompt start if `pending_handback` (window opens, flag cleared) or if it is the first such line with `isMeta` not `True` (window 1 already exists). With `split_prompts` false no window opens. Other non-meta string user lines add 1 to the current window's `human_messages`; for the main file the first non-meta string user line is the prompt start and is not counted. Assistant lines: each `tool_use` block with string `id` and `name` is recorded once at the first line holding it, in the current window; usage rows come from `claude_logs.row_from_line` and `keep_largest` with key `(session_id, agent_id, message_id)`, `order` = first line index for that key, window of the first line. Every line with a parsable time widens the current window's `first_time`/`last_time`. A `tool_result` block (user line, list content) sets `result_time` (first only) and `is_error` (true if any block has `is_error is True`) for its ID.
- `build_invocations`: validate run ID and session IDs, locate files (error if a session has no file), read each file (`split_prompts` true for subagents), price rows with `pricing.cost_usd`, set roles, order, number and link (`launched_by` and `requested_agent_type` from `agent_calls` of the main file of the same session: the subagent's meta `toolUseId` is looked up in `agent_calls`; absent meta, absent id or no match gives `None` for both). A session with only subagent files and no main file has no orchestrator row.
- `cross_check`: `unattributed = Counter(report_rows) - Counter(invocation_rows)` and `missing = Counter(invocation_rows) - Counter(report_rows)`; the quantity comparison always runs (so a failure lists every differing quantity), with `a` = sum of `summarise(invocation_rows)[-1]` and `summarise(unattributed)[-1]`, `b` = `summarise(report_rows)[-1]`, and the failure message is built from the CLI table (first line only when `missing` is non-empty, one line per differing quantity, then the cause line); if `missing` is empty and no quantity differs it returns `unattributed`. Compare, for `requests, input_tokens, ..., reasoning_tokens, cost_usd`, the sum of `summarise(invocation_rows)[-1]` and `summarise(unattributed)[-1]` with `summarise(report_rows)[-1]` (cost: both unavailable, or equal within `math.isclose(rel_tol=1e-9, abs_tol=1e-9)`; if either part is `None` the sum is `None`).

### Reuse
`jsonl.read_objects`, `jsonl.as_int`, `claude_logs.row_from_line/keep_largest/agent_meta`, `pricing.cost_usd`, `export.collect_rows`, `report.summarise`, `run_report.write_report`, `cli.TOOL_DIR`. Nothing in `run_report` or `report` is re-implemented.

## UI contract
No screen: local CLI. States are the stdout success line, the stderr warnings and errors, and exit codes in "CLI contract" above. Requests per load and per retry, Wrong role, Link history, Refresh, Back and Forward, Expired session or logout, Backend down, Longest wait before an error and No generic failure message do not apply (no network, no browser). Every failure uses its exact message from the CLI table; there is no generic failure text. A re-run with the same inputs is the retry; it makes no network request.

## AI usage
None. The tool makes no LLM call and sends no data anywhere.

## Test plan
Test files in `tests/` (all use synthetic logs in `tempfile` folders built by `helpers_trk03.py`; run with `python -m unittest discover -s tests` from the tool folder; tests call `tracker.cli.main(argv)` and capture stdout and stderr, and call `pricing`, `invocation_meta.read_metadata` and `crosscheck.cross_check` directly by the signatures above). Name each test `test_trk03_<topic>`; the table maps criteria to tests.

| AC | Tests (file) |
|---|---|
| AC1 | `test_trk03_haiku_entry_in_prices_json` (prices): loads the real `prices.json`, asserts both tiers' five rates, `as_of`, a source containing "pricing page" |
| AC2 | `test_trk03_haiku_tier_boundary_100000_first_tier`, `test_trk03_haiku_100001_second_tier`, `test_trk03_prompt_size_counts_cache_reads_and_both_writes` (prices) |
| AC3 | `test_trk03_flat_entry_unchanged`, `test_trk03_sonnet_opus_costs_unchanged`, `test_trk03_unknown_model_cost_none`, `test_trk03_malformed_tiers_cost_none`, `test_trk03_no_applicable_tier_cost_none`, `test_trk03_cost_breakdown_sums_to_cost_usd` (prices) |
| AC4 | `test_trk03_one_invocation_per_subagent_and_orchestrator_row`, `test_trk03_ids_numbered_per_role_by_start_time`, `test_trk03_id_order_ties_broken_by_session_agent_prompt`, `test_trk03_multiple_sessions_one_run` (invocations) |
| AC5 | `test_trk03_resumed_agent_splits_per_handback_prompt`, `test_trk03_meta_lines_and_prompt_id_do_not_split`, `test_trk03_file_without_nonmeta_prompt_is_one_invocation` (invocations) |
| AC6 | `test_trk03_role_from_meta_agent_type`, `test_trk03_missing_meta_role_unknown_with_warning_exit_0`, `test_trk03_role_characters_sanitised` (invocations) |
| AC7 | `test_trk03_launched_by_matches_agent_tool_use_id`, `test_trk03_launched_by_unavailable_without_match` (invocations) |
| AC8 | `test_trk03_no_logs_for_session_exit_2_exact_message`, `test_trk03_duplicate_session_id_error`, `test_trk03_empty_session_id_error`, `test_trk03_invalid_run_id_error`, `test_trk03_errors_write_nothing` (cli) |
| AC26 | `test_trk03_haiku_dated_variant_priced_as_haiku`, `test_trk03_haiku_bracket_suffix_priced`, `test_trk03_haiku_5_50_not_priced`, `test_trk03_haiku_5_5x_not_priced`, `test_trk03_other_haiku_version_and_provider_prefix_not_priced`, `test_trk03_sonnet_variant_not_priced`, `test_trk03_exact_key_beats_variant_and_longest_marked_key_wins`, `test_trk03_variant_priced_row_in_invocation_report` (prices, using a temp `prices.json` for the longest-key and exact-wins cases) |
| AC27 | `test_trk03_requested_agent_type_from_agent_call`, `test_trk03_requested_agent_type_unavailable_without_match`, `test_trk03_requested_agent_type_rejects_long_or_odd_text` (a `subagent_type` with spaces or over 64 characters gives `unavailable` and is not echoed), `test_trk03_orchestrator_row_blank_agent_type_fields`, `test_trk03_role_label_from_sidecar_shown_next_to_role`, `test_trk03_role_label_does_not_change_invocation_id`, `test_trk03_generic_role_identified_by_label_and_requested_type`, `test_trk03_resumed_prompts_share_requested_type` (invocations, render) |
| AC28 | `test_trk03_error_invalid_run_id_names_option_and_value`, `test_trk03_error_empty_session_names_position`, `test_trk03_error_duplicate_session_names_id_and_positions`, `test_trk03_error_no_logs_names_id_and_projects_path`, `test_trk03_error_sidecar_messages_name_path_line_and_value` (one per sidecar error), `test_trk03_error_unknown_invocation_lists_run_ids`, `test_trk03_error_write_failure_names_option_and_path`, `test_trk03_warning_missing_meta_names_agent_and_session` (cli; each asserts the quoted detail pieces from the CLI table are in stderr) |
| AC9 | `test_trk03_model_match_yes_no_unavailable`, `test_trk03_observed_models_sorted_joined` (metrics) |
| AC10 | `test_trk03_cost_split_by_type_sums_to_cost`, `test_trk03_unpriced_model_cost_columns_unavailable`, `test_trk03_haiku_tier_applies_per_request_in_invocation` (metrics) |
| AC11 | `test_trk03_reasoning_share`, `test_trk03_reasoning_share_unavailable_without_field`, `test_trk03_cache_hit_ratio`, `test_trk03_zero_cache_read_after_first`, `test_trk03_cache_write_after_gap_over_300s`, `test_trk03_gap_exactly_300s_not_counted`, `test_trk03_gap_skipped_when_timestamp_missing`, `test_trk03_context_first_max_mean` (metrics) |
| AC12 | `test_trk03_tool_calls_counted_once_per_id_across_duplicate_lines`, `test_trk03_tool_calls_by_name_sorted`, `test_trk03_failed_tool_calls_is_error`, `test_trk03_file_reads_total_distinct_repeated`, `test_trk03_read_path_normalisation`, `test_trk03_only_read_tool_counts_as_file_read` (metrics) |
| AC13 | `test_trk03_elapsed_and_active`, `test_trk03_tool_time_partial_reports_calls_timed`, `test_trk03_tool_time_unavailable_when_no_pair_timed`, `test_trk03_tool_time_zero_without_calls`, `test_trk03_wait_before_start_latest_earlier_finish`, `test_trk03_wait_unavailable_when_none_finished_before`, `test_trk03_human_messages_exclude_prompt_and_meta` (metrics) |
| AC14 | `test_trk03_missing_fields_give_unavailable_not_zero` (metrics) |
| AC15 | `test_trk03_sidecar_columns_in_csv_and_markdown`, `test_trk03_no_sidecar_columns_blank` (meta) |
| AC16 | `test_trk03_sidecar_unknown_id_error`, `test_trk03_sidecar_duplicate_id_error`, `test_trk03_sidecar_wrong_columns_error`, `test_trk03_sidecar_bad_trigger_error`, `test_trk03_sidecar_bad_revision_round_error`, `test_trk03_sidecar_unreadable_error`, `test_trk03_sidecar_wrong_field_count_error` (meta; each asserts exact stderr text, exit 2, no files) |
| AC17 | `test_trk03_markdown_layout_and_headers`, `test_trk03_csv_columns_and_row_kinds`, `test_trk03_run_total_elapsed_latest_finish_minus_earliest_start`, `test_trk03_total_row_sums_and_merges` (render) |
| AC18 | `test_trk03_rerun_byte_identical_markdown_and_csv`, `test_trk03_default_output_paths`, `test_trk03_out_md_out_csv_options`, `test_trk03_float_formats_and_unavailable_token`, `test_trk03_markdown_escapes_table_delimiters` (render) |
| AC19 | `test_trk03_unattributed_zero_when_all_claimed`, `test_trk03_unattributed_counts_stray_session_log`, `test_trk03_unattributed_is_not_an_error_and_totals_reconcile` (render) |
| AC20 | `test_trk03_crosscheck_sums_equal_report_total` (crosscheck; compares against `summarise(collect_rows(...))` filtered to the sessions) |
| AC21 | `test_trk03_crosscheck_mismatch_exit_1_nothing_written`, `test_trk03_crosscheck_keeps_existing_output_files`, `test_trk03_crosscheck_message_names_sessions`, `test_trk03_crosscheck_message_names_each_differing_quantity_with_values_and_difference`, `test_trk03_crosscheck_message_names_affected_sources_and_row_counts`, `test_trk03_crosscheck_message_states_likely_cause`, `test_trk03_crosscheck_message_has_no_log_text` (crosscheck; exact lines per the CLI table) |
| AC22 | `test_trk03_privacy_no_sentinel_in_markdown_csv_stdout`, `test_trk03_privacy_no_sentinel_in_errors_and_warnings`, `test_trk03_read_path_may_appear_other_tool_inputs_not`, `test_trk03_agent_call_description_and_prompt_not_in_output` (privacy) |
| AC29 | `test_trk03_likely_agent_window_rule`, `test_trk03_likely_agent_shortest_window_wins`, `test_trk03_likely_agent_nearest_when_no_window`, `test_trk03_likely_agent_nearest_tie_goes_to_first_in_output_order`, `test_trk03_likely_agent_none_when_row_has_no_timestamp`, `test_trk03_likely_agent_none_when_session_invocations_have_no_times`, `test_trk03_likely_agent_groups_and_sorts_entries`, `test_trk03_likely_agent_none_text_without_stray_rows`, `test_trk03_likely_agent_labelled_in_markdown_and_csv_column` (unattributed, render; the stray row is a same-session log placed outside the layout) |
| AC30 | `test_trk03_likely_agent_does_not_change_invocation_rows_or_total`, `test_trk03_stray_numbers_only_on_unattributed_row` (unattributed) |
| AC23 | verifier reads both READMEs against the list under "R8 docs" (no automated test) |
| AC24 | existing tests unmodified and passing (37; the verifier checks `git diff` shows no change to existing test files); `test_trk03_run_report_unchanged` runs `run-report` on a fixture identical to `test_run_report.py` and compares with its expected text; `test_trk03_report_and_export_unchanged` runs `report` and `export` on a fixture and compares with the same literal expected output as before the change (in `test_trk03_regression`) |
| AC25 | verifier checks imports are standard library only and no real log is committed |

Privacy test method (R7): synthetic logs carry distinct sentinel strings (for example `SENTINEL_PROMPT_7f3a`, `SENTINEL_REPLY_7f3a`, `SENTINEL_THINKING_7f3a`, `SENTINEL_BASH_7f3a`, `SENTINEL_GREP_7f3a`, `SENTINEL_WRITE_7f3a`, `SENTINEL_EDIT_7f3a`, `SENTINEL_RESULT_7f3a`, `SENTINEL_FILE_7f3a`, `SENTINEL_META_DESC_7f3a`, `SENTINEL_AGENT_DESC_7f3a`, `SENTINEL_AGENT_PROMPT_7f3a`) in: the user prompt string, meta user lines, assistant text, thinking blocks, `Bash` `command`, `Grep` `pattern`, `Write` `content`, `Edit` `new_string`, the `Agent` call's `description` and `prompt` (its `subagent_type` is a valid short name and is expected in the output), `tool_result` content and `toolUseResult`, a file-content result for a `Read`, and `.meta.json` `description`. A second Agent call uses a sentinel-bearing text with spaces as `subagent_type`; its row shows `unavailable` and the sentinel is absent. Run the command successfully, then in failure runs (unknown sidecar ID, cross-check mismatch, missing session, missing meta warning); assert no sentinel in the Markdown, CSV, stdout, stderr. The `Read` `file_path` used in the test contains no sentinel and is asserted present in the CSV `repeated_paths` when read twice.

Security tests from the threat model: none apply (no web surface); the privacy test is the security test. Record its result in `workflow/security/` only if the orchestrator wants it logged; not required for a local tool.

### R8 docs (what the READMEs must state)
Command, options and defaults; output files and layouts; the sidecar columns and the two-step flow (run once to get IDs, then write the sidecar); metric rules in short; exit codes. Known limits: the Claude Code log format is undocumented and may change (fields are observed in one probe session, `workflow/specs/TRK-03/log-probe.md`); where a worktree-isolated subagent's log is stored is unverified; Codex gets token totals through `run-report` but not Claude-specific tool, file-read, context or detailed timing metrics; the Haiku tier rule is an unverified assumption, and Haiku variant IDs are priced by the prefix rule in "Data model" (a provider-prefixed or otherwise non-prefix ID is not priced); list prices are estimates, not billed ("tracker list-price estimates, not billed"); wall-clock gaps are not dependencies; orchestrator elapsed includes idle time and its tool time includes waiting for subagents; "human messages" may include injected non-meta messages; repeated reads ignore offsets; roles depend on the session's agent registry; the probe is one session only. The README must also explain how to read the role columns (`role` = what the log says, `requested_agent_type` = what the orchestrator asked for in the Agent call, `role_label` = what the human says it was, display only, never in an ID), that `likely_agent (inferred guess)` is an inference with the three rules (`window`, `nearest`, `none`) and is never added to an agent's own totals, and the descriptive error and cross-check messages.

## Decisions
- Orchestrator rows are one per session (not split per human turn): simplest, deterministic, matches the blank-agent-ID rule; stated as a limit.
- Cross-check is done at the row level (multiset of `UsageRow`) and then on sums via `summarise`, so a divergence between the new reader and the existing code is caught, and a stray log of a listed session is shown as unattributed usage instead of an error.
- Cost split is added as `pricing.cost_breakdown`; `cost_usd` is derived from it, so there is one pricing code path.
- Output file names `report-v2.md` and `metrics-v2.csv` avoid `report.md` and `invocations.csv` of the `invocation-v1` run folder.
- Unavailable (data missing) and blank (not applicable) are distinct in both formats.
- Variant model IDs: one rule (`match_variants` prefix with a non-alphanumeric boundary), switched on per price entry, so only Haiku 5.5 changes behaviour and every existing result stays byte-identical.
- Stray usage stays unattributed (not an error); the likely-agent label is computed in its own module from session ID and times only, and is applied only to the unattributed line and row.
- Role observability: `role` (log), `requested_agent_type` (Agent call), `role_label` (human, sidecar); none of them feeds the invocation ID except `role` as before.
- `invocation-v1`, `run-report` and its manifest are not changed; only `_cell` delegates escaping to `mdtable`.
