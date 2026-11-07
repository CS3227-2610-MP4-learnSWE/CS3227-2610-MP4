# learnSWE Preview User Guide

Start the app using [README.md](../README.md). This guide covers the current preview; the feature list and user stories describe future production behaviour.

## Enter a workspace

At `/login`, use **Sign in** with your email and password. The server decides your role (student, teacher or admin) and takes you to that workspace; opening another role's page sends you back to your own. To register, choose **Create account**, enter a display name, email and a password of 10 to 128 characters (not a common password and not your email), then sign in. Accounts created this way are always student accounts; the page gives the same reply whether or not the email was already registered. **Log out** in the sidebar opens **Confirm logout**. Choose **Cancel**, Escape or the backdrop to stay signed in; choose **Log out** in the dialog to end the session. While the request is pending the controls are disabled. A failed logout keeps you signed in and the dialog open for retry. Session expiry still signs you out immediately without asking. You stay signed in for up to 12 hours. After too many failed attempts the page says how long to wait.

The Student, Teacher and Admin tabs on the login page only choose which demo shortcut to show; they do not change who you sign in as. After 5 wrong passwords for one email, sign-in for that email is refused for 15 minutes, even with the right password. Restarting the local backend clears this.

Separately, the **Demo shortcut (development)** buttons under the form open sample-data screens with no account and no session. In that demo mode the sidebar says "Demo (not signed in)", and you can switch roles using the header selector or return to the login page using the footer link. Demo mode cannot use live teacher materials/drafts, practice or the study companion. Teacher data pages show "Sign in to manage teacher materials and drafts."; student practice and the companion show "Sign in to use live practice and the study companion". A signed-in user does not see the role selector.

The sun/moon button toggles light/dark mode. The initial theme follows your operating-system preference. Theme and other local state reset on refresh. On narrow screens, open the navigation drawer with the menu button. The sidebar guidance card and its Open companion shortcut remain available in short windows; scroll the navigation list to reach other pages. Close a sidebar guidance card (including "Listen. Learn. Improve.") with its **Dismiss sidebar tip** X button. It stays hidden as you navigate the workspace; refresh or a new account/workspace restores it.

## Student

