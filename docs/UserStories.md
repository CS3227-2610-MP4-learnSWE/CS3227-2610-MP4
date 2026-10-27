# learnSWE User Stories

These proposed user stories map to [FeatureList.md](FeatureList.md). Acceptance criteria define intended behaviour for implementation and testing; they do not indicate that a feature is complete.

## Student

### US-STU-01 — Read study materials

As a student, I want to browse and read published lessons by course and topic so that I can learn in an organised way.

Acceptance criteria:
- I can browse and open published lessons in courses I can access.
- I can mark a lesson completed, and the status persists after signing in again.
- Draft lessons and content from courses I cannot access are unavailable, including through direct requests.

### US-STU-02 — Practise and review answers

As a student, I want to attempt practice questions and review results so that I can identify gaps in my understanding.

Acceptance criteria:
- I can answer multiple-choice and short code-reading questions in a published practice set.
- After submitting, I can see my score, correct answers and teacher-approved explanations.
- My attempt is saved for progress reporting; submission does not require executing my code.

### US-STU-03 — Get AI learning help

As a student, I want an AI assistant to explain course material and give hints so that I can work through difficulties.

Acceptance criteria:
- I can ask a question and receive an explanation grounded in published material I am authorised to access, with source references.
- I can request a hint before asking for a full answer.
- When the available material does not support an answer, the assistant states that limitation instead of inventing a source.
- Rate limits and service failures produce a clear message without losing my typed question.

### US-STU-04 — Track learning progress

As a student, I want to see my lesson completion and practice performance so that I can decide what to revise next.

Acceptance criteria:
- I can view my completed lessons and saved practice scores.
- Topics needing practice are derived from my recorded results using a documented rule.
- If I have no attempts, the dashboard explains that more activity is needed; I cannot view another student's private dashboard.

### US-STU-05 — Submit targeted feedback

As a student, I want to answer relevant feedback forms so that I can report problems and suggest improvements.

Acceptance criteria:
- I can view and complete open forms targeted to me or my student group.
- Required fields are validated, and successful submission is confirmed.
- My response is saved against the correct form and is unavailable to other students.

### US-STU-06 — Read admin follow-up

As a student, I want to read admin responses and relevant announcements so that I know how my feedback is being addressed.

Acceptance criteria:
- I can open messages and announcements addressed to me or an audience I belong to.
- Each message shows its sender and sent time.
- Messages intended for other users or groups are inaccessible.

## Teacher

### US-TEA-01 — Organise source materials

As a teacher, I want to upload and organise source materials so that I can prepare lessons for my courses.

Acceptance criteria:
- I can upload a supported file and associate it with a course and topic I manage.
- Unsupported or oversized uploads are rejected with an explanation of the accepted limits.
- I can find my uploaded materials, and an upload alone does not publish student-facing content.

### US-TEA-02 — Generate draft learning content

As a teacher, I want AI to draft notes and questions from my materials so that I can reduce preparation time.

Acceptance criteria:
- I can select an authorised source material and request draft notes or practice questions.
- Generated questions include suggested answers and explanations, and generated content remains a draft.
- An unusable generation is identified clearly; a failed request preserves the uploaded source and any existing draft.

### US-TEA-03 — Review and publish content

As a teacher, I want to edit and approve drafts before publication so that students receive content I have checked.

Acceptance criteria:
- I can edit draft notes, questions, answers and explanations for courses I manage.
- Publishing requires an explicit teacher action and validation of required content fields.
- Students can access the published version, while unpublished drafts remain hidden.

### US-TEA-04 — Manage practice sets

As a teacher, I want to organise questions into topic-based practice sets so that students can practise relevant concepts.

Acceptance criteria:
- I can select questions and associate a practice set with a course topic I manage.
- I can maintain answer keys and explanations before publication.
- Saved attempts retain the question and answer-key version used when submitted, so later edits do not silently change previous results.

### US-TEA-05 — Understand learning difficulties

As a teacher, I want to see completion and practice results so that I can identify topics that need more explanation.

Acceptance criteria:
- I can view completion rates, practice results and commonly missed questions for courses I manage.
- Reports identify their reporting period and use documented calculations.
- Courses with no activity show an empty state, and I cannot access reports for courses I do not manage.

### US-TEA-06 — Participate in feedback

As a teacher, I want to submit feedback and read admin responses so that I can help improve teaching workflows.

Acceptance criteria:
- I can complete open forms targeted to me or my teacher group, with required-field validation and submission confirmation.
- I can read follow-up messages addressed to me or my group.
- Other teachers' private submissions and messages are inaccessible.

## Admin

### US-ADM-01 — Measure feature usage

As an admin, I want to inspect feature analytics so that I can understand which features are used and where failures occur.

Acceptance criteria:
- I can view chatbot request counts, completed practice attempts and AI generation success rates for a selected period.
- Event definitions and success-rate denominators are documented and applied consistently.
- Reports distinguish no recorded activity from unavailable data and do not require displaying private chat contents.

### US-ADM-02 — Distribute targeted forms

As an admin, I want to create and distribute targeted feedback forms so that I can investigate a particular feature or lesson.

Acceptance criteria:
- I can define questions, required fields, an intended student/teacher audience and an optional feature or lesson association.
- I can publish and close a form; only its intended audience can submit while it is open.
- I can view collected responses without later form edits breaking the meaning of existing answers.

### US-ADM-03 — Analyse feedback with AI

As an admin, I want AI to summarise feedback and identify recurring issues so that I can prioritise improvements.

Acceptance criteria:
- I can select an authorised set of responses and generate a summary, grouped issues and suggested improvements.
- Findings reference supporting responses; suggestions are clearly distinguishable from reported feedback.
- The result remains reviewable and is not automatically sent to users or used to change the app.
- Empty input, request limits and generation failures produce clear messages.

### US-ADM-04 — Send feedback follow-up

As an admin, I want to send reviewed responses and announcements so that users know what action is being taken.

Acceptance criteria:
- I can compose and review a message and its intended recipients before sending it.
- Sent messages are saved and visible to the intended recipients through the app.
- Private feedback from other respondents is not automatically included in a response or announcement.

### US-ADM-05 — Manage accounts and access

As an admin, I want to manage user roles and course access so that users have appropriate permissions.

Acceptance criteria:
- I can manage account access, assign supported roles and grant or revoke course access.
- The server rejects account-management requests from non-admin users, including attempts to assign themselves admin privileges.
- Permission changes apply to subsequent protected requests, including requests to AI features.

### US-ADM-06 — Monitor AI resources

As an admin, I want to view AI usage and failures so that I can manage the available SoC LLM capacity.

Acceptance criteria:
- I can view request counts and failures by AI feature and reporting period.
- Token or resource measurements are displayed when available; missing measurements are labelled unavailable.
- Rate-limit failures are identifiable without exposing API credentials or private request contents.

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
