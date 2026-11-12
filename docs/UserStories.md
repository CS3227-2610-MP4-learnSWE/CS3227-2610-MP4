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
- The companion uses the page: on a lesson page it answers from that lesson, and on other pages it uses related published lessons it finds. Chat history is still local to the browser: it survives navigation and minimise but resets on page reload, login or demo role switching; account-session persistence is not implemented yet.

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

#### US-TEA-01-03 — Delete unused source material

As a teacher, I want to permanently delete an unused uploaded source so that I can remove unwanted files and recover upload capacity.

Acceptance criteria:

- Any teacher managing the course can delete the source after a confirmation naming it and explaining permanence.
- Deletion is blocked while any note draft or MCQ batch references it; unrelated work remains unchanged.
- Source metadata and original bytes are removed together; failures preserve the source and explain recovery.

### TEA-02 — AI content generation

#### US-TEA-02-01 — Generate draft notes

As a teacher, I want to generate study notes from selected source material so that I can reduce lesson preparation time.

Acceptance criteria:

- I can select an authorised source and receive editable draft notes.
- Generation does not publish content; failure preserves the source and existing drafts.

#### US-TEA-02-02 — Generate draft questions

As a teacher, I want to generate practice questions from selected source material so that I can prepare practice activities more quickly.

Acceptance criteria:

- Each generated batch contains exactly three MCQs, with four choices, exactly one correct choice and an explanation per question; no free-text answer questions.
- The complete batch is the unit of future practice-set publication; teachers do not assemble or mix individual questions.
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
- All three questions in a generated batch save atomically, preserving identity and attribution while recording the last editor.
- Concurrent changes cannot silently overwrite newer saved work; failures preserve local edits and conflicts offer loading the latest saved version.
- Unsaved changes require confirmation before cancellation or navigation.

#### US-TEA-03-04 — Publish reviewed content

As a teacher, I want to explicitly publish reviewed content so that I can make approved learning material available to students.

Acceptance criteria:

- Publication validates required content fields and requires my explicit action.
- A practice-set publication includes all three saved questions from one reviewed MCQ batch, with its title and course topic; no selection or mixing step. Published content is an immutable snapshot, separate from editable drafts.
- Authorised students can access published notes and practice questions while other drafts stay hidden.
- Publishing does not expose answer keys or solution explanations before successful whole-set submission.

#### US-TEA-03-05 — Delete unpublished note drafts

As a teacher, I want to permanently delete unwanted unpublished note drafts so that I can keep my course workspace organised.

Acceptance criteria:

- Any teacher managing the course can delete a draft after confirmation naming it and explaining permanence.
- A stale version cannot delete newer saved work; failures preserve unrelated work and provide recovery.
- Published content and future publication/practice references remain protected; deletion does not remove student history or unpublish content.

#### US-TEA-03-06 — Delete unpublished MCQ batches

As a teacher, I want to permanently delete an unwanted unpublished MCQ batch so that I can remove its generated questions together.

Acceptance criteria:

- Any teacher managing the course can confirm deletion of the whole batch, explicitly including all three questions; individual-question deletion is not supported.
- Batch and questions are removed atomically; stale versions cannot delete newer work and failures preserve unrelated records.
- Published content and future publication/practice references remain protected; deletion does not remove student history or unpublish content.

### TEA-04 — Publish three-question practice sets

#### US-TEA-04-01 — Publish a reviewed MCQ batch as a practice set

As a teacher, I want to publish a reviewed batch of three MCQs as one topic-based practice set so that students can practise the content I prepared.

Acceptance criteria:

- I provide a practice-set title and a topic in the course I manage, then explicitly publish through US-TEA-03-04.
- The set contains all three saved questions from exactly one batch, in their existing order, with four choices and one correct choice per question.
- There is no separate assembly screen, subset selection, mixing batches or adding/removing individual questions from a set.
- Publication creates a separate immutable snapshot; only authorised students can access it, and answers/explanations remain hidden until whole-set submission.

#### US-TEA-04-02 — Preserve published practice versions

As a teacher, I want published practice content and student attempt versions to remain stable so that corrections to drafts cannot alter students’ existing work.

Acceptance criteria:

- Questions, choices, keys and explanations can be corrected in the originating batch draft using US-TEA-03-03 before publication.
- Later draft edits never mutate a published snapshot or the versions referenced by student attempts.
- Published references protect the originating batch/questions from permanent draft deletion; deleting a draft must not remove student history.
- Unpublishing, published-content deletion and an additional practice-set editor are outside this scope.

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

*Superseded by ADM-07 once approved.*

#### US-ADM-01-01 — Inspect feature usage

As an admin, I want to view chatbot outcomes and student practice-set completion for a selected reporting period so that I can understand how these learning features are being used.

Acceptance criteria:

