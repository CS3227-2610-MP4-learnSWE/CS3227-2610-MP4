# learnSWE User Stories

These proposed stories describe user goals within the capabilities in [FeatureList.md](FeatureList.md). Features group related stories; they are not implementation tasks. Each story should deliver a demonstrable outcome, with acceptance criteria defining completion. None is marked implemented.

Story IDs use `US-<feature ID>-<story number>` to preserve traceability. These replace the original broad one-story-per-feature draft. Stories may depend on shared capabilities or earlier stories; they need not be implemented in isolation.

The student, teacher and admin sections define MVP stories. The separate optional section is outside the MVP.

## Student

### STU-01 — Study materials

#### US-STU-01-01 — Read published lessons

As a student, I want to browse lessons by course and topic and open a lesson so that I can find the material I need.

Acceptance criteria:

- Only published lessons in courses I can access are listed and readable.
- Drafts and unauthorised lessons remain inaccessible through direct requests.

#### US-STU-01-02 — Record lesson completion

As a student, I want to mark a lesson as complete or incomplete so that I can track my study and correct accidental changes.

Acceptance criteria:

- I can mark an incomplete lesson complete and a completed lesson incomplete.
- Either status persists after signing in again and updates my completion totals and progress view.

### STU-02 — Practice questions

#### US-STU-02-01 — Submit a practice attempt

As a student, I want to answer and submit a published practice set so that I can check my understanding.

Acceptance criteria:

- I complete all single-answer multiple-choice questions (MCQs), then submit the whole set in one action; incomplete sets are rejected with the missing questions identified.
- Every question supplies choices with exactly one correct answer; I select one choice per question. Code snippets may appear in a question, but there is no free-text answer input.
- I can revise answers before whole-set submission; there is no per-question submission, score or immediate correctness feedback.
- Successful submission saves the complete attempt, answers and set score against the question and answer-key version used, then makes results available.
- Failed submission does not unlock results or full AI solutions and preserves my entered answers for retry.
- Submission does not execute student code.

#### US-STU-02-02 — Review a practice attempt

As a student, I want to review a saved attempt so that I can understand my mistakes.

Acceptance criteria:

- Only after successful whole-set submission can I see my submitted answers, set score, correct answers and teacher-approved explanations.
- Direct requests cannot retrieve answer keys or solution explanations for an unsubmitted attempt.
- I cannot retrieve another student’s private attempts.

### STU-03 — AI learning assistant

#### US-STU-03-01 — Ask for a course explanation

As a student, I want to receive guided AI explanations that build on what I already understand so that I can identify conceptual gaps and solve questions independently.

Acceptance criteria:

- The assistant uses guiding questions and explanations to address the gap I describe, asking what I have tried or understood when needed.
- Guidance is grounded in authorised published materials, with source references that do not expose protected solutions.
- For unsubmitted practice, explanations remain hints only, including when the question is pasted into a general chat.
- When material does not support an answer, the assistant states the limitation instead of inventing a source.
- A service failure or rate limit leaves my typed question available to retry.

#### US-STU-03-02 — Request a learning hint

As a student, I want to request a hint for a practice question so that I can make progress before seeing the solution.

Acceptance criteria:

- Until the whole set is successfully submitted, every response gives hints or guiding questions without revealing or confirming correct answers, full solutions or equivalent solution code.
- Explicit requests for answers, repeated hints, answer-checking requests and teaching preferences do not override this rule.
- The server checks my attempt status and excludes protected answer keys and solution explanations from pre-submission context; hints and source links are checked for answer leakage.

#### US-STU-03-03 — Understand a submitted solution

As a student, I want to ask for a full explanation after submitting a practice set so that I can learn from my mistakes.

Acceptance criteria:

- Full solution help is available only after the server verifies successful whole-set submission for my own attempt.
- Explanations correspond to that attempt’s question and answer-key version.
- A previous submission does not unlock answers for a new unsubmitted attempt; retry and question-reuse rules must address already-seen answers.

#### US-STU-03-04 — Keep a conversation while learning

As a student, I want a floating study companion available while navigating lessons and practice so that I can ask for guidance without leaving my current page.

