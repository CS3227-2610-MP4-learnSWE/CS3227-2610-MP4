# Plan: ADM-02 Targeted feedback forms

Status: Draft (human approval required before build)

## Data model
Use the existing relational persistence/transaction infrastructure with an additive migration and foreign keys, preserving existing account and lesson records. All timestamps are UTC ISO-8601 strings. Form, response and inbox IDs are server UUIDs. Existing account IDs are opaque strings, never UUIDs. Active admins share administration access.

- `feedback_forms`: id, title, description, association JSON, questions JSON, state (`draft|open|closed`), integer version starting 1, created_by, created_at, updated_at, published_at nullable, closed_at nullable, audience_role nullable. Draft save increments version. Publish and first close each increment version; terminal repeat close returns current version. Publication freezes all content and association.
- `feedback_recipients`: form_id, user_id (AccountID), display_name_snapshot, role_snapshot, inbox_id, read_at nullable; unique(form_id,user_id), unique(inbox_id). Publication inserts all rows in the same transaction as form-state change. Publication validates active, fixed-role audience and currently published association under locks; failure rolls back everything.
- `feedback_responses`: id, form_id, user_id (AccountID), display_name_snapshot, submitted_at, form_snapshot JSON, answers JSON; unique(form_id,user_id). Snapshot includes form title, description, association and full ordered questions with prompt, required, type/options/scale. Immutable even if a future release edits forms. Snapshot references are server-built, never accepted from clients.
- Form association references a supported feature ID from `FeatureList.md`, or one existing published lesson and its course. No association grants extra course rights. Account archive does not cascade-delete feedback. Referential consistency must survive app restarts and migration upgrade on populated databases.

### Wire types and validation
All JSON object keys below are exact; reject extra keys on writes. `UUID` means canonical UUID string; `DateTime` UTC ISO-8601 string. Nullable values are explicit `null`. JSON integers exclude booleans. Responses contain no unspecified private fields.

`AccountID` is an existing opaque account identifier of 1-64 characters, compared exactly to stored IDs; do not UUID-parse or casefold it. Reject leading/trailing whitespace rather than changing identity.

`Association = null | {kind:"feature",id:string} | {kind:"lesson",id:UUID}`. Feature IDs must exist in FeatureList; lesson must be published and not withdrawn. `Option={id:UUID,label:string}`. `Question={id:UUID,type:"short_answer"|"paragraph"|"multiple_choice"|"dropdown"|"checkbox"|"linear_scale",prompt:string,required:boolean,options:Option[],scale:null|{min:integer,max:integer,min_label:string,max_label:string}}`.

Client generates UUIDs for draft question and option IDs; immutable through save/reopen. Text questions require options=[] and scale=null. Choice questions require 2-20 options and scale=null. Scale questions require options=[], 0<=min<max<=10 and endpoint labels at most 80 characters (empty allowed). Prompt 1-500 characters; option label 1-200; title 1-160; description 0-2000; 1-30 questions on save/publication. Question IDs globally unique within a form and option IDs unique within each question. Duplicate trimmed/casefold labels invalid. Partial empty editor is local until valid save.

`DraftInput={title:string,description:string,association:Association,questions:Question[]}`. `Form={id:UUID,title:string,description:string,association:Association,questions:Question[],state:"draft"|"open"|"closed",version:integer,audience_role:null|"student"|"teacher",recipient_count:integer,response_count:integer,created_at:DateTime,updated_at:DateTime,published_at:DateTime|null,closed_at:DateTime|null}`. `FormSummary` is Form without description/questions. `Page(T)={items:T[],next_offset:integer|null}`. Lists use `limit` default 20, range 1-100 and `offset` default 0, range 0-100000; stable order created_at descending then id ascending, responses by submitted_at descending then id ascending; no totals required except form response_count and inbox unread_count.

`Answer={question_id:UUID,value:null|string|UUID[]|integer}`. Text answers are strings <=500 (short) or <=5000 (paragraph). Single-choice/dropdown values are one option UUID string; checkbox values arrays of 1-20 distinct configured option IDs; scale values are integers in range. Every question appears once in answers, with null for omitted optional questions. Empty string/empty array normalises to null for optional answers; required empties fail. No skipped required, extra, duplicate or unknown questions. Body size <=262144 bytes; combined text answer characters <=20000; no files. Mutation quotas per authenticated account: 60 per rolling minute; response submits additionally 10 per rolling minute; 429 includes Retry-After seconds. Read quota 120/minute. Use shared limiter abstraction, document process-local limitations if that is the existing implementation.

