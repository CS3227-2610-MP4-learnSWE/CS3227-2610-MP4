# Plan: TEA-03-publishing — Teacher publication on the STU-01 foundation

Status: Approved through explicit user implementation request, 2026-11-05. Binding contract for independent developer/test-designer. Base1784729, after master STU-01/PR19 merge. Read spec.md and this plan together. Preparation history remains in logs/BatchPublicationPreparation.md and logs/MergeMasterPublishing20261105.md; this is the implementation contract.

## Data model

Add Alembic revision `20261105_tea03_publications`, down_revision `20261104_stu01_lessons`.

1. Extend existing `published_lesson` with nullable integer `source_version`, check NULL or >=1. Existing rows remain NULL; preserve IDs, source_draft_id, nullable topic, completion rows and withdrawal state. No unique constraint on note source_draft_id: low-level helper append behaviour is an existing compatibility contract.
2. Create `published_practice_set`: UUID id PK; UUID course_id FK course.id; nonnull UUID topic_id with composite FK(topic_id,course_id) to topic(id,course_id); title varchar200; UUID source_draft_id UNIQUE FK mcq_draft_batch.id RESTRICT; source_version integer>=1; published_by varchar64 FK user.id; published_at timestamptz defaultnow(). All nonnull. Add named unique(id,course_id) to mcq_draft_batch and composite origin FK(source_draft_id,course_id) to its(id,course_id), ensuring the originating batch/course match. Title char_length1..200.
3. Create `published_practice_question`: UUID id PK, set_id UUID FK published_practice_set.id RESTRICT, source_question_id UUID FK mcq_draft_question.id RESTRICT, position integer1..3, question varchar200, choices JSONB, correct_choice_index integer0..3, explanation varchar200. All nonnull. UNIQUE(set_id,position), UNIQUE(set_id,source_question_id); duplicate current draft checks for text lengths1..200/question+explanation and four JSON string choices1..80. Exact-three, nonblank/canonical text, distinctness and correct origin-batch mapping are checked by the atomic application copy. Snapshot question IDs are new; original IDs are never student output.

Do not store original bytes or a second note snapshot. Published values have no application update/delete endpoint; no changes to withdrawal fields. FK protections include original question references so even future direct question deletion cannot destroy published provenance. Existing material-to-draft restrictions protect original sources.

Downgrade locks published_practice_set and published_lesson before checking, in a consistent fixed order, and refuses when any published set exists or any published_lesson.source_version is nonnull. Safe refusal message: `Cannot downgrade publication storage while published sets or recorded note publication provenance exist. Preserve the database or restore a backup instead.` Do not erase/reset data or alter schema/version stamp on refusal. When empty of new publication state, drop question/set tables, origin composite constraint/added unique, and source_version/check only; retain all pre-existing lessons/completions. Re-upgrade restores empty new structures/NULL legacy versions. Migration tests use isolated schemas only.

## API endpoints

### Shared types and responses

`PublicationKind` is exactly `note` or `practice_set`. Metadata M has:

- `id`, `course_id`, `title`, `published_at`: strings (UUID IDs, UTC ISO8601 Z timestamp).
- `kind`: PublicationKind; `topic_id`: UUID string or null for legacy notes; `topic_name`: string (General when topic is null/missing label).
- Practice-set M additionally has `question_count`: integer3; notes omit this key.

Teacher metadata T extends M with `source_draft_id`: UUID string or null only for legacy notes; `source_version`: positive integer or null only for legacy notes; `published_by`: user-id string; `withdrawn`: boolean (lesson.withdrawn_at is not null; always false for sets). `published_at` means the existing lesson timestamp or new set timestamp, never draft creation/update time. No original filename, storage path/key, bytes, email, password or provider data.

Teacher note detail is exactly T plus `content`: saved plain-text string. Teacher practice detail is exactly T plus `questions`: ordered3 objects `{id,position,question,choices,correct_choice_index,explanation}` where choices is four strings and the answer index0..3. No source_question_id in JSON.

Student set metadata is M only. Student set detail is exactly `{id,title,questions}`, ordered questions `{id,text,code:null,choices:[{id,text}]}`. Choice IDs are `a`,`b`,`c`,`d` in stored order. No key, explanation, correct index, source_* fields, publisher or withdrawn state anywhere in student set JSON. The new detail is compatible with the existing safe PracticeSet DTO; no results/key endpoint is introduced.

### New endpoints

All list success responses are bare arrays. All7 new endpoints have Cache-Control:no-store on success AND failure; shared error envelope remains `{detail:{code,message}}` (existing shared auth may include its existing safe fields). No pagination/filter query introduced in this increment.

