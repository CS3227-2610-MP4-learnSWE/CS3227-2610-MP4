# STU-03 cap experiments

Goal: evidence for the AI study companion caps (input characters, history messages, output tokens, per-student rate limit, timeout) against the SoC LLM. Standard library only; no backend dependency added.

## Safety
- Dry run is the default: fake LLM, no network, no key, output in `results-dry/` (not kept).
- Live runs need `--live` and a local, git-ignored `.env` with `SOCLAAS_BASE_URL`, `SOCLAAS_API_KEY`, `SOCLAAS_MODEL`. The key is used only for the request header and is never printed or stored. Only rate-limit-related response headers are recorded.
- A hard cap of 100 live calls across all phases is counted in `results/_live_calls.txt`; the phase 5 burst stops at the first 429.
- Each live phase is run only after the user says go; the user reads the SoCLaaS dashboard before and after.

## Phases (live calls)
| Phase | What | Calls |
|---|---|---|
| 1 | `/models` and one tiny chat: endpoint, `usage` field, headers, model | 2 |
| 2 | Natural reply length per mode (hint 8, explain 8, help 6), output cap 800 | 22 |
| 3 | Input length 100/300/600/1200 characters and history 0/6/12, output cap 300 | 14 |
| 4 | Extraction and injection attempts, pasted question, off-topic, output cap 300 | 15 |
| 5 | Sequential burst of tiny calls, stops at first 429 | up to 10 |

## Commands (from this folder, PowerShell, one per line)
```
python -I run.py 1
python -I run.py 2 --live
python -I analyze.py results
```
`analyze.py` prints token percentiles per mode, the share of replies each candidate cap would cut off, latency p50/p95 and the phase 4 leak flags (a rough text match; replies are read manually).

## Results
All seven phases were run on 30 Oct 2026 (347 billed chat requests, no rate-limit hit). Phase 6 is the factorial sweep (`run.py 6 --live --delay 0.3`, resumable, scored by `rules.py`, analysed by `analyze6.py`; add `--hint-no-question` for the relaxed hint rule) and phase 7 repeats the phase 4 attacks with the short-answer instruction. Recommended caps and findings: see `RESULTS.md`.
