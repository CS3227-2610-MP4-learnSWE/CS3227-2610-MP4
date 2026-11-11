"""One command that fills a fresh development database: run it after `alembic upgrade head`.

    uv run --env-file .env python dev_seed.py

Runs each seed in dependency order and stops at the first failure. Refuses unless APP_ENV=development.
Every step is idempotent, so running it again is safe. Never run it against a shared or production database.
"""
import os
import subprocess
import sys

STEPS = (
    "teacher_materials.seed",   # demo users, course, topic
    "auth.seed",                # sign-in credentials from SEED_*_EMAIL / SEED_*_PASSWORD
    "study_lessons.seed",       # sample lessons
    "teacher_publications.seed",  # a published practice set
    "feedback_dev_seed",           # one open feedback form with a response per seeded student
    "feature_analytics.seed_dev",  # a week of activity for the Feature Analytics hub
    ("ai_usage.activate", "--feature", "STU-03", "--feature", "TEA-02"),  # AI usage counting on from now
)


def main() -> int:
    if os.environ.get("APP_ENV") != "development":
        print("dev_seed is for development databases only (set APP_ENV=development).")
        return 1
    for step in STEPS:
        module, *args = (step,) if isinstance(step, str) else step
        print(f"== {module}")
        code = subprocess.call([sys.executable, "-m", module, *args])
        if code != 0:
            print(f"dev_seed stopped: {module} exited with {code}")
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
