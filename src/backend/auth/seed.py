"""Seed login credentials for the demo accounts from the environment. Idempotent; never prints passwords.

Run after migrations and teacher_materials.seed:  uv run python -m auth.seed [--reset-passwords]
"""
import os
import sys
from collections.abc import Mapping

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from auth.passwords import check_password_rules, hash_password, normalise_email
from teacher_materials.models import User

# role -> (fixed user id, display name used only when the user must be created)
TARGETS = {"student": ("demo-student", None), "teacher": ("demo-teacher", None), "admin": ("demo-admin", "Admin")}


def seed_accounts(db: Session, environ: Mapping[str, str], reset_passwords: bool = False) -> tuple[list[str], bool]:
    """One report line per role, and whether any line is an error (wrong role, email taken)."""
    lines, failed = [], False
    for role, (user_id, display_name) in TARGETS.items():
        prefix = f"SEED_{role.upper()}"
        raw_email, password = environ.get(f"{prefix}_EMAIL", ""), environ.get(f"{prefix}_PASSWORD", "")
        if not raw_email.strip() or not password:
            lines.append(f"{user_id}: skipped: {prefix}_EMAIL or {prefix}_PASSWORD is not set")
            continue
        try:
            email = normalise_email(raw_email)
        except ValueError:
            lines.append(f"{user_id}: skipped: email is not valid")
            continue
        if check_password_rules(password, email):
            lines.append(f"{user_id}: skipped: password breaks the password rules")
            continue
        user = db.get(User, user_id)
        if user is None and display_name is None:
            lines.append(f"{user_id}: skipped: user is missing (run teacher_materials.seed first)")
            continue
        if user is not None and user.role != role:
            lines.append(f"{user_id}: error: existing user has a different role")
            failed = True
            continue
        if user is not None and user.password_hash is not None and not reset_passwords:
            lines.append(f"{user_id}: unchanged")
            continue
        holder = db.scalar(select(User.id).where(User.email == email))
        if holder is not None and holder != user_id:
            lines.append(f"{user_id}: error: email is already used by another user")
            failed = True
            continue
        if user is None:
            user = User(id=user_id, display_name=display_name, role=role)
            db.add(user)
        user.email, user.password_hash = email, hash_password(password)
        db.commit()
        lines.append(f"{user_id}: seeded")
    return lines, failed


if __name__ == "__main__":
    with Session(create_engine(os.environ["DATABASE_URL"])) as session:
        report, had_error = seed_accounts(session, os.environ, "--reset-passwords" in sys.argv[1:])
    print("\n".join(report))
    sys.exit(1 if had_error else 0)
