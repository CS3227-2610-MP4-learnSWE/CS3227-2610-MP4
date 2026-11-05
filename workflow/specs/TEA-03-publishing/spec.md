# Spec: TEA-03-publishing — Publish reviewed notes and three-question sets

Status: Approved by Dylan's explicit implementation request, 2026-11-05. This replaces the preparation-only contract after merge1784729 (STU-01 and PR19). Publishing implementation may start only after this contract passes the spec checker and is committed as the shared start for Variant B.

## Goal

As a teacher, I want to explicitly publish reviewed content so that I can make approved learning material available to students (US-TEA-03-04). One saved MCQ batch becomes one practice set containing all three questions, without question assembly (US-TEA-04-01). Published snapshots remain stable after draft corrections (US-TEA-04-02).

## Behaviour

Any current teacher managing a course may publish its saved note or complete three-question batch once, providing a title and a topic in that course. A read-only preview and explicit confirmation precede the request. Notes use the existing published_lesson store/helper and existing student Materials/completion APIs. MCQs use immutable published-set records and safe student read APIs; existing practice selection, attempts, scoring and companion lookup are not connected to these sets in this increment.

Generation never publishes automatically. Publication makes no AI request. Later draft edits remain private and cannot update or republish the snapshot. Published references prevent draft/question deletion; source protection follows its existing references. No unpublish, withdrawal control, published editing/deletion, subset selection or mixed batches.

## Acceptance criteria

- [ ] AC1: Publication validates required content fields and requires an explicit teacher action. Every protected operation enforces live session, role, course and record access; unsafe requests require CSRF/Origin validation before mutation-input validation.
- [ ] AC2: A practice-set publication includes all three saved questions from one reviewed batch, with title and course topic; no selection/mixing step. Copying is atomic and preserves order, four choices, one answer and explanation per question.
- [ ] AC3: Authorised students can read published notes and practice questions while drafts stay hidden. Existing lesson/course/completion APIs and student Materials UI remain compatible; note publication becomes visible after refresh under existing listing limits.
- [ ] AC4: Publishing never exposes MCQ keys/explanations/private draft provenance through student read APIs. Existing whole-set submission, attempt ownership, grading and companion safeguards remain unchanged. New published-set IDs are not accepted by the old attempt flow yet.
- [ ] AC5: Published content is an immutable snapshot separate from editable drafts. Existing published-lesson IDs, completions, nullable legacy topics, withdrawal state and helper append-snapshot behaviour remain intact. New note snapshots record the source version; existing versions are not guessed.
- [ ] AC6: Each draft may publish once through the teacher HTTP workflow. Exact retries return the single matching existing snapshot200; new publication201; differing/legacy/ambiguous existing publications409 already_published. Concurrent publish/edit/delete yields a consistent snapshot or controlled conflict, never duplicates/partial work.
- [ ] AC7: Current managing teachers can reopen publication metadata/details in a real catalogue. Published-origin deletion is blocked and the editor clearly states later edits remain private. Withdrawn legacy lessons are visible to managing teachers with their status, never offered for withdrawal/republishing.
- [ ] AC8: Confirmation, cancellation, loading, field validation, duplicate prevention, lost-response recovery, stale-version recovery, session expiry and obsolete responses follow the exact UI contract below. Existing dirty editors and keyboard/mobile/theme behaviour remain protected.
- [ ] AC9: Additive migration preserves all existing data and guards downgrade against losing new publications/provenance. Database failures roll back the entire publication. Isolated automated tests, guides and shared contract accurately describe what works.
- [ ] AC10: Spec/plan/tasks contain required PR19 sections, exact interfaces, UI table and eleven labelled items. Checker passes before developer/test-designer start; independent tests, verifier and maximum two correction rounds follow Variant B. No live LLM or developer-data changes.

## UI states and copy

Controls named here are their accessible names. Alerts use role=alert, loading/success role=status, and confirmations role=dialog named by their headings. Generated/published text is escaped plain text; notes preserve line breaks, never interpret HTML/Markdown.