- **Chatbot outcome definition:** A chatbot request is successful only when the chatbot returns a valid response message; an error or missing response is non-successful.
- **Chatbot counts:** For the selected period, the report shows each student's and each teacher's successful and non-successful chatbot request counts, grouped by role, plus the totals for each outcome across both roles.
- **Practice-set completion definition:** A started practice attempt is complete only when the student successfully submits the whole set. For attempts started during the selected period, the completion percentage is attempts submitted by the end of that period divided by attempts started during that period.
- **No denominator:** If no practice attempts were started in the selected period, show that the completion percentage is not applicable rather than displaying a percentage.
- **Data states:** Show zero when data is available and the count is zero; label data unavailable when the report cannot obtain a reliable count.
- **Privacy and scope boundary:** Show chatbot counts associated with the relevant user account, but do not show chatbot messages or other private conversation content. This story reports feature outcomes, not AI service-call totals, failure categories, or resource measurements; those belong to ADM-06.

#### US-ADM-01-02 — Inspect generation reliability

As an admin, I want to compare the success rates of AI content-generation workflows for a selected reporting period so that I can identify workflows that may be unreliable.

Acceptance criteria:

- **Workflow selection:** The report identifies the content-generation workflow and reporting period for every rate shown.
- **Attempt definition:** Count a generation attempt when a valid request is accepted for generation. Requests rejected before generation begins, including rate-limited requests, are not generation attempts.
- **Success definition:** An attempt is successful only when it returns a complete output in the expected format; errors, timeouts, and incomplete or invalid outputs are unsuccessful.
- **Rate calculation:** For each workflow and period, calculate successful attempts divided by all generation attempts in that workflow and period.
- **No denominator:** If there were no generation attempts, show that no rate can be calculated rather than showing a percentage.
- **Scope boundary:** This story reports generation outcome percentages, not chatbot interaction outcomes (ADM-01-01) or AI service-call and failure counts (ADM-06-01).

#### US-ADM-01-03 — Assess AI response quality and session activity

As an admin, I want to review AI-assisted quality grades and session activity for student exercises and teacher lesson planning so that I can identify areas where AI assistance may need improvement.

Acceptance criteria:

- **Assessment scope:** I can select a reporting period and review results separately for student exercise assistance and teacher lesson-planning assistance. Each assessment covers an individual completed AI response to a request received in that period and identifies its workflow and reporting period.
- **Quality rubric:** AI grades each assessable response separately for relevance to the request, factual accuracy against available authorised context, clarity, and safety. Each dimension uses a 1–5 scale: 1 is unacceptable, 2 has major shortcomings, 3 is adequate with notable shortcomings, 4 is good with minor shortcomings, and 5 is excellent with no identified shortcomings.
- **Evidence and uncertainty:** Each grade includes a brief reason grounded in the response and available authorised context, without quoting private conversation content. If a dimension cannot be assessed from that material, it is marked unassessable rather than assigned a grade.
- **Human review:** The admin can review the grades and reasons. Grades are AI assessments, not verified facts, and do not automatically change access or application content.
- **Response time:** For each assessed request, show the elapsed time from receipt of the user's request to delivery of the final response. Identify failed or incomplete requests separately and do not present their elapsed time as a successful response time.
- **Session message count:** A session begins with the first message linked to an activity and ends when that activity ends or the user starts a new conversation, whichever occurs first. For sessions that begin in the selected period, show the average number of user and AI messages per session, counting each message separately and dividing the total messages by the number of sessions included. Show the number of sessions used.
- **Associated activity time:** For sessions linked to an exercise or lesson-planning activity, show the average session message count alongside the average elapsed time from the recorded start to the recorded end of each distinct associated activity. Show the number of linked sessions and distinct activities used, and identify the activity start and end events; elapsed time includes idle time unless it is measured separately.
- **Missing data:** Exclude sessions without a recorded link or activity start and end from the associated-activity comparison, and show how many were excluded. Label a metric unavailable when its measurements are missing or incomplete; if there are no eligible records, show that no average can be calculated.
- **Privacy and safeguards:** Evaluate only responses and the minimum context authorised for this purpose; exclude credentials, unnecessary personal data, and protected answer keys or solutions. Do not display private conversation content in the analytics report, and treat evaluated content as untrusted input.
- **Interpretation and scope:** Present timing and message counts as descriptive measurements, not as quality grades or evidence of time saved. Comparing against a no-AI baseline is outside this story.

### ADM-02 — Targeted feedback forms

*Superseded by ADM-08.*

#### US-ADM-02-01 — Draft a feedback form

As an admin, I want to create and save an unpublished feedback form using common survey question types so that I can prepare a focused survey before distributing it.

Acceptance criteria:

