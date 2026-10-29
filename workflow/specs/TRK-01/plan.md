# Plan: TRK-01 Token usage tracker

## Location and run
`workflow/tools/token-tracker/`, run from that folder: `python -m tracker export` and `python -m tracker report`. Python 3.12+, standard library only; tests use `unittest` (`python -m unittest discover -s tests`).

## Modules (one job each)
| Module | Job |
|---|---|
| `model.py` | `UsageRow` dataclass and CSV column order. |
| `claude_logs.py` | Find and parse Claude Code logs into rows (dedupe, subagents, cache split). |
| `codex_logs.py` | Find and parse Codex rollouts into rows. |
| `pricing.py` | Load `prices.json`; compute cost for a row. |
| `export.py` | Collect rows from both parsers, apply filters, write CSV deterministically. |
| `report.py` | Filter and group rows; render table and summary CSV. |
| `cli.py`, `__main__.py` | Argument parsing and wiring only. |

## Contract
Row columns, in order: `tool, session_id, agent_id, agent_type, is_subagent, model, branch, cwd, timestamp, input_tokens, cache_read_tokens, cache_write_5m_tokens, cache_write_1h_tokens, output_tokens, reasoning_tokens, cost_usd`.

Functions (importable, used by tests):
- `claude_logs.read_claude_rows(claude_dir: Path) -> list[UsageRow]`
- `codex_logs.read_codex_rows(codex_dir: Path) -> list[UsageRow]`
- `pricing.load_prices(path: Path | None) -> dict`; `pricing.cost_usd(row, prices) -> float | None`
- `export.collect_rows(claude_dir, codex_dir, prices, cwd_contains=None, since=None) -> list[UsageRow]` (sorted by timestamp, tool, session, agent)
- `export.write_csv(rows, path)`
- `report.summarise(rows, branch=None) -> list[dict]` grouped by `agent_type, model` with token sums, `requests`, `cost_usd`; plus a totals row.

CLI: `export [--claude-dir] [--codex-dir] [--prices] [--cwd-contains] [--since] [--out usage.csv]`; `report [same filters] [--branch] [--out summary.csv]`.

`prices.json`: `{"as_of": "", "source": "", "models": {"<model>": {"input": 0, "cache_read": 0, "cache_write_5m": 0, "cache_write_1h": 0, "output": 0}}}`, USD per million tokens. Shipped empty; filled from official pricing with the date recorded.

## Tests
One test file per module under `tests/`, building synthetic log files in temporary directories; no real logs in the repo.

## Decisions
- Idempotent regeneration instead of appending, to avoid double counts and merge conflicts.
- Standard library only so teammates need no setup.
