"""SHR-01 seed script (AC7) and additive migration (AC24), each in a throwaway PostgreSQL schema.

The shared test schema is never touched: seeds and migrations run in their own schema that is
dropped afterwards. Direct SQL only reads, or sets up rows the plan names.
"""
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from auth_helpers import SEED_ENV, psycopg_url, schema_url

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parents[1]
NEW_REVISION = "20261103_shr01_auth"
PREVIOUS_REVISION = "20261102_tea01_db_storage"
COURSE_A = "11111111-1111-4111-8111-111111111111"


class Isolated:
    def __init__(self, base, schema):
        self.base, self.schema = base, schema
        self.url = schema_url(base, schema)

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith("SEED_")}
        env.update(DATABASE_URL=self.url, APP_ENV="development", ALLOW_DEMO_IDENTITY="true",
                   FILE_STORAGE_DIR=os.environ.get("FILE_STORAGE_DIR", str(BACKEND)))
        env.update(extra)
        return env

    def run(self, *args, check=True, **env):
        r = subprocess.run([sys.executable, *args], cwd=BACKEND, env=self.env(**env),
                           capture_output=True, text=True)
        if check and r.returncode != 0:
            raise AssertionError(f"{args} failed: {r.stdout[-500:]} {r.stderr[-500:]}")
        return r

    def migrate(self, *args, check=True):
        return self.run("-m", "alembic", *args, check=check)

    def seed_teacher(self):
        return self.run("-m", "teacher_materials.seed")

    def seed_auth(self, *flags, check=False, **env):
        return self.run("-m", "auth.seed", *flags, check=check, **env)

    def sql(self, statement, params=()):
        import psycopg

        with psycopg.connect(psycopg_url(self.base), autocommit=True) as conn:
            conn.execute(f'SET search_path TO "{self.schema}"')
            cur = conn.execute(statement, params)
            return cur.fetchall() if cur.description else None


@pytest.fixture
def iso():
    base = os.environ.get("TEA01_TEST_DATABASE_URL")
    if not base:
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    import psycopg

    schema = "shr01_" + uuid.uuid4().hex
    with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{schema}"')
    try:
        yield Isolated(base, schema)
    finally:
        with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


@pytest.fixture
def seeded_schema(iso):
    iso.migrate("upgrade", NEW_REVISION)
    iso.seed_teacher()
    return iso


def row(iso, uid):
    r = iso.sql('SELECT id, email, role, password_hash, display_name FROM "user" WHERE id = %s', (uid,))
    return r[0] if r else None


# ------------------------------------------------------------------ AC7 seed
def test_shr01_ac7_seed_sets_email_and_hash_for_the_three_demo_users(seeded_schema):
    r = seeded_schema.seed_auth(check=True, **SEED_ENV)
    for uid, role, key in (("demo-student", "student", "STUDENT"), ("demo-teacher", "teacher", "TEACHER"),
                           ("demo-admin", "admin", "ADMIN")):
        _, email, got_role, pw_hash, _ = row(seeded_schema, uid)
        assert email == SEED_ENV[f"SEED_{key}_EMAIL"].lower()
        assert got_role == role
        assert pw_hash.startswith("scrypt$16384$8$1$")
        assert SEED_ENV[f"SEED_{key}_PASSWORD"] not in pw_hash
    assert r.returncode == 0
    for value in SEED_ENV.values():
        if "Pw" in value:
            assert value not in r.stdout and value not in r.stderr  # never print a password
    assert "seeded" in r.stdout


def test_shr01_ac7_demo_admin_is_created_without_memberships(seeded_schema):
    assert row(seeded_schema, "demo-admin") is None
    seeded_schema.seed_auth(check=True, **SEED_ENV)
    uid, _, role, _, name = row(seeded_schema, "demo-admin")
    assert role == "admin" and name == "Admin"
    assert seeded_schema.sql("SELECT count(*) FROM course_membership WHERE user_id = 'demo-admin'")[0][0] == 0
    # the teacher-seed memberships are untouched
    assert seeded_schema.sql("SELECT count(*) FROM course_membership WHERE user_id = 'demo-student' "
                             "AND course_id = %s", (COURSE_A,))[0][0] == 1