- **Supported question types:** I can add short-answer and paragraph text questions; multiple-choice and dropdown questions that accept one answer; checkbox questions that accept multiple answers; and linear-scale questions where a respondent selects one value within the scale's configured range.
- **Choice options:** For multiple-choice, dropdown, and checkbox questions, I can enter the answer options respondents can choose from.
- **Linear-scale setup:** For a linear-scale question, I can configure its range and optionally label its endpoints.
- **Required questions:** I can mark each question required or optional. Respondents cannot submit a form while a required question is unanswered.
- **Form association:** I can optionally associate the form with a feature or lesson.
- **Persistence:** When I save and reopen a draft, its questions, required-field settings, and optional association are unchanged.
- **Publication restriction:** A draft is unpublished and cannot be opened for response submission, including by direct request.
- **Scope boundary:** Drafting does not send inbox requests or make the form available to respondents; publication and recipient selection are covered by ADM-02-02.

#### US-ADM-02-02 — Publish a targeted form

As an admin, I want to select students or teachers as the audience for a form and publish it so that the intended users can provide feedback.

Acceptance criteria:

- **Audience review:** Before publication, I can review whether the form is being sent to the selected student or teacher audience.
- **Inbox delivery:** Publishing creates an in-app inbox request with a link to the form for each intended recipient.
- **Access restriction:** While the form is open, only intended recipients can view and submit it; other users are denied through both the interface and direct requests.
- **Submission eligibility:** A form can receive responses only after publication and before it is closed.
- **Scope boundary:** This story distributes the form request; it does not cover composing a separate follow-up message or announcement (ADM-04).

#### US-ADM-02-03 — Close feedback collection

As an admin, I want to close a published form so that users can no longer submit feedback when collection has ended.

Acceptance criteria:

- **State change:** I can close a published form to end response collection.
- **Submission restriction:** After closure, the form rejects new responses through both the interface and direct requests, including requests from intended recipients.
- **Existing data:** Closing the form preserves responses already submitted; authorised admins can still review them.
- **Scope boundary:** Closing does not delete the form or its responses. Reopening a closed form is outside this story.

#### US-ADM-02-04 — Review collected responses

As an admin, I want to review the responses to a feedback form so that I can understand what respondents submitted.

Acceptance criteria:

- **Response association:** Each submitted response is shown with its form and the questions it answers.
- **Question snapshot:** The wording and required status of each question at the time of submission remain available with the response; later form edits do not alter that record.
- **Access restriction:** Only an authorised admin can review collected responses.
- **Scope boundary:** This story provides direct review of form responses. It does not generate AI summaries or select evidence for an analysis (ADM-03).

### ADM-03 — AI feedback analysis

*Superseded by ADM-08.*

#### US-ADM-03-01 — Generate a feedback analysis

As an admin, I want AI to analyse feedback responses that I select and am authorised to review so that I can identify recurring issues and possible improvements.

Acceptance criteria:

- **Input selection:** I can select responses for analysis, and the analysis uses only selected responses that I am authorised to review.
- **Result sections:** The result contains a summary, recurring issues grouped by theme, and suggested improvements.
- **Fact versus suggestion:** The result distinguishes issues reported in the selected feedback from AI-generated suggestions.
- **Evidence references:** Each grouped issue includes references to supporting responses in the selected input. A suggestion presented as based on specific feedback also references its supporting responses; a suggestion without such evidence is identified as an AI suggestion, not a reported finding.
- **Empty input:** If no responses are selected, the system does not generate an analysis and tells me that a selection is required.
- **Failure states:** If a request limit is reached or analysis fails, the system tells me which occurred and does not present a partial or failed result as complete.
- **Scope boundary:** Analysis is advisory only; it does not edit forms or responses, send messages, or apply suggested changes.

#### US-ADM-03-02 — Review supporting feedback

As an admin, I want to open the feedback responses cited by an AI finding so that I can check the evidence before deciding what to do.

Acceptance criteria:

- **Reference target:** Selecting a supporting-response reference opens the exact response cited by that finding.
- **Access restriction:** The response is displayed only if I remain authorised to access it; an invalid, deleted, or inaccessible reference does not reveal response content.
- **Scope boundary:** This story opens only responses cited by an analysis. Browsing all responses for a form is covered by ADM-02-04.
- **No side effects:** Opening a finding or response does not send a message or modify the analysis, form, or response.

### ADM-04 — Feedback follow-up

*Superseded by ADM-08.*

#### US-ADM-04-01 — Send a feedback response

As an admin, I want to compose, review, and send a message to an individual feedback submitter so that I can explain how their feedback is being addressed.

Acceptance criteria:

- **Recipient scope:** I can address a response to the individual who submitted the selected feedback; the recipient is shown before sending.
- **Message review:** I can review the message content before confirming the send action.
- **Delivery:** After sending, the message appears as unread in that recipient’s in-app inbox.
- **Privacy restriction:** The message does not include or expose other respondents’ private responses.
- **Scope boundary:** This is a one-to-one follow-up, not a group announcement; group announcements are covered by ADM-04-02. Email and push delivery are outside the MVP.

#### US-ADM-04-02 — Send a targeted announcement

As an admin, I want to review and send an announcement to a selected student or teacher audience so that I can share relevant improvements with those users.

