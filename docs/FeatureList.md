# learnSWE Feature List

## Product scope

learnSWE is a programming/software engineering learning web app with three roles: student, teacher and admin. Teachers prepare and publish learning content, students learn and practise, and admins use analytics and feedback to improve the app.

This document records the proposed features agreed during initial planning. It describes intended behaviour, not features already implemented. The initial programming subject and learner level remain to be decided.

All role features below are MVP requirements. Optional extensions are listed separately as nice-to-haves.

## Student

- **STU-01 — Study materials:** Browse teacher-published lessons by course and topic, read their contents, and mark lessons as complete or incomplete; either change persists and updates progress.
- **STU-02 — Practice questions:** Complete all single-answer multiple-choice questions (MCQs) in a practice set and submit the whole set once, then view the set score, correct answers and teacher-approved explanations. There is no per-question submission or immediate correctness feedback. Code execution is a nice-to-have, outside the MVP.
- **STU-03 — AI learning assistant:** Receive guided explanations on gaps in concepts or understanding, building on what the student already understands so they can solve questions independently. Use guiding questions and hints grounded in authorised published materials. Before whole-set submission, provide hints only: never reveal or confirm answers, full solutions or equivalent solution code, even on explicit request. After successful submission, provide full explanations for that submitted attempt.
- **STU-04 — Progress dashboard:** View completed lessons, practice scores and topics needing further practice based on recorded attempts.
- **STU-05 — Submit feedback:** Complete targeted feedback forms about lessons or app features.
- **STU-06 — Student inbox:** Receive admin survey requests, feedback responses and announcements in an in-app inbox. Open the relevant form from a survey request; track read/unread status and an unread count. Email and push notifications are outside the MVP.

### Study companion behaviour (STU-03)

- Open a bottom-right chat box from the floating icon on any student page. Close minimises without losing history or the unsent draft; refresh clears both and starts fresh.
- In the authenticated app, history belongs to one signed-in account and survives navigation and browser reload until logout or explicit clear. Logout/account switching removes it from the active session.
- Use the current page and relevant authorised visible contents as context, updating as the student navigates. Do not include protected answer keys/solutions before submission, unpublished content or other users’ data.
- This release previews the widget with local history, fixed replies and a page label only. Browser reload or leaving the student demo resets chat; real AI context retrieval and authenticated persistence remain future work.

## Teacher

- **TEA-01 — Manage learning materials:** Upload source materials, organise them by course and topic, and permanently delete unused sources only when no note drafts or MCQ batches reference them. Supported file types and size limits will be specified before implementation.
- **TEA-02 — AI content generation:** Generate draft study notes and batches of exactly three single-answer MCQs from uploaded materials. Each question has answer choices, exactly one correct choice and an explanation; no free-text answer questions.
- **TEA-03 — Review and publish:** Preview, edit, approve and publish generated study notes, MCQs, answer keys and explanations. Students can access published notes and questions; answer keys and solution explanations are released only after successful whole-set submission. AI generation never publishes automatically. Any teacher managing the course can permanently delete its unpublished note drafts or whole MCQ draft batches after confirmation; published or otherwise referenced content must remain protected.
- **TEA-04 — Publish three-question practice sets:** One reviewed generated MCQ batch becomes one practice set containing all three questions, with a title and course topic. No subsets, mixing batches or separate question-assembly workflow. Use TEA-03’s explicit publication workflow; published snapshots and student attempt versions remain unchanged by later draft edits.
- **TEA-05 — Learning overview:** View student completion rates, practice results and commonly missed questions for courses the teacher manages.
- **TEA-06 — Feedback and teacher inbox:** Complete targeted feedback forms and receive admin survey requests, responses and announcements in an in-app inbox. Survey requests link to the relevant form; messages have read/unread status and an unread count. Email and push notifications are outside the MVP.

## Admin

