# Plan: TEA-03-mcqs-cleanup

Status: Approved through explicit user implementation request, 2026-11-04. Binding contract for independent developer/test-designer; start from master da57eab (PR16), after PR15 storage. Spec: spec.md.

## Data model

Add revision `20261104_tea03_mcq_edit` after `20261103_shr01_auth`. Extend mcq_draft_batch: version integer NOT NULL DEFAULT 1 CHECK >=1, updated_at timestamptz NOT NULL DEFAULT now(), updated_by varchar(64) NOT NULL FK user.id. Backfill updated_at=created_at and updated_by=created_by; preserve existing rows/IDs/questions. New generation sets version1, updated_by=created_by and identical created_at/updated_at. Downgrade removes only these additive columns/constraints; re-upgrade restores audit baseline from original creation (edited question values remain). Keep source and question FKs restrictive; delete batch children explicitly inside one transaction. material_file FK cascade may remove original bytes when deleting material. Do not introduce publication flags/tables.

## Authentication and reusable interfaces

Reuse `auth.dependencies.current_user(role="teacher")`, `require_course_member`, shared session/CSRF/Origin validation, ApiError, shared text/timestamp helpers, existing private byte extraction and SoC client. Migrate ALL `/api/teacher` endpoints, not only mutations. Never honour demo headers or gate. Keep request-scoped teacher data transactions READ COMMITTED explicitly; avoid changing shared auth/student semantics unnecessarily. Safe identity failure order: configuration503; session401; unsafe Origin/CSRF403; role403; accessible UUID/resource lookup; mutation-body/query422; locked recheck/version. Bad UUID422; foreign/missing resource404. Lock current user/membership/target as appropriate through commit so revoked permission cannot race a write.

For generation: initial current session/role/course authorization then copy scalar source context/bytes, close transaction before extraction/LLM. After model returns, authenticate the SAME cookie again in a fresh transaction, check unexpired/nonrevoked session/current user/role/membership/source, lock the authenticated auth_session row (prevent concurrent logout/revocation from invalidating the authorization decision), current user, membership and source through insertion commit. Acquire compatible locks in a consistent order; an already expired/revoked session fails401 before inserting. Logout, expiry, deletion or role/course revocation during inference must prevent persistence. Do not accept a newly supplied identity claim or use cached AuthUser as final authorization. Preserve no-open-transaction LLM rule and original caller_id derived from actual session user. No shared LLM client changes.

Teacher frontend transport retains FormData/browser boundaries, blob downloads, 10s defaults/45s generation. Send same-origin cookies and in-memory CSRF token on unsafe methods; reuse unauthenticated handling. Only teacher success parser accepts204=>undefined; retain strict JSON response checks on other APIs. Remove teacher demo-header construction and obsolete identity labels. Authenticated teachers see `Signed in as {display_name}` instead of development identity. Anonymous data screens render SignInNotice-style guidance without issuing teacher calls; sample-only teacher screens may remain demos. Clear/ignore account-obsolete request outcomes. Session expiry or successful logout unmounts/clears protected teacher data and local editor buffers; a dirty blocker must not preserve private access or reveal buffers under another account. Failed logout retains the current session/editor per shared auth behaviour. Do not automatically retry after sign-in.

## API endpoints and representations

Existing paths/behaviour retained with cookie authentication. Batch metadata exact fields: id,course_id,source_material_id,source_title,created_by,created_at,question_count,version,updated_at,updated_by. UUIDs canonical strings, user IDs strings, timestamps UTC Z, version positive integer, question_count3. Detailed batch adds questions[3], sorted by unchanged positions1..3, each {id,position,question,choices,correct_choice_index,explanation}. List sorts created_at DESC,id DESC; edits do not reorder.

PATCH `/api/teacher/mcq-drafts/{batch_id}` JSON exactly {version,questions}. version strict positive integer, no bool/float/string. questions exactly3 objects with exactly {id,question,choices,correct_choice_index,explanation}; IDs UUID strings resolving the existing batch's exact three question IDs once, no new/foreign/duplicate IDs. Input array order need not match positions; server updates by ID and preserves positions. No nullable/optional/extra keys, no position claims. Each choice array exactly4 strings; correct_choice_index strict integer0..3. Normalise CRLF/CR=>LF then Unicode strip; count Unicode code points. question1..200, each choice1..80, explanation1..200. Reject NUL/unpaired surrogates, blank or wrong type; choice duplicates within question and question stems across batch compare normalized casefold. Manual edits have no aggregate2000 cap. A valid no-op request still increments version once (UI does not send semantic no-ops). Lock batch/refresh and compare version, atomically update questions+editor+UTC timestamp+version;200 complete batch. Preserve IDs/positions/course/source/title snapshot/creator/creation time.

