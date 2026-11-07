# Remaining admin UI baseline rollout - 2026-11-07

User requested the other admin screens follow workflow/ui-design.md, with specs and docs updated, excluding the ADM-04 surfaces already redesigned. Worked as one developer for scoped presentation maintenance; no delegated feature pipeline or independent verification claim.

## Result

- ADM-02: padded saved-form/response rows; sectioned editor (Form details, Association, Questions); separate form overview/question panels; clearer primary actions; recipient search/selection grouping, persistent selected count and bounded review lists; response names first, local semantic timestamps and secondary IDs.
- ADM-05: account discovery/results beside a 360px creation panel, stacking responsively; separate creation/list panels for courses; outlined portal-dialog controls and retained confirmations, focus return, pending guards and existing status/toast behavior.
- ADM-06: separate Report filters and Service-call report panels, UTC range guidance, local collection instants, original ISO attributes, existing keyboard-scrollable wide report and explicit unavailable reasons.
- Scoped styles apply to existing admin preview routes too; sample-only behavior retained. ADM-04 source/tests and recipient Inbox not edited. No new API, background refresh, schema, server authorization or AI behavior.
- Amended existing ADM-02/05/06 specs/plans/tasks, the app-shell preview plan, both guides, security evidence and handoff/resource records.

## Evidence

New tests preceded implementation: missing Form details heading failed before source changes. A first 11-case run passed 10, with one new test using button instead of the existing reply link role; corrected the test to the approved link contract. A broader 178-case run passed 174: two existing ADM-04 failures and two stale ADM-06 single-panel selectors. Updated ADM-06 selector to identify the new result panel; timestamp/row tests were updated to assert semantic ISO values and the documented 80px cards, preserving navigation, hover, counts and security assertions.

Final relevant run: 146/146 PASS in 1.9 minutes, zero retries (ADM-02 feedback/review, ADM-05 access, ADM-06 usage, admin UI coverage and app navigation). Separate focused AI-usage/design run: 55/55 PASS. Typecheck, lint, production build, scoped Prettier and spec checker (3 checked, 0 failed, 0 waived) PASS. Final build uses node_modules/.cache/admin-ui-final-build to avoid clearing the retained ignored baseline export.

44 screenshots captured for 1365px/390px and light/dark, covering ten pages and the audience dialog. Inspected four contact sheets and final original response/form screenshots. New 320px checks verify no page overflow, visible outlines, focus and >=3:1 input-outline contrast. Light secondary text scoped darker for contrast. Screenshots remain ignored under src/frontend/node_modules/.cache/admin-ui-visuals. Full backend and full browser suites were not run; no live AI, user database or .env changes.

Existing ADM-04 issue: adm04-messaging.spec.ts:103 fails waiting for Student 50 after Next. The initial search effect in AdminMessaging.tsx unconditionally resets the page after 300ms, racing a fast Next click. Reproduced on both changed tree and an untouched export of the merge index; source/test/helper are byte-equivalent to the index after line-ending normalization. Receipt-recovery immediate request-count case failed once in broad run and passed alone in both trees. Neither was changed because the user excluded already-redesigned ADM-04. Combined all-suite-green is not claimed.

## Operations and limitations

Used own Playwright servers on 5197/5198 with API_PORT=59999 to avoid developer API traffic. Tests exit their own servers. Existing mocked tests may log expected proxy failures to the unused port. Temporary Playwright config removed. Automatic approval review rejected recursive cleanup of the owned baseline export with blocked by policy; left it ignored at src/frontend/dist/admin-ui-baseline (including its dependency junction), and built elsewhere. No commits/pushes; existing staged merge work and unrelated .claude/worktrees remain.

Tool recoveries: PowerShell console encoding required ASCII/Unicode escapes in generated text; corrected temporary question marks. Two edit scripts used the wrong cwd and failed before writes, then reran from root. Fixed new helper copy to match the existing 160-character form-title limit. Pillow absent; used System.Drawing contact sheets. Standard usage CLI rejected older events in the reused session; used its existing parser/pricing/renderer with exact source/time filtering and identical-row deduplication. No tracker code changed, invented usage or raw provider logs committed.

Usage: workflow/usage/runs/2026-11-07-ADMIN-UI-01/report.md. One developer invocation, metadata-derived session ID, inherited effort, observed gpt-6.1-sol. Manifest created following discovery and before spec/test/source changes. Table and run total inspected. The report is an observed closeout snapshot; complete task totals and cost remain unavailable. No feature revision rounds or delegated-agent retries.