- Study companion access is checked again before a reply is returned. If your session ends or your account is disabled while waiting, the reply is withheld and you must sign in again.
- Overview shows three real figures for a signed-in student, all read from the server in one request: "Lessons completed" (completed lessons out of all published lessons in your courses), "Practice average" (the average, rounded down, of your latest score on each practice set you have submitted; "–" until you submit one) and "Topics to revise" (how many topics need practice, see Progress). If they cannot be read they show "–" with a note (or ask you to sign in in demo mode). The link "View full progress" opens the Progress page. The hero and the study companion strip are unchanged; the old sample figures, streak and activity chart are gone.
- Progress (requires a student sign-in; sidebar item "Progress") shows three sections. Lesson progress lists each of your courses with "N of M lessons complete" (or "No lessons published yet.") and your five most recently completed lessons, which link to the lesson. Practice scores lists every practice set you have submitted: your best score, your latest score (both written "correct / total") and how many attempts you submitted; attempts you have not submitted are ignored. Topics to revise uses this rule: for each practice set only your latest submitted attempt counts; a topic needs practice when you answered at least 3 questions on it (added up over those attempts) and fewer than 60% were correct (exactly 60% is fine); a topic with fewer than 3 answers is listed as not enough activity yet and is not called weak. Questions without a known topic count under "General". Empty states explain what to do (join a course, submit a practice set). If the server cannot be read the page says so with "Try again". Scores are kept on the server, so they survive a restart, sign-out and a new browser. Teachers and admins cannot open this page.
- Study materials (requires a student sign-in) lists the courses you belong to. Choose a course, filter by topic, search lesson titles and open a lesson. The list says how many lessons of the course you have completed. On a lesson, "Mark as complete" (or "Mark as incomplete") saves your choice on the server after it confirms; it is kept when you reload, sign out and sign in again, and updates the Overview figure when you open it. Lessons are plain text. You see lessons only after a teacher publishes them, through the content studio; developers can also add sample lessons with the seed command, and a new student sees "No courses yet" until added to a course. Demo mode shows a sign-in notice here instead of sample lessons.
- Practice (requires a student sign-in; sidebar item "Practice") opens a picker, "Choose a practice set": one section per course you belong to (A to Z), with the practice sets your teachers published there, newest first. Each row shows the set title (a link), "Topic: ..." and either "Best score: C / T" or "No attempts yet". A course without sets says "No practice sets published in this course yet."; with no course the page says "Join a course to start". If the list cannot be read the page says why and offers "Try again" (not for the access message). Choosing a set opens `/student/practice/SETID`. A set that does not exist, belongs to a course you are not in, or has a malformed address (for example an old bookmark) shows "This practice set is not available to you." with "Back to practice sets"; if access disappears while you practise, the page shows "This practice set is no longer available to you." and removes the questions and results. You can take a set as often as you like; the picker and Progress show your best and latest scores, and because answers are shown after submitting, repeated attempts can raise a score (there is no cap yet). The practice page loads one set of single-answer MCQs from the server (code snippets can appear in a question, but answers are selected choices, never free text). Answer every question and submit the whole set in one action; if any is unanswered, nothing is sent and the page names the missing question numbers. After a successful submission the score, your choice, the correct answer and the explanation for each question come from the server, and the choices lock. "Start another attempt" gives an empty form. If the server cannot be reached or fails, the page says so, keeps your answers and offers "Try again". If the failure happens after your answers were saved on the server, they are locked and "Try again" finishes the submission. Answers and results are kept while you move between student pages; a browser reload starts fresh. The server uses your signed-in student account for your attempts. The hint panel is a scripted demo, not AI. After submission a wrong answer is marked in red (your choice outlined in red, its explanation on a red background) and the correct choice is outlined in green; a right answer stays green, and the score banner turns amber unless every answer is right.
- The study companion is a bottom-right chat icon on every student page. Click it to open the chat box; Close or Escape minimises it and preserves messages and the unsent draft. The refresh icon clears both and starts fresh without reloading the page. Messages survive navigation within the student workspace; browser reload, returning to login or switching demo roles clears this temporary chat. Type a question (up to 1,000 characters; a counter under the box shows how many you have used, and a note appears if text beyond the limit was not added) and send it; a "Thinking..." note shows while the reply is on its way, and replies appear as plain text. If something goes wrong (no connection, the service is busy or unavailable, too many messages) the widget says so in plain words, keeps what you typed and lets you send again. You can send up to 20 messages a minute and 300 a day; past that it says how long to wait. The limit is counted per signed-in student account. Replies come from the SoC language model and can be wrong. The server decides what the companion may do: on the Practice page before you submit, it gives a short hint and a guiding question and does not state or confirm answers (it is not given the answer choices or the answer key); after you submit, open the companion from the Practice page results and it can explain that attempt, but if you have started a newer unsubmitted attempt it goes back to hints; on other pages it gives short app help and general software engineering explanations, says this is not course material and declines off-topic requests. If you paste a practice question into the chat on any page, you get a hint, not the answer. A check on the server blocks replies that name the right choice by letter in common forms (for example "the answer is b", "b is the answer", "Option A", "Correct: b", "the correct one is b", "answer = b", a tick, or a list such as "q1: a, q2: b"), that quote its text, or that mark a choice right or wrong; a blocked reply is replaced by a fixed message saying answers cannot be shared. This check is not perfect: a hint can still point towards an answer in other words, and other phrasings can still get through, such as paraphrases, "go with b", "pick B", "choose b", "the best choice here is b", hedged wording such as "the answer is probably b" or "the answer here is b", "the second option", letters written with look-alike Cyrillic characters, letters inside HTML tags, "[b]", spaced-out letters or numbers written as words. The companion does not use lesson content yet, so it cannot cite lessons. It needs the backend to be set up with the SoC LLM settings; otherwise it says it is unavailable. The chat itself is temporary and is not saved across reload or logout.
- A signed-in Inbox contains your targeted feedback requests, with private resumable drafts and Completed status after submission (see ADM-02 below), plus private feedback replies and announcements in Messages (ADM-04). The anonymous demo Inbox starts with two sample unread messages and a sample form whose preview submission saves nothing.

## Teacher

