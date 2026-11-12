# ADM-08 phase 5 test mapping (task P5-2, AC22, AC25)

Run 2026-11-12-ADM08-03. Legend: **Cov** already covered by an existing adm08 test; **Port** repointed to hub paths in an `adm08-ported-*` spec with assertions unchanged (adjustments listed); **Sup** superseded, with reason; **Keep** unchanged (student/teacher side, or no removed admin route). All backend tests: **Keep**.

Granularity: one row per test (parameterised loops are one row). "Port" tests of a file are all tests of that file unless noted. Every ported spec passes against the current build: 132 passed, 0 failed (`npx playwright test --project=mocked tests/adm08-ported`). The redirect spec `adm08-redirects.spec.ts` (AC21) is EXPECTED TO FAIL until P5-5: 35 passed, 53 failed (the passes are the cases where the old page already ends at a matching URL or wrong-role/anonymous cases).

## Ported-file overview and helper handling

| New file | Source | Notes |
|---|---|---|
| adm08-ported-adm02Api.ts, adm08-ported-adm03Api.ts, adm08-ported-adm04Api.ts | adm02Api.ts, adm03Api.ts, adm04Api.ts | Copies. URL constants point to hub (`NEW` = `/admin/feedback-hub/follow-up`, `REPLY` = hub reply URL). Request logs leave out the hub's three mount-time count requests via `adm08-ported-hubCounts.ts` (first count-shaped forms and analyses GET after each full load, and all `followup-counts`), so old "N requests" assertions keep their meaning; adm04 helper answers `followup-counts` without recording. Originals stay until P5-5; after deletion the originals' respondent-side users (adm02-feedback respondent tests, adm04-inbox, admin-ui, stu05-06 etc.) still import `adm02Api.ts` and `adm04Api.ts`, so P5-5 must keep `adm02Api.ts` and `adm04Api.ts` (rename the ported copies back or keep both) and may delete `adm03Api.ts`. |
| adm08-ported-hubCounts.ts | new helper | See above. |

## adm02-feedback.spec.ts (split at P5-5: respondent tests stay, admin tests deleted after port)

| Test (line) | Class | Target / reason |
|---|---|---|
| 26 AC01-03 six question controls (respondent) | Keep | student page |
| 67 AC22 autosave restores (student, teacher loop) | Keep | respondent |
| 96, 131 AC22 draft load / debounce | Keep | respondent |
| 158 AC25 draft save failure loop | Keep | respondent |
| 177, 217, 233 AC25 stale two-tab, leaving flush, failed flush | Keep | respondent |
| 246 AC04_24 required validation | Keep | respondent |
| 285, 313, 335 AC24 submit tests | Keep | respondent |
| 354 AC15 draft closure | Keep | respondent |
| 369 terminal direct open loop; 398 load errors loop; 412 15 s timeout; 424 logout clears draft | Keep | respondent |
| 445 wrong role loop: row STUDENT `/admin/feedback` | Port | adm08-ported-adm02-feedback "ADM-02 wrong role student /admin/feedback-hub/forms ..." (also Cov adm08 AC11); rows ADMIN and TEACHER visit the student form page: Keep |
| 455 AC09-10 inbox links; 474 inbox empty state | Keep | student inbox |
| 487 AC01-06 admin creates draft | Port | adjusted: after create the forms GET count is 1, not 0 (AC29 adds exactly one forms-count refetch; Cov adm08 "AC29 create form adds exactly one forms-list GET") |
| 530 AC01-03 authoring loop (5 kinds) | Port | unchanged |
| 593 AC09 audience review precedes publication | Port | unchanged (also Cov adm08 J1 in part) |
| 637 AC14 close requires confirmation | Port | unchanged |
| 667 AC18-20 response snapshot harmless text | Port | unchanged |
| 699 admin form and response rows full-row links | Port | unchanged |
| 763 admin empty response review | Port | unchanged |
| 774 responsive resumed draft (student) | Keep | respondent (inside the width loop with the admin test) |
| 802 responsive admin editor audience and response snapshots | Port | unchanged |
| 867 admin failed draft save preserves editor fields | Port | unchanged |
| 890 mobile empty dropdown label | Keep | respondent |

## adm02-review.spec.ts (all admin; delete after port)