| Screen or action | Control and exact label | Loading | Success | Empty | Failure message | Recovery |
|---|---|---|---|---|---|---|
| Draft publication status | button `Retry publication status`; readonly viewer buttons `Publish notes` or `Publish practice set` | `Checking publication status…` | Existing publication offers `View published version` and badge `Working draft · Published snapshot exists` | Unpublished draft keeps `Unpublished draft · Review required` | `Could not load publication status. Please try again.` for network/timeout; HTTP errors use table below | Retry only publications GET; keep saved draft/editor usable, disable Publish/Delete while status unknown |
| Publish dialog | dialog `Publish notes?` / `Publish practice set?`; fields `Publication title`, `Publication topic`; buttons `Cancel`, `Confirm publication` | `Loading publication topics…`; POST `Publishing…` | Notes: `Notes published. Enrolled students can read them in Study materials.` Sets: `Practice set published. Student practice integration is pending.` | `No topics available. A course topic is required before publishing.` | Topic network failure `Could not load publication topics. Please try again.`; POST errors below | `Retry topics`; preserve fields on failure, clear fields/errors on Cancel; no automatic POST retry |
| Lost or timed-out POST | button `Refresh publication status` | `Checking publication status…` | Existing match offers `View published version` | If none exists, same form can explicitly retry | `Could not confirm publication. Refresh publication status before retrying.` | Refresh sends one list GET, preserves form and never repeats POST automatically |
| Stale draft | button `Reload draft` opens dialog `Reload latest draft?`; buttons `Keep form`, `Reload draft` | `Loading latest draft…` | Fresh viewer requires another publication confirmation | Not applicable | `This draft has changed. Reload and review it before publishing.` | Confirmation says `Reloading will discard the publication form entries. Review the latest draft before publishing.`; accepted reload closes/resets form and fetches source draft once |
| Existing publication | button `View published version` | Existing catalogue detail loading | Exact retry: `Already published. Showing the existing version.` | Not applicable | `This draft has already been published.` | Refresh status once; show existing publication, no overwrite action |
| Catalogue at /teacher/review | navigation link `Published content`; heading `Published content`; selectors `Course`, `Content type` with options `All content`, `Notes`, `Practice sets`; each item button accessible name `Open {title}` | `Loading published content…`; selected detail `Loading published version…` | Readonly note content or all3 MCQs with teacher keys; source-version/publisher/date metadata | `No published content yet.`; no selection `Choose a published item to view it.` | Network/timeout `Could not load published content. Please try again.` / `Could not load this published version. Please try again.`; HTTP errors below | Scoped button `Retry` repeats only failed read; failed detail offers `Clear publication selection` |

Every publish confirmation displays the saved note or all three questions/choices/correct answers/explanations and the text `Publishing saves a permanent version once. Later draft changes will not update it.` Practice dialog also says `Student practice screens are not connected to these published sets yet.` Do not expose a new student practice selector or claim attempts work on published sets.

Title defaults to saved note.title or batch.source_title. Topic defaults to its original material.topic_id only if still offered by the managed course; otherwise no selection. Topic is required. Title helper: `n / 200 characters`; invalid helper `Enter 1–200 valid text characters.` Topic invalid helper `Choose a course topic.` Disable Confirm until valid/topics loaded; disable Publish while editing/saving/generating/status unknown. During POST disable dialog fields/Cancel/Confirm and ignore Escape/backdrop. Route departure is allowed after the permanent action was confirmed; it neither cancels nor retries the server action. Ignore all resulting UI updates after route/account departure, including an A-to-B-to-A round trip. Do not add a second React Router blocker beside the existing editor blocker. Existing dirty-edit/native-unload guards remain unchanged; successful logout/expiry clears protected data, overrides blockers and reaches login; failed logout retains editor.

Published drafts keep their existing Edit controls, with `This draft was published once. Changes here remain private and cannot update or republish the published version.` Disable Delete with adjacent text `A published snapshot references this draft and prevents deletion.` Backend must still enforce the reference even if UI status is stale. Catalogue legacy labels: `Withdrawn` when withdrawn=true, `General` for null topic, `Source draft unavailable` for null source_draft_id, and `Source version unavailable` for null source_version. No edit/delete/withdraw/publish control in the catalogue.

HTTP error copy is fixed for new publication UI; operation-specific network copy above must not replace HTTP messages:

| HTTP/code | Exact visible message |
|---|---|
|401 unauthenticated|Existing shared redirect to /login; anonymous teacher guidance remains `Sign in to manage teacher materials and drafts.`|
|403 csrf_failed|Your request could not be verified. Refresh the page and try again.|
|403 forbidden|You do not have permission to publish or view this content.|
|404 not_found|This item is no longer available or you cannot access it.|
|409 draft_conflict|This draft has changed. Reload and review it before publishing.|
|409 already_published|This draft has already been published.|
|422 validation_error|Check the title, topic and draft version.|
|503 service_unavailable|Published content is unavailable. Please try again.|
|Other unexpected HTTP failure|The publication request failed. Please try again.|