Acceptance criteria:

- **Audience review:** Before sending, I can review whether the selected audience is students or teachers.
- **Message review:** I can review the announcement content before confirming the send action.
- **Delivery:** The announcement appears as unread in the in-app inbox of each intended recipient.
- **Access restriction:** Only intended recipients can access the announcement, including through direct requests.
- **Scope boundary:** An announcement is a shared message to an audience, not a response to an individual submission (ADM-04-01). Email and push delivery are outside the MVP.

### ADM-05 — User and access management

#### US-ADM-05-01 — Manage account access

As an admin, I want to enable or disable an account’s access so that I can control who can use the app.

**Scope boundary:** Account status changes do not change the fixed role, course assignments or stored learning/authorship records. Permanent archiving is covered by US-ADM-05-04.

Acceptance criteria:

- **Status management:** I can inspect an account’s access status and explicitly change it.
- **Disable and re-enable:** Disabling access prevents subsequent protected requests and ends all sessions; re-enabling requires a fresh login.
- **Retained records and assignments:** Disabling preserves learning records and course assignments; admins can edit assignments while the account remains disabled.
- **Administrator protection:** Admins cannot disable themselves, and concurrent actions cannot remove the last enabled admin.

#### US-ADM-05-02 — Create fixed-role accounts

As an admin, I want to create student, teacher and admin accounts so that users receive the appropriate capabilities without changing an existing account’s role.

**Scope boundary:** Accounts have one fixed type; there is no role-change, promotion or demotion workflow. Public signup remains available for students only. Admin-set initial passwords have no mandatory first-login password-change flow.

Acceptance criteria:

- **Authorised account creation:** Only an authorised admin can create accounts with a selected supported role; public signup remains student-only.
- **Fixed roles:** Each account has exactly one immutable role; promotion, demotion and self-escalation are rejected.
- **Initial password:** The admin enters and confirms an initial password; existing shared password rules apply, passwords are stored only as hashes and never returned in account details.
- **Password-change scope:** Mandatory first-login password changes are deferred; guides include a validated test-only example password, never a default credential.

#### US-ADM-05-03 — Manage course access

As an admin, I want to grant or revoke a user?s course access so that I can restrict course content to its intended users.

**Scope boundary:** Course access does not change account status or role. Admins manually manage student enrolments and teacher assignments, including while the account is disabled; admin accounts do not receive course assignments.

Acceptance criteria:

- **Access display and changes:** I can inspect and change course access for the selected user: student enrolments and teacher management assignments are distinct.
- **Revocation enforcement:** Revocation affects subsequent content and AI retrieval requests; access is checked again before releasing AI results, while other already-authorised requests may finish.
- **Repeated and concurrent changes:** Repeated grants and revocations succeed harmlessly; concurrent opposite actions follow server processing order.
- **Retained history:** Revocation preserves learning and authorship records; granting access again restores visibility of retained records within existing feature rules.

#### US-ADM-05-04 — Archive accounts permanently

As an admin, I want to permanently archive an account so that it cannot access the app again without deleting linked history.

**Scope boundary:** Archiving is permanent access removal with retained history, not hard deletion or anonymisation. It cannot be reversed and does not make the archived email reusable.

Acceptance criteria:

- **Permanent archive:** Archiving ends all sessions, blocks login permanently and removes all course permissions, while retaining linked learning and authorship records.
- **Email reservation:** Archived accounts cannot be restored and their emails remain reserved for both public signup and admin creation.
- **Administrator protection:** Admins cannot archive themselves, and concurrent actions cannot remove the last enabled admin.

#### US-ADM-05-05 — Create courses

As an admin, I want to create a course with a title and assign teachers so that teachers can manage its content and students can be enrolled.

**Scope boundary:** ADM-05 creates courses and assigns teachers. Teachers upload, generate, review and publish content under the existing TEA stories; viewing authorised learning results belongs to TEA-05 and is not newly implemented by ADM-05. Course editing and deletion are outside this change.

Acceptance criteria:

- **Course creation:** I can create a course with a validated title and explicitly assign teachers using course-access management; each new course atomically receives a default General topic so assigned teachers can publish content through the existing workflow.
- **Teacher assignments:** Teacher accounts begin without course assignments; teachers manage content and authorised learning results only in their assigned courses.

#### US-ADM-05-06 — Find accounts and confirm access removal

As an admin, I want to find accounts and review destructive access changes so that I can manage the correct person safely.

**Scope boundary:** This story provides account discovery and confirmation of access-removing actions; it does not introduce bulk operations or audit analytics.

Acceptance criteria:

- **Account discovery:** I can search accounts by name or email, filter by role and status, and browse paginated results including archived accounts through a status filter.
- **Confirmations:** Disabling, archiving and removing course access require confirmation; creation and grants use explicit form buttons.


### ADM-06 — AI usage monitoring

*Superseded by ADM-07 once approved.*

#### US-ADM-06-01 — Inspect AI requests and failures