`ResponseSummary={id:UUID,form_id:UUID,respondent:{id:AccountID,display_name:string},submitted_at:DateTime}`. `ResponseDetail=ResponseSummary & {form_snapshot:{title:string,description:string,association:Association,questions:Question[]},answers:Answer[]}`. Recipient reads never return ResponseDetail or answers.

## API endpoints
All paths below use authenticated cookies and existing CSRF/origin protections where applicable. Protected responses including errors have no-store. New feature errors use `errors.ApiError` with the exact JSON envelope `{detail:{code:string,message:string,details?:object}}`; validation details hold field paths. Reuse existing framework validation mapping so malformed feature requests use the specified codes/copy. HTTP codes and feature code/message below are binding. Reject unknown or duplicate query parameters with V01. Audience pages sort by casefolded display_name then exact account ID; inbox pages sort by created_at descending then inbox ID ascending. 

| Method/path | Role | Request | Success |
|---|---|---|---|
| GET `/api/admin/feedback/forms` | admin | limit,offset | 200 Page(FormSummary) |
| POST `/api/admin/feedback/forms` | admin | DraftInput | 201 Form |
| GET `/api/admin/feedback/forms/{form_id}` | admin | none | 200 Form |
| PUT `/api/admin/feedback/forms/{form_id}` | admin | DraftInput plus version:integer | 200 Form; draft only, exact version |
| GET `/api/admin/feedback/associations` | admin | none | 200 `{features:[{id:string,label:string}],lessons:[{id:UUID,title:string}],truncated:boolean}`; each list max 500 sorted id; if more, truncated=true and UI says `More associations exist. Use a feature association or leave this form unassociated.` |
| GET `/api/admin/feedback/forms/{form_id}/audience` | admin | role=student or teacher, search string <=100 default empty, limit,offset | 200 Page({id:AccountID,display_name:string,role:"student"|"teacher"}); active eligible accounts only; search matches display name case-insensitively; no email returned |
| POST `/api/admin/feedback/forms/{form_id}/publish` | admin | `{version:integer,audience_role:"student"|"teacher",recipient_ids:AccountID[]}` 1-500 distinct IDs | 200 Form; atomic draft->open |
| POST `/api/admin/feedback/forms/{form_id}/close` | admin | `{version:integer}` | 200 Form; open->closed; already closed returns current Form regardless stale version |
| GET `/api/admin/feedback/forms/{form_id}/responses` | admin | limit,offset | 200 Page(ResponseSummary) |
| GET `/api/admin/feedback/forms/{form_id}/responses/{response_id}` | admin | none | 200 ResponseDetail; response must belong to form |
| GET `/api/feedback/inbox` | student,teacher | limit,offset | 200 `{items:[{id:UUID,form_id:UUID,title:string,created_at:DateTime,read_at:DateTime|null,state:"open"|"closed",submitted:boolean}],next_offset:integer|null,unread_count:integer}`; only own requests; association never changes recipient access or exposes associated lesson content |
| GET `/api/feedback/forms/{form_id}` | intended student/teacher | none | 200 `{id:UUID,title:string,description:string,association:Association,state:"open"|"closed",submitted:boolean,questions:Question[]}`; questions=[] if closed/submitted; transaction marks own request read; no other recipients/identity/answers |
| POST `/api/feedback/forms/{form_id}/responses` | intended student/teacher | `{answers:Answer[]}` | 201 `{id:UUID,form_id:UUID,submitted_at:DateTime}`; no raw response echo |

Every endpoint: 401 E01 if session missing/expired/inactive, 403 E02 wrong role, 429 E06 throttled, 503 E07 transient storage failure, 500 E08 unexpected error. Record endpoints return 404 E03 for missing/malformed/inaccessible IDs. Query/body validation 422 V01-V10 as relevant; oversized body 413 V08. Never return raw exception strings. No delete or reopen endpoint. Idempotent close and uniqueness make retries safe; publication repeat returns 409 C02 without new inbox rows; submit repeat returns 409 C05 without answer echo.