| Method/path | Role/current access | Request | Success |
|---|---|---|---|
|POST /api/teacher/note-drafts/{id}/publish|teacher managing draft course|PublishIn|201 teacher note detail, or200 exact-existing retry|
|POST /api/teacher/mcq-drafts/{id}/publish|teacher managing batch course|PublishIn|201 teacher set detail, or200 exact-existing retry|
|GET /api/teacher/courses/{id}/publications|teacher managing course|none|200 T[] combining all notes (including NULL-origin/withdrawn legacy lessons) and sets; published_at DESC,id DESC,kind ASC tie-break|
|GET /api/teacher/published-notes/{id}|teacher managing lesson course|none|200 teacher note detail, including legacy/withdrawn records|
|GET /api/teacher/published-practice-sets/{id}|teacher managing set course|none|200 teacher set detail|
|GET /api/study/courses/{id}/practice-sets|student enrolled in course|none|200 student set metadata[], published_at DESC,id DESC|
|GET /api/study/practice-sets/{id}|student enrolled in set course|none|200 safe student set detail|

`PublishIn` is exactly `{version,title,topic_id}`: strict integer version>=1 (no bool/float/string), strict string title trimmed using existing Unicode strip then1..200 codepoints with valid PostgreSQL text, and strict UUID string topic_id belonging to the authorised course. No null/default topic; prefilling is client convenience only. Reject duplicate JSON keys as invalid input rather than accepting conflicting version/title/topic values. Reject extra/missing fields, invalid UUID/type/text with422 validation_error. Do not accept actor/course/content/question claims.

No duplicate student note/course endpoint: reuse existing GET /api/study/courses, /courses/{id}/lessons, /lessons/{id} and existing completion endpoint unchanged, including envelopes, limits/order and role checks. New lessons appear after student refresh under existing oldest500 listing semantics; current listing limits are not changed. New set IDs must still return existing not-found behaviour from old /api/practice-sets and attempt flow, until a separate integration feature.

### Authorization, operation order and publication transaction

Use existing `teacher_access.teacher_session`, current teacher/course helpers, session/CSRF/Origin checks and READ COMMITTED. Authenticate and authorise an existing source before parsing mutation body. For existing GETs keep access rules; new student endpoints reuse shared student role and require_course_member. UUID errors after identity checks are422; inaccessible/unknown records/course return404 consistently. No admin bypass.

After PublishIn validation and same-course topic lookup, use existing access lock order (live auth session, current user, course membership, then originating draft/batch FOR UPDATE with populate_existing). Lock/recheck topic during snapshot commit; no early commit. Refresh source existence/current course; deleted resource404. The current helper already avoids expired-session cleanup while holding share locks; preserve it.

Within the origin lock:

1. Find EVERY existing publication for that origin (notes include withdrawn lessons). One existing snapshot with nonnull source_version and matching request version, normalized title and topic returns200 existing complete detail; do not compare today's draft version first. Thus a lost-response retry after a later private draft edit remains idempotent. An existing snapshot with differing payload, unknown version, or multiple linked legacy lessons returns409 already_published; do not guess one or modify it.
2. If no existing publication, compare current source.version with request.version; mismatch409 draft_conflict.
3. Validate saved content. Notes: nonblank representable string1..2000, copy exact stored content. MCQs: exactly3 positions1..3 from locked batch, each representable/nonblank text within current field limits, four distinct choices, correct strict integer0..3 and distinct normalized/casefold question stems. Use existing validation helpers but do not silently repair/truncate copied strings. No request-provided content replaces saved values. Invalid stored content returns422 validation_error without a snapshot.
4. Note: call extended publish_lesson with explicit validated title/topic, captures draft.version. Set: insert parent and exactly3 copied questions with new UUIDs and original question FK links. Flush and serialize full detail inside the transaction, then commit. Any failure rolls back everything, leaving existing work unchanged.

Origin row locking serialises public same-draft requests even though legacy note helper intentionally permits multiple internal appends. Practice UNIQUE origin is a final DB guard. Map known unique-origin races to the same existing-publication resolution; never return a duplicate or uncontrolled500. Map restrictive deletion conflict to existing409 draft_in_use. Other database failures503; no SQL/private details. No transaction/model call occurs outside the publication transaction because no model is called at all.

Exact new backend messages:

| Status/code | Message |
|---|---|
|401 unauthenticated|Sign in to continue.|
|403 forbidden|You do not have access to this.|
|403 csrf_failed|The request could not be verified.|
|404 not_found|Course not found. / Draft not found. / Publication not found. / Topic not found. (matching lookup)|
|422 validation_error|Provide a valid title, course topic and positive integer draft version.|
|409 draft_conflict|This draft has changed. Reload and review it before publishing.|
|409 already_published|This draft has already been published.|
|503 service_unavailable|Published content service is unavailable. Please try again.|

### Shared helper signature

