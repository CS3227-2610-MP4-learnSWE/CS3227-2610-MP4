# learnSWE Preview User Guide

Start the app using [README.md](../README.md). This guide covers the current preview; the feature list and user stories describe future production behaviour.

## Enter a workspace

At `/login`, choose Student, Teacher or Admin. Email/password fields and Sign in/Create account are decorative previews: they do not transmit credentials or register users. Use the separate Explore demo link to enter a workspace. Switch roles using the header selector or return to the login preview using the footer link.

The sun/moon button toggles light/dark mode. The initial theme follows your operating-system preference. Theme and other local state reset on refresh. On narrow screens, open the navigation drawer with the menu button.

## Student

- Overview shows illustrative progress, activity and course suggestions.
- Study materials supports topic filters and title search. Open a lesson, mark it complete, then mark it incomplete if desired. Completion updates the overview until refresh.
- Practice contains three questions. Answer every question and submit the whole set in one action. An incomplete attempt is rejected. After submission, view the score, answer keys and explanations; start another demo attempt to reset.
- AI study companion returns fixed, labelled sample responses. Before practice submission it gives hints only. After successful submission it can explain the sample answers. It is not connected to an LLM.
- Inbox starts with two unread messages. Opening one marks it read and updates the count. Open the survey link to see a sample feedback form. Its submission button shows a preview message without saving anything.

## Teacher

- Overview displays sample participation and draft-review information.
- Materials library supports search. Upload material opens a file-picker preview; only the filename is displayed, with no reading or upload.
- AI content studio lets you select source and draft type. Preview generation shows fixed sample notes or questions; changing the source does not generate different content.
- Review & publish offers tabs for notes and practice questions/answer keys/explanations. Edit locally and preview publication; nothing is saved or published.
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

All workspaces are public local demonstrations with unrestricted role switching. Do not use real credentials or sensitive materials. All state is temporary; refresh returns to sample defaults. Unknown routes return to login or a role-specific not-found view. An unavailable backend shows a footer status and does not prevent exploring screens. Real authentication, authorisation, secure answer release, file storage, AI integration, PostgreSQL and online deployment are future work.
