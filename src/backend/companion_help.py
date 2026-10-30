"""Fixed app-help text for Help mode. Written from docs/UserGuide.md; keep the two in step and claim only what works."""

HELP_TEXT = """\
learnSWE app help. This is help about the app itself, not course material.
- Study materials: sample lessons you can filter by topic, search by title and open. You can mark a lesson complete or incomplete; the overview updates until the page is refreshed.
- Practice: one set of multiple-choice questions loaded from the server. Answer every question, then submit the whole set in one step. If a question is unanswered nothing is sent and the page lists the missing question numbers. After a successful submission the page shows your score and, for each question, your choice, the correct answer and an explanation, and the choices lock. "Start another attempt" gives an empty form. If the server cannot be reached the page says so, keeps your answers and offers "Try again".
- Inbox: sample messages. Opening one marks it read.
- Study companion: the chat icon at the bottom right of every student page. Escape or the minimise button hides it and keeps your chat and unsent text. The refresh icon clears the chat. Reloading the browser clears it too.
- Companion limits: each message can be up to 1,000 characters, and you can send up to 20 messages a minute and 300 a day. In this preview everyone shares one placeholder student id, so that limit is shared by everyone using the same deployment.
- Before you submit a practice set the companion gives hints and guiding questions only; it does not give or confirm answers. After you submit, it can explain that attempt.
- Teacher and admin areas are demonstrations with sample data.
"""
