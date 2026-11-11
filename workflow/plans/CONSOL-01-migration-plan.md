# CONSOL-01: Analytics hub and Feedback hub (migration plan, DRAFT for human approval)

Branch: `feat/analytics-feedback-consolidation` (local, cut from `origin/master` at d637729; not pushed).

## Goal
- **ANA (Analytics)** replaces ADM-01 + ADM-06: one admin area with Health, Feature outcomes, AI usage and Quality sections.
- **FBK (Feedback)** replaces ADM-02 + ADM-03 + ADM-04: one admin area for forms, responses, AI analysis and follow-up.
- ADM-05 (users/courses) is unchanged.
- Analytics shows real data from recorded events only. No mock or sample values; missing data shows "unavailable".

## Strategy: add new, switch over, then delete old
Old features keep working and passing until the new ones are approved. Nothing old is deleted before phase 5.

| Phase | Work | Human gate |
|---|---|---|
| 0 | This plan approved; decisions below answered | **Gate A** |
| 1 | Specs only: `workflow/specs/ANA-01/` and `FBK-01/` (spec, plan, tasks), new user stories and feature-list entries added next to the old ones. Includes UI contract (layout, states, copy). Old specs untouched | **Gate B** (review specs) |
| 2 | Build ANA on existing data (tests first). New `/admin/analytics` hub with tabs; old routes still reachable. Health strip, hourly charts, expand overlay, period selector top right | **Gate C** (try it in the browser) |
| 3 | Build FBK hub as a shell over the existing ADM-02/03/04 backend routes (tabs: Forms, Responses, Analysis, Follow-up). Backend refactor only if needed | **Gate D** (try it) |
| 4 | New event collection (hourly request log with outcome, category, latency; login events; practice-created; attempt start/submit). Migrations + backfill rules. ANA charts switch from "unavailable" to real values | **Gate E** (check real data) |
| 5 | Delete old: pages, routes, specs ADM-01/02/03/04/06, tests that only cover removed code (test coverage moved first, never weakened), old docs sections | **Gate F** (review deletion list before running it) |
| 6 | Docs final pass (UserGuide, DeveloperGuide, UserStories, FeatureList, STATUS), usage report, `logs/` summary, PR into `master` | final review |

Why phase 4 comes after the UI: you asked for the refactor to be approved first. Until phase 4, charts that lack data show a labelled unavailable state, not invented numbers.

## Impact list (to be verified in phase 1)
- Frontend: `pages/AdminAnalytics.tsx` (850 lines), `AdminAiUsage.tsx`, `AdminFeedback*.tsx`, `AdminMessaging.tsx`, services `featureAnalytics.ts`, `aiUsage.ts`, routes in `App.tsx`, nav in `Shell.tsx`.
- Backend: `feature_analytics/`, `ai_usage/`, `feedback*.py`, `feedback_analysis/`, `messaging*.py`. Keep API paths stable where possible to limit churn; renames only if a spec says so.
- Docs: `UserStories.md`, `FeatureList.md`, `UserGuide.md`, `DeveloperGuide.md`, `workflow/STATUS.md`, `workflow/checklist.md`.
- Security: re-run SHR-01/02/05 checks (server-side admin-only on every moved endpoint) and log them in `workflow/security/`.

## Decisions (answered 2026-11-11)
1. IDs: **ADM-07 = Analytics hub**, **ADM-08 = Feedback hub** (old ADM-01..04, 06 superseded until phase 5).
2. Merge ADM-01 and ADM-06 scope: yes.
3. Full multi-agent workflow for ADM-07; lighter for ADM-08 shell.
4. Thresholds: red above 5%, amber 2-5%, no colour below 20 requests.
5. Hourly buckets stored UTC, shown in local time. UI clean and minimal.
6. Hourly request log retention: 30 days.

## Original questions
1. **IDs.** New IDs `ANA-01` and `FBK-01`, or keep the `ADM-` prefix (e.g. `ADM-01` rewritten, others retired)? Recommended: new IDs; old ones marked "superseded" until phase 5.
2. **Scope merge.** ADM-01 says AI call counts belong to ADM-06. The merged ANA spec removes that boundary and puts both under one hub. OK?
3. **Orchestration.** Run phases 1-4 with the full multi-agent workflow (spec-writer, test-designer, developer, verifier, token report per run), or lighter single-agent for the FBK shell? Recommended: full workflow for ANA; lighter for FBK shell since it mostly moves UI.
4. **Thresholds.** Red above 5% failure rate; amber 2-5%? Minimum sample size before colouring (e.g. 20 requests)?
5. **Timezone** for hourly buckets: store UTC, display in browser local time?
6. **Retention** of the hourly request log (e.g. 90 days)?