Extend `study_lessons.publish.publish_lesson(db: Session, draft: StudyNoteDraft, teacher: AuthUser, *, title: str | None = None, topic_id: UUID | None = None) -> PublishedLesson`.

None uses current existing defaults: title from draft.title; topic from source Material.topic_id (including null). Supplied title/topic override only snapshot values, never draft/material fields. Always record draft.version in new source_version. Preserve3-positional-argument calls, immutable copy, append-new-ID semantics, flush+refresh and no commit. Do not move HTTP uniqueness, auth, body validation or error mapping into this helper. Caller commits. No uniqueness restriction on legacy helper appends; existing repeat-helper tests must keep asserting distinct rows.

## Components and modules

Backend: extend existing study_lessons model/helper and add focused publication models/routes/serializers using the same Base and ApiError. Reuse teacher auth/access/UUID/time/text/MCQ validators and original byte storage unchanged. New student set routes stay under /api/study, using explicit safe serializers; do not route them through teacher detail serializers. Existing student practice/store/logic/schemas/companion and generic llm_client.py stay behaviourally unchanged.

Frontend: keep existing notes/questions studio and editors. Add focused typed publication service, read-only preview/confirmation and a real catalogue at the existing review route, with current MUI controls/CSS. Remove obsolete sample Review editor/preview publication action; delete teacherDemo.ts only if no callers remain. Adapt the existing teacher-demo answer assertion in practice.spec.ts to authenticated publication fixtures rather than deleting its answer-boundary intent. No assembly screen returns. Rename its sidebar label from Review & publish to `Published content`; studio is the publishing entry point.

Teacher GET in-flight sharing uses getSessionGeneration plus a teacher mutation epoch bumped before AND after unsafe teacher requests. Key includes path, representation (JSON/blob) and timeout so unlike reads do not coalesce. Identical in-flight reads return one promise; finally removes only its own entry; completed data never caches. Preserve FormData boundaries, downloads, JSON validation, default10second timeout, existing45second generation and401 account-ownership guards. Do not refactor the separate student lessons readOnce cache or introduce persistent storage. Account/route response lifetime guards remain per consumer; sharing a GET cannot revive obsolete UI.

Publication status is separate from material/draft resources so its failure/retry does not repeat successful reads. Filter status by kind AND source_draft_id, not UUID alone. Treat ANY linked note publication as published; for multiple legacy matches show existing snapshots in catalogue and block new publication. Choose newest linked snapshot for View published version, ordered published_at DESC,id DESC; readonly list still includes all. Keep null legacy provenance readable, with labels from spec. After successful POST update local status from its returned detail; no compulsory extraGET. A409 already_published refreshes publications once to resolve existing links and retains the error; lost network response needs explicit Refresh publication status. No POST auto retry.

## UI contract

All exact controls, role names, dialog text and errors are in spec.md and binding here. Route for catalogue: `/teacher/review?course={id}&type={note|practice_set}&kind={note|practice_set}&publication={id}`; omit type for All content and kind/publication when unselected. Type changes clear kind/publication; selection preserves course/type filters. `Content type` is client-side All content/Notes/Practice sets; catalogue selection only requests the matching detail endpoint. Wrong kind/foreign selection never shows content from another course. Student routes/UI are not replaced. Existing /teacher/practice redirect remains replacement navigation to questions studio.

Publication status pending disables publication and draft deletion, not saved editing/generation. Known published status replaces unpublished badge, disables Delete with explanatory text, and keeps Edit with private-change warning. Publish is only in read-only source viewer. Dialog Cancel discards metadata/error state; POST failures keep it. Pending publication prevents duplicate sends and dialog dismissal, but route departure is allowed after confirmation. Do not add a publication useBlocker alongside the existing editor blocker; React Router permits only one. Monotonic route/account ownership ignores late responses, including A-to-B-to-A navigation, without cancelling or retrying the committed action. Scoped Retry topics/status/list/detail controls avoid repeated successful GETs. On successful publish close/reset dialog, announce exact success, and restore focus to surviving Publish/View published version control. Catalogue content is plain text, with source version, publisher and publication time, never editable. Clearing selection focuses catalogue list heading. Initial confirmation focus enters the dialog and all controls remain reachable.

