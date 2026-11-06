"""Coordinate session issuance with administrative account changes."""
from sqlalchemy import text
from sqlalchemy.orm import Session


def lock_account_changes(db: Session) -> None:
    # Transaction-scoped, shared across processes. One ordering for admin writes
    # and login prevents sessions appearing after disable/archive commits.
    db.execute(text("SELECT pg_advisory_xact_lock(3227, 5005)"))