- Materials library stores metadata and original source bytes together in PostgreSQL. Select a managed course, optionally filter by topic or search, upload a PDF or UTF-8 text file (up to 10 MiB each, 100 MiB total upload storage across the app), download the original, or change its topic. Cancelling upload clears the form and errors. Uploading does not publish a lesson. Uploads survive backend restarts/redeploys. If the total budget is exceeded, the dialog explains the limit and keeps your input; cancel or retry explicitly. The limit counts original bytes, not total database usage.
- AI content studio generates concise study-note drafts from one source. Choose a course and source, then **Generate draft notes**. Generation sends source text to the SoC LLM; it needs the backend SOCLAAS settings. Inputs must have at most 8,000 normalised characters and 100 PDF pages. Scanned PDFs need a text-based source; longer sources are rejected rather than shortened.
- Successful drafts are saved in PostgreSQL and listed under **Saved drafts**. Open a draft to see its source title, creator and creation time. The URL can reopen the draft after refresh/restart. Every success creates a new unpublished draft; no student can read it through the teacher API. Notes may be inaccurate and require teacher review. Review saved content before publishing.
- In **Practice questions**, choose a course/source and **Generate 3 draft MCQs**. Every successful request saves a new batch of three questions, each with four choices, one correct answer and an explanation. Open **Saved MCQ batches** to review a batch; its URL reopens it after refresh or backend restart. Answers are visible only in the teacher workspace. Unpublished batches show **Unpublished draft · Review required**: AI may be inaccurate. One complete batch publishes as one three-question practice set; no question-selection or mixing screen is provided. Source limits and the real-request notice match note generation; malformed or truncated AI output is rejected without saving a partial batch. Generation disables selection/duplicate clicks. Explicit retry can create another batch if the first response was lost; no automatic retry occurs.
- Open a saved draft and choose **Edit notes**. Change its title or content, then **Save changes**; no AI call is made. Titles allow 1–200 characters and note content 1–2,000 Unicode characters after trimming/line-ending normalisation. The counter and validation explain the limit. The source title and original creator stay unchanged; last editor/time update on save.
- **Cancel** discards local edits after confirmation when needed. Navigation to another draft/course/page, including browser back/forward, asks **Keep editing** or **Discard changes** when edits are unsaved. A pending save must finish before in-app departure. Refresh/tab close uses the browser's native warning where supported; discarded/reloaded local edits are not stored.
- Failed saves keep your input and offer **Retry save**. Another teacher's save gives a conflict: **Load latest saved version**, then confirm discarding local edits, before editing the newer version. Failed latest loads preserve your local input. There is no force-overwrite; after a lost save response an explicit retry may report a conflict because the first save already committed.
- Unusable generated notes are rejected without saving a draft. Generation failures keep the selected source and existing drafts. Try generation again explicitly; if the previous response was lost, another saved draft may be created. Rate-limit failures say how long to wait when available. If you navigate away from a pending generation or change its selection, a late response cannot reopen it or display an obsolete error, even after returning to the same page.
- Teacher Materials and AI content studio require a teacher sign-in and current course membership. Any teacher managing the course may manage its sources and drafts. Anonymous demos show sign-in guidance without loading teacher records. Session expiry or successful logout clears private screens and unsaved edits; failed logout keeps the session and editor. **Published content** lists real immutable snapshots. Overview remains a sample preview. The signed-in Inbox contains real targeted feedback requests with resumable private drafts plus ADM-04 private messages; the anonymous inbox remains a sample preview.


- Open a saved MCQ batch and choose **Edit questions** to change all three questions, their four choices, correct answers and explanations. Use **Save changes** or **Cancel**. Questions/explanations allow 200 characters, choices 80; questions and choices must be distinct. Editing does not call AI. Counters, unsaved-navigation warnings and conflict recovery work like note editing.
- In read-only viewers choose **Delete note draft** or **Delete MCQ batch**, then **Delete permanently** to confirm. Batch deletion includes all three questions. Deletion is permanent and never publishes or unpublishes anything. A newer saved version must be loaded before retrying a stale deletion.
- In Materials choose **Delete material** and confirm to remove both its metadata and original bytes. First delete any note drafts and MCQ batches referencing that source; otherwise deletion is refused. Deleted original bytes release the upload budget after commit, but physical database usage may not shrink immediately. Failed or uncertain deletion keeps the item visible; refresh before retrying after a lost response.

The former **Practice sets** builder has been removed. Its old URL opens the content studio’s **Practice questions** tab. Review/edit the saved batch there; publish the complete reviewed batch as one practice set.

## Admin

