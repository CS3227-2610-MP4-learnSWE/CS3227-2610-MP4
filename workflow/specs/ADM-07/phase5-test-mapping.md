# ADM-07 phase 5: assertion mapping before deletion (test-designer)

Scope: frontend tests to be deleted (`adm01-analytics.spec.ts`, `adm01-privacy.spec.ts`, `adm01Api.ts`, `adm06-usage.spec.ts`, the ADM-06 test and the `["usage", "/admin/ai-usage"]` visual row in `admin-ui.spec.ts`). Nothing was deleted or edited. New files (all under `src/frontend/tests/`):

- `adm07-retained.spec.ts` (Quality, Feature outcomes, grading, privacy, history, roles, layout ported from the ADM-01 tests; run against the hub).
- `adm07-retained-aiusage.spec.ts` (ADM-06 screen test, ADM-06 test and visual row of `admin-ui.spec.ts`, ported to the hub's AI usage section).
- `adm07-redirect.spec.ts` (Gate F decision: `/admin/ai-usage` redirects to the hub; no "AI usage" nav link). Fails until the deletion step; that is expected.
- `adm07Fixtures.ts` (the generation, quality and grading-run body builders copied unchanged from `adm01Api.ts`).

Result on the merged run branch (HEAD 854a182 already contains the code of `feat/analytics-feedback-consolidation`): see the final section.

Legend. **Cov** = already covered by an existing assertion in `adm07-analytics.spec.ts` (A) or `adm07-p4-values.spec.ts` (P4). **Port** = ported to a new file (name suffix after "retained"). **Sup** = superseded by a spec change (cited). Test titles are shortened.

## 1. adm01-analytics.spec.ts (58 tests)

| Old test (ADM-01 AC) | Disposition |
|---|---|
| AC40 page title, purpose, panels, period fields, nav links | Sup: hub header, four sections, selector (spec UI table "Header", "Period selector", "Navigation"); Cov A "header, muted line, sections, period options", "nav link Feature Analytics". The old purpose sentence and "Periods use UTC dates. Maximum 366 days." are replaced by the muted line and the custom dialog help text (Sup: spec Header and Custom range rows). |
| AC40 three requests, parallel, default 30 days; quality params; tab selected | Sup: seven requests, default Last 7 days (spec "Requests per load"); Cov A "load sends exactly seven parallel requests" (quality workflow/limit/offset). Default tab selected plus loading keeps tabs: Port (`retained` "default workflow tab ... loading status keeps the tabs"). |
| AC40 each panel own loading status, others not blocked | Cov A "each block shows its own loading text" (and the "no duplicate requests" assertion). Tabs and notice stay while loading: Port (same test as above). "Apply period not disabled by loading": Sup (no Apply button; spec Period selector row "Selector stays usable"; Cov A checks Refresh disabled instead). |
| AC40 usage panel tables, subtotals, grand total, completion sentence | Cov A "AC25 users table" (columns, Students total, Teachers/All users total unavailable, rows) and "AC5 six KPI tiles" (completion sentence "7 of 10 attempts submitted..."). Rows with names and counts (Alice 5, Bob 7): Cov A shows name Alice Tan only; the per-row counts and the 12/3 subtotal are Sup: the hub mock has different numbers and the table has a Failure rate column and paging (AC25). |
| AC40 usage empty and not-applicable | Cov A "AC25 students with no requests ... zero totals", "not-applicable and unavailable tiles", "AC21 no attempts started". |
| AC40 usage unavailable reasons (`period_before_recording`, `no_source`, `read_failed`) | `no_source`: Cov A (Teachers tab and totals). `read_failed`: Cov A "not-applicable and unavailable tiles". `period_before_recording` copy: Sup by AC39 (partial coverage; whole-period case is `unavailable`/`period_before_recording` with the spec's own wording "recording began on {since}, after this period ended"). Wording is not asserted in any hub test (small gap, not a retained assertion: the old text "after this period started" is replaced). |
| AC40 usage panel more than 500 users truncation note | Sup: ADM-07 AC25 (paging replaces the 500-row cap; retained-criteria Part C). |
| AC40 generation panel both workflows, rates, no-rate message | Cov A "AC27 generation table" (columns, 66.7%, no-rate message). The MCQ row has three zero cells and no `%`: Port. |
| AC40 generation unavailable rows show reason | Port. |
| AC40 quality panel tabs, notice, sections, averages, times, table | Cov A "AC27 quality section" covers notice, tablist, table name only. Everything else: Port. |
| AC40 item statuses and unassessable labels | Port. |
| AC40 quality empty states | Port. |
| AC32 descriptive measurements, never time saved or no-AI comparison | Port. |
| AC40 teacher tab unavailable | Port. |
| AC11/AC40 plain-text names and reasons, no markup | Port (users name and quality reason). |
| AC40 no analytics data in browser | Cov A "AC31 no analytics data is kept in browser storage" (users data) plus Port for the Quality data and `expectNoSecretsInBrowser`. |
| AC40 per panel network failure (usage, generation, quality) with Retry, one request | Cov A "backend down" (all blocks) and "server error ... Retry sends exactly one request" (HTTP 503, not network). Single-block network failure with one Retry request: Port. |
| AC40 per panel HTTP 500/502/503/504/404, status copy, server message ignored | 503 Cov A. 500/502/504/404, private detail absent, no "Could not reach", no "something went wrong": Port. |
| AC40 per panel 403 | Cov A only for the hourly block ("403 on a block"). Port for users, generation, quality. |
| AC40 backend down, every panel, title and period panel stay, recovery by Apply | Cov A "backend down" (recovery by Refresh instead of Apply; Sup: no Apply). |
| AC40 malformed 200 body | Cov A only for AI usage. Port for users, generation, quality. |
| AC40 15 s timeout, no auto retry | Cov A for Health only. Port for Quality. |
| AC40 assessed-responses page failure keeps page | Cov A has the equivalent for the users table; the Quality one: Port. |
| AC40 failed tab switch selects clicked tab | Port. |
| AC42 Apply period: changed period sends 3 requests, pushes; unchanged sends none | Sup: AC30 and Period selector row; Cov A "preset change pushes history...", "selecting the already selected period", "custom range valid apply pushes... unchanged range sends nothing". |
| AC42 Back and Forward restore period and reload | Sup by spec "Back and Forward" row, but Cov A has NO Back/Forward test: Port (`retained` "Back and Forward restore the period and reload all seven blocks"). |
| AC42 workflow tab: one quality request, replace URL | Cov A "quality section ... workflow tab replaces the URL" (one request and history length). |
| AC42 only workflow changes in history reloads one request; refresh restores | Port ("Back to a URL that differs only by workflow reloads only quality"; "a workflow switch after a period change survives a browser refresh"). Cov A "browser refresh restores the period and workflow" covers the plain refresh. |
| AC42 Retry on one panel sends one request | Cov A "server error ... Retry sends exactly one request" (all blocks except AI usage). AI usage Retry: Port (aiusage file). |
| AC42 pagination one request per click, URL kept, end buttons disabled | Port (Quality). Cov A has the users table paging only. |
| AC42 pagination buttons disabled while pending | Port. |
| AC42 URL query restores period and workflow | Cov A "browser refresh restores the period and workflow from the URL". |
| AC42 invalid or incomplete URL query (5 variants) | Cov A "URL state: invalid values fall back" covers one variant. Port for the five old variants (defaults, no alert, seven requests). |
| AC41 client validation (4 cases): message, no request, values kept, focus on first invalid | Cov A "custom range ..." loop (6 cases, superset: adds format and future). |
| AC41 two invalid fields: focus first, corrected period loads | Port (custom range dialog). |
| AC44 student and teacher redirected with replace, no request | Cov A "AC31 a student/teacher is redirected" (no history-length assertion). The replace (history +1) assertion and "nothing from the hub renders": Port. |
| AC44 anonymous to sign-in with replace, no request; with query string | Cov A "anonymous visitor goes to sign-in (replace)". History length and query-string variant: Port. |
| AC44 401 ends session at sign-in, message "Your session has expired. Sign in again.", Back shows no data | Cov A "a 401 mid-session ends at sign-in" (no message assertion, no Back check). Port. |
| AC44 logout clears report, Back shows sign-in | Port. |
| AC43 grading dialog exact text, Cancel and Escape send nothing, focus returns | Cov A "grading flow" checks the dialog text only. Port. |
| AC43 one POST with workflow and period, polling until finished, one quality reload, polling stops | Cov A "grading flow" is partial (no body, no reload count, no stop). Port. |
| AC43 start button disabled while start pending | Port. |
| AC43 nothing to grade | Port. |
| AC43 failed run per code (6 codes) | Port (6 codes). `privacy_scanner_unavailable` is new; see ambiguities. |
| AC43 failed start 409/429/403/422/network | Cov A "grading 409" (message only). Port for all five including closed dialog, results and period kept, one POST, no retry, 409 adds one quality GET. |
| AC43 start timeout 15 s | Port. |
| AC43 polling network failure, Check progress one request | Port. |
| AC43 polling HTTP error copy | Port. |
| AC43 polling 15 s timeout copy | Port. |
| AC43/AC44 401 while polling | Port. |
| AC42 active run in quality response resumes polling | Port. |
| AC45 period controls keyboard order, Apply from keyboard | Sup/Cov A "AC32 keyboard only: period, Refresh, Expand, modal, sort and tabs". |
| AC45 workflow tabs arrow keys, grade dialog traps focus | Port. |
| AC45 named controls and landmarks | Port. |
| AC45 light/dark x 320/390: no page scroll, controls visible and outlined, wide table in container | Cov A "AC32 ... no horizontal page scroll" and "wide tables scroll inside a focusable container" (users table only; no outline check). Port: controls fit, selector outlined, Quality items table scrolls inside its container. |
| AC45 error and dialog states fit 320px dark | Port (hub blocks plus grade dialog). |
| AC45 received time is a `<time>` with ISO value | Port. |

## 2. adm01-privacy.spec.ts (4 tests)

| Old test | Disposition |
|---|---|
| strict mode: status text, button disabled, "7 responses excluded...", no extra requests | Cov A "AC28 strict privacy mode" (text, disabled, count, no POST). "No extra requests" (7 loads): Port. |
| 409 `privacy_grading_disabled`: alert, URL unchanged, button disabled after strict reload, 2 quality GETs | Port. |
| 503 `privacy_scanner_unavailable`: alert, URL unchanged, button enabled, 1 quality GET | Port. |
| blocked count visible when nothing is eligible | Port. |

## 3. adm06-usage.spec.ts (28 tests, loops expanded) and admin-ui.spec.ts

| Old test (ADM-06 AC) | Disposition |
|---|---|
| AC2/3/7/13 named controls, metadata, columns, values, period line, query | Cov A "AI usage section" (columns, caption, note, results region, request per change, defaults via "load sends seven requests"). Values 731/99, no `%`, "Collection started:" per row, the "Period: ... (UTC)" line, option labels: Port. Old heading "AI usage" h1, "Demo · Sample data" absence, nav link "AI usage" to `/admin/ai-usage`: Sup (hub; nav link removed, Gate F redirect; Port in redirect file). Start/End date fields: Sup (no AI usage dates; the hub period applies). |
| AC13 loading: one StrictMode request, duplicate action prevented | Cov A "load sends exactly seven requests", "no duplicate requests". Apply disabled: Sup (no Apply button). |
| AC4 complete zero separate from unavailable tokens | Port. |
| AC4 unavailable selected feature prevents the no-activity claim | Port. |
| AC4/8 four unavailable reasons with no false zero | Port (4 reasons). |
| AC2/13 Apply sends one selected-feature request, keeps URL | Cov A (one request per feature change). URL unchanged and selection kept: Port. |
| AC11 local validation (start after end, 31+ days, future, empty): fields kept, report cleared, no GET | Sup for the date inputs (custom range dialog, AC30; Cov A custom range loop). The 31-day limit and "report cleared": Cov A "period longer than 31 days" for 6 requests and message; table absence and the 31 versus 32 day boundary: Port. |
| AC13 HTTP 403/422/429/503 exact copy | 403, 429, 503: Cov A. 422: Port. |
| AC13 HTTP 404, 409, 500 shown as "invalid report" copy | Sup: spec UI table "Other HTTP status" gives "AI usage could not be loaded: the server returned an error ({status}). Try again." (Cov A for 500). 404 and 409 with the status copy: Port. Old Retry-hidden-on-403 assertion: not ported (spec says Retry button for common failures; open question below). |
| AC13 Retry uses applied filters, not unsent edits | Port (hub: feature choice stays; retry repeats it). |
| AC13 network, json, shape failure distinct, one request, Retry recovers | json: Cov A "malformed body". Network single block and shape: Port. |
| AC13 15 s timeout, no auto retry | Port (message is the common timeout copy, Sup of the old "AI usage request timed out" text). |
| AC10 wrong role redirected, no request | Sup: AC31; Cov A "AC31 a student/teacher is redirected" and Port with history assertion. |
| AC13 refresh and Back/Forward reload default filters once | Sup: hub spec; Cov A "Refresh reloads seven blocks"; Back/Forward Port (hub-wide). |
| AC10 expired session clears report, shared sign-in flow | Port (401 on the AI usage request, message, no table, Back). |
| AC13 failed logout preserves session and report; success and Back clear | Port. |
| AC13 old pending result cannot flash after account switch | Port. |
| AC8/13 malformed counters (-1, 2^53, true, "731", null) rejected | Port (5 values). |
| AC13 navigating away drops late result; return gets fresh report | Port. |
| AC5 browser stores no report; malformed content not rendered | Port. |
| AC13 390 and 1100 px: controls, results region, spacing, reason 14 px, caption 16 px and width | Control visibility, keyboard focus, no page scroll: Port (passes at 1100, caption width fails at 390, see results). Reason font at least 14 px and caption at least 16 px: Port as a separate test (FAILS: reasons render at 13 px). The old `.ai-usage-panel` spacing (16 px) assertion is Sup: the CSS class and the "Service-call report" panel are removed (spec Hub layout paddings). |
| admin-ui "ADM-06 admin baseline separates filters from unavailable report and retains retry" | Headings "Report filters" and "Service-call report": Sup (hub has four section headings). Outlined control, failed read keeps controls with Retry, one request then 2, 320 px no overflow: Port. |
| admin-ui visual row `["usage", "/admin/ai-usage"]` (1365 and 390, light and dark, no overflow, screenshot) | Port: hub visual coverage at the same four combinations (`retained-aiusage`). The row in the loop also hit the old AI usage page through a route mock; once the old page is deleted the row must be removed, and the ADM-06 `ai-usage?**` route mock with it. |

## 4. Backend mapping in `retained-criteria.md`: confirmed or corrected

Method: test function names in `src/backend/tests/test_adm01_*.py`, `test_adm06_*.py`, `test_adm07_*.py` (no source read). "Listed" = what `retained-criteria.md` says.

| Criterion | Listed | Actual covering files | Verdict |
|---|---|---|---|
| ADM-01 AC1 | `test_adm01_access` | `test_adm01_access` (usage, generation, quality, grading-runs), `test_adm01_cross_user`, and `test_adm07_access` for the new endpoints | Confirmed (add the two) |
| AC2 | `test_adm01_hooks` | `test_adm01_hooks`; also `test_adm07_p4_hooks`/`test_adm07_p4_routes` for new hooks | Confirmed |
| AC3 | usage, generation, quality | Period validation is tested in `test_adm01_access` (`ac3_*`, 21 tests) and `test_adm07_access`; no `ac3` test in usage, generation or quality | Wrong: replace with `test_adm01_access`, `test_adm07_access` |
| AC4 | `test_adm01_usage` | `test_adm01_usage` (`ac4_*`), `test_adm01_hooks` (outcome recording), `test_adm07_health` (`ac38_*`, new rule) | Confirmed (add hooks, health) |
| AC5 | `test_adm01_usage` | `test_adm01_usage`; on the hub `test_adm07_chatbot_users` (`ac25_*`) | Confirmed |
| AC6, AC7 | `test_adm01_usage` | `test_adm01_usage`; `test_adm07_health` `ac11_*`, `test_adm07_chatbot_users` (`ac25_*` boundaries, no-request users) | Confirmed |
| AC8, AC9, AC10 | `test_adm01_usage` | `test_adm01_usage` (8 tests). On the hub only ONE test, `test_adm07_health::ac5_practice_completion_equals_the_usage_report_definition` (3 attempts: one submitted in period, one open, one submitted after the period). It compares against `/usage`. AC10 (`not_applicable`, no percentage) and the before-period-start case are only tested through `/usage` and the empty-period shape test (`ac5_exact_top_level_shape_and_empty_period_states`) | Confirmed, but thin: see gaps |
| AC11 | `test_adm01_usage`, `test_adm01_privacy` | `test_adm01_usage::ac11_*`, `test_adm01_cross_user::ac11_*` (3 tests), `test_adm07_access::ac4_*` | Wrong: `test_adm01_privacy` is the grader-input gate, not the usage response. Use cross_user and `test_adm07_access` |
| AC12 | `test_adm01_usage` | `test_adm01_usage::ac12_*` (a `period_before_recording` test that is Sup), `test_adm07_health::ac5_one_failing_read...`, `test_adm07_kept_partial` | Confirmed (second sentence on hub: `test_adm07_health`) |
| AC13 | `test_adm01_usage` | `test_adm01_usage::ac13_*`; `test_adm07_chatbot_users::ac26_*` | Confirmed |
| AC14 | `test_adm01_generation` | same (`ac14_*`); `test_adm07_kept_partial` | Confirmed |
| AC15 | generation, hooks | `test_adm01_generation::ac15_*` (note: `ac15_decision8_refused_calls_do_not_move_the_report` encodes the OLD rule and must now conflict with ADM-07 AC40 unless already updated), `test_adm01_hooks::ac15_*`, `test_adm07_p4_hooks`/`p4_routes` (`ac33_*`) | Confirmed; flag the old refused-call report test |
| AC16 | generation, hooks | same (`ac16_*`) | Confirmed |
| AC17, AC18 | generation | `test_adm01_generation::ac17_*`, `ac18_*`; new denominator: `test_adm07_p4_reports::ac40_*` | Confirmed (add p4_reports) |
| AC19 | generation | `test_adm01_generation::ac19_*` | Confirmed |
| AC20 | quality | `test_adm01_quality::ac20_*` | Confirmed |
| AC21 | quality, grading helpers | `test_adm01_quality::ac21_*` | Confirmed |
| AC22 | quality, privacy, privacy_dispatch | `test_adm01_quality::ac22_*` (4 tests), `test_adm01_privacy::privacy_grade_reasons_*` (3), `test_adm01_privacy_dispatch::privacy_new_name_in_grade_reason...` | Confirmed |
| AC23 | privacy, privacy_model, privacy_dispatch, quality | `test_adm01_privacy` (12 gate tests), `test_adm01_privacy_dispatch` (dispatch re-scan), `test_adm01_quality::ac23_*` (prompt, redaction, no identifiers), `test_adm01_hooks::ac23_*` (answer keys never stored). `test_adm01_privacy_model` has ONE parametrised test (names recognised within 500 ms), nothing on the claimed provisioning | Confirmed; add hooks; privacy_model is narrow |
| AC24 | quality, privacy | `test_adm01_quality::ac24_*` | Confirmed (privacy: no `ac24` test there) |
| AC25 | quality, cross_user | `test_adm01_quality::ac25_*` (2 tests). `test_adm01_cross_user` has no ac25 test | Wrong for cross_user |
| AC26 | quality | `test_adm01_quality::ac26_*` | Confirmed |
| AC27 | quality, hooks | `test_adm01_quality::ac27_*` (12), `test_adm01_hooks::ac27_*`, `test_adm01_concurrency::ac27_*` | Confirmed (add concurrency) |
| AC28, AC29 | quality | `test_adm01_quality::ac28_*`, `ac29_*` | Confirmed |
| AC30 | quality | `test_adm01_quality::ac30_*` (one of them, `ac30_a_period_before_recording_makes_every_measure_unavailable`, is Sup by AC39; `test_adm07_kept_partial::ac39_quality_*` replaces it) | Confirmed |
| AC31 | quality | `test_adm01_quality::ac31_*` | Confirmed |
| AC32 | `adm01-analytics.spec.ts` | Frontend only | Confirmed; ported (above) |
| AC33 | quality, privacy, concurrency | `test_adm01_quality::ac33_*` (8), `test_adm01_privacy_dispatch` (409 strict, 503 not ready: those are the amended start rules), `test_adm01_concurrency::ac33_*`. `test_adm01_privacy.py` does not test the start endpoint | Wrong: `test_adm01_privacy` should read `test_adm01_privacy_dispatch` |
| AC34 | quality, privacy_dispatch | `test_adm01_quality::ac34_*` (5). `privacy_blocked` never selected: dispatch (`policy_mismatch...`) | Confirmed |
| AC35 | quality, privacy_dispatch | `test_adm01_quality::ac35_*`, `test_adm01_privacy_dispatch::..._midrun_*` | Confirmed |
| AC36 | quality | `test_adm01_quality::ac36_*` (9) | Confirmed |
| AC37 | quality, privacy, privacy_model | `test_adm01_quality::ac37_*` (3). `test_adm01_privacy_dispatch::..._policy_mismatch_purges_without_dispatch` covers "legacy rows without the marker never eligible". No test found by name for the migration purge of legacy text and reasons before workers serve requests, nor for the pinned `spacy`/model wheel provisioning (`privacy_model` has one name-recognition test) | Partly wrong: `privacy`/`privacy_model` do not cover it; migration purge and provisioning look untested |
| AC38 | concurrency | `test_adm01_concurrency::ac38_*` (11), `test_adm07_p4_hooks::ac37_*`, `test_adm07_concurrency` | Confirmed |
| AC39 | cross_user, hooks | `test_adm01_cross_user::ac39_*` (9), `test_adm01_hooks::ac39_*` | Confirmed |
| Privacy amendment: strict and local modes | privacy, quality | `test_adm01_privacy::privacy_strict_setting_blocks...`, `test_adm01_privacy_dispatch::privacy_strict_start_is_409...`; `privacy_mode`/`privacy_blocked_count` response fields: no test by name in quality | Partly confirmed; fields only checked indirectly |
| Privacy amendment: gate contract, UI deltas | privacy*, `adm01-privacy.spec.ts` | gate: `test_adm01_privacy*`; UI: now ported | Confirmed |
| ADM-06 AC1 | usage, transport | `test_adm06_transport::ac1_*` (3), usage (`ac2_3_7`) | Confirmed |
| ADM-06 AC2, AC3 | usage (+transport for AC3) | `test_adm06_usage::ac2_3_7_exact_breakdown...`; AC3 rate-limit category: `test_adm06_transport::ac1_3_retry...` | Confirmed |
| ADM-06 AC4 | usage | `test_adm06_usage::ac4_*` (4) | Confirmed |
| ADM-06 AC5, AC6 | usage, transport | `test_adm06_usage::ac5_6_admin_report_fixed_content_free_schema`; `test_adm06_migration::ac5_schema_enforces_nonnegative_token_fields`; transport has no ac5/ac6 test | Partly wrong: transport does not cover; migration covers the schema part |
| ADM-06 AC7, AC8, AC9 | usage | `test_adm06_usage::ac2_3_7_*`, `ac8_*` (4), `test_adm06_transport::ac7_9_*`, `ac8_*` (2) | Confirmed (add transport) |
| ADM-06 AC10 | usage | `test_adm06_usage::ac10_*` (4) | Confirmed |
| ADM-06 AC11 | usage, migration | `test_adm06_usage::ac11_*` (7), `test_adm06_migration::ac11_*` (2) | Confirmed |
| ADM-06 AC12 | usage, transport, migration | `test_adm06_transport::ac12_*` (5), `test_adm06_usage::ac12_*` (2), `test_adm06_migration::ac11_*` for durability | Confirmed |
| ADM-06 AC13 (screen) | frontend | ported; `test_adm06_usage::ac13_report_read_never_invokes_model` is a backend AC13 test | Confirmed |

## 5. Is ADM-06 AC12's "ADM-03 stays uninstrumented" stale? (from test names and the spec, not `src/`)

Yes for the call path; not for the report. `test_adm03_adversarial.py` asserts `reserved == ["ADM-03"] * 4` for an ADM-03 analysis run through the shared client with an observer, and `test_adm03_llm_client_options.py::ac26_*` asserts reserve/finish pairs for ADM-03 calls. `test_adm01_quality.py::every_grading_call_is_labelled_adm01...` asserts `["ADM-01", "ADM-01"]`. So ADM-03 and ADM-01 calls are recorded under their own feature labels. But the coverage rows stay disabled: `test_adm06_usage.py::ac4_all_features_stable_order_covered_zero_and_uninstrumented` expects ADM-03 and ADM-01 rows `not_enabled` with `coverage_start` null, and `ac12_activation_idempotent...` expects `enabled` false for both and rejects activating ADM-03. `test_adm07_p4_cleanup.py` keeps ADM-03 with a coverage start in one scenario. Suggested text for the phase 5 doc update: "STU-03, TEA-02, ADM-03 and ADM-01 calls are recorded by the shared observer under their own labels; the report shows ADM-03 and ADM-01 as `not_enabled` until their coverage is activated." The ADM-06 spec text ("ADM-03 remains explicitly uninstrumented until its own feature integrates") should not be copied forward.

## 6. Gaps, ambiguities and findings

Frontend retained assertions with no equivalent were all ported, except these that are NOT ported by design: old nav link, old h1, Start/End date fields, Apply buttons, `.ai-usage-panel` spacing, "Report filters"/"Service-call report" headings, 500-user truncation note (all Sup, cited above).

Findings from running the ported tests on the hub:

1. FAIL (hub behaviour vs retained ADM-06 readability follow-up, 2026-11-06): unavailable-reason text in the AI usage table renders at 13 px (test requires at least 14 px) and the caption is wider than its scroll container at 390 px (537 px text in a 321 px region; test requires it to fit). Tests: `adm07-retained-aiusage.spec.ts`, "readability 390px/1100px" and "390px AI usage controls". Retained-criteria Part C marks the follow-up as superseded by AC27, AC29 to AC32, but none of those states font sizes or caption width. Decision needed: fix the CSS, or record the follow-up as dropped and delete these three tests.
2. Ambiguity: spec "Run failure copy by code" lists `privacy_scanner_unavailable` as "the local privacy scanner is not ready" (for "Grading stopped: ..."), while the Quality start-grading row says a 503 or mid-run scanner failure shows an alert "AI grading is unavailable because the local privacy scanner is not ready. Try again later." The hub renders the alert. The ported test asserts the alert; the status-line variant is not asserted.
3. Ambiguity: ADM-06 hid the Retry button on a 403; the hub spec gives every failure a Retry button except 401. No assertion either way.
4. Ambiguity: the Feature combobox label for ADM-01 grading calls (Open question 13). Ported tests assert only the three labels in the spec plus "All features".
5. Spec check: the old ADM-01 quality counts line "12 assessed, 5 waiting to be graded, 1 could not be graded" is not in the hub UI table but the hub renders it (the ported test asserts it unchanged). Add it to the spec table or drop the assertion.
6. Gap in `adm07-analytics.spec.ts` (now filled by the port): no Back/Forward test existed although the spec has a "Back and Forward" row.
7. Helper dependency: `adm07Api.ts` imports `generationBody`, `qualityBody`, `run`, `Run` from `adm01Api.ts`. Before `adm01Api.ts` is deleted, change that one import to `./adm07Fixtures` (a copy is provided). `adm07-retained*.spec.ts` already import `adm07Fixtures`. No other test file imports `adm01Api.ts`.
8. Backend dependency on removed code: `test_adm07_health.py::ac5_practice_completion_equals_the_usage_report_definition` calls `/api/admin/analytics/usage`; `test_adm07_access`/`test_adm07_chatbot_users` use `/usage?include_rows`. The deletion list keeps `/usage`, so this holds; if `/usage` is ever removed those tests change.
9. Backend gaps (no test found by name): migration purge of legacy grading text and reasons (AC37 amended and the provisioning rule), `privacy_mode`/`privacy_blocked_count` fields in `/quality`, and hub-level AC9/AC10 edge cases (completion before the period start, rounding, `not_applicable`) other than the single comparison test. `test_adm01_generation::ac15_decision8_refused_calls_do_not_move_the_report` states the old rule (rate-limited calls do not change the report); if that test still passes, `/generation` does not yet count refused requests, which would contradict ADM-07 AC40, and `test_adm07_p4_reports::ac40_*` says it does. Check before deleting the file.

## 7. Verification run (merged branch HEAD 854a182, `--project=mocked`)

- `npx tsc --noEmit`: clean. `npx eslint .`: clean. `npx prettier --check` on the four new files: clean (the repo-wide check flags 191 existing files only because of CRLF checkout on Windows, including `adm07-analytics.spec.ts`).
- `adm07-retained.spec.ts` and `adm07-retained-aiusage.spec.ts`: 120 passed, 3 failed (findings 1).
- `adm07-redirect.spec.ts`: 2 failed, as expected (the old page and nav link still exist, `/admin/ai-usage` does not redirect yet).