As an admin, I want to view AI request and failure counts by feature and reporting period so that I can understand service usage and problems.

Acceptance criteria:

- **Request unit:** Count each AI service-call attempt as one request, including a retry as a separate attempt.
- **Breakdown:** For the selected feature and reporting period, show the total request count and failure count.
- **Failure category:** Identify rate-limit failures separately from other failures.
- **Zero activity and unavailable data:** If the data is available and no requests occurred in the selected period, show zero requests and failures. If the data source is unavailable or incomplete, label the affected counts unavailable rather than showing zero.
- **Privacy restriction:** Do not display credentials, private prompts, or private response content.
- **Scope boundary:** This story reports operational counts and failure categories, not generation success percentages (ADM-01-02) or resource measurements (ADM-06-02).

#### US-ADM-06-02 — Inspect AI resource measurements

As an admin, I want to view available token and other resource measurements for AI use so that I can plan within SoC LLM limits.

Acceptance criteria:

- **Measurement context:** Each available token or other resource measurement identifies the AI feature and reporting period it describes.
- **Unavailable values:** If a measurement is unavailable, label it unavailable; do not show an estimate as if it were an observed value.
- **Scope boundary:** Show recorded measurements only. Forecasts, inferred measurements, and private request content are outside this story.

### ADM-07 — Analytics hub

Merges and supersedes ADM-01 and ADM-06 once approved: one admin page, "Feature Analytics", with Health, Feature outcomes, AI usage and Quality sections. Real recorded data only; a metric without a data source is labelled unavailable. Chat message content is never shown.

#### US-ADM-07-01 — Monitor feature health

As an admin, I want a health summary at the top of the analytics page so that I can see at a glance whether the chatbot and content generation are failing.

Acceptance criteria:

- **Health tiles:** The first content shows tiles for chatbot failure rate, generation failure rate, rate-limited requests, chatbot response time (median and 95th percentile), content-generation response time (median and 95th percentile) and practice-set completion for the selected reporting period.
- **Failure-rate status:** A failure rate above 5% is marked critical, 2% to 5% warning, and below 2% healthy. With fewer than 20 requests the tile shows "low sample" and no status colour. Status is always shown with an icon and words, never by colour alone.
- **Definitions:** Failure rates and practice-set completion follow the definitions in US-ADM-07-04 and US-ADM-07-05. Response times are shown separately for the chatbot and for content generation. Each tile has a compact All / Successful / Failed selector (default All); failed includes timed-out requests; a set with no requests says "No requests", never zero. Requests still in progress are excluded and shown as "N in progress"; a request with no outcome after 2 minutes counts as a failure with category timeout.
- **Data states:** A tile whose data source does not exist or is incomplete says it is unavailable and why; it never shows zero or an estimate.

#### US-ADM-07-02 — Review hourly request patterns

As an admin, I want hourly charts of requests and failures so that I can find when problems and peak load occur.

Acceptance criteria:

- **Charts:** The page shows side by side a requests-per-hour chart (successful and failed), a failure-rate-per-hour chart with a 5% reference line, and a peak-hours heatmap by weekday and hour. Hovering shows the count and failure percentage.
- **Time zone:** Hourly buckets are stored in UTC and displayed in the browser's local time.
- **Expanded view:** Each chart opens in a larger overlay with a data table, a CSV download, a focus trap, Esc to close and accessible names. The same information is available as text, not only in hover or colour.
- **Retention and data states:** Hourly data is kept 30 days; a period it cannot cover is labelled unavailable.

#### US-ADM-07-03 — Review daily usage and learning activity

As an admin, I want daily activity figures so that I can see adoption and how students use practice sets.

Acceptance criteria:

- **Logins:** Show logins per day and unique active users per day, separately for students and teachers, with a total. Admin sign-ins are not counted.
- **Practice drafts started:** Show, per day, the practice sets whose first draft was saved by a teacher that day. A set is counted once, whatever happens to it later.
- **Practice sets published:** Show, per day, the practice sets first published that day. A set is counted once, on its first publication; unpublishing and republishing do not change the count. Drafts started and published are separate series with separate names.
- **Attempt funnel:** Show practice attempts started versus submitted per day.
- **Attempts per student:** Show, per day, the median number of attempts started per student and the distribution.
- **Privacy and data states:** Events hold no message content. A metric that is not yet collected is labelled unavailable, never zero.

#### US-ADM-07-04 — Inspect chatbot outcomes and practice completion

As an admin, I want to view chatbot outcomes and student practice-set completion for a selected reporting period so that I can understand how these learning features are being used.

Acceptance criteria:

