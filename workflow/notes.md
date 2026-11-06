# Handoff notes

Newest entry first. Older entries describe the state at the time; the newest entry supersedes their open/merged status. Keep the newest 10 entries here; older ones are in `notes-archive.md`. Feature state is in `STATUS.md`.

## 2026-11-06: developer frontend CI Progress history synchronization
- Done: reproduced reported count1instead2 race10/10 under6xCPU; history/heading trace shows URL push/pop before Practice rendered. Test now waits Practice heading and Progress absence before both Back operations; exact1/2/3request counts retained. No app source/timeout/retry changes; DeveloperGuide note added.
- Validation:20/20throttled repeatsPASS(1.7min); isolated full513/513browserPASS286.19s, zero skipped/flaky/retries, backend proxy deliberately unavailable. JSON stats asserted; type/lint/format/diffPASS. No backend run needed. PowerShellstderr wrapper anomaly diagnosed separately from greenJSON.
- Next: push local branch and rerun remoteCI. Earlier locationkey hardening did not establish this synchronization cause; actual reproduction/evidence in logs/ProgressHistoryCiFix.md.
- Resources: single-session test-maintenance exemption; no agents/tracker/manifest/report, inherited model/effort and per-tasktokens/cost unavailable; no new feature rounds. No liveAI/env/DB/userprocess changes. Temporary test removed; unrelated .claude/worktrees/ retained.

## 2026-11-06: developer ADM-06 report readability
- Done:24px inset/16px mobile; larger14?16px report/table text; fixed wrapping columns and caption within visible scroll width. User-approved visual contract/testRED committed4b05725 before source; copy/auth/request behavior unchanged. Both guides updated.
- Validation:40ADM06 browserPASS26s;2extra visual casesPASS and1365dark/390light images inspected. Type/lint/build/format/spec1/0/0/diffPASS. No backend/unrelated full browser rerun. Log: logs/Adm06ReadabilityFix.md.
- Next: refresh AIusage. Period/caption inset and unavailable explanations wrap; wide table remains horizontally scrollable. No env/DB/backend restart needed.
- Resources: single-session maintenance exemption; no agents/tracker/manifest/report, inherited model/effort, tokens/cost unavailable, no new feature rounds. One cwd write recovered; user processes/data untouched, .claude/worktrees/ preserved.

## 2026-11-06: developer STU-03 failure reflection
- Done: added one concise evidence-linked reflection on connection ownership, independent-review blind spots and deterministic constrained-pool testing. Preserved other reflection content; no generic model/context claims.
- Validation: evidence links/commit records/diffPASS; docs only, no runtime tests or app/env/DB changes. Log: logs/Stu03FailureReflection.md.
- Resources: single-session docs exemption, no agents/tracker/report; inherited model/effort, tokens/cost unavailable, zero new feature rounds. Next: human reads docs/Reflections.md STU-03 resource-assumption section.

## 2026-11-06: developer STU-03 companion concurrency 503 fix
- Done: reproduced help/practice503 with one-connection pool, tests/maintenance contract committedf66d647 before source. Companion returns initial read-only auth connection before nested store/model work; fresh post-model session/account check retained. No pool expansion/retry/CI/original concurrency assertion changes. Both guides updated.
- Validation: new2RED before source;6targetedGREEN;20original30parallel runsPASS (600requests); final full backend1171PASS348.43s. Compile/spec8/0/12existingwaivers/diffPASS. No frontend changes/browser rerun or independent verifier claim. RemoteCI underlying SQLAlchemy trace unavailable; deterministic local resource defect reproduced with same public503.
- Next: push local branch and rerun remoteCI. Logs/Stu03ConcurrencyPoolFix.md, security/test-log.md. No liveAI/developerDB/env changes or user process restarts.
- Resources: single-session small-fix exemption; no agents/invocations/tracker/report, model/effort inherited, exacttokens/cost unavailable. Initial duplicate-node command selected1test; temporary plugin confirmed20. No new feature revisionrounds. Unrelated .claude/worktrees/ preserved.

