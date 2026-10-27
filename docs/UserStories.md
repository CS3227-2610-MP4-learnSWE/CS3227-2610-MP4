# learnSWE User Stories

These proposed stories describe user goals within the capabilities in [FeatureList.md](FeatureList.md). Features group related stories; they are not implementation tasks. Each story should deliver a demonstrable outcome, with acceptance criteria defining completion. None is marked implemented.

Story IDs use `US-<feature ID>-<story number>` to preserve traceability. These replace the original broad one-story-per-feature draft. Stories may depend on shared capabilities or earlier stories; they need not be implemented in isolation.

## Student

### STU-01 — Study materials

#### US-STU-01-01 — Read published lessons

As a student, I want to browse lessons by course and topic and open a lesson so that I can find the material I need.

Acceptance criteria:

- Only published lessons in courses I can access are listed and readable.
- Drafts and unauthorised lessons remain inaccessible through direct requests.

#### US-STU-01-02 — Record lesson completion

As a student, I want to mark a lesson as completed so that I can keep track of what I have studied.

Acceptance criteria:

- The selected lesson is recorded as completed for my account.
- Completion persists after signing in again and appears in my progress view.

### STU-02 — Practice questions

#### US-STU-02-01 — Submit a practice attempt

As a student, I want to answer and submit a published practice set so that I can check my understanding.

Acceptance criteria:

- I can answer multiple-choice and short code-reading questions.
- Submission saves my answers and score against the question and answer-key version used.
- Submission does not execute student code.

#### US-STU-02-02 — Review a practice attempt

As a student, I want to review a saved attempt so that I can understand my mistakes.

Acceptance criteria:

- I can see my submitted answers, score, correct answers and teacher-approved explanations.
- I cannot retrieve another student’s private attempts.

### STU-03 — AI learning assistant

#### US-STU-03-01 — Ask for a course explanation

As a student, I want to ask AI to explain course material so that I can understand a concept I find difficult.

Acceptance criteria:

- Answers use published material I am authorised to access and reference the supporting sources.
- When material does not support an answer, the assistant states the limitation instead of inventing a source.
- A service failure or rate limit leaves my typed question available to retry.

#### US-STU-03-02 — Request a learning hint

As a student, I want to request a hint for a practice question so that I can make progress before seeing the solution.

Acceptance criteria:

- The initial response gives guidance without revealing the full answer.
- I can explicitly request a full explanation afterwards.

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

### STU-06 — View responses

#### US-STU-06-01 — Read student follow-up

As a student, I want to read admin messages and relevant announcements so that I can know how feedback is being addressed.

Acceptance criteria:

- I can read messages addressed to me or an audience I belong to, with sender and sent time.
- Messages intended for other users or groups remain inaccessible.

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

- Generated drafts include questions, suggested answers and explanations.
- Unusable output is identified clearly and failed requests preserve existing work.
- Generated questions remain unpublished until reviewed and explicitly published.

### TEA-03 — Review and publish

#### US-TEA-03-01 — Preview generated content

As a teacher, I want to preview draft content so that I can check its accuracy before editing or publishing.

Acceptance criteria:

- I can inspect notes, questions, answers and explanations for my managed courses.
- Previewing does not make drafts visible to students.

#### US-TEA-03-02 — Edit draft notes

As a teacher, I want to edit and save draft notes so that I can correct errors before students read them.

Acceptance criteria:

- Saved edits persist when I reopen the draft.
- Edits to an unpublished draft do not change the published version.

#### US-TEA-03-03 — Correct draft questions

As a teacher, I want to edit draft questions, answer keys and explanations so that I can provide accurate practice content.

Acceptance criteria:

- I can save corrections to each question and its associated answer and explanation.
- Required fields are validated and corrections persist when reopened.

#### US-TEA-03-04 — Publish reviewed content

As a teacher, I want to explicitly publish reviewed content so that I can make approved learning material available to students.

Acceptance criteria:

- Publication validates required content fields and requires my explicit action.
- Authorised students can access the published version while other drafts stay hidden.

### TEA-04 — Manage practice sets

#### US-TEA-04-01 — Assemble a practice set

As a teacher, I want to select questions for a topic-based practice set so that I can give students focused practice.

Acceptance criteria:

- I can save a set with selected questions and a topic in a course I manage.
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

### TEA-06 — Feedback participation

#### US-TEA-06-01 — Submit teacher feedback

As a teacher, I want to complete a feedback form intended for me so that I can help improve teaching workflows.

Acceptance criteria:

- Open forms targeted to me or my teacher group are available.
- Required fields are validated, successful submission is confirmed and other teachers cannot access my private submission.

#### US-TEA-06-02 — Read teacher follow-up

As a teacher, I want to read admin follow-up messages so that I can understand what action is being taken.

Acceptance criteria:

- Messages addressed to me or my group display sender, sent time and content.
- Other users’ private messages remain inaccessible.

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
- The sent message is saved and visible to that recipient in the app.
- Other respondents’ private feedback is not automatically included.

#### US-ADM-04-02 — Send a targeted announcement

As an admin, I want to review and send an announcement to a selected student or teacher audience so that I can communicate relevant improvements.

Acceptance criteria:

- The message and audience are shown before sending.
- The saved announcement is accessible only to intended recipients.

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

## Shared acceptance criteria

The following apply across all relevant stories and map to SHR-01 through SHR-05 in the feature list:

- Unauthenticated requests are rejected, and server-side checks enforce role, course and record access for every protected operation.
- AI context contains only authorised records; instructions embedded in uploads, feedback or chat cannot override access controls or reveal secrets.
- User input and generated output are validated and rendered safely; AI services do not receive credentials or unnecessary personal data.
- Requests have bounded input/output sizes and configured quotas. Rate limits and temporary failures are handled without uncontrolled retries.
- Interfaces provide accessible labels and understandable loading, empty, success and error states.
- Private student progress and feedback remain visible only to authorised users. Raw feedback is restricted to admins unless a different sharing policy is explicitly agreed.

## Decisions to resolve before implementation

- Initial programming subject and learner level.
- Supported upload formats and file-size limits.
- How users join courses and how teacher accounts are approved.
- Short-answer matching rules, repeat-attempt scoring and the rule for identifying weak topics.
- Whether feedback is identified or anonymous, together with retention and deletion rules.
- Exact SoC LLM quotas, model configuration and resource measurements available to the app.