- **Chatbot outcome definition:** A chatbot request is successful only when the chatbot returns a valid response message; an error or missing response is non-successful.
- **Chatbot counts:** For the selected period, the report shows each student's and each teacher's successful and non-successful chatbot request counts, grouped by role, plus the totals for each outcome across both roles. The per-user table is sortable and paginated and by default lists the ten users with the most non-successful requests.
- **Practice-set completion definition:** A started practice attempt is complete only when the student successfully submits the whole set. For attempts started during the selected period, the completion percentage is attempts submitted by the end of that period divided by attempts started during that period.
- **No denominator:** If no practice attempts were started in the selected period, show that the completion percentage is not applicable rather than displaying a percentage.
- **Data states:** Show zero when data is available and the count is zero; label data unavailable when the report cannot obtain a reliable count.
- **Privacy:** Show chatbot counts associated with the relevant user account, but do not show chatbot messages or other private conversation content.

#### US-ADM-07-05 — Inspect generation reliability

As an admin, I want to compare the success rates of AI content-generation workflows for a selected reporting period so that I can identify workflows that may be unreliable.

Acceptance criteria:

- **Workflow selection:** The report identifies the content-generation workflow and reporting period for every rate shown.
- **Request definition (changed from US-ADM-01-02):** Count a generation request when a valid request is accepted for generation, and also when a valid request is refused by the rate limiter; a rate-limited request counts as unsuccessful. Requests rejected earlier (for example for invalid input or missing access) are not counted.
- **Success definition:** A request is successful only when it returns a complete output in the expected format; errors, timeouts, rate-limited requests, and incomplete or invalid outputs are unsuccessful.
- **Rate calculation:** For each workflow and period, calculate successful requests divided by all generation requests in that workflow and period.
- **No denominator:** If there were no generation requests, show that no rate can be calculated rather than showing a percentage.

#### US-ADM-07-06 — Inspect AI requests, failures and resource measurements

As an admin, I want to view AI request and failure counts and available token measurements by feature and reporting period so that I can understand service usage and plan within SoC LLM limits.

Acceptance criteria:

- **Request unit:** Count each AI service-call attempt as one request, including a retry as a separate attempt.
- **Breakdown:** For the selected feature and reporting period, show the total request count and failure count.
- **Failure category:** Identify rate-limit failures separately from other failures.
- **Zero activity and unavailable data:** If the data is available and no requests occurred in the selected period, show zero requests and failures. If the data source is unavailable or incomplete, label the affected counts unavailable rather than showing zero.
- **Privacy restriction:** Do not display credentials, private prompts, or private response content.
- **Measurement context:** Each available token or other resource measurement identifies the AI feature and reporting period it describes.
- **Unavailable values:** If a measurement is unavailable, label it unavailable; do not show an estimate as if it were an observed value.
- **Scope boundary:** Show recorded measurements only. Forecasts, inferred measurements, and private request content are outside this story.

#### US-ADM-07-07 — Assess AI response quality and session activity

As an admin, I want to review AI-assisted quality grades and session activity for student exercises and teacher lesson planning so that I can identify areas where AI assistance may need improvement.

Acceptance criteria:

- **Assessment scope:** I can select a reporting period and review results separately for student exercise assistance and teacher lesson-planning assistance. Each assessment covers an individual completed AI response to a request received in that period and identifies its workflow and reporting period.
- **Quality rubric:** AI grades each assessable response separately for relevance to the request, factual accuracy against available authorised context, clarity, and safety. Each dimension uses a 1–5 scale: 1 is unacceptable, 2 has major shortcomings, 3 is adequate with notable shortcomings, 4 is good with minor shortcomings, and 5 is excellent with no identified shortcomings.
- **Evidence and uncertainty:** Each grade includes a brief reason grounded in the response and available authorised context, without quoting private conversation content. If a dimension cannot be assessed from that material, it is marked unassessable rather than assigned a grade.
- **Human review:** The admin can review the grades and reasons. Grades are AI assessments, not verified facts, and do not automatically change access or application content.
- **Response time:** For each assessed request, show the elapsed time from receipt of the user's request to delivery of the final response. Identify failed or incomplete requests separately and do not present their elapsed time as a successful response time.
- **Session message count:** A session begins with the first message linked to an activity and ends when that activity ends or the user starts a new conversation, whichever occurs first. For sessions that begin in the selected period, show the average number of user and AI messages per session, counting each message separately and dividing the total messages by the number of sessions included. Show the number of sessions used.
- **Associated activity time:** For sessions linked to an exercise or lesson-planning activity, show the average session message count alongside the average elapsed time from the recorded start to the recorded end of each distinct associated activity. Show the number of linked sessions and distinct activities used, and identify the activity start and end events; elapsed time includes idle time unless it is measured separately.
- **Missing data:** Exclude sessions without a recorded link or activity start and end from the associated-activity comparison, and show how many were excluded. Label a metric unavailable when its measurements are missing or incomplete; if there are no eligible records, show that no average can be calculated.
- **Privacy and safeguards:** Evaluate only responses and the minimum context authorised for this purpose; exclude credentials, unnecessary personal data, and protected answer keys or solutions. Do not display private conversation content in the analytics report, and treat evaluated content as untrusted input.
- **Interpretation and scope:** Present timing and message counts as descriptive measurements, not as quality grades or evidence of time saved. Comparing against a no-AI baseline is outside this story.

