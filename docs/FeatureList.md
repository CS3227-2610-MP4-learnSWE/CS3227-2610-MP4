# learnSWE Feature List

## Product scope

learnSWE is a programming/software engineering learning web app with three roles: student, teacher and admin. Teachers prepare and publish learning content, students learn and practise, and admins use analytics and feedback to improve the app.

This document records the proposed features agreed during initial planning. It describes intended behaviour, not features already implemented. The initial programming subject and learner level remain to be decided.

## Student

- **STU-01 — Study materials:** Browse teacher-published lessons by course and topic, read their contents, and mark lessons as completed.
- **STU-02 — Practice questions:** Attempt multiple-choice and short code-reading questions, then view results and teacher-approved explanations. Code execution is outside the initial scope.
- **STU-03 — AI learning assistant:** Ask questions about published course materials and receive explanations with references to relevant sources. Request hints before revealing full answers.
- **STU-04 — Progress dashboard:** View completed lessons, practice scores and topics needing further practice based on recorded attempts.
- **STU-05 — Submit feedback:** Complete targeted feedback forms about lessons or app features.
- **STU-06 — View responses:** Read admin follow-up messages about feedback and relevant announcements.

## Teacher

- **TEA-01 — Manage learning materials:** Upload source materials and organise them by course and topic. Supported file types and size limits will be specified before implementation.
- **TEA-02 — AI content generation:** Generate draft study notes and practice questions from uploaded materials, including suggested answers and explanations.
- **TEA-03 — Review and publish:** Edit, approve and publish generated content before students can access it. AI generation never publishes automatically.
- **TEA-04 — Manage practice sets:** Select questions, assign practice sets to course topics and maintain answer keys and explanations.
- **TEA-05 — Learning overview:** View student completion rates, practice results and commonly missed questions for courses the teacher manages.
- **TEA-06 — Feedback participation:** Complete targeted feedback forms and read admin follow-up messages.

## Admin

- **ADM-01 — Feature analytics:** Track selected feature usage, including chatbot requests, practice completion and AI generation success rates. Define event meanings and reporting periods consistently.
- **ADM-02 — Targeted feedback forms:** Create and distribute feedback forms to students or teachers, associating each form with a specific feature or lesson where relevant.
- **ADM-03 — AI feedback analysis:** Summarise collected responses, group recurring issues and suggest improvements, with references to supporting feedback. Admins review the analysis before acting on it.
- **ADM-04 — Feedback follow-up:** Review and send responses or announcements to relevant students and teachers through the app.
- **ADM-05 — User and access management:** Manage accounts, roles and course access. Prevent users from granting themselves additional privileges.
- **ADM-06 — AI usage monitoring:** View AI request counts, failures and available resource-usage measurements to help manage SoC LLM limits. Show unavailable measurements explicitly rather than estimating them as facts.

## Shared requirements

- **SHR-01 — Authentication and authorisation:** Require login and enforce role, course and record access on the server, including AI retrieval and analytics endpoints.
- **SHR-02 — AI safeguards:** Treat uploads, chat messages and feedback as untrusted input; restrict retrieved context to authorised records; validate AI output and render it safely. Test prompt-injection attempts and cross-user data access.
- **SHR-03 — Resource management:** Use SoC LLM for app AI features. Apply input/output limits, request quotas, rate-limit handling and clear failure messages. Reuse saved generations where appropriate.
- **SHR-04 — Simple, usable interface:** Provide clear navigation, accessible forms, loading states, empty states and recoverable errors.
- **SHR-05 — Data boundaries:** Keep unpublished content hidden from students, individual progress private to authorised users, and raw feedback restricted to admins unless a separate sharing policy is agreed.

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

All listed role features remain in the proposed scope; this order is not a removal of later features. Live code execution, adaptive learning paths, gamification and complex dashboards are deferred.

## Related document

See [UserStories.md](UserStories.md) for stories and acceptance criteria mapped to these feature IDs.