- Requests per load and per retry: studio courses1 per mounted screen, per selected course materials1+draft-list1+publications1; selected draft detail1. Publication dialog topics1 per open, retry topics1. POST1 per explicit confirmation; success updates local status without requiredGET.409 already_published handler reads publications1. Explicit Refresh publication status/status retry reads1. Material/draft retry reads2 only. Catalogue courses1 then publications1; each selected publication detail1; type filter0; retries only failed request. Auth/health are separate; anonymous/wrong-role screens0 teacher calls. StrictMode identical reads share in-flight promise, not duplicate network requests.
- Wrong role: existing role redirect before teacher reads; anonymous guidance/demo-off login; dynamic403 uses exact spec message and no automatic mutation retry.
- Link history: push or replace: catalogue/sidebar/filter/selection/View/Clear actions push; legacy redirect and expiry replace; logout pushes. Dialog open/cancel/retry/success does not navigate.
- Refresh: existing native warning for dirty/saving draft editors where browser supports it; publication adds no unload warning; reload discards unsaved state and loads server publication/source snapshots. Direct catalogue URLs recheck course access.
- Back and Forward: restore query selections via fresh reads, preserving current dirty guard and permanently ignoring responses invalidated by navigation/account changes.
- Expired session or logout: protected views/forms unmount, requests cannot populate the next account; shared redirect reaches login even if an editor was dirty. Failed logout retains session/editor.
- Backend down: operation-specific network messages and explicit retry keep form/saved source state. No false success and no unexpected POST repetition.
- Longest wait before an error: default10seconds newreads/POST; existing generation45seconds. No indefinite spinner; error/retry messages as spec.
- No generic failure message: code-specific HTTP copy overrides network copy; never call403/404/409/422/503 a connection failure. No raw SQL/server exception.

## AI usage

None for publishing, read or catalogue. Existing generation may still use shared SoC LLM independently, unchanged. No new wrapper/provider, prompt, quota, context, key retrieval or live AI verification. Published question keys are teacher-only until a future attempt/results integration implements normal whole-set release; no student key route is added here.

## Test plan

Independent designer reads approved spec/plan/tasks, stories/threat model and tests only until own test commit. Use isolated PostgreSQL16 schemas, existing fixture/seed helpers and fake get_llm_client overrides. Existing base test fixture seeds materials/auth, not study lessons; create needed legacy publications explicitly. Never use developer .env/data or live provider. Preserve original existing behaviour assertions when adapting endpoint fixtures.

| Criteria | Required verification |
|---|---|
|AC1|Each endpoint anonymous/expired/unknown cookies, forged headers, student/admin wrong roles, CSRF/Origin, foreign course/source/publication/topic, role/member/session revocation and authorization-before-invalid body; safe envelopes/no-store success+errors|
|AC2/5|Exactly3 questions/4choices/new immutable IDs/order/source references and persisted contents; notes existing helper defaults/nullabletopic/append calls; source_version backfillNULL/new capture; draft edit after publish does not change snapshots|
|AC3/4|Publish note then existing student lessons/read/completion/course counts after refresh; cross-user progress still private; safe student set list/detail recursive absence of keys/explanations/source/publisher fields; stable a-d mapping; old set IDs/attempt routes/companion tests unaffected and newUUID not supported by old attempt flow|
|AC6|201 new/200 exactretry/409 differing or unknown/multiple legacy; withdrawn origins also block a new publication, while a known exact retry only returns the same withdrawn snapshot; exactretry after later draft edit; concurrent identical/different publish, publish-v-edit/delete, later deletion blocked; database failure after parent/child insertion rollsback all; no LLM invocation|
|AC7/8|Readonly catalogue directURLs/filter/reload/legacylabels; dialog preview/title/topic/defaults/cancel-reset/inlinevalidation, pending duplicate/dialog-dismissal prevention and allowed departure with stale-outcome suppression, requestcounts StrictMode and partialretry, lostresponse/statusrefresh/conflict reload; disabled referenced delete; stale account/route outcomes; escaped strings; focus; mobile390/desktop1440 both themes/reducedmotion|
|AC9/10|Migration fresh/populated preserve old lessons/completions, constraints, guarded downgrade unchanged schema/stamp/data and empty downgrade/reupgrade; full backend/browser, type/lint/format/build, speccheck --all with no newwaiver; guides/help/contracts reviewed|

Developer runs existing applicable suites plus frontend checks before handoff, and commits source before designer sees it. Designer then integrates implementation in own worktree, runs suites, reports contract mismatches versus bugs; parent merges tests. Strongest verifier independently reruns and reviews AC/security/concurrency/docs, then max2 correction rounds with regressions. Record request-budget mismatches as contract failures rather than relaxing assertions.

## Decisions

Both notes and sets; teacher publication once per draft; one batch is one3-question set. Existing helper append semantics and existing student lesson API/UI are reused. Teacher read catalogue includes legacy/withdrawn content; student notes keep existing withdrawal filtering. Legacy unknown/multiple publications cannot be guessed/idempotently recreated. Required new title/topic, no default request topic. No duplicate published-note tables/student lesson API. No practice attempt/grading/companion or student-screen integration for new sets yet. No assembly, new dependencies, live AI, deployment or push. User's explicit plan approval covers this derived contract; only human gate remaining after local implementation is push/PR/master integration.
