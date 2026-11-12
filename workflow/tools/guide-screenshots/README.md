# Guide screenshots

Regenerates the screenshots in `docs/images/guide/` by running the User Guide walkthrough in a real browser. Because it performs every step in the guide, it also proves the walkthrough still works.

Run it against a **fresh database with the sample data** and the AI settings configured (the AI steps call the SoC LLM), so the screens match the guide:

1. Follow the README setup with the sample data option, and start the backend and frontend.
2. From `src/frontend` make sure Playwright's browser is installed: `npx playwright install chromium`.
3. From the repository root run:

```sh
node workflow/tools/guide-screenshots/capture.mjs
```

Settings (environment variables, all optional): `GUIDE_BASE` (default `http://127.0.0.1:5173`), `GUIDE_OUT` (default `docs/images/guide`), and `GUIDE_STUDENT_EMAIL`, `GUIDE_STUDENT_PASSWORD`, `GUIDE_TEACHER_*`, `GUIDE_ADMIN_*` if you changed the example accounts.

The script creates data (a course, an account, a feedback form, messages), so run it once per fresh database; to run it again, start over with a clean database (see the README). Review the new images before committing them: they should show no real names, emails or secrets.