DELETE `/api/teacher/note-drafts/{id}?version=N` and `/api/teacher/mcq-drafts/{id}?version=N`: version query required once, ASCII decimal positive integer (reject zero, signs, whitespace, decimals, duplicates and absent values) after accessible lookup. No body required. Lock/recheck current access and target, compare version, delete note or questions+batch atomically;204 empty body. DELETE `/api/teacher/materials/{id}`: no body/version; lock quota advisory32272610 and source, reject any note/batch reference, delete metadata+bytes atomically;204. Repeated/inaccessible delete404. Source doesn't require material_file to exist before deletion: removing an otherwise unused broken metadata row is safe. Metadata APIs never include bytes/keys/paths.

| Condition | Status/code | Safe backend message |
|---|---|---|
| No/unknown/expired/revoked session |401 unauthenticated|Sign in to continue.|
| Nonteacher |403 forbidden|You do not have access to this.|
| Unsafe Origin/CSRF failure |403 csrf_failed|The request could not be verified.|
| Foreign/missing object |404 not_found|Material not found. / Draft not found. / Course not found. (matching resource)|
| Invalid edit body |422 validation_error|Provide three valid questions and a positive integer version.|
| Invalid delete version |422 validation_error|Provide a positive integer version.|
| Stale edit/delete |409 draft_conflict|This draft has changed. Load the latest saved version before trying again.|
| Source referenced |409 material_in_use|Delete the note drafts and MCQ batches referencing this material first.|
| Restrictive draft reference |409 draft_in_use|This draft is referenced by other content and cannot be deleted.|
| SQL/config/storage failure |503 service_unavailable|Teacher service is unavailable. Please try again.|

Keep existing operation-specific messages on unchanged endpoints; new/migrated frontend maps codes independently. Error envelope {detail:{code,message}}, no private exception details; existing shared auth errors may retain safe extra fields. Generation/source/LLM status/code/retry mappings remain current. Map only actual restrictive FK violations during deletion to409, other database failures503 with rollback.

## Concurrency and integrity

Use stable lock order for access then record; quota-sensitive source deletion acquires existing advisory lock before checking usage/removing original. Batch lock serialises all question edits/deletes; draft version protects an editor from deleting newer work. Source row FOR UPDATE conflicts with generation's postmodel FOR SHARE: generation wins=>reference blocks source delete409; delete wins=>generation recheck404/no draft. Restrictive FKs remain final defense; source-delete reference races yield409 not503. Harden lookup-then-lock None cases including topic reassignment=>404. Concurrent saves one200/one409; edit/delete same version one successful mutation, loser409 or404 depending whether row remains. Lost-response retries are never automatic; old version can't overwrite/delete newer work. Quota serialized100MiB raw-original-byte budget remains; delete frees logical bytes after commit, not guaranteed immediate disk shrinkage.

## UI contract

Preserve `/teacher/generate?tab=questions&course={id}&batch={id}` and existing note URLs. Add focused MCQ editor, reusing existing note dirty/blocker lifecycle patterns without generic editor frameworks. Reuse material list and saved note/MCQ viewers for deletion. All names below are accessible labels; errors role=alert, loading/success role=status, dialogs accessible role=dialog with stated heading.

MCQ viewer buttons: `Edit questions`, `Delete MCQ batch`; editor fields `Question 1`, `Question 1 choice A` through D, `Question 1 explanation`, and analogous2/3. Radiogroup `Question 1 correct answer`, radio names `Choice A` through D (scope by group); existing correct-choice selected. Counters `n / 200 characters` for stem/explanation, `n / 80 characters` for choice (codepoints after normalization). Inline invalid helper `Enter 1–200 characters.` / `Enter 1–80 characters.` / `Choices must be distinct.` / `Questions must be distinct.`; backend remains canonical Unicode duplicate authority. `Save changes`, `Cancel`; valid canonical changes only permit Save, raw differences trigger dirty guards. During saving disable editing/save/cancel/selectors/generation; synchronous request guard prevents duplicates. Successful save shows `Question changes saved.`, returns viewer, updates batch audit metadata without reorder. Viewer labels `Created by`, `Created`, `Last edited by`, `Last edited`, `Source`; retain `Unpublished draft · Review required`.

Dirty Cancel or navigation: dialog `Unsaved changes`, message `Discard your unsaved question changes?`, buttons `Keep editing`, `Discard changes`. Note editor retains existing note wording. Pending save: dialog `Saving changes`, message `Wait for the save to finish before leaving.`, button `Stay here`; no queued departure after settlement. Browser beforeunload while dirty/saving; no persisted local draft. Back/Forward and links/course/batch/tab changes route through blocker; do not unmount editor before blocker decision.

409 edit retains fields, disables stale saves, displays backend conflict message and `Load latest saved version`. That action opens dialog `Load latest saved version?`, message `Loading the latest saved version will discard your local changes.`, buttons `Keep editing`, `Discard changes`. Replace baseline only after successful fresh GET; latest-load failure `Could not load the latest saved version. Your edits are still here.` retains edits and retry load control. No force overwrite. Other save errors retain fields and offer `Retry save` only when valid/nonbusy.