- **ADM-01 — Feature analytics:** Report chatbot outcomes, practice-set completion and generation success rates for defined periods. Review advisory AI response-quality grades, response timing, session message counts and linked activity durations, with privacy safeguards and explicit unavailable data; operational AI service counts belong to ADM-06.
- **ADM-02 — Targeted feedback forms:** Draft forms with short-answer, paragraph, single-choice, dropdown, checkbox and linear-scale questions, required/optional settings and optional feature/lesson associations. Publish to selected students or teachers through inbox requests, close collection and review admin-only responses with question snapshots.
- **ADM-03 — AI feedback analysis:** Analyse selected authorised feedback into summaries, recurring issues and clearly distinguished suggestions, with supporting-response references, explicit failure states and human review. Analysis and evidence review do not send messages or change content.
- **ADM-04 — Feedback follow-up:** Review and send one-to-one responses to feedback submitters or announcements to selected student or teacher audiences through private in-app inboxes. Recipients receive unread messages; email and push delivery are outside the MVP.
- **ADM-05 — User and access management:** Create fixed-role student, teacher and admin accounts; enable, disable or permanently archive accounts; create courses and manage student enrolments and teacher assignments. Provide account search/filtering and confirmations; prevent self-escalation and administrator lockout while retaining linked history.
- **ADM-06 — AI usage monitoring:** Report AI service-call attempts (including retries), failure counts and rate-limit failures by feature and period, separately from feature outcome percentages. Show recorded token/resource measurements with explicit unavailable values; exclude private request content and inferred measurements.

## Shared requirements

- **SHR-01 — Authentication and authorisation:** Require login and enforce role, course and record access on the server, including AI retrieval and analytics endpoints.
- **SHR-02 — AI safeguards:** Treat uploads, chat messages and feedback as untrusted input; restrict retrieved context to authorised records; validate AI output and render it safely. Enforce submission status on the server before releasing answer keys or solution explanations, and exclude them from pre-submission AI context. Test prompt injection, cross-user access and answer leakage through hints, sources and output; do not rely on prompts alone to enforce access.
- **SHR-03 — Resource management:** Use SoC LLM for app AI features. Apply input/output limits, request quotas, rate-limit handling and clear failure messages. Reuse saved generations where appropriate.
- **SHR-04 — Minimalist, Responsive and Accessible Interface:** Provide a Google-inspired, distraction-free interface with clear navigation, consistent spacing and typography, and layouts that adapt to mobile and desktop screens. Include accessible forms, visible loading feedback, contextual empty states and clear error-recovery actions. Respect reduced-motion preferences.
- **SHR-05 — Data boundaries:** Keep unpublished content hidden from students, individual progress private to authorised users, and raw feedback restricted to admins unless a separate sharing policy is agreed.

## Nice-to-have features — outside the MVP

- **OPT-01 — Run code against test cases (student):** Write and execute code against teacher-defined tests, then inspect results. This requires isolated execution, time/memory limits and abuse testing before release. Any pre-submission output must preserve the hints-only policy.
- **OPT-02 — AI teaching preferences (student):** Choose preset explanation length, bullet points versus paragraphs, and hints versus worked examples. Worked examples must not reveal answers to unsubmitted questions; submission safeguards take precedence.
- **OPT-03 — AI generation preferences (teacher):** Choose preset audience level, tone and detail for generated notes and questions. Preferences do not bypass teacher review.

Preferences cannot override fixed app rules, access permissions, data privacy or learning safeguards. Enforce data/action access on the server; instruction filtering alone is insufficient. Editable system prompts are not supported. A free-text teaching-style field is a later consideration, treated as untrusted input rather than inserted into the system prompt.

## Delivery requirements from the assignment

These are team-level obligations, separate from the role features:

- Follow spec-driven development and coordinate specialised software engineering agents with recorded responsibilities and handoffs.
- Implement and test security for app AI features and the development workflow.
- Deploy online with separate development and production environments, managed by the team through suitable automation; do not use a prohibited build-and-host environment.
- Record context-engineering and resource-usage experiments, development interaction summaries and evidence-based reflections.
- Maintain the required source, workflow, documentation and log structure, user/developer guides, reflection document and GitHub Pages product website.
- Keep the public repository's `master` branch up to date for grading.

## Suggested delivery order

1. Establish shared authentication, access controls and AI request handling.
2. Deliver the teacher upload → generate → review → publish workflow alongside student reading, practice and AI help.
3. Deliver targeted forms, feedback collection, admin AI analysis and follow-up.
4. Complete progress views, learning analytics and AI usage reporting.

All listed MVP role features remain in scope; this order does not remove later MVP work. OPT-01 through OPT-03 are optional extensions. Adaptive learning paths, gamification and complex dashboards are deferred.

## Related document

See [UserStories.md](UserStories.md) for stories and acceptance criteria mapped to these feature IDs.