def test_shr01_ac7_seed_is_idempotent_and_does_not_overwrite_passwords(seeded_schema):
    seeded_schema.seed_auth(check=True, **SEED_ENV)
    before = {u: row(seeded_schema, u) for u in ("demo-student", "demo-teacher", "demo-admin")}
    again = seeded_schema.seed_auth(check=True, **SEED_ENV)
    assert again.returncode == 0 and "unchanged" in again.stdout
    changed_env = dict(SEED_ENV, SEED_STUDENT_PASSWORD="a-different-Pw-5555-zz")
    seeded_schema.seed_auth(check=True, **changed_env)  # no --reset-passwords
    after = {u: row(seeded_schema, u) for u in before}
    assert after == before


def test_shr01_ac7_reset_passwords_flag_overwrites_the_hash(seeded_schema):
    seeded_schema.seed_auth(check=True, **SEED_ENV)
    old = row(seeded_schema, "demo-student")[3]
    changed_env = dict(SEED_ENV, SEED_STUDENT_PASSWORD="a-different-Pw-5555-zz")
    seeded_schema.seed_auth("--reset-passwords", check=True, **changed_env)
    new = row(seeded_schema, "demo-student")[3]
    assert new != old and new.startswith("scrypt$")
    assert row(seeded_schema, "demo-teacher")[3].startswith("scrypt$")


def test_shr01_ac7_hashes_are_salted(seeded_schema):
    seeded_schema.seed_auth(check=True, **dict(SEED_ENV, SEED_TEACHER_PASSWORD=SEED_ENV["SEED_STUDENT_PASSWORD"]))
    assert row(seeded_schema, "demo-student")[3] != row(seeded_schema, "demo-teacher")[3]


def test_shr01_ac7_missing_variables_skip_that_role_only(seeded_schema):
    env = {k: v for k, v in SEED_ENV.items() if not k.startswith("SEED_TEACHER")}
    r = seeded_schema.seed_auth(check=True, **env)
    assert r.returncode == 0 and "skipped" in r.stdout
    assert row(seeded_schema, "demo-teacher")[1] is None and row(seeded_schema, "demo-teacher")[3] is None
    assert row(seeded_schema, "demo-student")[3] is not None
    only_email = dict(env, SEED_TEACHER_EMAIL="demo-teacher@learnswe.test")
    r = seeded_schema.seed_auth(check=True, **only_email)
    assert "skipped" in r.stdout and row(seeded_schema, "demo-teacher")[3] is None


@pytest.mark.parametrize("password", ["short", "x" * 129, "1234567890", "demo-teacher@learnswe.test"])
def test_shr01_ac7_password_breaking_the_rules_is_skipped(seeded_schema, password):
    env = dict(SEED_ENV, SEED_TEACHER_PASSWORD=password)
    r = seeded_schema.seed_auth(check=True, **env)
    assert r.returncode == 0 and "skipped" in r.stdout
    assert row(seeded_schema, "demo-teacher")[3] is None
    if password in ("x" * 129, "1234567890"):
        assert password not in r.stdout + r.stderr  # never echo the password
    assert row(seeded_schema, "demo-student")[3] is not None


def test_shr01_ac7_refuses_to_change_the_role_of_an_existing_user(seeded_schema):
    seeded_schema.sql('UPDATE "user" SET role = %s WHERE id = %s', ("teacher", "demo-student"))
    r = seeded_schema.seed_auth(**SEED_ENV)
    assert r.returncode != 0
    uid, email, role, pw_hash, _ = row(seeded_schema, "demo-student")
    assert role == "teacher" and pw_hash is None and email is None


def test_shr01_ac7_refuses_an_email_already_used_by_another_user(seeded_schema):
    seeded_schema.sql('INSERT INTO "user"(id, display_name, role, email) VALUES (%s, %s, %s, %s)',
                      ("someone-else", "Other", "student", SEED_ENV["SEED_STUDENT_EMAIL"]))
    r = seeded_schema.seed_auth(**SEED_ENV)
    assert r.returncode != 0
    assert row(seeded_schema, "demo-student")[3] is None
    assert row(seeded_schema, "someone-else")[1] == SEED_ENV["SEED_STUDENT_EMAIL"]


