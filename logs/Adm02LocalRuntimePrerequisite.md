# ADM-02 local runtime prerequisite clarification — 2026-11-07

User reported the ADM-02 admin list displayed “The feedback service is temporarily unavailable” during the local walkthrough. Diagnosis found PostgreSQL healthy, the local backend responding on port 8000, and its process launched without `--env-file .env`. The configured database had only the prior ADM-06 migration applied.

Applied `uv run --env-file .env alembic upgrade head` from `src/backend`; `uv run --env-file .env alembic current` verified `20261107_adm02_feedback (head)`. The backend process was not stopped or restarted; user must restart it with `uv run --env-file .env uvicorn main:app --host 127.0.0.1 --port 8000 --reload` so runtime configuration matches the migrated database.

Updated the ADM-02 spec and plan, Developer Guide, User Guide and workflow handoff to call out the migration/environment prerequisite and explain that the 503 is a transient dependency failure, not a disabled feature. No application source, tests, credentials or process state were changed. No tests run (documentation/setup correction).
