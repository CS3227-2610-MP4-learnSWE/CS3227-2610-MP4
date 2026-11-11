# ADM-07 phase 5: deletion list for Gate F (nothing below has been deleted)

Source: read-only verifier inventory, 2026-11-11, branch feat/analytics-feedback-consolidation. Retained criteria: `retained-criteria.md` (its per-criterion test mapping is a best guess from file names and must be confirmed before any test file is deleted).

## Delete (after the listed checks)
1. `src/frontend/src/pages/AdminFeatureAnalyticsLegacy.tsx`, its lazy import and route in `App.tsx`. Low risk; removes the duplicated Quality code. Then remove service exports used only by it (confirm with typecheck). Keep `hooks/useAnalyticsLoad.ts` (used by `useAnalyticsBlock.ts`).
2. Frontend tests `adm01-analytics.spec.ts`, `adm01-privacy.spec.ts`, `adm01Api.ts`. Medium risk: first map every assertion (esp. Quality-section privacy UI) to `adm07-analytics.spec.ts` / `adm07-p4-values.spec.ts`; move any without an equivalent, unchanged.
3. `src/frontend/src/pages/AdminAiUsage.tsx`, the `ai-usage` case in `Admin.tsx`, the nav entry in `data.ts`, unused `.ai-usage-*` CSS, test `adm06-usage.spec.ts` (after mapping its privacy/unavailable assertions), and the ADM-06 test and `["usage", "/admin/ai-usage"]` row in `admin-ui.spec.ts`.
4. Specs `workflow/specs/ADM-01/` and `workflow/specs/ADM-06/`, only after the retained-criteria test mapping is confirmed; rewrite `docs/FeatureList.md` lines for ADM-01/ADM-06 and the `docs/UserStories.md` cross-references so nothing dangles; grep `workflow/` for links to the deleted specs.
5. Docs: remove the "ADM-06" and "ADM-01" user-guide sections and legacy sentence; update DeveloperGuide (legacy page note, ADM-01/ADM-06 sections; keep backend descriptions of /usage, /generation, /quality, /ai-usage under ADM-07).

## Keep (do not delete)
- `src/frontend/src/services/aiUsage.ts` (used by the hub's AI usage section).
- Backend `GET /api/admin/ai-usage` and its no-store middleware; `/usage` `include_rows` logic (part of the approved ADM-07 contract, AC24).
- Backend tests: `test_adm01_{access,concurrency,cross_user,generation,hooks,privacy,privacy_dispatch,privacy_model,quality,usage}.py`, `test_adm06_{migration,transport,usage}.py`, helpers `adm01_{fixtures,helpers,grading_helpers,tea02}.py`, all `test_adm07_*` and `adm07_helpers.py`.
- Frontend tests `adm07-analytics.spec.ts`, `adm07-p4-values.spec.ts`, `adm07Api.ts`, `admin-ui.spec.ts` (edited).

## Decision needed from the human
- What should `/admin/ai-usage` do after deletion: 404, or redirect to `/admin/analytics`? (Not stated in spec or plan.)
- Approve deleting items 1-5 once the test-assertion mapping is done, or delete only the pages/routes now and keep the old specs and old browser tests until the mapping is verified.
- ADM-06 AC12 in retained-criteria says ADM-03 is uninstrumented; check against code before relying on it.

## Gate F decisions recorded
- 2026-11-11, human: `/admin/ai-usage` redirects to `/admin/analytics` after the old page is deleted.
- Still open: delete old browser tests and specs only after the assertion mapping is verified (recommended), or remove pages/routes now.
