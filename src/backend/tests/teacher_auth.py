"""Test-only cookie sessions for teacher API contracts; no demo identity bypass."""
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone


def teacher_headers(user="demo-teacher", *, csrf=True):
    if user is None:
        return {}
    token, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    headers = {"Cookie": f"learnswe_session={token}"}
    if csrf:
        headers["X-CSRF-Token"] = nonce
    import psycopg
    raw = os.environ.get("DATABASE_URL", "")
    if not raw.startswith("postgresql+psycopg://"):
        return headers
    url = raw.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url, autocommit=True) as db:
        if db.execute('SELECT id FROM "user" WHERE id=%s', (user,)).fetchone():
            now = datetime.now(timezone.utc)
            db.execute("INSERT INTO auth_session(id,token_hash,user_id,csrf_token,created_at,expires_at) VALUES(%s,%s,%s,%s,%s,%s)",
                       (uuid.uuid4(), hashlib.sha256(token.encode()).hexdigest(), user, nonce, now, now + timedelta(hours=1)))
    return headers