| Test | Class | Target |
|---|---|---|
| 14 uncertain publication cannot be replayed | Port | adm08-ported-adm02-review, same name |
| 77 successful create hands off to detail without a follow-up GET | Port | unchanged (the one forms count refetch is outside the detail screen's own requests; passes unchanged) |
| 103 transient submit failure recovers | Port | unchanged |
| 142 lost access 401/403/404 loop | Port | unchanged |
| 178 audience role floating label | Port | unchanged |
| 213 rejected draft save names the field | Port | unchanged |

## adm03-select.spec.ts, adm03-result.spec.ts, adm03-history-delete.spec.ts, adm03-response-delete.spec.ts (all admin; delete after port)

| Old test group | Class | Target / adjustment |
|---|---|---|
| select: wrong role / anonymous (14) | Port | adm08-ported-adm03-select, unchanged (also Cov adm08 AC11, redirects spec) |
| select: AC5 page load, AC18 Select all, Clear selection/Refresh, Generate disabled/Starting, request_id kept, Generate failure loop, load failures, no responses, 320/390 overflow | Port | unchanged; the hub count requests are excluded by the helper |
| select: AC1 explicit ticks ... Generate replaces history | Port | adjusted only for the URL the test navigates back to: `/admin/feedback` becomes `/admin/feedback-hub/forms` (the test starts on the hub Forms tab) |
| result: AC24 charts at once, AC22 sampled notice, AC2-4 complete result, evidence direct open, evidence extra-GET failure loop, AC6/AC24/AC31 failed AI loop, analysis_not_found, load failure Retry, 7 polling tests, 401 while loading, wrong role on result URL, 320/390 overflow | Port | unchanged, hub URL `/admin/feedback-hub/analysis/{id}` |
| history-delete: AC30 previous analyses, empty/status/link, load failure, AC38 dialog, confirm from list, consistency, delete from result, failure loop, 404, 401, retry | Port | unchanged except "confirm from the list": the assertion "no GET after a delete from the list" becomes "exactly one analyses GET (the AC29 count refetch)" (Cov adm08 "AC29 generate analysis and analysis delete each add exactly one analyses GET") |
| response-delete: AC48 dialog texts, closed form text, confirm single DELETE, AC49 failure loop, retry, 404, 401 | Port | unchanged; end URL regex `/responses$` becomes `/responses/{form_id}$` (hub list URL, path map) |
| Overlap already Cov (kept as Port, no deletion of coverage): J4, J5, J6 in adm08-journeys cover the same flows at journey level | Cov (partial) | not sufficient alone, so the full files are Port |

## adm04-messaging.spec.ts (admin; delete after port)

| Test group | Class | Target / adjustment |
|---|---|---|
| AC01-05 feedback entry (reply), AC06-08 announcement navigation, AC06 selected ids persist, AC13 unchanged search, debounced search, AC12 edit restores, reload after lost send, uncertain send, Back/Forward/refresh recovery, preview failure loop, send failure loop, in-memory invalidation loop, recovered loop, empty Subject/Message, zero recipients, recipient network failure, 15 s send timeout, AC11 wrong role/anonymous loop, expiry from send, logout/other account, mobile long text | Port | adm08-ported-adm04-messaging, assertions unchanged except: (a) final "Back to feedback" URL regex now `/responses/{form_id}/{response_id}$`; (b) the old nav link "Announcements" is replaced by the hub steps "Feedback hub" link then "Follow-up" tab, because that is the hub route to the composer (the URL assertion is the hub follow-up URL); (c) the helper answers the hub's follow-up count request without recording it |

## adm04-redesign.spec.ts

| Test | Class | Target |
|---|---|---|
| 12 composer separates recipient search and outlined inputs | Port | adm08-ported-adm04-redesign (composer at hub follow-up) |
| 43, 75, 122 badge / refresh / late summary (student inbox badge) | Keep | respondent side |
| 149 loop: responsive composer and inbox (3 variants) | Port | adm08-ported-adm04-redesign (composer part on hub; its inbox part is unchanged and runs in the same test) |

## adm04-inbox.spec.ts

All tests: **Keep** (student and teacher inbox, no admin route).

## admin-ui.spec.ts

| Test | Class | Target / reason |
|---|---|---|
| ADM-02 baseline editor outlines 320px (light, dark) | Port | adm08-ported-admin-ui, `/admin/feedback-hub/forms/new` |
| ADM-05 account discovery (light, dark) | Keep | `/admin/users` and `/admin/courses`, not removed |
| ADM-02 baseline audience selection | Port | adm08-ported-admin-ui |
| ADM-02 baseline response dates | Port | adm08-ported-admin-ui |
| admin preview overview / forms / usage at 320px | Keep | demo preview pages that stay (iteration `responses` is the demo Feedback insights page: see below) |
| admin preview responses at 320px (loop iteration `responses`) | Sup, deletable iteration | covers only the demo Feedback insights page, which is removed (AC25); remove `"responses"` from the loop |
| admin baseline visual coverage (4 variants): rows users, courses, analytics | Keep | not removed pages; in the ported file the rows are dropped because only feedback rows are ported; the original keeps them |
| admin baseline visual coverage: rows forms, editor, form, responses, response | Port | adm08-ported-admin-ui on hub paths |
| admin baseline visual coverage: row `analysis` = `/admin/responses` | Sup, edit | the demo page; delete the row (screenshot-only plus heading and overflow checks, no behaviour); the hub analysis page is covered by adm08 AC15 overflow tests and adm08-ported-adm03 320/390 tests |

At P5-5: edit `admin-ui.spec.ts` in place (remove the ADM-02 admin tests and rows now ported, keep ADM-05 and the preview loop minus `responses`).

## app.spec.ts and shell-confirmation.spec.ts (demo "Feedback insights" and demo admin routes)

Search result: the label "Feedback insights" is used by `shell-confirmation.spec.ts` (nav click) and `adm08-hub.spec.ts` (AC9 asserts the link visible); the demo route `/admin/responses` is exercised by `app.spec.ts` and `admin-ui.spec.ts`. No test asserts the demo page's own text ("Listen a little closer.", "Fixed sample") or its sample data. No test exists that covers only that page, so there is **no whole-test deletion** for it; only entries are removed.

| Test | Class | Action |
|---|---|---|
| app.spec "admin routes render on direct navigation and reload" (list contains `/admin/responses`, also `/admin/forms`, `/admin/announcements`, `/admin/usage`) | Keep, edit | remove `"/admin/responses"` from the route list; the other routes are unchanged. After AC25 the nav lacks "Feedback forms" and "Announcements" but their anonymous demo routes are not in the removal scope (spec "Out of scope": only the Feedback insights item), so keep. If P5-5 also removes those demo routes, remove them from the lists too |
| app.spec "desktop and mobile layouts render without overflow in both themes" (route list contains `/admin/responses`) | Keep, edit | remove the `/admin/responses` entry (Sup for that entry: demo page only) |
| app.spec "... /admin/announcements ... Preview announcement" test (line 185-200, demo announcements preview with no session) | Keep | the demo announcements page is not in the removal list; if removed later it is a Sup |
| shell-confirmation "shr01 shell tip dismisses ..." (clicks "Feedback insights") | Port | adm08-ported-shell.spec.ts, only the clicked link changes to "Feature Analytics"; delete the original test (or edit it the same way) at P5-5 |
| other shell-confirmation tests | Keep | unaffected |
| adm08-hub "AC9 nav link ... old links remain" | Sup after P5-5 | lists "Feedback forms", "Announcements", "Feedback insights" as visible; P5-5 flips it to `toHaveCount(0)` per AC25 (new test written by the test owner, not by weakening) |
| adm08-hub "AC10 an old URL shows no tab bar ..." and adm08-journeys "AC27 the link is absent on the old route", "AC29 the same actions on the old routes send no count request" | Sup after P5-5 | their precondition (old pages render) ends with AC21; coverage moves to `adm08-redirects.spec.ts`. They must be removed in the same step as the redirects, not before |
| adm08-journeys `OLD_ADDRESS` guard (`expectNoOldAddress`) | Keep | still valid |
| Overview dashboard link `to="/admin/responses"` | note | the demo overview page links to the demo page; the link and sample data share the module deleted in P5-3, so P5-3 must repoint or remove that link (no test pins it) |

## Other tests that mention removed routes

| Test | Class |
|---|---|
| adm07-redirect.spec.ts, adm07-* | Keep (analytics, unrelated) |
| stu05-06-*, tea06-inbox, student/teacher specs | Keep |

## Redirect coverage (AC21) in adm08-redirects.spec.ts

For each of the 12 old URLs of the redirect map: final URL on a fresh load for no query, `?x=1` and `?x=1#part`; replace-not-push (history length +1 and Back lands on the page before); `?review=` kept for the reply and `/admin/announcements/new`; `/admin/feedback/analysis` not treated as a form id (no `forms/analysis` request); no not-found alert or 404 text for any old URL; student, teacher (12 URLs each) go to their home with zero feedback requests and Back does not return; anonymous (12 URLs) goes to `/login` with zero requests. Current result: 35 pass, 53 fail (expected). Anonymous and wrong-role cases that already pass do so through the old route guard.

## Backend tests

All of `src/backend/tests/` (including `adm02_helpers.py`, `adm03_fixtures.py`, `adm03_helpers.py`, `adm04_helpers.py`): Keep.

## Ordering notes for P5-5

1. Add redirects, run `adm08-redirects.spec.ts` (must pass).
2. Delete or edit the Sup-after-P5-5 tests listed above in the same commit.
3. Delete adm02-review, adm03-*, adm04-messaging, the admin tests of adm02-feedback and adm04-redesign, the ported admin tests of admin-ui and the first shell test only after the ported specs pass.
4. Keep `adm02Api.ts` and `adm04Api.ts` for the remaining respondent tests (or fold the ported copies into them and update imports); `adm03Api.ts` can go once adm03 originals are deleted.

## P5-5 final state (test side, 2026-11-12, Gate F decisions applied)

Status: test edits done and committed on the test-designer branch; typecheck and lint clean. Playwright was not run: the edited tests expect the redirects and deletions and fail against the current build until the developer's change is merged.

| Change | Final state |
|---|---|
| Defect 1 | `adm08Api.ts` imports `analysis`, `uuid`, `Analysis` from `./adm08-ported-adm03Api` (identical builders). `adm03Api.ts` deleted. |
| Defect 2 / D2 | `app.spec.ts` test "teacher generation is real while admin messages remain explicit previews" (185-200) is **Sup** for its second half: the anonymous demo `/admin/announcements` composer is deleted and the route redirects to `/login` (AC21, Gate F D2). The teacher-generation half is kept; the test is renamed "teacher generation is real". `/admin/responses` and `/admin/announcements` removed from both route lists. The anonymous `/admin/announcements` ends-on-`/login` expectation already exists in the `adm08-redirects.spec.ts` anonymous loop (the redirect map includes `/admin/announcements` and `/admin/announcements/new`), so no new test was needed for it. |
| D1 | New in `adm08-redirects.spec.ts`: `/admin/responses` ends at `/admin/feedback-hub/forms` (plain, `?x=1`, `?x=1#part`), replaced not pushed, student and teacher go home with zero requests. |
| Whole files deleted | adm02-review, adm03-select, adm03-result, adm03-history-delete, adm03-response-delete, adm04-messaging specs (ports checked in the deletion list: equal titles and expect counts) and `adm03Api.ts`. |
| `adm02-feedback.spec.ts` | Admin tests removed (create draft, authoring loop, audience review, close, response snapshot, row links, empty review, responsive admin test, failed draft save). Respondent tests and the wrong-role loop (STUDENT row `/admin/feedback` still ends at the student home, because the role guard runs before the redirect) kept. Unused imports dropped. |
| `adm04-redesign.spec.ts` | Composer test (12) and the responsive composer-and-inbox loop (149) removed (both ported); the three badge tests kept. |
| `admin-ui.spec.ts` | ADM-02 tests (editor outlines, selection across search, response dates) removed; `responses` removed from the preview loop; visual rows forms, editor, form, responses, response, analysis and the audience-dialog branch removed (rows users, courses, analytics kept). |
| `shell-confirmation.spec.ts` | Tip-dismiss test deleted (ported as `adm08-ported-shell.spec.ts`). |
| `adm08-hub.spec.ts` | AC9 now expects "Feedback forms", "Announcements", "Feedback insights" `toHaveCount(0)` and "Analytics", "Feature Analytics" visible. AC10 "old URL shows no tab bar" removed: the precondition (old pages render) ends with AC21; coverage is `adm08-redirects.spec.ts`. |
| `adm08-journeys.spec.ts` | Removed AC27 "link is absent on the old route" (no old route renders a screen) and AC29 "same actions on the old routes send no count request" (old routes redirect; the AC29 hub tests remain). `OLD_ADDRESS` guard kept. |
| Comment references | `adm03_helpers.py:1`, `test_stu05_06_access.py:3`, `adm08-ported-adm03Api.ts:12`, `stu0506Api.ts:8` point to `workflow/specs/ADM-08/retained-criteria.md` (`adm03Api.ts` is deleted). |
| Kept | `adm02Api.ts`, `adm04Api.ts`, `adm04-inbox.spec.ts`, all `adm08-*`. |

Defect 5 (non-blocking, recorded): `adm08-ported-adm04Api.ts` omits every `followup-counts` request from its request log, and `adm08-ported-hubCounts.ts` omits the first count-shaped forms and analyses GET after each load. The ported specs therefore cannot see a missing or extra count refetch; the adm08 AC26 and AC29 tests in `adm08-hub.spec.ts` and `adm08-journeys.spec.ts` cover that.

Sidebar tip (Gate F D3/D4): the tip text "Explore feedback" linking to `/admin/feedback-hub/forms` has no pinning test (the only test that clicked the old link was deleted; the ported shell test clicks "Feature Analytics"). Not added, to avoid asserting beyond the written criteria; tell the orchestrator if a pin is wanted.
