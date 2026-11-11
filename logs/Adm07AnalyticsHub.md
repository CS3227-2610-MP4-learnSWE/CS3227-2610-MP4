# ADM-07 Analytics hub: working-session summary, 2026-11-11 to 2026-11-12

Orchestrated phases 2, 4 and 5 of ADM-07 on `feat/analytics-feedback-consolidation` (phase 1 specs were approved earlier). Each phase ended at a human gate: C (hub in the browser), E (real data, plan amendment), F (deletion list: `/admin/ai-usage` redirects; map assertions first).

## What was done
- **Phase 2 (run 2026-11-11-ADM07-02):** new `/health`, `/hourly`, `/daily`, `/chatbot-users` and `/usage?include_rows` on existing tables, partial coverage with `data_starts_on`, hub UI at `/admin/analytics`, old page moved to a legacy route. One fix round (a 401 on any hub request now ends the session). Verifier PASS.
- **Phase 4 (run -03):** migration `20261111_adm07_events` (four tables, 30-day backfill), hooks at the host call sites, retention purge (30 d request log, 400 d sign-ins), the `ai_usage.cleanup` command, queries switched to the new tables. Verifier round 1 found one blocking defect (start key hid the backfill; plan line 21 amended by the orchestrator); round 2 found no product defects.
- **Phase 5 (runs -04, -05):** retained criteria and a deletion list written first, assertions mapped and ported, then the legacy page, old AI usage page, old browser tests and ADM-01/ADM-06 specs deleted; `/admin/ai-usage` redirects to `/admin/analytics`. Verifier PASS.

## Refinements after browser review (2026-11-12, outside the gated runs)
Done directly at the user's request, no multi-agent run: header icon refresh; success-rate KPI tiles with inverted chips; larger numbers; contrasting section and subheader styles; click-to-open chart cards, two per row; users totals as cards; table borders and sort arrows; Quality cards; AI usage labels without IDs; AI usage collection switch (`PUT /api/admin/ai-usage/coverage`, tests added); `dev_seed.py` and `feature_analytics.seed_dev`. Spec AC43-AC47, plan and tasks (P7) updated. Checks: backend ADM-06 usage and switch tests 57 passed on a throwaway database; Playwright mocked adm07 and admin-ui 243 passed; typecheck and lint clean. Not run: the full backend suite, and a real-browser check of the last two rounds.

## Checks (as run, not re-run for this log)
Backend ADM-07/ADM-01/ADM-06: 1130 passed (phase 5 verifier). Host suites touched by wiring: passed in phase 4 (954 + 417 across two runs, not re-run after phase 5). Playwright mocked adm07 + admin-ui: 242 passed. Typecheck and lint clean. The full backend suite was never run end to end.

## Not done / human items
- `ai_usage.cleanup --dry-run`, review, then `--apply --approved-by` (P4-10c): not run by any agent. The migration has not been run on a real database by an agent.
- Deviations: the orchestrator amended plan.md line 21 and edited one test assertion directly (recorded in `workflow/experiments/resource-log.md`). Usage reports overlap in their orchestrator rows (same session), so they must not be summed.
- Backend test docstrings still cite the deleted ADM-01 plan (history only).

## Usage reports
`workflow/usage/runs/2026-11-11-ADM07-02/`, `-03`, `-04`, `-05`, `-06` (`report.md` in each).

## Suggested PR description (target `master`)
Title: `feat(adm07): Analytics hub, event collection, retire ADM-01/ADM-06 UI`

Merges the consolidated admin Analytics hub (ADM-07). Apply Alembic migration `20261111_adm07_events` before running the updated backend. After deploy, run `ai_usage.cleanup --dry-run` and review before any `--apply --approved-by`. Specs: `workflow/specs/ADM-07/`. Tests: see the checks above; CI will run the rest.