def test_shr01_ac7_seed_normalises_the_email(seeded_schema):
    env = dict(SEED_ENV, SEED_STUDENT_EMAIL="  Demo-Student@LearnSWE.Test ")
    seeded_schema.seed_auth(check=True, **env)
    assert row(seeded_schema, "demo-student")[1] == "demo-student@learnswe.test"


def test_shr01_ac7_repository_contains_no_real_seed_password():
    example = (BACKEND / ".env.example").read_text(encoding="utf-8")
    for line in example.splitlines():
        if line.startswith("SEED_") and line.split("=")[0].endswith("PASSWORD"):
            assert line.split("=", 1)[1].strip() == "", line
    for key in ("SEED_STUDENT_EMAIL", "SEED_STUDENT_PASSWORD", "SEED_TEACHER_EMAIL", "SEED_TEACHER_PASSWORD",
                "SEED_ADMIN_EMAIL", "SEED_ADMIN_PASSWORD"):
        assert key in example


# ------------------------------------------------------------------ AC24 .env.example and config docs
def test_shr01_ac24_env_example_lists_all_new_variables_without_values_for_secrets():
    example = (BACKEND / ".env.example").read_text(encoding="utf-8")
    for key in ("SESSION_COOKIE_NAME", "SESSION_COOKIE_SECURE", "SESSION_COOKIE_SAMESITE", "SESSION_TTL_SECONDS",
                "ALLOWED_ORIGINS", "TRUST_PROXY_HEADERS", "AUTH_LOGIN_MAX_FAILURES_PER_EMAIL",
                "AUTH_LOGIN_MAX_FAILURES_PER_IP", "AUTH_LOGIN_WINDOW_SECONDS", "AUTH_SIGNUP_MAX_PER_IP",
                "AUTH_SIGNUP_WINDOW_SECONDS"):
        assert key in example, key
    for value in SEED_ENV.values():
        assert value not in example


def test_shr01_ac24_docs_name_the_shared_dependency_and_seed_command():
    guide = (REPO / "docs" / "DeveloperGuide.md").read_text(encoding="utf-8")
    for needle in ("current_user", "require_course_member", "auth.seed"):
        assert needle in guide, needle
    contract = (REPO / "docs" / "SharedDataContract.md").read_text(encoding="utf-8")
    assert "auth_session" in contract and "/api/auth/login" in contract


def test_shr01_ac24_user_guide_describes_sign_in_without_overclaiming():
    guide = (REPO / "docs" / "UserGuide.md").read_text(encoding="utf-8").lower()
    assert "sign in" in guide and "log out" in guide