#### US-ADM-07-08 — Choose a reporting period and refresh

As an admin, I want one compact period selector and a refresh control so that every section describes the same period and I know how current it is.

Acceptance criteria:

- **Layout:** The title "Feature Analytics" is on the left; a compact reporting-period selector, the last-updated time and a refresh button are at the top right. The page is clean and minimal, with lower-urgency sections further down.
- **Period:** The admin can choose a preset or a custom range of UTC dates (at most 366 days). Every section names or follows the selected period.
- **Partial data:** If a metric has only been recorded since a date inside the period, the section shows the data from that date with the note "Data starts on {date}" instead of marking the whole metric unavailable; a metric with no data in the period at all is unavailable.
- **Failure isolation:** A section that fails to load shows its own message and retry; the other sections remain usable.
- **Safeguards:** Only admins can see the page; shared accessibility, loading, empty-state and error criteria apply.


### ADM-08 — Feedback hub

Merged and superseded ADM-02, ADM-03 and ADM-04: one admin area, "Feedback hub", with tabs Forms, Responses, Analysis and Follow-up. The screens and rules of those features are unchanged; the hub changes where they live and how they link. Real data only. Student and teacher survey forms and inboxes are unchanged.

#### US-ADM-08-01 — Find all feedback tools in one place

As an admin, I want one Feedback hub with tabs for forms, responses, analysis and follow-up so that I can run the whole feedback loop from one place.

Acceptance criteria:

- **Hub and tabs:** One admin page, "Feedback hub", has four tabs: Forms, Responses, Analysis and Follow-up. The selected tab and screen are shown in the address, so any screen can be bookmarked, refreshed and reopened.
- **Same behaviour:** Every task in the tabs behaves as in US-ADM-08-02 to US-ADM-08-08 (copied from the earlier stories); the hub changes where things are, not what they do.
- **Navigation:** Links between screens stay inside the hub; Back and Forward move between screens; leaving a form with unsaved changes asks first.
- **Tab counts:** Each tab shows a small count (open forms on Forms, submitted responses on Responses, saved analyses on Analysis, feedback responses still without a reply on Follow-up) that is also announced to screen readers; a count that cannot be loaded is simply not shown and never blocks a tab. Counts load when the hub opens and are refreshed after my own changes that affect them (for example publishing a form, deleting a response or sending a reply), not when I switch tabs; changes made by other people appear the next time I open the hub.
- **Shortcut to analysis:** From a form's submitted responses, the admin can choose "Analyse this form" to open the Analysis tab with that form already selected; nothing is generated until the admin chooses to.
- **Failure isolation:** A screen that fails to load shows its own message and retry; the tab bar and the other tabs stay usable.
- **Safeguards:** Only admins can see the hub and use its data; shared accessibility, loading, empty-state and error criteria apply.

#### US-ADM-08-02 — Draft a feedback form

As an admin, I want to create and save an unpublished feedback form using common survey question types so that I can prepare a focused survey before distributing it.

Acceptance criteria (copied from US-ADM-02-01):

- **Supported question types:** I can add short-answer and paragraph text questions; multiple-choice and dropdown questions that accept one answer; checkbox questions that accept multiple answers; and linear-scale questions where a respondent selects one value within the scale's configured range.
- **Choice options:** For multiple-choice, dropdown, and checkbox questions, I can enter the answer options respondents can choose from.
- **Linear-scale setup:** For a linear-scale question, I can configure its range and optionally label its endpoints.
- **Required questions:** I can mark each question required or optional. Respondents cannot submit a form while a required question is unanswered.
- **Form association:** I can optionally associate the form with a feature or lesson.
- **Persistence:** When I save and reopen a draft, its questions, required-field settings, and optional association are unchanged.
- **Publication restriction:** A draft is unpublished and cannot be opened for response submission, including by direct request.
- **Scope boundary:** Drafting does not send inbox requests or make the form available to respondents; publication and recipient selection are covered by US-ADM-08-03.

#### US-ADM-08-03 — Publish a targeted form and close collection

As an admin, I want to select students or teachers as the audience for a form and publish it so that the intended users can provide feedback, and to close it when collection has ended.

Acceptance criteria (copied from US-ADM-02-02 and US-ADM-02-03):

- **Audience review:** Before publication, I can review whether the form is being sent to the selected student or teacher audience.
- **Inbox delivery:** Publishing creates an in-app inbox request with a link to the form for each intended recipient.
- **Access restriction:** While the form is open, only intended recipients can view and submit it; other users are denied through both the interface and direct requests.
- **Submission eligibility:** A form can receive responses only after publication and before it is closed.
- **Scope boundary:** This story distributes the form request; it does not cover composing a separate follow-up message or announcement (US-ADM-08-07 and US-ADM-08-08).
- **State change:** I can close a published form to end response collection.
- **Submission restriction:** After closure, the form rejects new responses through both the interface and direct requests, including requests from intended recipients.
- **Existing data:** Closing the form preserves responses already submitted; authorised admins can still review them.
- **Scope boundary:** Closing does not delete the form or its responses. Reopening a closed form is outside this story.

