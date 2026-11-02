# Plan: TEA-03-notes — Edit draft notes

Status: Approved through the user's implementation request, 2026-11-02. This is the shared developer/independent-test interface; no application code before this contract is committed.

## Data model and migration

Extend study_note_draft with: source_title varchar(200) NOT NULL; version integer NOT NULL default1 CHECK(version>=1); updated_at timestamptz NOT NULL default now(); updated_by varchar(64) NOT NULL FK user.id. Backfill old rows from title, created_at and created_by respectively, version1. Source_title is immutable after creation. New generation copies source title into both title/source_title, created_by into updated_by and uses identical created_at/updated_at timestamps, version1. Retain the content length constraint1..2000, existing keys and source/course foreign keys. No existing note content/title is discarded. A new additive Alembic revision follows 20261101_tea02; do not change historical schema definitions to include new fields. Downgrade removes the four new columns and new FK/check, preserving rows/title/content. Upgrade again backfills from their then-current title/creator/time; no historical source-title recovery is promised after downgrade.

## HTTP contract

All paths /api/teacher. Metadata now contains exactly id,course_id,source_material_id,created_by,title,created_at,source_title,version,updated_at,updated_by. IDs UUID strings except user IDs; version JSON integer, timestamps UTC Z; all nonnullable. GET course note-drafts returns metadata[] sorted created_at DESC,id DESC; GET single, POST generation and PATCH return metadata plus content. Update old fixture response expectations for these additive fields without weakening existing access/content checks.

PATCH /note-drafts/{draft_id} requires JSON {title:string,content:string,version:integer}; no nullable/optional fields or extras. Strict version>=1 rejects bool, strings and floats. Title.strip() length1..200; content.replace('\r\n','\n').replace('\r','\n').strip() length1..2000, counting Python Unicode code points (PostgreSQL char_length), not UTF-16 code units. Preserve internal whitespace. Reject U+0000 and unpaired surrogate code points in title/content as 422 validation_error: PostgreSQL UTF-8 text cannot store them. Valid astral Unicode characters remain supported. Successful valid requests save even when canonical values equal existing values; increment version once, set updated_by from current teacher, updated_at current UTC.200 returns complete committed draft; never modify source_title, IDs, original creator/time or list ordering.

Identity/gate/role -> accessible UUID/resource/membership lookup -> body validation -> locked current version/access check -> update/serialize/commit. Reuse existing teacher session/access helpers, SQLAlchemy models, safe ApiError handler and HTTP transport. Lock/recheck current user role and membership and authorised draft through commit (or transactionally equivalent), not an earlier cached ORM snapshot. Compare supplied version after locking/refresh. No record access/mutation is based on body claims.

| Condition | Status/code | Fixed safe message |
|---|---|---|
| Gate disabled, absent/unknown identity, wrong role, inaccessible draft | Existing403 demo_identity_disabled,401 unauthenticated,403 forbidden,404 not_found | Existing safe teacher messages |
| Bad UUID, malformed JSON/type/fields/limits |422 validation_error | Provide a valid title, note content and positive integer version. |
| Supplied version differs from locked row |409 draft_conflict | This draft has changed. Load the latest saved version before saving. |
| Missing/unavailable DB/storage, SQL/commit failure |503 service_unavailable | Teacher notes service is unavailable. Please try again. |

Errors retain {detail:{code,message}}; no content, credentials, paths or exception text. Roll back failure. Concurrent saves from one version: one200/version+1, one409; no lost update. After an ambiguous response, reusing the old version safely409s if already committed.

## UI and routing

Keep /teacher/generate?course={id}&draft={id}. Extend the existing content studio rather than adding another edit screen. Idle action Edit notes; editor labels Note title, Note content; buttons Save changes, Cancel. Title/content populate from selected saved draft and its version. Source display reads source_title. Viewer displays Created by, Created, Last edited by, Last edited; saved list retains title/creator/date and updates the title after save. Keep Unpublished draft · Review required. Successful save announces Draft changes saved. Return to read-only viewer and refresh/update list metadata without reorder.

Dirty means raw editor title/content differ from the loaded editor baseline; Save changes requires valid canonical values that differ from saved canonical title/content. Count canonical content code points with Array.from(...).length, show n / 2000 characters and clear field helper errors; do not use UTF-16 maxlength that cuts astral characters. Save disabled on invalid/no semantic change. During save disable editor controls, save/cancel, generation and course/draft selection; guard against repeated PATCH using a synchronous in-flight ref. Other navigation attempts are blocked as below. Read-only rendering and all metadata remain escaped plain text.