- Analytics has sample reporting periods and labelled illustrative figures.
- Signed-in Feedback forms opens the persistent ADM-02 form manager described below. The anonymous legacy `/admin/forms` demo only previews a survey request and creates no form or inbox request.
- Feedback insights offers sentiment filtering, fixed AI analysis and links to supporting sample responses.
- Signed-in **Announcements** sends reviewed private messages to selected student or teacher audiences through the ADM-04 workflow below. The anonymous legacy announcement preview sends nothing.
- **Users** requires an admin sign-in and manages real accounts. Search by name or email, filter by role/status, and use Previous/Next to browse results. **Manage account** immediately opens an Account details overlay with status and course access; use **Close account details**, Escape or the backdrop to close it when no save is pending. Accounts have one fixed role; there is no promotion or demotion.
- Use **Create account** to create a student, teacher or admin. Enter a display name, email, role, password and matching confirmation. A green **Account created.** toast confirms success; name, email and both password fields clear while the chosen role stays selected (initially Student). Failed creation keeps your input. Existing password rules apply (10–128 characters, not common or equal to the email/name part). The password is not shown in account details. New accounts sign in with the password entered here, not a `SEED_*_PASSWORD` from `.env`. Share it privately with the owner; mandatory first-login password changes and password reset are not implemented.
- **Courses** creates courses with a title of 1–200 characters and a default **General** topic for teacher publishing. To assign a teacher or enrol a student, return to Users, choose their account, select a Course and choose **Grant course access**. New accounts begin with no assignments; teachers can manage only assigned courses. Disabled accounts can still have assignments edited. Admin accounts do not receive course assignments.
- **Disable account** requires confirmation and ends all sessions while keeping records and assignments. **Enable account** permits a fresh login; old sessions do not return. **Archive account** requires confirmation and is permanent: login is blocked, sessions/assignments are removed, and the email remains reserved. Learning/authorship records are retained. You cannot disable/archive yourself, and the last enabled admin is protected.
- **Remove course access** requires confirmation. Subsequent content requests are denied, but completion/authorship records remain; granting access again restores their visibility under existing feature rules. AI results are withheld if account/session access is lost while generation runs. Teacher generation also rechecks current course access; the student companion's legacy practice fixtures are not course-grounded retrieval.
- **AI usage** requires an admin sign-in and reports recorded service attempts, failure categories and available token measurements. Collection must be activated after migration/restart; incomplete history and missing measurements are shown as unavailable. See ADM-06 below.

### Set up local admin sign-in (PowerShell)

