# Retro: ADM-04 Feedback follow-up

Feature: ADM-04 | Branch: feat/adm04-feedback-follow-up | PR: [31](https://github.com/CS3227-2610-MP4-learnSWE/CS3227-2610-MP4/pull/31) | Closed on: 2026-11-07

## Revision rounds
Rounds used (cap 2): 1. Independent integration found strict request-type error taxonomy and corrupted loading/status ellipses; both corrected in `30d663b`.

## Defects found
| Defect | Found by | Blocking? | Fixed in round |
|---|---|---|---|
| Non-list recipient IDs used count-error code instead of malformed-request code | test-designer | yes, contract mismatch | 1 |
| Corrupted ellipsis characters in exact loading/status copy | test-designer | yes, contract mismatch | 1 |
| Migration fixture assumed historical demo-admin; long mobile content assertion omitted scroll | test-designer | test setup / overspecified viewport, assertions retained | fixture-only `318d568` |
| All-active audience search labels filtered result count as selected count before review | verifier | no; immutable review/send audience is exact | follow-up, retained |
| New Python test extra EOF blank line | verifier | no, whitespace only | `f4865f3`, after full runs; assertions unchanged |

## Resource use
Tracker run: yes, orchestrator-owned. [Run report](../../usage/runs/2026-11-07-ADM04-01/report.md). Isolated parent/whole-run token usage and cost unavailable where nested provider metadata attribution is incomplete. Provider usage-limit interruption required resumed designer/verifier invocations; return timestamps remain bounds in manifest/report. Wall time includes interruption and human approval wait. No source correction round used for interruption or test-environment recovery.

## RED before GREEN
| Criterion or defect | Test commit / RED evidence | Fix commit / GREEN evidence |
|---|---|---|
| AC01?05 response entry/recipient/privacy | independent `4ce8c3d`/`83be154`; initial 3 backend failures and missing response-entry browser failure at approved `47fb1fb` | source `de5c17b` + correction `30d663b`; focused final116backend/48browser PASS |
| AC06?13 remaining acceptance/security cases | independent `4ce8c3d`/`83be154` before implementation visibility; no complete pre-implementation RED run shown for every case | corrected source `30d663b`; focused116/48 PASS |
| Strict request type and exact loading copy | initial full feature-focused integration114backendPASS/2FAIL and45browserPASS/3FAIL included source and fixture findings | `30d663b` + fixture-only `318d568`; focused116/48 PASS |

## Steps done outside the pipeline
Orchestrator supplied source-aware integration facts to implementation-isolated spec-writer before approval. Designer fixture repairs retained migration preservation and mobile no-overflow assertions. Parent merged independent tests after complete focused report while designer full regression continued, then launched read-only verifier; final closure requires all full outcomes. Source remained fixed during full runs. User approval preceded application code at `47fb1fb`.

Windows default pytest temporary-root permissions required explicit ignored basetemp; no ACL changes. Node rejected TypeScript configs inside node_modules; ignored runner config extension/location corrected. Playwright default output cleanup removed earlier ignored artifacts after stats/visual inspection; resumed full reports use separate preserved paths. Full-format noise from core.autocrlf=true was checked in-memory with LF-normalized content, with no mass rewrites. Docker Desktop/Compose PostgreSQL restarted after interruption; only disposable schemas used. No live AI, developer environment/database migration or user app-process changes.

## What to change next time
- `workflow/coordination.md`: prefer an ignored test-runner location outside Playwright output, explicit outputDir/cwd and final JSON/JUnit preservation.
- `workflow/usage/README.md`: keep interruption bounds explicit and improve attribution of inherited metadata in forked provider logs before claiming isolated parent totals.
- `workflow/specs/ADM-04/plan.md`: distinguish filtered search totals from selected audience labels before immutable review.

Final strongest read-only check at `7f1ff5e`:1358backendPASS733.97s (116ADM04),615browserPASS468.165s (48ADM04), zero failures/errors/skips/retries/flaky; type/lintPASS, changed-source formatPASS, all130 tracked frontend targetsPASS with in-memory LF normalization. No blocking finding; optional count-label follow-up retained.

Independent final full regression:1358backendPASS930.30s and615browserPASS470.465s, exits0; XML/JSON zero failure/error/skip/retry/flaky assertions. Final whitespace-only cleanup `f4865f3` merged as `90b13ce`; application source unchanged from verifier snapshot. Both full suites include all116backend/48browserADM04 cases.