### Exact error dictionary
| ID | HTTP/code | Exact message |
|---|---|---|
| E01 | 401 `unauthenticated` | Backend: `Sign in to continue.` UI: `Your session has expired. Sign in again.` |
| E02 | 403 `forbidden` or existing `csrf_failed` | Preserve existing backend auth/CSRF messages. UI: `You do not have permission to access this feedback page.` |
| E03 | 404 `feedback_not_found` | This feedback form or response is not available. |
| E04 | transport `network_error` | Cannot connect to the server. Check your connection and try again. |
| E05 | client timeout `request_timeout` | The request timed out. Check the current form before trying again. |
| E06 | 429 `feedback_rate_limited` | Too many feedback requests. Wait before trying again. |
| E07 | 503 `feedback_unavailable` | The feedback service is temporarily unavailable. Try again later. |
| E08 | 500/other unexpected status `feedback_error` | The feedback service encountered an error. Try again later. |
| V01 | 422 `invalid_feedback_input` | Check the feedback form fields and try again. |
| V02 | 422 `invalid_feedback_title` | Enter a title of 1 to 160 characters. |
| V03 | 422 `invalid_feedback_questions` | Add 1 to 30 valid questions with unique identifiers. |
| V04 | 422 `invalid_feedback_options` | Enter 2 to 20 distinct options for each choice question. |
| V05 | 422 `invalid_feedback_scale` | Set a scale with whole-number endpoints from 0 to 10, with the minimum below the maximum. |
| V06 | 422 `invalid_feedback_association` | Select an available feature or published lesson. |
| V07 | 422 `invalid_feedback_text` | One or more feedback fields exceed their text limit. |
| V08 | 413 `feedback_too_large` | This feedback request is too large. Reduce its content and try again. |
| V09 | 422 `invalid_feedback_audience` | Select 1 to 500 different recipients from one audience role. |
| V10 | 422 `invalid_feedback_answers` | Answer every required question and check that all answers match their question type. |
| C01 | 409 `feedback_version_conflict` | This form changed in another session. Reload the saved form before continuing. |
| C02 | 409 `feedback_state_conflict` | This action is not available in the form's current state. |
| C03 | 409 `feedback_audience_changed` | Some selected recipients are no longer eligible. Review the audience again. |
| C04 | 409 `feedback_closed` | This form is closed. |
| C05 | 409 `feedback_already_submitted` | You have already submitted feedback. |

Validation priority: auth -> role -> record visibility -> state/version -> input validation. Submission checks published recipient visibility, current account state before revealing closed/submitted status; closed precedes duplicate. Payload validation selects the first applicable V code in dictionary order, with field paths in details. Any structurally invalid unknown-key/type body uses V01 (answers use V10). A forged unpublished form is E03 to respondents, never C02.

## Components and modules
Proposed new single-purpose modules: backend `feedback_models.py` for wire validation, `feedback_store.py` for transactions/access, `feedback.py` for routes; frontend `feedbackApi.ts`, `AdminFeedback.tsx`, `FeedbackInbox.tsx`, `FeedbackForm.tsx`, `FeedbackQuestion.tsx`. These are proposed new module names; follow existing package placement conventions.

### Source compatibility mapping supplied by orchestrator
Reuse `auth.dependencies.current_user(role=...)` (iterable roles supported), the shared cookie/Origin/CSRF checks, `auth.db.get_session`, `errors.ApiError`, and `User`, `Course`, `CourseMembership` from `teacher_materials.models`. Published-lesson metadata is `PublishedLesson` in `study_lessons.models`, including `withdrawn_at`; use existing `teacher_publications`/`study_lessons` access infrastructure and expose no lesson body. Reuse `auth.rate_limit.admit(key,limit,window_seconds) -> wait_seconds|None` (process-local; do not use the lower limiter without its lock), SQLAlchemy `Base` from `teacher_materials.models`, and the existing migration chain, never a second database/session pool. Register routes in backend `main.py`; reuse admin lookup patterns from `admin_access/routes.py` and `service.py`. Frontend routes and shell live in `src/App.tsx` and `components/Shell.tsx`. The eligible-recipient endpoint above is needed for focused active student/teacher selection; it may internally reuse the existing admin account query.

Frontend uses `services/client.ts` `request(method,path,body?,{timeoutMs?,distinguishTimeout?,cache?})`, returning unknown: validate its result, pass `timeoutMs:15000`, `distinguishTimeout:true`, and no-store caching. The existing session-generation mechanism invalidates stale reads. Existing `readOnce` coalesces StrictMode reads but does not pass timeout distinction; extend its optional options compatibly, or use a session-scoped in-flight adapter for feedback that preserves timeout classification and abort/generation safety. Reuse router, role shells and session logout flow. Existing `Inbox.tsx` and `FeedbackForm` are demo surfaces: student/teacher navigation must lead to persistent feedback requests with no fake inbox rows mixed in. Replace the existing `/student/inbox` and `/teacher/inbox` demo list with this persistent survey-request list; use `/.../feedback/{form_id}` only for respondent forms. Preserve the existing sidebar Inbox destination. Preserve unrelated admin demo messaging explicitly as demo if outside scope.