## 2026-11-06: developer ADM-06 concise testing walkthrough
- Done: replaced ADM-06 prose with short setup steps, paired Windows/macOS/Linux commands, focused77backend/40browser test commands, manual checklist/expected results and real-count/recovery steps. Only ADM-06 guide sections changed; app behavior unchanged.
- Validation: sixPowerShell/sixbash blocks parse; heading/file links and diffPASS; collection-only77backend/40browser. Local Compose help confirms --wait health support. No runtime suites/setup commands/liveAI/developerDB/env/process changes. Policy-blocked shell-write recovered via apply_patch; trailingblank corrected.
- Next: follow DeveloperGuide ADM-06 local setup, then UserGuide Manual test checklist. Automated tests give immediate mocked counts; real totals require dates after activation's nextUTCmidnight. Log: logs/Adm06TestingWalkthrough.md.
- Resources: single-session docs exemption, no agents/invocations/tracker/report; inherited model/effort, exacttokens/cost unavailable; zero new feature revisionrounds. Unrelated .claude/worktrees/ preserved.

## 2026-11-06: orchestrator ADM-06 verified and committed locally
- Done: approved spec/source contract, independent tests and implemented metadata-only persistent SoC telemetry, attempt/retry/failure/token report, admin UI, migration/activation and both guides. Source3c603c1; one correction batch27cd224/c4df076. Strongest read-only verifier PASS at e85279e, no remaining defects.
- Evidence: final full backend1169 PASS509.73s. Browser full512 PASS/1 old timeout-fixture FAIL383.73s, corrected boundary independently1PASS; all513cases covered passing across runs, not one entirelygreen fullrun. Independent final focused80backend/41browserPASS; desktop/mobile screenshots inspected. Type/lint/build/format/compile/CLI/spec8/0/12existingwaivers/diffPASS. Initial failures/recoveries distinguished in logs/Adm06Implementation.md.
- Security: active-admin endpoint, metadata privacy, exact observed tokens/unavailable semantics, retries, failclosed reservation, atomic replay/activation, concurrent snapshot, strict filter/throttle, no-cache and session/history isolation. Cases in workflow/security/test-log.md. Provider mocked; live SoC field availability unverified. Limiter remains process-local.
- Next: human follows DeveloperGuide migration, restarts all workers, explicitly activates STU-03/TEA-02. Earlier history and first partialUTC day unavailable. Review local branch/PR text workflow/specs/ADM-06/pr.md; no remote push/PR/deployment (GitHubCLI unavailable). User env/schema/data and original running processes preserved.
- Files: feature/source/migration/independent tests/guides; status, tasks, retro, security/session/resource records. Unrelated .claude/worktrees/ untouched.
- Invocations:2026-11-06-ADM06-01 records7starts/returns including developer correction continuation and designer integration; requested strongest gpt-6-astra/high; others inherited. Elapsed manifest governs (44min span includes approval wait, not continuous agent time). Tracker executed, report workflow/usage/runs/2026-11-06-ADM06-01/report.md; no local records matched, so totaltokens/cost unavailable and generatedzeros are not zero actualusage. One application correctionround used; tool/fixture recoveries in session log.

## 2026-11-06: orchestrator ADM-06 developer ready / independent integration
- Done: developer source3c603c1 implements durable aggregate telemetry, admin endpoint/UI, additive migration, activation CLI and guides. Independent test commit9308f15 predates implementation visibility:77 backend RED (29 fail/48 setup error due missing feature),40 browser cases compile/list. User approval/source amendment50cc4b4; empty-state clarificationed13821.
- Checks: existing backend1089 PASS/3 historical migration-head assertion FAIL,354s. Classified historical fixture maintenance; designer pins old target/ancestry and retains populated data checks. Type/lint/build/8-file format/compile/CLIhelp PASS. No independent test weakening or developer test inspection.
- Next: authorised designer merges source into isolated worktree, verifies full backend/browser on fresh5183/5184; then parent merges tests and launches strongest read-only verifier. Zero application correction rounds so far.
- Invocation IDs: developer-01 returned; test-designer-01 returned; test-designer-02 integrating under2026-11-06-ADM06-01. Source IDs and elapsed in manifest; inherited model/effort; tokens/cost unavailable pending report, no zero usage claim. Report workflow/usage/runs/2026-11-06-ADM06-01/report.md. No live AI/developer env/schema changes; user servers untouched. Developer recovered cwd/UTF8/npm policy tooling issues.

