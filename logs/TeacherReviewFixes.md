# Teacher review corrections — 2026-11-02

User authorised necessary fixes for all four Ponytail findings: note-generation lifetime, invalid generated Unicode, invalid upload titles and duplicated studio lifecycle. Approved corrective contract committedd02418bc43d5d9a791e7bc9bbbe09cfaec93d82d on existing feat/tea02-generate-mcqs branch. No new schema/API/provider/auth scope.

Independent test-designer starts at that commit in sibling work/teacher-review-tests, writes/commits RED regressions before app changes. Developer inspects/designs while waiting for RED; owns source/product guides, not independent tests/workflow logs. Parent owns session/security/resource/handoff records. Strongest verifier reviews integrated result. No live calls, developer data/.env, push/PR/master merge. Exact resource totals unavailable.

Verification in progress; final evidence follows.

## RED evidence

Independent tests292af7d committed before source changes. Four browser regressions failed as expected: stale success navigated to an obsolete generated draft, stale failure showed an alert after course round trip or draft history round trip. Backend four failures: generated NUL503 instead of502, generated high/low surrogate UnicodeEncodeError, invalid NUL title503 instead of422. Positive control with200 astral title characters and1999 astral note characters passed. Docker Desktop/test container were stopped; parent started Docker Desktop and existing learnswe-tea01-test, then backend RED succeeded. No developer database used. Developer authorised source edits only after this evidence.

## Implementation

Source/product guides committed81ba253f91fef124504da75803b6224300b53182 before independent-test visibility. `useTeacherStudioSources` owns course/source/list loading and retry state; `useStudioGeneration` owns mounted/pending state and permanent navigation/selection invalidation. Detail views/editor stay separate. Shared backend `is_postgres_text` predicate preserves caller-owned422/502 errors and valid astral Unicode. No migration or shared LLM client changes. Actual frontend pages+hooks758lines versus790 baseline:32net lines removed (review estimate40–60 was not measured). Source+productdocs overall17net lines removed. Existing478 backend/47focusedbrowser/types/lint/format/build passed. Independent test integration/GREEN and full checks pending.

## Independent integration verification

Designer integrated source into unchanged regression branch at0680399: original5backend/4browser regressions allGREEN, then full483backend/153browser/types/lint/format/build passed. Added source-selection-only A→B→A success/failure cases postintegration, explicitly not claimed RED on old code, committedabc92dfe29743b2ad746ba4f90e9c852da9ff0f9. Final155browser/types/lint/format/build passed. No harness corrections or weakened assertions; no app edits by designer. Parent fast-forward mergedabc92df and requested strongest read-only verifier review of all four findings, shared lifecycle, docs and regressions. Verifier verdict pending.

## Final verdict

Strongest independent verifier PASS atabc92dfe29743b2ad746ba4f90e9c852da9ff0f9: all four findings resolved, no blocking defects or material documentation gaps. Fresh independent483backend/155browser/typecheck/lint/format/diff checks passed; independent designer fullbuild passed. Zero verifier correction rounds needed for this corrective run. Original review report remains historical with resolution cross-reference. Shared frontend32net lines removed including new hooks; no generic framework. No code changed after verified revision; final handoff commit contains workflow evidence only. No live provider quality/production auth/deployment checked. No migration required; restart backend and refresh frontend. No push/PR/master merge.