# ------------------------------------------------------------------ AC24 migration
def test_shr01_ac24_migration_on_a_fresh_schema_adds_only_the_planned_objects(iso):
    # STU-01 adds a later revision, so this test upgrades to the SHR-01 revision explicitly, not 'head'.
    iso.migrate("upgrade", NEW_REVISION)
    assert iso.sql("SELECT version_num FROM alembic_version")[0][0] == NEW_REVISION
    cols = {r[0]: (r[1], r[2]) for r in iso.sql(
        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = 'user'", (iso.schema,))}
    assert cols["email"] == ("character varying", "YES")
    assert cols["password_hash"] == ("character varying", "YES")
    assert {"id", "display_name", "role", "created_at"} <= set(cols)
    sess = {r[0]: r[1] for r in iso.sql(
        "SELECT column_name, is_nullable FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = 'auth_session'", (iso.schema,))}
    assert set(sess) == {"id", "token_hash", "user_id", "csrf_token", "created_at", "expires_at"}
    assert all(v == "NO" for v in sess.values())
    idx = {r[0] for r in iso.sql("SELECT indexname FROM pg_indexes WHERE schemaname = %s", (iso.schema,))}
    assert "ux_user_email" in idx


def test_shr01_ac24_email_constraints_and_session_cascade(seeded_schema):
    s = seeded_schema
    s.sql('INSERT INTO "user"(id, display_name, role, email) VALUES (%s, %s, %s, %s)',
          ("u-" + "a" * 32, "A", "student", "dup@example.com"))
    import psycopg

    with pytest.raises(psycopg.errors.UniqueViolation):
        s.sql('INSERT INTO "user"(id, display_name, role, email) VALUES (%s, %s, %s, %s)',
              ("u-" + "b" * 32, "B", "student", "dup@example.com"))
    with pytest.raises(psycopg.errors.CheckViolation):
        s.sql('INSERT INTO "user"(id, display_name, role, email) VALUES (%s, %s, %s, %s)',
              ("u-" + "c" * 32, "C", "student", "Upper@Example.com"))
    # several users without an email are allowed
    assert s.sql('SELECT count(*) FROM "user" WHERE email IS NULL')[0][0] >= 3
    uid = "u-" + "a" * 32
    s.sql("INSERT INTO auth_session(id, token_hash, user_id, csrf_token, expires_at) "
          "VALUES (%s, %s, %s, 'c', now() + interval '1 hour')", (uuid.uuid4(), "f" * 64, uid))
    with pytest.raises(psycopg.errors.UniqueViolation):
        s.sql("INSERT INTO auth_session(id, token_hash, user_id, csrf_token, expires_at) "
              "VALUES (%s, %s, %s, 'c', now() + interval '1 hour')", (uuid.uuid4(), "f" * 64, uid))
    s.sql('DELETE FROM "user" WHERE id = %s', (uid,))
    assert s.sql("SELECT count(*) FROM auth_session")[0][0] == 0


def test_shr01_ac24_migration_on_a_populated_schema_keeps_rows_and_downgrades_cleanly(iso):
    iso.migrate("upgrade", PREVIOUS_REVISION)
    iso.sql("INSERT INTO course(id, title) VALUES (%s, 'Keep course')", (COURSE_A,))
    iso.sql('INSERT INTO "user"(id, display_name, role) VALUES (\'demo-teacher\', \'Teacher\', \'teacher\')')
    iso.sql('INSERT INTO "user"(id, display_name, role) VALUES (\'demo-student\', \'Student\', \'student\')')
    iso.sql("INSERT INTO course_membership(course_id, user_id) VALUES (%s, 'demo-student')", (COURSE_A,))
    before_users = iso.sql('SELECT id, display_name, role, created_at FROM "user" ORDER BY id')

    iso.migrate("upgrade", NEW_REVISION)
    assert iso.sql('SELECT id, display_name, role, created_at FROM "user" ORDER BY id') == before_users
    assert iso.sql('SELECT email, password_hash FROM "user" WHERE id = \'demo-student\'')[0] == (None, None)
    assert iso.sql("SELECT to_regclass('auth_session')")[0][0] is not None

    iso.migrate("downgrade", PREVIOUS_REVISION)
    assert iso.sql("SELECT version_num FROM alembic_version")[0][0] == PREVIOUS_REVISION
    assert iso.sql("SELECT to_regclass('auth_session')")[0][0] is None
    columns = {r[0] for r in iso.sql("SELECT column_name FROM information_schema.columns "
                                     "WHERE table_schema = %s AND table_name = 'user'", (iso.schema,))}
    assert "email" not in columns and "password_hash" not in columns
    assert {"id", "display_name", "role", "created_at"} <= columns
    assert iso.sql('SELECT id, display_name, role, created_at FROM "user" ORDER BY id') == before_users
    assert iso.sql("SELECT count(*) FROM course_membership")[0][0] == 1
    assert "ux_user_email" not in {r[0] for r in iso.sql(
        "SELECT indexname FROM pg_indexes WHERE schemaname = %s", (iso.schema,))}

    iso.migrate("upgrade", NEW_REVISION)  # re-upgrade works
    assert iso.sql("SELECT version_num FROM alembic_version")[0][0] == NEW_REVISION
    assert iso.sql('SELECT count(*) FROM "user"')[0][0] == 2


def test_shr01_ac24_existing_teacher_users_and_memberships_are_preserved(seeded_schema):
    seeded_schema.seed_auth(check=True, **SEED_ENV)
    assert row(seeded_schema, "demo-teacher-other")[2] == "teacher"
    assert seeded_schema.sql("SELECT count(*) FROM course_membership WHERE user_id = 'demo-teacher' "
                             "AND course_id = %s", (COURSE_A,))[0][0] == 1


def test_shr01_ac24_historical_migrations_are_not_edited():
    versions = BACKEND / "alembic" / "versions"
    assert (versions / f"{NEW_REVISION}.py").exists()
    text = (versions / f"{NEW_REVISION}.py").read_text(encoding="utf-8")
    assert f'down_revision = "{PREVIOUS_REVISION}"' in text