## 2026-11-06: orchestrator ADM-06 approved build started
- Done: user approved spec/plan in chat; source-aware integration amendment fixes shared error envelope, token mapping, existing client protocol and ContextVar feature attribution. Speccheck 1/0/0 PASS. Approved start commit50cc4b4.
- Next: developer in run folder and independent test-designer in sibling CS3227-ADM06-tests worktree; tests reset to exact start commit. Verification follows committed source/tests and integration. User dev processes on5173/8000 remain untouched; browser verification uses isolated ports.
- Invocation IDs: 2026-11-06-ADM06-01-developer-01 and test-designer-01; inherited Codex model/effort, elapsed recorded in manifest; report workflow/usage/runs/2026-11-06-ADM06-01/report.md regenerated at close. Exact token/cost attribution pending/unavailable if unmatched; no zeros claimed.
- Resources: tracking active; no live SoC calls or developer database/env changes. One spec-check command directory recovery; no application revision rounds yet. No approval blocker remains for approved contract.

## 2026-11-06: spec-writer ADM-06 draft contract
- Done: drafted AI service-attempt reporting, privacy-safe persistent metadata and coverage, independent recorded-token availability and accessible admin UI contracts. No application code/tests/SoC calls; spec and plan remain Draft.
- Next: human reviews UTC 31-day date range, grouped TEA-02 calls, forward-only coverage and fail-closed metadata reservation. Orchestrator resolves source-aware existing module/provider-field compatibility before independent designer/developer begin; no guessed provider availability.
- Validation: ADM-06 speccheck PASS (1 checked, 0 failed, 0 waived). Contract includes count/retry unit, pending/coverage gaps, no inferred tokens, auth/session/history/error states, concurrency and privacy tests.
- Files touched: workflow/specs/ADM-06/spec.md, plan.md, tasks.md; notes/archive handoff only.
- Invocation ID: 2026-11-06-ADM06-01-spec-writer-01. Source session: 01a1b002-09f9-7d50-8aaf-7b12499d0b9d. Model/effort inherited, exact attribution unavailable; elapsed: manifest timestamps authoritative.
- Feature-run report: workflow/usage/runs/2026-11-06-ADM06-01/report.md (orchestrator generates at run close).
- Resource use: tracker not run by spec-writer (orchestrator-owned); total tokens/cost unavailable until report. No retries or feature correction rounds. Blocking: human spec/plan approval and source-aware compatibility mapping; no feature implementation authorised through this draft.
## 2026-11-06: developer frontend CI maintenance
- Done: restored sidebar tip/companion shortcut in short viewports; Progress reads now depend on the router history-entry key as well as retry state. Existing approved shell/STU-04 contracts and all test assertions retained; both guides updated.
- Validation: isolated full browser suite 473/473 PASS (4.5 minutes, no retries); first reused-local-server run 472 PASS/1 unrelated backend-interference failure; 40 repeated reported cases PASS (20 each), types/lint/build and LF-normalized formatting of 108 frontend files PASS. Raw format check reports existing Windows CRLF warnings. Historical Progress flake not reproduced before source hardening; no proven original flake mechanism claimed.
- Next: review local commit and rerun remote frontend CI after push (not performed here). No backend or deployment changes.
- Files: styles.css, Progress.tsx, both guides, logs/FrontendCiFix.md and workflow records.
- Resources: single-session small-fix exemption; no agents/invocation manifest/report/tracker. Inherited Codex model/effort; exact tokens/cost/elapsed attribution unavailable. Diagnostic/configuration recoveries and profile warning; no new feature correction rounds. See session log for run timing caveats.