#### US-ADM-08-04 — Review collected responses

As an admin, I want to review the responses to a feedback form so that I can understand what respondents submitted.

Acceptance criteria (copied from US-ADM-02-04, plus the response delete approved with ADM-03 on 2026-11-09):

- **Response association:** Each submitted response is shown with its form and the questions it answers.
- **Question snapshot:** The wording and required status of each question at the time of submission remain available with the response; later form edits do not alter that record.
- **Access restriction:** Only an authorised admin can review collected responses.
- **Scope boundary:** This story provides direct review of form responses. It does not generate AI summaries or select evidence for an analysis (US-ADM-08-05).
- **Delete a response (carried from the approved ADM-03 amendment):** An admin can permanently delete a submitted response after confirming. Nothing else is changed except that the respondent may submit again while the form is open; stored analyses stay readable and links to the deleted response show that it is no longer available.

#### US-ADM-08-05 — Generate a feedback analysis

As an admin, I want AI to analyse feedback responses that I select and am authorised to review so that I can identify recurring issues and possible improvements.

Acceptance criteria (copied from US-ADM-03-01):

- **Input selection:** I can select responses for analysis, and the analysis uses only selected responses that I am authorised to review.
- **Result sections:** The result contains a summary, recurring issues grouped by theme, and suggested improvements.
- **Fact versus suggestion:** The result distinguishes issues reported in the selected feedback from AI-generated suggestions.
- **Evidence references:** Each grouped issue includes references to supporting responses in the selected input. A suggestion presented as based on specific feedback also references its supporting responses; a suggestion without such evidence is identified as an AI suggestion, not a reported finding.
- **Empty input:** If no responses are selected, the system does not generate an analysis and tells me that a selection is required.
- **Failure states:** If a request limit is reached or analysis fails, the system tells me which occurred and does not present a partial or failed result as complete.
- **Scope boundary:** Analysis is advisory only; it does not edit forms or responses, send messages, or apply suggested changes.
- **Statistics and history (carried from the approved ADM-03 spec):** Statistics are shown at once and independently of the AI step; I can see my previous analyses and permanently delete my own.

#### US-ADM-08-06 — Review supporting feedback

As an admin, I want to open the feedback responses cited by an AI finding so that I can check the evidence before deciding what to do.

Acceptance criteria (copied from US-ADM-03-02):

- **Reference target:** Selecting a supporting-response reference opens the exact response cited by that finding.
- **Access restriction:** The response is displayed only if I remain authorised to access it; an invalid, deleted, or inaccessible reference does not reveal response content.
- **Scope boundary:** This story opens only responses cited by an analysis. Browsing all responses for a form is covered by US-ADM-08-04.
- **No side effects:** Opening a finding or response does not send a message or modify the analysis, form, or response.

#### US-ADM-08-07 — Send a feedback response

As an admin, I want to compose, review, and send a message to an individual feedback submitter so that I can explain how their feedback is being addressed.

Acceptance criteria (copied from US-ADM-04-01):

- **Recipient scope:** I can address a response to the individual who submitted the selected feedback; the recipient is shown before sending.
- **Message review:** I can review the message content before confirming the send action.
- **Delivery:** After sending, the message appears as unread in that recipient’s in-app inbox.
- **Privacy restriction:** The message does not include or expose other respondents’ private responses.
- **Scope boundary:** This is a one-to-one follow-up, not a group announcement; group announcements are covered by US-ADM-08-08. Email and push delivery are outside the MVP.

#### US-ADM-08-08 — Send a targeted announcement

As an admin, I want to review and send an announcement to a selected student or teacher audience so that I can share relevant improvements with those users.

Acceptance criteria (copied from US-ADM-04-02):

- **Audience review:** Before sending, I can review whether the selected audience is students or teachers.
- **Message review:** I can review the announcement content before confirming the send action.
- **Delivery:** The announcement appears as unread in the in-app inbox of each intended recipient.
- **Access restriction:** Only intended recipients can access the announcement, including through direct requests.
- **Scope boundary:** An announcement is a shared message to an audience, not a response to an individual submission (US-ADM-08-07). Email and push delivery are outside the MVP.


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
- ADM-05 resolves course joining and teacher approval: admins create teacher accounts and courses, assign teachers and manually enrol students; account roles are fixed.
- Repeat-attempt scoring, question reuse after answers have been seen, and the rule for identifying weak topics. The fixed policy is hints only until each whole-set attempt is successfully submitted.
- Whether feedback is identified or anonymous, together with retention and deletion rules.
- Exact SoC LLM quotas, model configuration and resource measurements available to the app.
