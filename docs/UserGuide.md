# learnSWE Preview User Guide

Start the app using [README.md](../README.md). This guide covers the current preview; the feature list and user stories describe future production behaviour.

## Enter a workspace

At `/login`, choose Student, Teacher or Admin. Email/password fields and Sign in/Create account are decorative previews: they do not transmit credentials or register users. Use the separate Explore demo link to enter a workspace. Switch roles using the header selector or return to the login preview using the footer link.

The sun/moon button toggles light/dark mode. The initial theme follows your operating-system preference. Theme and other local state reset on refresh. On narrow screens, open the navigation drawer with the menu button.

## Student

- Overview shows illustrative progress, activity and course suggestions.
- Study materials supports topic filters and title search. Open a lesson, mark it complete, then mark it incomplete if desired. Completion updates the overview until refresh.
- Practice loads one set of single-answer MCQs from the server (code snippets can appear in a question, but answers are selected choices, never free text). Answer every question and submit the whole set in one action; if any is unanswered, nothing is sent and the page names the missing question numbers. After a successful submission the score, your choice, the correct answer and the explanation for each question come from the server, and the choices lock. "Start another attempt" gives an empty form. If the server cannot be reached or fails, the page says so, keeps your answers and offers "Try again". If the failure happens after your answers were saved on the server, they are locked and "Try again" finishes the submission. Answers and results are kept while you move between student pages; a browser reload starts fresh. The student identity is a fixed placeholder until real login exists. The hint panel is a scripted demo, not AI. After submission a wrong answer is marked in red (your choice outlined in red, its explanation on a red background) and the correct choice is outlined in green; a right answer stays green, and the score banner turns amber unless every answer is right.
- The study companion is a bottom-right chat icon on every student page. Click it to open the chat box; Close or Escape minimises it and preserves messages and the unsent draft. The refresh icon clears both and starts fresh without reloading the page. Messages survive navigation within the student workspace; browser reload, returning to login or switching demo roles clears this temporary chat. The widget shows the current page label and fixed preview replies, not real AI or page-content retrieval. Before submission it never reveals or confirms answers. In the future authenticated app, chat should remain account-scoped until logout/explicit clear, including across reload, and use relevant authorised content from the current page.
- Inbox starts with two unread messages. Opening one marks it read and updates the count. Open the survey link to see a sample feedback form. Its submission button shows a preview message without saving anything.

## Teacher

- Overview displays sample participation and draft-review information.
- Materials library supports search. Upload material opens a file-picker preview; only the filename is displayed, with no reading or upload.
- AI content studio lets you select source and draft type. Preview generation shows fixed sample notes or MCQs, including answer choices; changing the source does not generate different content.
- Review & publish offers tabs for notes and MCQs, their choices, answer keys and explanations. Edit locally and preview publication; nothing is saved or published.
- Practice sets lets you edit the title/topic and select questions. The preview action does not save a set.
- Inbox and feedback follow the same preview behaviour as the student workspace.

## Admin

- Analytics has sample reporting periods and labelled illustrative figures.
- Feedback forms lets you edit questions, required flags, audience and related feature. Preview survey request opens a summary without creating a form or sending a request.
- Feedback insights offers sentiment filtering, fixed AI analysis and links to supporting sample responses.
- Announcements accepts a subject/message and shows a recipient preview. Nothing is sent.
- People & access filters fictitious records by role. Preview access cannot change permissions.
- AI usage displays illustrative requests/failures; actual token usage is explicitly unavailable.

## Limitations and recovery

All workspaces are public local demonstrations with unrestricted role switching. Do not use real credentials or sensitive materials. All state is temporary; refresh returns to sample defaults. Unknown routes return to login or a role-specific not-found view. An unavailable backend shows a footer status and does not prevent exploring screens, except the student Practice page, which needs the backend to load questions. The practice server withholds the answer key and explanations until whole-set submission and checks attempt ownership using the placeholder student header. This is not real authentication: everyone using the preview shares the configured student identity. Real login, role/course authorisation, file storage, AI integration, PostgreSQL and online deployment are future work. Attempts are held in server memory and are lost when the backend restarts; browser reload clears the current page state.