Minimal router conversion: main entry uses createBrowserRouter([{path:'*',element:<App/>}]) and RouterProvider instead of BrowserRouter; preserve App's existing route tree and all direct/unknown routes. Use useBlocker when dirty OR saving, including pathname/search changes. Route changes, course/draft selection and browser history use the same blocker, not unguarded local state mutations. Do not clear source/editor/query state until navigation is allowed. Existing stale request guards remain; edits cannot be replaced by a delayed older load.

Confirmation contract:
- Dirty navigation or Cancel: dialog heading Unsaved changes; message Discard your unsaved note changes?; Keep editing cancels the action, Discard changes performs the requested navigation/cancel.
- Conflict load: dialog heading Load latest saved version?; message Loading the latest saved version will discard your local changes.; Keep editing closes, Discard changes starts GET and replaces editor baseline/version only after successful fetch. Preserve local fields if GET fails.
- Saving navigation: dialog heading Saving changes; message Wait for the save to finish before leaving.; button Stay here. No discard/proceed while save is pending. After settlement, reset any blocked navigation and stay on page; do not navigate unexpectedly. Native beforeunload warning is registered while dirty/saving (browser controls wording and whether shown).

409 shows This draft has changed. Load the latest saved version before saving. and Load latest saved version; retain local edits, disable further stale saves until successful latest load/Cancel, no force overwrite. Other failures show Could not save changes. Your edits are still here. and Retry save (only valid/nonbusy); no automatic PATCH retries, including network timeout. Latest GET failures show Could not load the latest saved version. Your edits are still here. and retain a retryable load action. Missing/revoked draft access must not clear local edits; allow Cancel/discard to leave safely. On malformed/foreign response payload, show recoverable failure rather than assigning it to the selected editor.

## Test interfaces and verification

Use TEA01_TEST_DATABASE_URL: unique temporary PostgreSQL schema, Alembic upgrade/seed, temporary FILE_STORAGE_DIR; never developer data. Seed IDs: courseA11111111-1111-4111-8111-111111111111, courseB22222222-2222-4222-8222-222222222222, demo-teacher/courseA, demo-teacher-other/courseB, demo-student. Tests may insert extra same-course teacher membership by SQL to check shared authorship/concurrent updates. Source fixtures can use existing upload API. Create initial draft by existing generation using app.dependency_overrides[llm_client.get_llm_client]=lambda:fake; fake.complete(messages,*,max_tokens,caller_id) returns LlmReply(text,finish_reason,prompt_tokens,completion_tokens). Clear overrides after each test; editing must never invoke fake or real LLM. Existing generation guards and shared client remain unchanged.

| Criteria | Independent evidence |
|---|---|
|AC1,AC2,AC9|Populated TEA02 migration/backfill, fresh head, downgrade/re-upgrade; generation fields; save/get/list/new process persistence; preserved source bytes/references/creator/source snapshot/order|
|AC3|Missing/extra/wrong/null fields, strictversion,0/negative, unicode1999/2000/2001, title200/201, CRLF/CR and Unicode whitespace normalisation, blank content|
|AC4,AC5|Gate/identity/role/foreign/guessed/malformed IDs, malformed body before access, revoked access; stale version, threaded same-version race exactly one success; injected commit failure; committed-but-lost-response retry409|
|AC6,AC8|Populate/edit/save/reload, title-source separation, updater metadata, no-op/invalid controls, exact counter, escaped content, no LLM call,500 retry/409 preserve-load recovery, failed/latest/stale response guards and duplicate PATCH prevention|
|AC7|Cancel clean/dirty, course/draft switch, links/role/login navigation, back/forward with Keep editing and Discard changes; pending save cannot leave; native unload listener/Playwright dialog where browser supports; no persisted edits on reload|
|AC9,AC10|Existing backend/browser suites and routes, types/lint/format/build; mobile/desktop both themes, guides truthful and handoff updated; no student/publication change|

Follow Variant B: developer and independent test-designer from same committed contract in separate worktrees; independent tests committed before integration, then strongest read-only verifier, max two correction rounds. No live model calls. No push/PR/merge without human approval.

## Decisions

User chose notes editing only and the2,000-character manual limit. Source title snapshot, positive strict versions, explicit dialogs/error labels, raw dirty versus canonical save eligibility, and safe latest-load behaviour make the approved scope independently testable. TEA-02 merged through PR11/040dc07; user reported successful live generation on2026-11-02. Record that as user-reported evidence, not automated live-provider verification. Published-version isolation remains future design; no published records exist or are introduced here.