The binding independent test contract is HTTP. No new internal function signatures are required; route/store decomposition follows the existing shared modules. All actor IDs originate only from verified sessions. The spec-writer did not inspect application source; this mapping was supplied by the orchestrator's source-aware integration review.

## UI contract
The spec table's success/loading/empty copy and this plan's error dictionary are exact. Use a simple shared role shell, stacked labelled controls and plain text response rendering; responsive at 390px and desktop, keyboard-operable native controls, visible focus, no essential animation. Main headings are level 1. Dialogs trap focus and restore it to their opening button; close button `Cancel` cancels without requests.

Admin routes: `/admin/feedback` list; `/admin/feedback/new` new draft; `/admin/feedback/{form_id}` detail; `/admin/feedback/{form_id}/edit` draft editor; `/admin/feedback/{form_id}/responses` response list; `/admin/feedback/{form_id}/responses/{response_id}` response detail. Detail links/buttons `Edit draft`, `Review audience`, `Close collection`, `Review responses` appear only when appropriate (edit/review draft, close open, response review any state). Editor uses textbox `Form title`, textbox `Description`, combobox `Association type` options `None`, `Feature`, `Lesson`, combobox `Feature` or `Lesson` with title labels. `Add question` appends a locally generated question. Each fieldset legend `Question {n}` contains combobox `Question {n} type` with exact labels `Short answer`, `Paragraph`, `Multiple choice`, `Dropdown`, `Checkboxes`, `Linear scale`; textbox `Question {n} prompt`; checkbox `Question {n} required`; button `Remove question {n}`. Choice configuration has textbox `Question {n} option {m}`, button `Add option to question {n}`, button `Remove question {n} option {m}`. Scale has spinbuttons `Question {n} minimum`, `Question {n} maximum`, textboxes `Question {n} minimum label`, `Question {n} maximum label`. Initial editor has zero questions; add defaults short_answer, required=false. No reorder control; order is insertion order and removal compacts numbering. Navigation during unsaved changes shows dialog `Discard unsaved changes?`, buttons `Keep editing` and `Discard changes`; refresh uses native browser protection where supported.

Audience dialog contains combobox `Audience role` options `Students`, `Teachers`; textbox `Search recipients`; button `Search`; recipient checkboxes accessible name `{display_name} ({user_id})` (IDs disambiguate duplicates); buttons `Next page`, `Previous page`, `Review selected recipients`. Selected IDs persist across pages/search, clear on role change. Review view lists exact role, count and names/IDs; heading `Selected students` or `Selected teachers`; button `Back to selection`, `Publish form`. Publication requires this explicit review; never publish on role dropdown change. Close dialog text `Closing collection prevents new responses and keeps existing responses.`

Existing sidebar link `Inbox` for students/teachers and `Feedback forms` for admins. Inbox displays `Unread requests: {count}` as status; rows use text `Unread` or `Read`, `Open`, `Closed` or `Submitted`. Open form is `/student/feedback/{form_id}` or `/teacher/feedback/{form_id}`; inbox `/student/inbox` or `/teacher/inbox`. Respondent fieldset legend is `{n}. {prompt}` plus visible `Required` or `Optional`; text controls named `{n}. {prompt}`; choice/checkbox groups use that legend with options labelled by option text; linear scale native radiogroup name `{n}. {prompt}` with radio names decimal values, optional endpoint labels visible. Display privacy copy `Your name and feedback are visible to administrators.` Submit is disabled during the single mutation, closed or submitted. No stored answers in terminal state.

Response detail heading `Response {response_id}`, text `Respondent: {display_name}`, UTC submission timestamp, form title and question snapshots, type and Required/Optional, value labels resolved from snapshot options; plain texts preserve line breaks and wrap. Admin list rows label status `Draft`, `Open`, `Closed`; count `Responses: {count}`. Empty/failed responses do not invent aggregate summaries.