Acceptance criteria:

- A bottom-right icon opens a bottom-right chat box on student pages, with accessible labels and mobile/light/dark support.
- Close minimises to the icon without clearing history or the unsent draft; reopening restores the conversation. Escape also minimises and restores focus to the icon.
- History remains scoped to the same authenticated account across page changes and reload until logout or explicit clear; account switching cannot expose another account’s conversation.
- The refresh/clear control removes conversation history and the unsent draft and starts a new conversation without reloading the page.
- Logout removes the active account’s chat from the client session. This requirement is not permission to implement cross-account chat storage.

#### US-STU-03-05 — Get guidance in the current page’s context

As a student, I want the companion to understand the page I am viewing so that I do not have to repeatedly explain the lesson or question.

Acceptance criteria:

- Current page context updates as I navigate and includes relevant authorised, student-visible lesson or question content, not just the URL.
- The backend revalidates access and submission status before retrieving context. Answer keys, protected solution explanations, drafts and other users’ data are excluded before submission.
- Page content and prior chat are untrusted input, cannot override fixed rules, and are bounded to the relevant context rather than indiscriminately scraping the entire app.
- This UI preview only displays a current-page label and fixed replies; real context-aware responses and account-session persistence are not implemented yet. Local history survives navigation/minimise but resets on page reload, login or demo role switching.

### STU-04 — Progress dashboard

#### US-STU-04-01 — View learning progress

As a student, I want to view lesson completion and saved practice scores so that I can understand how my learning is progressing.

Acceptance criteria:

- The view reflects my saved completion records and attempts.
- No activity produces an explanatory empty state.

#### US-STU-04-02 — Identify topics to revise

As a student, I want to see topics needing further practice so that I can focus my revision.

Acceptance criteria:

- Topics are identified from my recorded results using a documented rule.
- The view explains when there is insufficient activity to identify topics.

### STU-05 — Submit feedback

#### US-STU-05-01 — Submit student feedback

As a student, I want to complete an open feedback form intended for me so that I can report problems and suggest improvements.

Acceptance criteria:

- I can find forms targeted to me or my student group.
- Required fields are validated and submission is confirmed.
- The saved response belongs to the correct form and is unavailable to other students.

### STU-06 — Student inbox

#### US-STU-06-01 — Read student follow-up

As a student, I want to read admin messages and relevant announcements so that I can know how feedback is being addressed.

Acceptance criteria:

- My in-app inbox contains admin survey requests, feedback responses and announcements addressed to me or an audience I belong to, with sender and sent time.
- Messages intended for other users or groups remain inaccessible.

#### US-STU-06-02 — Open survey requests

As a student, I want to open a survey request from my inbox so that I can respond to the relevant form.

Acceptance criteria:

- Opening a request leads to the associated form, subject to audience checks.
- Closed or unavailable forms show a clear status and reject submissions.

#### US-STU-06-03 — Track unread messages

As a student, I want to distinguish read and unread inbox messages so that I can identify requests needing attention.

Acceptance criteria:

- New messages are unread, and opening a message marks it read for my account.
- Read status persists after signing in again, and the unread count matches unread messages I can access.
- Email and push delivery are outside the MVP.

## Teacher

### TEA-01 — Manage learning materials

#### US-TEA-01-01 — Upload source material

As a teacher, I want to upload source material to a course I manage so that I can prepare learning content from it.

Acceptance criteria:

- Supported files within configured size limits are saved to the selected course.
- Rejected uploads explain the accepted formats and limits.
- Uploading does not publish student-facing content.

#### US-TEA-01-02 — Organise source materials

As a teacher, I want to assign uploaded material to a topic and browse my course materials so that I can find the right sources for lesson preparation.

Acceptance criteria:

- I can assign a material to a topic in its course and find it under that topic.
- I cannot organise or retrieve materials for courses I do not manage.

### TEA-02 — AI content generation

#### US-TEA-02-01 — Generate draft notes

As a teacher, I want to generate study notes from selected source material so that I can reduce lesson preparation time.

Acceptance criteria:

