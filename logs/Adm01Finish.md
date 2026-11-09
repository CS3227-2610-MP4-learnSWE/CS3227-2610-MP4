# ADM-01 completion and test cleanup

Dates: 2026-11-09 to 2026-11-10. Branch: `feat/adm01-feature-analytics-build`.

Implemented and verified the existing analytics build, then the user-approved stronger privacy amendment (`906a249`). New implementation and tests were developed independently; test worktree: `../CS3227-ADM01-privacy-tests`. The user requested focused checks and low token use.

## Changes

- Fixed session/submission and grading-admission races, logout/Back data clearing, quality counts/copy and date input contrast.
- Removed 18 unnecessary test cases: seven synthetic maximum-year cases, six duplicate TEA-02 cases, two source-shape checks and three impossible native-date inputs. Practical date boundaries and core auth/privacy/concurrency tests remain.
- Replaced real TCP timeout waits in SHR-01 and STU-01 outage tests with deterministic driver failures, retaining their fail-closed assertions. Focused runs took 0.89s and 0.97s.
- Stronger privacy: local English name recognition plus identity/credential/ID detection; sanitised-only storage, bounded fixed-point recheck before dispatch, output checks, source exclusions, policy-version enforcement and legacy-text/reason purge. Missing/unhealthy scanner blocks grading. No runtime model downloads or additional AI provider.
- MCQ content, uploaded source/context and companion solution explanations are excluded. Factual accuracy is unassessable without context. Unusual names or unlabelled secrets can still be missed; user approved this bounded scope after plain-language explanation.
- Preserved retryable sanitised input after malformed model output. User approved one extra timing fix after the two-round cap: recheck the 200-second cutoff after privacy scanning and immediately before dispatch (`d943f73`).

## Evidence

- Earlier independent backend verification: 618 passed before the privacy amendment.
- General regression suffix: 1265 passed plus seven Windows Temp setup errors; exact seven recovered with a fresh owned basetemp, 7 passed in 12.85s. Earlier prefix failures were synthetic/obsolete fixtures and were corrected or removed under the recorded scope rulings. No uninterrupted all-green full-suite claim.
- Privacy phase broad affected run: 582 passed, 32 failed; remaining old-policy fixtures and two implementation defects were corrected. Eight corrected legacy cases passed separately; final gate/dispatch/restored retry selection: 77 passed. No passing claim for the transient weakened retry assertion; it was restored and rerun.
- Strongest privacy review: 34 focused checks passed; found the timing boundary above. Final boundary regression and existing cutoff check:2PASS. Strongest reviewer reran its original199.9?200.1s reproduction:zero calls, completed run, pending item/text untouched; final PASS.
- Current UI: 102 Playwright cases passed (1.6m), including privacy states and responsive light/dark checks. Typecheck, lint, production build and spec checker passed. Earlier four mobile screenshots were inspected at 320/390px.
- Frozen Linux offline model smoke passed; near-cap scan 49.96ms (500ms limit), peak RSS 192308KiB. Three native Windows model tests skip only for the verified Application Control block on thinc/cblas. Native Windows grading returns the fail-closed unavailable state; Linux provisioning is verified. No policy bypass attempted.

## Limits and follow-up

Healthy scanner contention during output validation can be reported as invalid_ai_output rather than a busy-scanner diagnostic. Strongest review classed this non-blocking: no unsafe output escapes and sanitised input remains retryable. Historical backups are operator-owned; migration clears live legacy analytics text/reasons, not historical backups. Apply migrations before service start and after restoration.

No live SoC calls, developer .env edits, direct master commits, merge or deployment. User .gitignore/presentation changes preserved. Usage was recovered after provider interruption; interrupted timestamps are last-observed bounds. Provider child usage can remain unavailable and is never treated as zero.

[Finish-run usage](../workflow/usage/runs/2026-11-09-ADM01-finish-02/report.md). [Initial interrupted build](../workflow/usage/runs/2026-11-09-ADM01-01/report.md).

Final strongest review PASS; PR/team review and remote CI remain separate. User requested test completion notifications rather than repeated polling; no further broad tests were run.