Delete actions available only in readonly viewers/material rows; cannot delete an active dirty draft until saved/cancelled. Dialogs and controls per spec table; body note `Permanently delete “{title}”? This cannot be undone.`; batch `Permanently delete the MCQ batch from “{source_title}” and all three questions? This cannot be undone.`; material `Permanently delete “{title}” and its original file? This cannot be undone.`. Only confirmation sends DELETE. Pending disables dialog actions/repeated deletion. Success closes dialog, removes item and selected query parameter, refreshes applicable list. Failure closes dialog and displays recoverable alert while retaining item; opening delete action again is explicit retry. Conflict includes `Load latest saved version` outside editor (fetch latest before another confirmation). Source material_in_use message instructs deletion of referenced drafts first. Unrelated navigation may proceed during delete; use request ownership guards so late success/error cannot change another route/account.

| UI error | Exact visible message |
|---|---|
|401 expired session|Shared auth redirect to /login; teacher guidance `Sign in to manage teacher materials and drafts.` when anonymous. Never automatic mutation retry.|
|403 csrf_failed|Your request could not be verified. Refresh the page and try again.|
|403 forbidden|You do not have permission to manage teacher content.|
|404|This item is no longer available. Refresh the list.|
|409 draft_conflict|This draft has changed. Load the latest saved version before trying again.|
|409 material_in_use|Delete the note drafts and MCQ batches referencing this material first.|
|409 draft_in_use|This draft is referenced by other content and cannot be deleted.|
|422 MCQ edit|Check the question fields and try again.|
|422 deletion|Could not verify the draft version. Load the latest saved version and try again.|
|503|Teacher service is unavailable. Please try again.|
|Network/timeout save|Could not save changes. Your edits are still here.|
|Network/timeout delete|Could not confirm deletion. Refresh the list before trying again.|
|Other unexpected save/delete failure|Could not save changes. Your edits are still here. / Could not delete this item. Please try again.|

Do not erase editable fields on backenddown,403,404,422,503; session expiry/successful logout must clear account-owned state and redirect or show signed-out guidance, even when dirty; failed logout preserves the current session/editor. Existing generation failures429/502/504 and retry warning remain existing messages; editing/deletion never call model or get429. Refresh after lost deletion safely discovers404; don't falsely report network failure as success. Default10s timeout, generation45s. Success announcements must remain visible after list refetch/selection clearing. Keyboard focus enters confirmation and returns to trigger or next appropriate list heading on deletion; light/dark/mobile/reduced-motion retained.

## Tests and workflow

Independent designer uses only this contract, stories/threat model and test folders until test commit. Existing auth_helpers/test fixtures supply seeded cookie sessions+CSRF; adapt every teacher fixture away from headers without weakening identity assertions. Use TEA01_TEST_DATABASE_URL unique PostgreSQL schemas, migration/seed, fake get_llm_client override; no developer DB/env/liveLLM. Explicit extra teacher memberships support any-managing-teacher tests. Keep original demo-user IDs eligible for test-created auth sessions; real seed auth users must have appropriate membership. No reliance on real seeded passwords in source/tests.

AC1/2: all teacher GET/POST/PATCH/DELETE cookie integration, demo forgery, student/admin, crosscourse, CSRF/Origin, revoked/expired session before generation save, closed transactions and original functional regressions. AC3/4: limits/types/Unicode/duplicates/ID sets/order, atomic validation/noop/save/reopen/audit, concurrent saves, rollback, committed-response-lost conflict, migration populated/fresh/down/up. AC5/6: each delete/confirm/cancel/version parsing/stale, missing/inaccessible/refFK, source reference protection and byte removal/quota reuse, generation-v-delete/edit-v-delete/topic-v-delete/upload-v-delete concurrency, rollback and no private details. AC7/8: controls/counters/dirty/cancel/backforward/unload/pending/failedsave/conflict/latestGETfailure, duplicate clicks/obsolete account+route responses,204/no auto retries. Reproduce existing note Back/Forward failure and fix if product blocker. AC9: full backend/browser suites, typecheck/lint/format/build, mobile390/desktop1440 both themes/focus/readability, guides and source-client unchanged.

VariantB: this approved contract committed before developer+designer start at identical recorded SHA in separate worktrees. Independent tests commit before source visibility; designer merges source/tests reports, parent integrates then strongest readonly verifier max2 correction rounds. Developer owns application/product guides; parent owns logs/security/resources/handoff/shared contract unless assigned explicitly. No shared LLM changes/live calls/deployment, no push/PR/master merge. Commit locally only.

## Decisions

Any managing teacher, whole3-question batch deletion, only unpublished work, source only when unreferenced. Database100MiB original-byte cap unchanged. No new dependency/framework or publication model. Shared auth UI behaviour retained; teacher transport now participates instead of legacy bypass. Future published/practice references must block deletion before those features launch.