- I can select an authorised source and receive editable draft notes.
- Generation does not publish content; failure preserves the source and existing drafts.

#### US-TEA-02-02 — Generate draft questions

As a teacher, I want to generate practice questions from selected source material so that I can prepare practice activities more quickly.

Acceptance criteria:

- Generated drafts contain MCQs only, with answer choices, exactly one correct choice and an explanation per question; no free-text answer questions.
- Unusable output is identified clearly and failed requests preserve existing work.
- Generated questions remain unpublished until reviewed and explicitly published.

### TEA-03 — Review and publish

#### US-TEA-03-01 — Preview generated content

As a teacher, I want to preview draft content so that I can check its accuracy before editing or publishing.

Acceptance criteria:

- I can preview generated study notes, practice questions, answer keys and explanations for my managed courses before approval or publication.
- Previewing does not make drafts visible to students.

#### US-TEA-03-02 — Edit draft notes

As a teacher, I want to edit and save draft notes so that I can correct errors before students read them.

Acceptance criteria:

- Saved edits persist when I reopen the draft.
- Edits to an unpublished draft do not change the published version.

#### US-TEA-03-03 — Correct draft questions

As a teacher, I want to edit draft questions, answer keys and explanations so that I can provide accurate practice content.

Acceptance criteria:

- I can review and correct each MCQ’s wording, answer choices, single correct choice and explanation.
- Required fields and the single correct choice are validated; corrections persist when reopened.

#### US-TEA-03-04 — Publish reviewed content

As a teacher, I want to explicitly publish reviewed content so that I can make approved learning material available to students.

Acceptance criteria:

- Publication validates required content fields and requires my explicit action.
- Authorised students can access published notes and practice questions while other drafts stay hidden.
- Publishing does not expose answer keys or solution explanations before successful whole-set submission.

### TEA-04 — Manage practice sets

#### US-TEA-04-01 — Assemble a practice set

As a teacher, I want to select questions for a topic-based practice set so that I can give students focused practice.

Acceptance criteria:

- I can save a set containing MCQs only and a topic in a course I manage.
- I can review the set before publishing it through the content publication workflow.

#### US-TEA-04-02 — Maintain practice answers

As a teacher, I want to update answer keys and explanations in a practice-set draft so that I can keep future practice accurate.

Acceptance criteria:

- I can save corrected keys and explanations before explicit publication.
- Existing submitted attempts retain their original question and answer-key versions.

### TEA-05 — Learning overview

#### US-TEA-05-01 — View course participation

As a teacher, I want to view lesson completion rates so that I can identify where students stop progressing.

Acceptance criteria:

- The report covers only courses I manage and identifies its reporting period.
- Completion calculations are documented and no activity shows an empty state.

#### US-TEA-05-02 — Identify common mistakes

As a teacher, I want to view practice results and commonly missed questions so that I can decide what to explain again.

Acceptance criteria:

- Results cover only courses I manage and identify the reporting period.
- Missed-question calculations are documented and no attempts shows an empty state.

### TEA-06 — Feedback and teacher inbox

#### US-TEA-06-01 — Submit teacher feedback

As a teacher, I want to complete a feedback form intended for me so that I can help improve teaching workflows.

Acceptance criteria:

- Open forms targeted to me or my teacher group are available.
- Required fields are validated, successful submission is confirmed and other teachers cannot access my private submission.

#### US-TEA-06-02 — Read teacher follow-up

As a teacher, I want to read admin follow-up messages so that I can understand what action is being taken.

Acceptance criteria:

- My in-app inbox contains admin survey requests, feedback responses and announcements addressed to me or my group, with sender, sent time and content.
- Other users’ private messages remain inaccessible.

#### US-TEA-06-03 — Open survey requests

As a teacher, I want to open a survey request from my inbox so that I can respond to the relevant form.

Acceptance criteria:

- Opening a request leads to the associated form, subject to audience checks.
- Closed or unavailable forms show a clear status and reject submissions.

#### US-TEA-06-04 — Track unread messages

As a teacher, I want to distinguish read and unread inbox messages so that I can identify requests needing attention.

Acceptance criteria:

