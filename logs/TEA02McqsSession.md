# TEA-02 MCQ generation session — 2026-11-02

## Request and approved decisions

User approved the Teacher Increment4 plan: create feat/tea02-generate-mcqs from updated master; generate/save/reopen exactly3 single-answer MCQs,4 choices each, with correct choice and explanation. Read-only/unpublished; editing, assembly and publication deferred. TEA-03 merged PR12, local master3069053. No live calls without separate approval and no push/PR/master merge.

## Workflow

- Orchestrator inspected clean master, requirements/current notes/client and Variant B instructions; baseline412 backend tests and frontend types/lint passed.
- Spec writer produced approved spec/plan/tasks, committed277aced65540f08781402cc2440943e2f4d4cdd4 before source work.
- Developer works in main run folder; independent test-designer in sibling work/mcq-tests from the same recorded start. Designer reads contract/threat model/stories/tests only until test commit.
- Tests use existing isolated learnswe-tea01-test container (started this session), unique schemas and temporary files; no developer DB or private source data. Shared client and provider are mocked.

## Verification and handoff

- Developer implementation committed0567212941d9c6b35ce91b33016fc7f22246ca80 before independent-test visibility. Existing backend412, types/lint/format/build passed; browser131 passed plus the expected obsolete MCQ-unavailable assertion.
- Independent tests committedaf54ee4877788342e30c940a2b86081e866f22b7 before source visibility; implementation merged4070fc9 in test worktree. Fullbackend478 passed, including66 new cases.
- Initial browser145/147: one new explanation locator assumed a separate text node although the label/content share a paragraph; one inherited companion test made an unmocked external request, whose503 composer restoration raced typing. Designer corrected locator without weakening expected text and added the existing fake companion API only to that test. Corrections79b5aa0 preserve assertions. Full browser147 passed (15 new), types/lint/format/build passed.
- Parent fast-forward integrated79b5aa0e5998dd539164da39b3745440760d7c81; strongest read-only verifier started on that revision. Parent inspected four populated long-content screenshots at390/1440 in light/dark: source/title/IDs/choices wrap, no horizontal overflow, visible keyboard focus. Generated screenshots remain ignored.
- Shared llm_client.py diff against master is empty. No provider call or deployment checked. Exact usage/cost unavailable; do not infer billed figures. Final verifier findings and correction rounds pending.


## Correction round1 — stale generation after history round trip

Strongest independent verifier reran478 backend/147 browser/types/lint/format/build, then confirmed an uncovered AC8 sequence: questions/courseA with no batch → saved batchA → hold generation → Back(no batch) → Forward(batchA) → release response. Scalar view-key equality revived the old request, allowing stale success to navigate to batchC or stale failure to show an alert. No other defect established in first pass. Additional role-change and source-course-change probes during model work returned403/404 and persisted zero batch/question rows.

Independent designer committed aaa55bc380dd10c6445aadbada2eb9f399dc9515 before the source fix. Both success/failure variants were RED on the original implementation, preserving batchA/no stale message assertions. Developer authorised to add monotonic navigation invalidation only after that RED evidence. Correction and re-verification pending.


Round1 source fix198c3f47f72d5ff533fb7492511f1b8201e428a6 adds a monotonic navigation epoch updated in a layout effect, checked for both success/error before showing or navigating. Developer45 focused browser cases and types/lint/format/build passed. Independent designer merged source into unchanged regression branch at3ebc6462b65c09e71a7fa141763409c402e2f9c4: both regressions GREEN; full149 browser plus types/lint/format/build passed. Parent fast-forward integrated3ebc646 and requested final read-only recheck. Backend unchanged from verifier's fresh478-pass revision. No tests weakened after RED.

## Local test instructions

1. From src/backend, run `uv run --env-file .env alembic upgrade head`; restart the backend and refresh the frontend.
2. Explore Teacher demo → AI content studio → Practice questions.
3. Select a course and an uploaded short UTF-8 text/text-based PDF, then Generate3 draft MCQs. This manual generation makes a real SoC request using existing local settings; agents did not make one.
4. Verify three questions, choices, correct answers, explanations and Unpublished draft · Review required. Reload/reopen a saved batch. Existing Study notes editing remains available.
5. Inputs remain limited to8,000 extracted characters/100PDFpages; output validation rejects unusable/truncated responses rather than repairing or saving partial questions. Retrying after a lost response can create a second saved batch.


## Final verdict and limits

Strongest independent verifier PASS at3ebc6462b65c09e71a7fa141763409c402e2f9c4, no open findings after one correction round. Fresh final17MCQ browser/type/lint/format checks passed; designer full149browser/build passed; backend unchanged from strongest verifier's fresh478pass. All acceptance tasks complete. This final handoff commit changes documentation/workflow evidence only. No live LLM quality, hosted CI or deployment tested. No secrets, .env, developer database or private uploaded files touched, no push/PR/master merge. Feature branch retained for human publishing approval; test container started for isolated verification remains available. Editing questions, assembly/publication/student release and production auth remain later increments.