Use these steps with the existing local database configured in your checkout. For a fresh database, first follow [developer database setup](DeveloperGuide.md#local-admin-setup-and-password-reset-powershell). Commands assume a PowerShell terminal inside this repository. Keep existing database and SoC settings; do not overwrite an existing `.env` with the example file.

1. Start Docker Desktop, then prepare the backend env file without replacing it:

   ```powershell
   Set-Location (git rev-parse --show-toplevel)
   docker compose up -d postgres
   Set-Location src\backend
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   notepad .env
   ```

2. In **`src/backend/.env`**, add/update these settings, save, and close the editor. Replace existing entries rather than adding duplicate keys. These are public **local-test examples**, not production credentials:

   ```dotenv
   APP_ENV=development
   SESSION_COOKIE_SECURE=false
   SESSION_COOKIE_SAMESITE=lax
   ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   SEED_ADMIN_EMAIL=adm05-test@example.com
   SEED_ADMIN_PASSWORD='ExampleOnly!7Qm#42vL'
   ```

   Keep the password quoted in `.env` so `#` is literal; sign in without the quotes. There is **no default admin credential**. Public Create account creates students only. `.env` is Git-ignored. SOCLAAS credentials are not needed for login or account/course management.

3. Install backend dependencies, migrate, and seed:

   ```powershell
   Set-Location (git rev-parse --show-toplevel)
   Set-Location src\backend
   uv sync --frozen
   uv run --env-file .env alembic upgrade head
   uv run --env-file .env python -m teacher_materials.seed
   uv run --env-file .env python -m auth.seed
   ```

   `demo-admin: seeded` means credentials were saved. `unchanged` keeps the existing password/email. `skipped` means missing or invalid settings; read the reported reason. If you changed the password of an **existing seeded account**, run this explicitly:

   ```powershell
   Set-Location (git rev-parse --show-toplevel)
   Set-Location src\backend
   uv run --env-file .env python -m auth.seed --reset-passwords
   ```

   This updates **all configured seed accounts**, including student/teacher if their email/password pairs are set, not just the admin. It does not reset accounts created through Users, enable disabled accounts or restore archived accounts. If the email belongs to another account, use an unused test email. Editing `.env` alone, restarting, or seeding without this flag does not replace an existing password.

4. Start the backend. If already running, first press **Ctrl+C** in its terminal:

   ```powershell
   Set-Location (git rev-parse --show-toplevel)
   Set-Location src\backend
   uv run --env-file .env uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

   Keep this terminal open. After backend `.env` changes, fully stop and restart this command: `--reload` does not reload environment values loaded into the parent process by `uv`.

5. In a **second terminal**, prepare the frontend env file:

   ```powershell
   Set-Location (git rev-parse --show-toplevel)
   Set-Location src\frontend
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   notepad .env
   ```

   In **`src/frontend/.env`**, save these settings:

   ```dotenv
   API_PORT=8000
   VITE_ENABLE_DEMO_ACCESS=true
   ```

   If `API_PROXY_TARGET` is already configured, use `http://127.0.0.1:8000` or remove that override so `API_PORT` is used. Stop any existing frontend with Ctrl+C, then run:

   ```powershell
   npm.cmd ci
   npm.cmd run dev
   ```

   Restart after frontend `.env` changes too. `npm.cmd` avoids PowerShell's `npm.ps1` execution-policy error.

6. Open **http://127.0.0.1:5173/login** and use **Sign in**, not the demo shortcut. With the example settings, use `adm05-test@example.com` / `ExampleOnly!7Qm#42vL`. Successful login opens the admin workspace. Continue with the account/course checks below.

7. To test a password change, keep the admin email unchanged, edit `SEED_ADMIN_PASSWORD`, save, and run the reset command in step 3. Sign out, try the old password once (it should fail), then sign in with the new password (it should succeed). Reset seeding does not end existing browser sessions; a page that remains signed in is not evidence that the new password works.

| Result | Meaning and next step |
|---|---|
| Initial `GET /api/auth/me` 401 | Normal before sign-in: no authenticated session yet. |
| `POST /api/auth/login` 401 | Incorrect credentials or inactive account. Check the seed output, then apply `--reset-passwords` if you changed an existing seed password. |
| Login 403 | Origin verification failed. Check `ALLOWED_ORIGINS` includes your exact frontend address/port, then fully restart the backend. Do not disable CSRF protection. |
| Login succeeds, but the session disappears on the next request | For local plain HTTP, check backend `SESSION_COOKIE_SECURE=false`, fully restart, and retry. Production HTTPS requires Secure cookies. This differs from a login 401 rejecting credentials. |
| Protected action 403 | Can be a wrong role or CSRF/Origin problem. Inspect `forbidden` versus `csrf_failed`; sign in with the appropriate account. |
| Login 429 | Too many attempts. Wait for the retry period; restarting a local development backend also clears its in-memory limiter. |
| API 503 or network failure | Check PostgreSQL, migrations, backend port and frontend proxy settings; this does not mean the password is incorrect. |

### Try account and course management locally

1. Sign in with your locally configured seeded admin. Open Courses and create `ADM-05 test course`.
2. Open Users and create a test student and teacher using different unused test emails. For a local test only, `ExampleOnly!7Qm#42vL` is a valid example password. It is public example text, never a production password or default credential.
3. Manage each account and grant the test course. Sign in as the teacher in a separate browser profile: the course appears in Materials with its General topic available for publishing. A student sees the course in Study materials, initially with no published lessons. Publish a note as the teacher to test student reading/completion.
4. Keep the student signed in while the admin disables them. Their next protected request must require sign-in. Re-enable the account and sign in again; enrolment/completion are retained.
5. Remove the student's course access and confirm. A fresh lesson request must show unavailable. Regrant to check retained completion.
6. Archive the test account and confirm. It cannot sign in, be re-enabled or recreated with the same email. Select Archived in the Status filter to inspect the retained account. Never use an important account for this irreversible test.

## Limitations and recovery

The demo shortcut screens are public local demonstrations with unrestricted role switching. Do not use real credentials or sensitive materials in them. Preview state is temporary; refresh returns to sample defaults. Teacher material metadata and original bytes persist together in PostgreSQL. The new storage version uses a fresh database; previous local uploads/drafts remain in the old setup and must be recreated in the new one. Unknown routes send a signed-in user to their own home and everyone else to login, except inside a role area, which shows a role-specific not-found view. An unavailable backend shows a footer status and does not prevent exploring screens, except the student Practice page, which needs the backend to load questions. The practice server withholds the answer key and explanations until whole-set submission and checks attempt ownership using the signed-in student's account. Teacher data screens require a teacher sign-in and current course membership. Admin Users and Courses use live account/course records; AI usage reports real recorded monitoring metadata after collection activation. Admin feedback forms, submitted-response review and announcements also use live records. Analytics and the legacy feedback-analysis and usage previews remain sample screens. Online deployment and AI feedback analysis remain future work. The student study companion and teacher note/MCQ generation call the SoC LLM. Every teacher API uses the shared authenticated session, checks course membership and ignores legacy identity headers. Practice attempts are stored in the database (attempts made before the STU-04 change are lost); browser reload clears the current page state.

## Publishing reviewed teacher content

Open a saved, read-only note or MCQ batch in **AI content studio**. Choose **Publish notes** or **Publish practice set**, enter a publication title and choose a required course topic. The confirmation shows the saved content; **Confirm publication** creates a permanent snapshot. Publication makes no AI request. Cancel clears the form. A batch always publishes all three questions together.

Notes become available to enrolled students in **Study materials** after refresh. Published practice sets appear in the student **Practice** picker for students of that course, who can answer, submit and review them there.

Each draft can publish once. Editing it afterward changes only the private working draft; it cannot update or republish the snapshot. Published references prevent draft deletion and therefore also protect the source. No unpublish or published-content deletion controls exist. **View published version** opens **Published content**, where course/type filters and direct links reopen read-only snapshots. Older lessons can show **General**, missing provenance or **Withdrawn**; withdrawal cannot be changed here.

Failed publication preserves form input. Reload and review stale drafts before confirming again. After an uncertain/lost response, use **Refresh publication status** before retrying; mutations never retry automatically. An identical retry returns the existing snapshot instead of another publication.


## Admin AI usage monitoring (ADM-06)

### Before testing

- Complete [ADM-06 local setup](DeveloperGuide.md#adm-06-local-setup).
- Use an enabled admin account. Demo shortcuts do not sign you in.
- Open **http://127.0.0.1:5173/login**.

### Manual test checklist

Report text is inset from the panel border. Long explanations wrap inside their columns; scroll the table horizontally to see all metrics.

| Step | Action | Expected result |
|---|---|---|
| 1 | Sign in as admin. Open **AI usage**. | Filters and feature rows. Default: All features, last seven UTC dates. |
| 2 | Select **Student assistant (STU-03)**. Click **Apply filters**. | One student-assistant row. |
| 3 | Select **Teacher generation (TEA-02)**. Apply. | One row combining notes and MCQ calls. |
| 4 | Select **Feedback analysis (ADM-03)**. Apply. | **Unavailable**: collection is not enabled. |
| 5 | Set Start date after End date. Apply. | Date-range error. Correct the dates and apply again. |
| 6 | Try more than 31 days, then a future End date. | Both selections rejected. |
| 7 | Change filters, refresh, then navigate away and Back. | Default filters and a fresh report each time. |
| 8 | Log out. Sign in as student or teacher. Open `/admin/ai-usage`. | Redirect to your own role's home. No admin report. |

### Check real request counts

1. Configure SoC credentials for chat/generation. Real calls use SoC quota.
2. After activation's next **00:00 UTC** (08:00 Singapore), set both dates to the current UTC date.
3. Select STU-03 or TEA-02. Record its Requests value.
4. In another browser profile, send one student chat message or generate teacher notes/MCQs.
5. Return as admin. Click **Apply filters**.

Expected results:

- Requests increases by one per provider attempt. A retry adds another attempt.
- Provider failures increase Failures. Provider 429s also increase Rate-limit failures.
- Local validation/quota rejection does not increase counts.
- Tokens appear only when that measurement was recorded for every call. Total tokens are never calculated from the other columns.
- Complete coverage with no calls shows zero counts and unavailable tokens.
- Earlier history, partial coverage and interrupted recording show **Unavailable** with a reason.
- Credentials, prompts, replies and user identities are excluded.

**Need results immediately?** Run the [ADM-06 automated tests](DeveloperGuide.md#adm-06-automated-tests). They use mocks: no waiting or live AI.

### Recovery checks

- Stop the backend with Ctrl+C. Apply filters. Expect an error with **Retry**.
- Restart the backend. Click **Retry**. The last applied selection loads; unsent edits stay in the fields.
- Requests time out after 15 seconds. No automatic retry.
- Session expiry returns to sign-in with "Your session has expired. Sign in again." Logout clears the report.

## ADM-02: targeted feedback forms

Sign in with a real account to use feedback. Anonymous demo inbox messages remain labelled sample data and do not send or save feedback.

Before the walkthrough, start PostgreSQL, apply the ADM-02 migration to your configured development database, and run the backend with `--env-file .env` as shown in the [ADM-02 developer setup](DeveloperGuide.md#adm-02-targeted-feedback-implementation). The migration and serving backend must use the same database. If the page reports `The feedback service is temporarily unavailable`, check the backend terminal, PostgreSQL, migration state and Vite proxy; ADM-02 is available once those dependencies are ready.

In the admin form list, the title, state and response count form one clickable row. Open a form and choose **Review responses**; each response row leads with the respondent name, with a local submission date/time and secondary response ID. Clicking anywhere in the row opens Feedback response, with the original ID shown separately. Rows have a subtle hover and keyboard-focus highlight.

### Admin: prepare, publish and review

1. Open **Feedback forms** (`/admin/feedback`), then **New feedback form**.
2. Enter a title and optional description. Optionally associate a feature or published lesson. Association is a reference only and grants no lesson access.
3. Use **Add question**. Choose Short answer, Paragraph, Multiple choice, Dropdown, Checkboxes or Linear scale. Enter the prompt and select **required** when needed. Choice questions need 2–20 distinct options. Scales use whole-number endpoints between 0 and 10, with the minimum below the maximum, and optional endpoint labels. A form has 1–30 questions.
4. Click **Save draft**. Saved unpublished forms can be reopened with **Edit draft**. They cannot receive responses and send no inbox requests.
5. From the saved form, choose **Review audience**. Select Students or Teachers, search, and select individual recipients. Selection persists across audience pages and clears when the role changes. Choose **Review selected recipients**, check the names and role, then **Publish form**. Up to 500 recipients from one role can receive a form.
6. Publication freezes the questions and selected audience and creates a private inbox request for each recipient. Later accounts do not receive the earlier request.
7. Use **Review responses** to open submitted feedback with the respondent name, submission time and the exact question snapshot. Unfinished response drafts are private to their owners and do not appear here or count as responses.
8. Choose **Close collection**, then **Confirm close**, to stop draft editing and submission permanently. Existing submitted responses remain available. Reopening, deleting, AI analysis and separate follow-up messages are outside this feature.

All active admins can manage the forms and review submitted responses. Feedback is identified; it is not anonymous. Records have no automatic expiry or deletion in this release.

### Student or teacher: save progress and complete a form

1. Open **Inbox** and select an intended feedback request. The inbox distinguishes **Not started**, **Draft**, **Completed** and **Closed**, independently of read/unread status.
2. Fill in any answers. Unfinished answers automatically save after one second without an edit. Required answers may be empty in a draft. Wait for **Draft saved. You can return to finish later.** before closing the browser.
3. Return to the request to continue from the saved answers, including after refresh or a later sign-in on another device. Normal navigation inside the app waits for pending draft changes to save. Browser termination or offline navigation cannot recover edits the server never received.
4. Click **Submit feedback** when finished. Required fields and answer types are validated. Successful submission shows **Completed** and **Feedback submitted. Thank you.** Submitted responses cannot be edited or submitted again.

Only you can read your unfinished draft. Once submitted, your name and feedback are visible to administrators. Closing collection stops saving and submission; it does not convert an unfinished draft into a submitted response.

### Recovering from a feedback error

- A failed save keeps current answers on the open page and shows that the latest changes are not saved. Keep the page open and use **Retry saving draft**. No automatic retry occurs.
- If another session changed the same draft, **Reload saved draft** asks before replacing local changes. The app never silently overwrites a newer saved revision.
- If submission times out or loses its connection, use **Check submission status** before trying again. A completed server submission remains completed even if its original response was lost.
- For uncertain admin save/publication/closure, use **Reload saved form** before another write. An uncertain new-form save opens the list so you can select the saved form instead of creating it blindly again.
- Requests time out after 15 seconds. Logout clears the page; acknowledged drafts remain on the server for your later authorised session. Disabled/archived accounts and users outside the selected audience cannot access a request.


## ADM-04: feedback replies and announcements

Admins can open a submitted feedback response and choose **Respond to feedback**. The recipient is fixed to that respondent and shown before sending. Enter **Subject** and **Message**, choose **Review message**, read the complete text and recipient list, then choose **Confirm send**. **Edit message** restores the composer. Messages are plain text; raw feedback is never included automatically. Review your wording before sending because sent messages cannot be edited or recalled.

For an announcement, open **Announcements**, select **Students** or **Teachers**, and choose **All active users** or **Selected users**. Selected recipients remain selected while you search or change pages; changing role clears the selection. Review shows the exact frozen audience before confirmation. At most 500 recipients can receive one announcement; choose a smaller selected audience when necessary. If a recipient's eligibility or name changes, review the audience again. An empty audience cannot be sent to.

Students and teachers receive each delivery as unread in the **Messages** section beneath their existing feedback requests. The section displays the full subject, text, type and timestamp, with its own unread count. **Mark as read** persists across refresh; **Load more messages** retrieves older messages. Other recipients and raw survey responses are not exposed. Email and push notifications are not sent.

A review remains valid for 15 minutes. Refreshing its URL recovers the review or its sent receipt and never sends automatically. If confirmation times out or loses connection, retry **Confirm send** on that same review; this checks/completes the same delivery without duplicating it. Creating a fresh review intentionally creates a different message. Keep the same review URL when delivery is uncertain. Use **Retry** or **Retry messages** for failed loads; errors retain unsent text while you remain in that session. Leaving an unreviewed composer or refreshing it clears local unsent fields. Logout clears private page state. Expired reviews require a fresh review.


### Student inbox: what you see and what is not available

- **Feedback requests** lists each published form sent to you with its title, a Read or Unread label and a status chip: **Not started**, **Draft**, **Completed** or **Closed**. Lists show 20 at a time with **Previous page** and **Next page**. Selecting a request opens its form. A closed form shows "This form is closed." and accepts no changes.
- **Messages** lists announcements and feedback replies. Each card shows its type, an Unread or Read chip, the subject, the text, the sent time and **From: Administrator**. The inbox does not show which administrator sent a message, so the sender is always shown as Administrator.
- The form page states: once submitted, your name and feedback are visible to administrators; your unfinished draft is private.
- A form is sent to named recipients chosen by an admin. Targeting a student group or class is not available. Email and push notifications are not available; the sidebar badge updates every minute and when you return to the window; reopen the Inbox to see new items (see the badge description above).


### ADM-04: redesigned inbox and composer
The **Inbox** sidebar badge counts unread feedback requests plus messages; it disappears at zero and shows **99+** for larger counts. Opening a request or marking a message read updates the count. While the app is visible it checks for new unread items every minute and when you return to the window; it does not provide instant push notifications. A temporary background failure retains the last known count until the next refresh.

The Inbox separates **Feedback requests** from **Messages**. Unread messages have a blue accent and an Unread chip; each card separates the subject, message and local date/time. Announcements and feedback replies use the same clear layout. The composer places **Message details** beside a separate **Recipients** panel on desktop and stacks them on mobile. Outlined Subject/Message fields remain visually distinct from headings. Search filters the recipient list only; **All active students/teachers selected** still means the entire role audience. Review always shows the exact recipient list before confirmation.


### Shared design across the admin workspace

Feedback forms, Users, Courses and AI usage follow the shared admin design: outlined labelled fields, distinct section headings, padded panels and clear keyboard focus in light and dark themes. Narrow screens stack the panels and wrap long names and identifiers.

- **Feedback forms:** the editor groups Form details, Association and Questions. The saved-form view separates its overview and question list. Review audience separates recipient search from selection, shows the selected count across searches/pages and presents the exact recipients before publication.
- **Users:** Find accounts and Create account appear side by side on wider screens and stack on smaller screens. Account details and access-removal confirmations retain their existing actions and keyboard behavior.
- **Courses:** Create course is separate from Available courses. Manage course access in Users remains the route to enrolments and teacher assignments.
- **AI usage:** Report filters are separate from the Service-call report. The reporting range is still UTC; collection timestamps display in local time. Wide results scroll within their own keyboard-focusable area. Missing measurements remain explicitly unavailable.

Analytics and the legacy feedback-analysis, form and usage demos retain their sample-only notices. This visual update does not activate live analytics or AI feedback analysis. ADM-04's composer and recipient Inbox retain their existing design.


When choosing announcement recipients, moving to another result page keeps that page selected until you change the search or audience role. Search updates after a short pause in typing; selected recipients remain selected across pages and searches.