- New messages are unread, and opening a message marks it read for my account.
- Read status persists after signing in again, and the unread count matches unread messages I can access.
- Email and push delivery are outside the MVP.

## Admin

### ADM-01 — Feature analytics

#### US-ADM-01-01 — Inspect feature usage

As an admin, I want to view chatbot requests and practice completion for a reporting period so that I can understand feature adoption.

Acceptance criteria:

- Counts use documented event definitions and the selected period.
- The report distinguishes no activity from unavailable data without displaying private chat content.

#### US-ADM-01-02 — Inspect generation reliability

As an admin, I want to view AI generation success rates so that I can identify unreliable workflows.

Acceptance criteria:

- The report uses a documented success definition and denominator for the selected period.
- Periods with no requests do not display a misleading success percentage.

### ADM-02 — Targeted feedback forms

#### US-ADM-02-01 — Draft a feedback form

As an admin, I want to create a form with questions and required fields so that I can collect focused feedback.

Acceptance criteria:

- I can save and reopen a draft with questions and an optional feature or lesson association.
- An unpublished form cannot receive responses.

#### US-ADM-02-02 — Publish a targeted form

As an admin, I want to choose a student or teacher audience and publish a form so that I can reach the relevant users.

Acceptance criteria:

- The selected audience is shown before publication.
- Publishing delivers an in-app inbox request with a form link to intended recipients.
- Only intended recipients can access and submit the open form.

#### US-ADM-02-03 — Close feedback collection

As an admin, I want to close a published form so that I can end collection when I have enough feedback.

Acceptance criteria:

- Closed forms reject further submissions, including direct requests.
- Previously collected responses remain available to authorised admins.

#### US-ADM-02-04 — Review collected responses

As an admin, I want to read responses to a form so that I can inspect the feedback users submitted.

Acceptance criteria:

- Responses are associated with the correct form and questions.
- Later form edits cannot silently change the meaning of existing answers.

### ADM-03 — AI feedback analysis

#### US-ADM-03-01 — Generate a feedback analysis

As an admin, I want to ask AI to analyse selected feedback responses so that I can identify recurring issues and possible improvements.

Acceptance criteria:

- The result includes a summary, grouped issues and suggestions clearly distinguished from reported feedback.
- Findings reference supporting responses in the selected authorised input.
- Empty input, request limits and failures produce clear messages.

#### US-ADM-03-02 — Review supporting feedback

As an admin, I want to open the responses supporting an AI finding so that I can verify the analysis before acting.

Acceptance criteria:

- Each supporting reference opens its corresponding authorised response.
- The analysis is reviewable and does not automatically send messages or change the app.

### ADM-04 — Feedback follow-up

#### US-ADM-04-01 — Send a feedback response

As an admin, I want to compose, review and send a response to a feedback submitter so that I can explain how their feedback is being addressed.

Acceptance criteria:

- I can review the message and intended recipient before sending.
- The sent message is saved in that recipient’s inbox as unread.
- Other respondents’ private feedback is not automatically included.

#### US-ADM-04-02 — Send a targeted announcement

As an admin, I want to review and send an announcement to a selected student or teacher audience so that I can communicate relevant improvements.

Acceptance criteria:

- The message and audience are shown before sending.
- The saved announcement appears as unread in intended recipients’ inboxes and is accessible only to them.

### ADM-05 — User and access management

#### US-ADM-05-01 — Manage account access

As an admin, I want to enable or disable an account’s access so that I can control who can use the app.

Acceptance criteria:

- I can inspect an account’s access status and explicitly change it.
- Disabling access prevents subsequent protected requests.

#### US-ADM-05-02 — Assign user roles

As an admin, I want to assign a supported role to a user so that I can give them the appropriate capabilities.

Acceptance criteria:

- Only an authorised admin can change roles; self-escalation by non-admins is rejected.
- Role changes affect subsequent protected requests.

#### US-ADM-05-03 — Manage course access

As an admin, I want to grant or revoke a user’s course access so that I can restrict course content to its intended users.

Acceptance criteria:

- I can inspect and change course access for the selected user.
- Revocation affects subsequent content and AI retrieval requests.