- Requests per load and per retry: authenticated studio loads courses1, then materials1/draft-list1/publications1 for its course; selected draft adds detail1. Auth/health are separate existing requests. Opening publication loads topics1. Confirm sends POST1; success updates publication status from the returned detail, no required follow-up GET. Refresh publication status/retry status repeats list1; source resources Retry still repeats materials1/draft-list1, not successful publication reads. Catalogue loads courses1/publications1, selected detail1; type filter0. Every Retry repeats only failed read. Same-session-generation/write-epoch identical in-flight teacher GETs share a request, including StrictMode effect replay; finished reads never cache. No teacher calls while anonymous or wrong-role redirecting.
- Wrong role: existing role guard redirects authenticated students/admins to their own home before teacher requests. Student read APIs reject teacher/admin403. Anonymous demo teacher data shows sign-in guidance; demo-off redirects login. A role revoked after loading shows403 message without silently repeating a mutation.
- Link history: push or replace: sidebar/catalogue, View published version, course/type/selection changes and Clear publication selection push normal entries. Catalogue URL is `/teacher/review?course={id}&type={note|practice_set}&kind={note|practice_set}&publication={id}`; omit type for All content and omit kind/publication when no detail is selected. Type changes clear kind/publication; selection preserves the type filter. Studio URLs remain unchanged. Legacy `/teacher/practice` still replaces to questions studio. Form open/cancel/retry and successful POST do not navigate. Logout pushes login; expiry replaces.
- Refresh: reload saved draft/publication/status from server; no publication form or draft edit is persisted locally. Existing native unload warning applies while a draft edit is dirty/saving; publication adds no unload warning. Catalogue deep links reopen only currently authorised content.
- Back and Forward: restore route selections with fresh reads; ignore obsolete responses, even after leaving and returning to the same selection. Existing unsaved drafts prompt; type/course/draft changes cannot discard an active editor implicitly.
- Expired session or logout: clear private content/forms and invalidate pending outcomes; no cross-account request reuse or post-login mutation retry. Failed logout retains current session/editor.
- Backend down: show operation-specific network messages, retain visible saved content and form inputs, and explicit scoped Retry/Refresh controls; never claim publication succeeded without a valid response or subsequent status read.
- Longest wait before an error: publication and all new reads10seconds. Existing generation remains45seconds. No publication429/AI request is introduced; publication failures do not affect provider quota.
- No generic failure message: network/timeout use operation-specific messages above, while HTTP errors map by code; never label403/404/409/422/503 as a connection failure.

## Out of scope

Question assembly, subsets/mixed batches, notes duplicate storage/student note APIs, student practice UI/attempt/grading/companion integration, republishing/unpublishing/withdrawal controls, published edit/delete, autosave, notifications, new role/account management, live AI and deployment. The internal lesson helper may retain append/withdraw-compatible storage for existing callers; those are not teacher HTTP actions.

## Security and AI safeguards

- Concurrent requests (same time): share current session/user/membership locks, lock/refresh originating draft or batch FOR UPDATE before publication lookup/version/copy/commit. Same-payload races return one201 and one200 for one snapshot; differing payloads one201 and one409. Publish/edit or publish/delete serialise without partial snapshots or orphan references. Handle expired parallel requests through existing safe teacher auth (never reintroduce shared-lock cleanup upgrades). Revocation cannot win before an authorised mutation commit without its access checks reflecting that ordering.
- Normalisation: parse UUID strings to UUIDs; trim title with existing Python-compatible Unicode strip, count Unicode codepoints, reject blank/NUL/unpaired-surrogate text. Version is strict positive integer, not bool/float/string; body rejects missing/extra fields. Copy validated stored note/question strings exactly; do not silently truncate/repair them. MCQ validation uses existing limits/distinctness/casefold semantics. Student serializers explicitly allow-list safe fields.

No publication calls the model or exposes original upload bytes/paths. Teacher keys remain behind teacher/current-course checks; student MCQ reads have no key, explanation, source draft/question IDs, version/publisher/withdrawal metadata. The new read API does not bypass whole-set answer release by adding an answer endpoint. Notes are normal teacher-approved lesson contents, not a source of practice answer-key fields. Cache-Control:no-store applies to new endpoint responses, including safe errors. Independent tests use isolated PostgreSQL16 schemas and fake LLM only; preserve source files and unrelated work on every failure.

## Open questions

None for this increment. User selected both content types, student read APIs rather than practice-flow integration, and one teacher publication per draft. Existing lesson catalogue semantics/listing limits and helper append compatibility are preserved. API/UI/data choices are fixed in plan.md; future practice integration remains a separate feature.