- Requests per load and per retry: Exactly the spec's per-screen counts, including once-only association fetch, explicit audience page/search fetch and no duplicate StrictMode request; all retry buttons repeat one failed operation. Navigation back into route issues one current read. Session bootstrap calls are separate existing auth flow, not extra feature reads.
- Wrong role: Replace redirect to own role landing route before rendering protected UI; zero feature API requests. Direct APIs return E02.
- Link history: push or replace: All navigation links push except auth/wrong-role redirects and post-create URL replacement. Local mutations/dialogs/filters/pagination do not push. Back/Forward reloads and clears prior private detail.
- No generic failure message: Exact E/V/C dictionary for each failure; unknown server status E08. No network error for HTTP responses. Timeout 15 seconds, abort requests on unmount/logout/account switch and ignore late responses. Preserve unsent local fields after recoverable failures; conflicts use reload and never silent overwrite. Inline validation is same copy as corresponding V error.

## AI usage
Not applicable: ADM-02 makes zero AI calls. Do not modify SoC LLM prompt/client or telemetry attribution. Feedback never enters companion page context; no authorisation decision depends on text instructions.

## Test plan
Independent designer works from approved contract in an isolated worktree, with the exact approved start commit, and does not read feature implementation before integration. Name every new test `test_adm02_...` (backend) or include `ADM-02` in browser names. Prove missing-feature RED before implementation integration. Mock provider clients if exercised indirectly; no live SoC calls.

| Criteria | Required evidence |
|---|---|
| AC01-AC03 | Save/reopen each of six types; browser renders correct native inputs; range endpoints/labels/options persist; reject invalid shapes/options/ranges |
| AC04 | Required validation for all six; whitespace and false/zero distinctions; optional empty becomes null; forged wrong types/foreign IDs rejected |
| AC05-AC06 | No/feature/lesson associations persist across app/store restart; unpublished lesson rejected; editing preserves IDs/order/settings; migration preserves existing rows |
| AC07-AC08 | Draft absent in inbox and respondent direct GET/POST denied with indistinguishable E03; draft save causes no delivery |
| AC09-AC10 | Role and named selected audience reviewed before explicit publication; atomic one-request-per-recipient inbox delivery; unselected users excluded; unread changes once on open |
| AC11-AC12 | Intended active student/teacher can open and submit only after publish; nonrecipient same-role/other-role/other-course forbidden; disabled/archived account loses access; association never grants lesson/course access; raw answers not returned to recipients |
| AC13, AC17, AC21 | No separate messages/AI/deletion/reopening introduced; browser exposes none; endpoint absence and no provider invocation |
| AC14-AC16 | Close blocks UI and direct submissions, keeps existing responses; repeated close safe; publish on closed rejected |
| AC18-AC20 | Response matches form/question IDs, immutable full snapshot and identity; admin-only list/detail; mismatched form/response path rejected; no private content in recipient/inbox payloads |
| Shared UI | Every success/loading/empty/error dictionary state; preservation after failed mutation; exact request counts per route/retry in effect replay; refresh/history/auth switch/timeout/late response; keyboard and mobile controls |
| Shared security | Injection/HTML stored as harmless text; unknown keys and impersonation fields rejected; bounded body/query/output and quotas; no-store; no credential/body exception leakage; no companion context ingestion |

Concurrency: two editors with same version produce one update and one C01; parallel publication yields one recipient set and no duplicate delivery; duplicate submissions yield one row/one success; close-vs-submit linearises correctly; publish-vs-update freezes exactly one revision; eligibility changes vs publish/submit cannot authorise a revoked user; failed inbox insert rolls back publication entirely. Test with real transactional persistence and a constrained pool, not only mocked sequential calls. Include restart persistence and raw snapshot immutability. Existing backend suite plus frontend tests, typecheck and lint are required before developer ready; independent integration and read-only verification follow. Record security results only in `workflow/security/test-log.md`, update both guides only when delivered.

## Decisions
Proposed for human approval: identified admin-only responses; no expiry/deletion in this release; all active admins authorised; publication immutable; exactly one audience role, explicit IDs (1-500), one response per recipient; lesson association is metadata only and never grants lesson access. Closing retains requests as closed in inbox. No retrospective targeting of newly joined accounts. Association list cap is explicit and cannot silently imply completeness.

Blocking before build: human approval of spec and plan, of the concrete privacy/retention proposals. Source compatibility mapping above is supplied by the orchestrator; amend the plan before independent work starts if a further integration check changes the public contract.