### ADM-06 — AI usage monitoring

#### US-ADM-06-01 — Inspect AI requests and failures

As an admin, I want to view requests and failures by AI feature and period so that I can understand capacity use and service problems.

Acceptance criteria:

- Counts reflect the selected feature and period, with rate-limit failures identifiable.
- The view does not expose credentials or private request contents.

#### US-ADM-06-02 — Inspect AI resource measurements

As an admin, I want to view available token and resource measurements so that I can plan use within SoC LLM limits.

Acceptance criteria:

- Available measurements identify their feature and reporting period.
- Unavailable measurements are labelled explicitly rather than presented as estimated facts.

## Nice-to-have stories — outside the MVP

### OPT-01 — Run code against test cases

#### US-OPT-01-01 — Run practice code

As a student, I want to run code against teacher-defined tests so that I can check its behaviour.

Acceptance criteria:

- Execution is isolated with enforced time and memory limits, without access to app secrets, other users’ data or unrestricted network resources.
- Results explain execution failures and limit breaches; security and abuse tests are required before release.
- Pre-submission output does not reveal protected solutions or circumvent the hints-only policy.

### OPT-02 — Student AI teaching preferences

#### US-OPT-02-01 — Choose explanation preferences

As a student, I want to choose preset explanation length, formatting and teaching style so that I can learn in a way I find useful.

Acceptance criteria:

- Presets include concise/detailed explanations, bullets/paragraphs and hints/worked examples; saved choices apply to subsequent help.
- Before submission, hints-only safeguards override worked-example preferences; examples cannot disclose the current question’s answer or equivalent solution.
- Preferences cannot override fixed rules, access permissions or privacy protections, and do not allow editing system prompts.

### OPT-03 — Teacher AI generation preferences

#### US-OPT-03-01 — Choose generation preferences

As a teacher, I want to choose preset audience level, tone and detail so that I can generate drafts suited to my students.

Acceptance criteria:

- Saved presets are applied to subsequent content-generation requests.
- Generated notes and questions still require teacher review and explicit publication.
- Preferences cannot override fixed rules, permissions or privacy protections, and do not allow editing system prompts.

Free-text teaching-style input is deferred beyond these presets. If introduced later, it must be treated as untrusted input, never inserted into the system prompt. Filtering contradictory instructions is not a substitute for server-side data and action controls.

## Shared acceptance criteria

The following apply across all relevant stories and map to SHR-01 through SHR-05 in the feature list:

- Unauthenticated requests are rejected, and server-side checks enforce role, course and record access for every protected operation.
- AI context contains only authorised records; instructions embedded in uploads, feedback, chat or preferences cannot override access controls or reveal secrets.
- The server verifies successful whole-set submission before releasing protected answers or solutions. Pre-submission context excludes answer keys and solution explanations. Tests cover direct access, pasted questions, prompt injection, repeated hints, answer confirmation and source/output leakage; prompts alone do not enforce the boundary.
- User input and generated output are validated and rendered safely; AI services do not receive credentials or unnecessary personal data.
- Requests have bounded input/output sizes and configured quotas. Rate limits and temporary failures are handled without uncontrolled retries.
- Interfaces follow a Google-inspired, distraction-free visual direction with consistent spacing and typography and clear navigation.
- Mobile and desktop layouts remain usable without obscured controls; forms have accessible labels and keyboard access.
- Loading feedback, contextual empty states and recoverable errors explain what is happening and what action to take; animations respect reduced-motion preferences.
- Private student progress and feedback remain visible only to authorised users. Raw feedback is restricted to admins unless a different sharing policy is explicitly agreed.

## Decisions to resolve before implementation

- Initial programming subject and learner level.
- Supported upload formats and file-size limits.
- How users join courses and how teacher accounts are approved.
- Repeat-attempt scoring, question reuse after answers have been seen, and the rule for identifying weak topics. The fixed policy is hints only until each whole-set attempt is successfully submitted.
- Whether feedback is identified or anonymous, together with retention and deletion rules.
- Exact SoC LLM quotas, model configuration and resource measurements available to the app.
