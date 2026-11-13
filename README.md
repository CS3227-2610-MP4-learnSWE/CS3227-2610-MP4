# learnSWE

[Visit the learnSWE product website](https://cs3227-2610-mp4-learnswe.github.io/CS3227-2610-MP4/) for the application and guides.

learnSWE is a web app for learning and teaching software engineering. Teachers turn their course materials into lessons and practice questions with help from AI, students learn and practise at their own pace with an AI study companion, and administrators manage accounts, collect feedback and watch how the service is doing.

| Role | What you can do |
|---|---|
| **Student** | Read published lessons and track completion. Take multiple-choice practice sets and see scores and explanations after you submit. Follow your progress. Ask the AI study companion for hints and explanations. Answer feedback requests and read replies and announcements. |
| **Teacher** | Upload course materials (PDF or text). Generate draft study notes and practice questions with AI, edit them, then publish them to your course. See how your students are doing. Answer feedback requests and read messages. |
| **Admin** | Create accounts and courses and manage who can access what. Build feedback forms, review responses, analyse them with AI, reply to respondents and send announcements. Monitor usage, reliability, response times and AI quality. |

## Set up

Follow these steps once. Allow about 10 minutes.

### 1. Prerequisites

Install these first. The check commands should print a version number.

| Tool | Version | Check | Install |
|---|---|---|---|
| Git | any | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| Docker Desktop (runs the PostgreSQL database) | any | `docker --version` | [docker.com](https://www.docker.com/products/docker-desktop/) |
| Node.js (includes npm) | 22 or newer | `node --version` | [nodejs.org](https://nodejs.org/) |
| uv (installs Python and the backend packages) | any | `uv --version` | [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |

Start Docker Desktop and wait until it says it is running.

### 2. Get the code

Downloads the project into a new `CS3227-2610-MP4` folder and opens it.

```sh
git clone https://github.com/CS3227-2610-MP4-learnSWE/CS3227-2610-MP4.git
cd CS3227-2610-MP4
```

Use this terminal window for the next steps and stay in the project folder.

### 3. Start the database

Starts PostgreSQL in Docker and keeps it running in the background. The first run downloads the image, which takes a minute.

```sh
docker compose up -d postgres
```

### 4. Set up the backend

Open a **new terminal window** for the backend, go to the project folder, then run each block in order.

**Go to the backend folder.**

```sh
cd src/backend
```

**Create your settings file.** `.env` holds your local settings and the sign-in accounts. It is ignored by Git, so your changes are never committed. This creates it from `.env.example` and fills in these **example accounts**, so you can sign in straight away:

| Role | Email | Password |
|---|---|---|
| Student | `student@example.com` | `Student-Demo-4821` |
| Teacher | `teacher@example.com` | `Teacher-Demo-4821` |
| Admin | `admin@example.com` | `Admin-Demo-4821` |

macOS / Linux:

```sh
grep -v '^SEED_' .env.example > .env
cat >> .env <<'EOF'
SEED_STUDENT_EMAIL=student@example.com
SEED_STUDENT_PASSWORD=Student-Demo-4821
SEED_TEACHER_EMAIL=teacher@example.com
SEED_TEACHER_PASSWORD=Teacher-Demo-4821
SEED_ADMIN_EMAIL=admin@example.com
SEED_ADMIN_PASSWORD=Admin-Demo-4821
EOF
```

Windows (PowerShell):

```powershell
Get-Content .env.example | Where-Object { $_ -notmatch '^SEED_' } | Set-Content .env
@'
SEED_STUDENT_EMAIL=student@example.com
SEED_STUDENT_PASSWORD=Student-Demo-4821
SEED_TEACHER_EMAIL=teacher@example.com
SEED_TEACHER_PASSWORD=Teacher-Demo-4821
SEED_ADMIN_EMAIL=admin@example.com
SEED_ADMIN_PASSWORD=Admin-Demo-4821
'@ | Add-Content .env
```

> **These accounts are public examples, only for trying the app on your own computer.** For anything other people can reach, use your own values instead: copy `.env.example` to `.env` (`cp .env.example .env` or `Copy-Item .env.example .env`) and fill in the six empty `SEED_` lines yourself. Passwords need 10 to 128 characters and cannot be a common password or the same as the email.

**Optional: review the other settings in `.env`.** Everything else works as it is, so you can skip this on your first run.

| Setting | Change it when |
|---|---|
| `SOCLAAS_BASE_URL`, `SOCLAAS_API_KEY`, `SOCLAAS_MODEL` | You want the AI features (study companion, AI notes and questions, feedback analysis). Paste the values you were given for the SoC LLM service. Leave them empty to run without AI: those features then say they are unavailable and everything else works. |
| `ALLOWED_ORIGINS` | You open the app at an address other than `http://localhost:5173` or `http://127.0.0.1:5173`. Add that address, or sign-in fails. |
| `APP_ENV`, `SESSION_COOKIE_SECURE` | You deploy for real users over https: set `APP_ENV=production` and `SESSION_COOKIE_SECURE=true`. Leave them as they are on your own computer. |
| Everything else | Leave it as it is. |

**Install the backend packages.** Creates a private Python environment in `.venv` and installs the locked packages.

```sh
uv sync --frozen
```

**Create the database tables.**

```sh
uv run --env-file .env python -m alembic upgrade head
```

**Add the starting data.** Pick one:

- **Sample data (recommended to try the app).** Creates the three accounts, a course with two lessons and a practice set, an example feedback form and a week of example usage figures, so every screen has something to show. It only runs when `APP_ENV=development`.

  ```sh
  uv run --env-file .env python sample_data.py
  ```

  You should see `demo-student: seeded`, `demo-teacher: seeded` and `demo-admin: seeded`. Running it again is safe: it does not duplicate anything or change existing passwords.

- **Accounts only (no sample content).** Creates the three accounts, two empty courses (Software Engineering and Programming) and a second teacher, Alex, who has no sign-in; rename or disable these in **Users** and **Courses** as you like. Use this for a real deployment.

  ```sh
  uv run --env-file .env python -m teacher_materials.seed
  uv run --env-file .env python -m auth.seed
  ```

**Start the backend.** Leave this window open while you use the app. Stop it with Ctrl+C.

```sh
uv run --env-file .env python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Wait for `Application startup complete`. To check it, open <http://127.0.0.1:8000/api/health>: it shows `{"status":"ok"}`.

> If you edit `.env` later, stop the backend with Ctrl+C and start it again. It reads `.env` only at startup.

### 5. Set up the frontend

Open a **second new terminal window**, go to the project folder, then run:

**Go to the frontend folder.**

```sh
cd src/frontend
```

**Create the frontend settings file.** The defaults work as they are.

| macOS / Linux | Windows (PowerShell) |
|---|---|
| `cp .env.example .env` | `Copy-Item .env.example .env` |

**Install the packages.**

```sh
npm ci
```

**Start the app.** Leave this window open too.

```sh
npm run dev
```

> On Windows, if PowerShell says running scripts is disabled, type `npm.cmd` instead of `npm` in both commands.

### 6. Open the app

Go to <http://127.0.0.1:5173/login> and sign in with one of the accounts above. You land on your role's home page.

You can now follow the **[User Guide](docs/UserGuide.md)**: it walks through every feature step by step for students, teachers and admins.

## If something goes wrong

| What you see | What to do |
|---|---|
| "We could not reach the server" when you sign in | Either the backend is not running (or the frontend `API_PORT` does not match its port, default 8000), or the address in your browser is missing from `ALLOWED_ORIGINS` in the backend `.env`. Start the backend, add the address if needed, restart the backend and try again. |
| "Email or password is incorrect" | Use the exact emails and passwords from your backend `.env`. After 5 wrong attempts the email is locked for 15 minutes (restarting the backend clears this). If you changed a `SEED_*_PASSWORD` after the accounts already existed, run `uv run --env-file .env python -m auth.seed --reset-passwords` in `src/backend`. |
| `docker compose` cannot connect or the backend says the database refused the connection | Start Docker Desktop, run `docker compose up -d postgres` again, wait a few seconds and retry. |
| A port is already in use | Stop the other program, or choose another port: start the backend with `--port 8001` and set `API_PORT=8001` in `src/frontend/.env`, then restart both. |
| Windows says an "Application Control policy" blocked a file | Run the commands exactly as written above (they use `python -m`); ask your administrator to allow `uv` and Node.js if it persists. |
| AI features say they are unavailable | Fill in the three `SOCLAAS_*` settings in the backend `.env` and restart the backend. |

## Run it again later

1. Start Docker Desktop and run `docker compose up -d postgres` in the project folder.
2. Backend window: `cd src/backend`, then `uv run --env-file .env python -m uvicorn main:app --host 127.0.0.1 --port 8000`.
3. Frontend window: `cd src/frontend`, then `npm run dev`.

Your data stays in the database between runs.

## Start over with a clean database

This **deletes all data** (accounts, lessons, practice results, feedback). In the project folder:

```sh
docker compose down -v
docker compose up -d postgres
```

Then repeat step 4 from "Create the database tables" onward.

## Deploying for real users

1. In the backend `.env`: set `APP_ENV=production` and `SESSION_COOKIE_SECURE=true`, use your real `https://` address in `ALLOWED_ORIGINS` (for example `https://learn.example.edu`), and use your own `SEED_*` emails and passwords, not the examples. Then run the "Accounts only" commands from step 4. The sample data command refuses to run when `APP_ENV=production`.
2. In the frontend `.env`: keep `VITE_ENABLE_DEMO_ACCESS=false`. It is read when you build, so set it before the next step.
3. Build the frontend: in `src/frontend` run `npm run build`. Serve the `dist` folder over https with any web server, with two rules: unknown paths such as `/admin/analytics` must return `index.html`, and everything under `/api` must be forwarded unchanged (including cookies and the `Origin` header) to the backend on port 8000. Keep the backend running as in step 4.
4. Open your https address and sign in with your own account. Login only works over https because the session cookie is marked secure.

More detail is in the [Developer Guide](docs/DeveloperGuide.md).

## More documentation

- [User Guide](docs/UserGuide.md): feature summary and a step-by-step walkthrough for each role.
- [Developer Guide](docs/DeveloperGuide.md): architecture, configuration, tests and contributing.
- [Feature list](docs/FeatureList.md) and [user stories](docs/UserStories.md).
