# ADM-05 integration and verification — 2026-11-06

The user authorised updating the agreed feature documents, implementing ADM-05, committing locally and providing test instructions. During implementation they supplied expanded admin stories and requested resynchronisation. Commit `1b0f9dc` preserved their ADM-01–04/ADM-06 story text exactly, restored the agreed fixed-role ADM-05 scope and aligned FeatureList summaries. Other admin workflows were not implemented.

## Workflow and changes

- Approved contract/start commit: `3a35aa2`; independent tests committed `f0162de` before source visibility in a separate worktree. Account POST returned 404 in the initial RED check.
- Implementation: `5014027`; fixed-role account creation, lifecycle/session controls, course creation/access, admin screens and guides. No role-changing API or password reset/change flow.
- Correction round 1: `1811523` stabilised accessible names. Subsequent mobile rows use a stacked layout; the earlier screenshot's identity loss resulted from horizontal scrolling after Manage, not an initially hidden column.
- Integration amendment: `45e00f6` requires an atomic default General topic for new courses, since existing teacher publication requires a topic and no topic-creation interface exists. Independent regression `84bc160` was RED before implementation `53ca096`. Additional tests cover actual teacher publication/student reading/revocation and rollback if topic insertion fails.
- Correction round 2: late-401 regression `0363e9c` was RED before `07deb57`. Generic requests now invoke the unauthenticated callback only for their originating session generation. A delayed session-A response cannot sign out a newly authenticated session B. Two application correction rounds used; no further application changes after `07deb57`.
- Historical seed operations now use core columns compatible with their pinned migrations. Two existing publication migration tests were corrected in `d5b6e1e` to target the publication revision and isolate its populated-data downgrade guard; legacy data and rollback assertions were retained.

## Validation evidence

Independent designer: 87 ADM-05 backend cases and 14 ADM-05 browser cases PASS. Existing browser run: 374 PASS plus three artifact-directory errors; the same three cases PASS on isolated-output rerun. Existing backend run: 950 PASS, two obsolete publication-migration failures and seven Windows TEMP setup errors; corrected migration cases and all seven TEMP cases PASS. Designer focused backend run: 89 PASS (87 new plus two publication migration tests).

Strongest read-only verifier: full backend collected 966 cases before the final two integration tests were added, returning 957 PASS, the same two old migration failures and seven TEMP errors. After the test corrections, all nine affected cases PASS with a unique accessible basetemp. All three General-topic integration cases independently PASS. Across full and focused runs all 968 final backend cases are covered. Concurrent archive/archive and disable/archive probes each left exactly one enabled administrator and rejected the revoked actor.

Typecheck, lint, build, Python compilation and diff checks PASS. Repository-wide speccheck: six checked, zero failed, twelve pre-existing waivers. Default Windows format checking reports CRLF differences in 91 files; the same complete Prettier check with `--end-of-line auto` PASS, with no formatting rewrites. CI itself was not run remotely.

Final strongest-verifier verdict: PASS at source `07deb57`. Exclusive full frontend run: 391/391 PASS in 4.3 minutes, including all 14 ADM-05 browser cases and the late-401 regression. No remaining ranked defects. The original stale-session reproduction now preserves the newer session with zero unauthenticated callbacks. Final typecheck/lint/build independently PASS.

Browser-run recoveries were environmental: concurrent runs initially shared output directories and reused servers owned by another short-lived test run. Final verifier run has exclusive ownership of ports 5173/5174 and a unique output directory. No application assertions were weakened to recover these runs.

## Security and limits

Checked cookie-only admin identity, wrong roles, CSRF/Origin, strict fields/identifiers, immutable roles, password hashing/no credential responses, reserved archived email, all-session invalidation, retained learning/authorship records, teacher/student course boundaries, idempotence and concurrent mutations, revoked actors waiting for locks, late AI account revocation, no-store responses, output/session isolation, default-topic publication and atomic rollback. Existing answer-release and provider controls are reused; no new model calls. The static practice/companion fixtures still have no course mapping, and ADM-05 does not claim new course-grounded retrieval or TEA-05 analytics.

Automated database work used isolated PostgreSQL schemas. No developer `.env`, developer schema, real account credentials, live LLM, remote Git push, PR, deployment or unrelated `.claude/worktrees` changes. Docker Desktop and the repository PostgreSQL service were started for tests. Disposable independent worktree remains available for audit.

## Resources

Run manifest/report: `workflow/usage/runs/2026-11-06-ADM05-01/`. Orchestrator owns tracking. Spec/developer/designer use inherited Codex model/effort; verifier explicitly requested `gpt-6-astra`, high, under the strongest-verifier role requirement. Child environment session IDs were inherited from the parent and cannot independently attribute child usage; unavailable measurements are not zero usage. One developer launch was interrupted by the user's story-sync update and explicitly resumed. Test-command/environment recoveries are recorded above; they are distinct from the two application correction rounds.

Tracker run-report succeeded after expanding the parent attribution window to its earliest observed session usage (the original exact-run window was rejected because earlier same-session rows lay outside it). Matched parent subtotal: 543 requests, 598,671 input, 59,384,448 cache-read, 137,384 output including 27,251 reasoning; prices/cost unavailable. This includes the earlier advisory/decision discussion and is not a complete agent-run total. Child rows are explicitly unavailable in the annotated generated report.
