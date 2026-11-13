"""Fail-closed release startup; also supports explicit locked migrations."""
import logging
import os
from pathlib import Path
import sys
import time
import threading

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from sqlalchemy.engine import make_url

from auth.settings import load_settings

MIGRATION_LOCK_KEY = 3227261001
LOCK_TIMEOUT_SECONDS = 60
BACKEND = Path(__file__).resolve().parents[1]


def migrate(database_url: str) -> None:
    if database_url != load_settings().database_url:
        raise ValueError('migration database must match configured database')
    hostname = make_url(database_url).host or ''
    if hostname.endswith('.neon.tech') and '-pooler.' in hostname:
        raise ValueError('session migration locking requires a direct database endpoint')
    engine = create_engine(database_url, poolclass=NullPool,
                           connect_args={'connect_timeout': 5, 'tcp_user_timeout': 5000,
                                         'options': '-cstatement_timeout=5000'})
    ready = threading.Event()
    permit_migration = threading.Event()
    cancelled = threading.Event()
    finished = threading.Event()
    errors = []
    acquired = []
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS

    def release():
        """The daemon owns the DB connection; the caller enforces the wall-clock bound."""
        try:
            with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
                while not cancelled.is_set():
                    locked = connection.execute(text('SELECT pg_try_advisory_lock(:key)'),
                                                {'key': MIGRATION_LOCK_KEY}).scalar()
                    if locked:
                        try:
                            acquired.append(True)
                            ready.set()
                            permit_migration.wait(max(0, deadline - time.monotonic()))
                            if cancelled.is_set() or time.monotonic() >= deadline:
                                raise RuntimeError('migration lock timeout')
                            config = Config(str(BACKEND / 'alembic.ini'))
                            config.set_main_option('script_location', str(BACKEND / 'alembic'))
                            command.upgrade(config, 'head')
                        finally:
                            connection.execute(text('SELECT pg_advisory_unlock(:key)'),
                                               {'key': MIGRATION_LOCK_KEY})
                        return
                    if time.monotonic() >= deadline:
                        raise RuntimeError('migration lock timeout')
                    cancelled.wait(0.25)
        except Exception as exc:
            errors.append(exc)
        finally:
            ready.set()
            finished.set()

    threading.Thread(target=release, daemon=True, name='release-migration').start()
    try:
        signalled = ready.wait(max(0, deadline - time.monotonic()))
        if not signalled or time.monotonic() >= deadline:
            cancelled.set()
            permit_migration.set()
            raise RuntimeError('migration lock timeout')
        if not acquired:
            raise errors[0] if errors else RuntimeError('migration lock acquisition failed')
        permit_migration.set()
        # Once acquired, migrations may take longer than the lock acquisition deadline.
        finished.wait()
        if errors:
            raise errors[0]
    finally:
        engine.dispose()


def main() -> None:
    try:
        if sys.argv[1:] == ['--migrate-only']:
            migrate(load_settings().database_url)
            return
        if sys.argv[1:]:
            raise ValueError('unsupported startup arguments')
        settings = load_settings()
        port = int(os.environ.get('PORT', '8000'))
        if not 1 <= port <= 65535:
            raise ValueError('invalid port')
        origin_ok = bool(settings.allowed_origins) and all(
            origin.startswith('https://') for origin in settings.allowed_origins)
        build = Path(os.environ.get('FRONTEND_DIST_DIR', ''))
        if (settings.app_env != 'production' or not settings.cookie_secure
                or settings.cookie_samesite != 'lax' or settings.trust_proxy_headers
                or not origin_ok or not (build / 'index.html').is_file()):
            raise ValueError('invalid production settings')
        migrate(settings.database_url)
    except Exception:
        logging.getLogger('deployment').error('Release startup failed; check configuration and migration status.')
        raise SystemExit(1) from None
    os.chdir(BACKEND)
    os.execv(sys.executable, [sys.executable, '-m', 'uvicorn', 'main:app',
                            '--host', '0.0.0.0', '--port', str(port), '--workers', '1',
                            '--no-proxy-headers'])


if __name__ == '__main__':
    main()
