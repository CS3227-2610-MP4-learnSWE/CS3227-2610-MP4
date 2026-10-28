# learnSWE Feature List

## Product scope

learnSWE is a programming/software engineering learning web app with three roles: student, teacher and admin. Teachers prepare and publish learning content, students learn and practise, and admins use analytics and feedback to improve the app.

This document records the proposed features agreed during initial planning. It describes intended behaviour, not features already implemented. The initial programming subject and learner level remain to be decided.

All role features below are MVP requirements. Optional extensions are listed separately as nice-to-haves.

## Student

- **STU-01 — Study materials:** Browse teacher-published lessons by course and topic, read their contents, and mark lessons as complete or incomplete; either change persists and updates progress.
- **STU-02 — Practice questions:** Complete all questions in a practice set and submit the whole set once, then view the set score, correct answers and teacher-approved explanations. There is no per-question submission or immediate correctness feedback. Code execution is a nice-to-have, outside the MVP.
- **STU-03 — AI learning assistant:** Receive guided explanations on gaps in concepts or understanding, building on what the student already understands so they can solve questions independently. Use guiding questions and hints grounded in authorised published materials. Before whole-set submission, provide hints only: never reveal or confirm answers, full solutions or equivalent solution code, even on explicit request. After successful submission, provide full explanations for that submitted attempt.
- **STU-04 — Progress dashboard:** View completed lessons, practice scores and topics needing further practice based on recorded attempts.
- **STU-05 — Submit feedback:** Complete targeted feedback forms about lessons or app features.
- **STU-06 — Student inbox:** Receive admin survey requests, feedback responses and announcements in an in-app inbox. Open the relevant form from a survey request; track read/unread status and an unread count. Email and push notifications are outside the MVP.

## Teacher

- **TEA-01 — Manage learning materials:** Upload source materials and organise them by course and topic. Supported file types and size limits will be specified before implementation.
- **TEA-02 — AI content generation:** Generate draft study notes and practice questions from uploaded materials, including suggested answers and explanations.
- **TEA-03 — Review and publish:** Preview, edit, approve and publish generated study notes, practice questions, answer keys and explanations. Students can access published notes and questions; answer keys and solution explanations are released only after successful whole-set submission. AI generation never publishes automatically.
- **TEA-04 — Manage practice sets:** Select questions, assign practice sets to course topics and maintain answer keys and explanations.
- **TEA-05 — Learning overview:** View student completion rates, practice results and commonly missed questions for courses the teacher manages.
- **TEA-06 — Feedback and teacher inbox:** Complete targeted feedback forms and receive admin survey requests, responses and announcements in an in-app inbox. Survey requests link to the relevant form; messages have read/unread status and an unread count. Email and push notifications are outside the MVP.

## Admin

- **ADM-01 — Feature analytics:** Track selected feature usage, including chatbot requests, practice completion and AI generation success rates. Define event meanings and reporting periods consistently.
- **ADM-02 — Targeted feedback forms:** Create and distribute feedback forms to students or teachers, associating each form with a specific feature or lesson where relevant. Publishing delivers a survey request to intended recipients’ in-app inboxes.
- **ADM-03 — AI feedback analysis:** Summarise collected responses, group recurring issues and suggest improvements, with references to supporting feedback. Admins review the analysis before acting on it.
- **ADM-04 — Feedback follow-up:** Review and send responses or announcements to relevant students and teachers through recipients’ in-app inboxes.
- **ADM-05 — User and access management:** Manage accounts, roles and course access. Prevent users from granting themselves additional privileges.
- **ADM-06 — AI usage monitoring:** View AI request counts, failures and available resource-usage measurements to help manage SoC LLM limits. Show unavailable measurements explicitly rather than estimating them as facts.

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
