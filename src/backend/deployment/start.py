"""Fail-closed release startup; also supports explicit locked migrations."""
import logging
import os
from pathlib import Path
import sys
import time

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from auth.settings import load_settings

MIGRATION_LOCK_KEY = 3227261001
LOCK_TIMEOUT_SECONDS = 60
BACKEND = Path(__file__).resolve().parents[1]


def migrate(database_url: str) -> None:
    if database_url != load_settings().database_url:
        raise ValueError('migration database must match configured database')
    engine = create_engine(database_url, poolclass=NullPool,
                           connect_args={'connect_timeout': 5})
    try:
        with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
            deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
            while not connection.execute(text('SELECT pg_try_advisory_lock(:key)'),
                                         {'key': MIGRATION_LOCK_KEY}).scalar():
                if time.monotonic() >= deadline:
                    raise RuntimeError('migration lock timeout')
                time.sleep(0.25)
            try:
                config = Config(str(BACKEND / 'alembic.ini'))
                config.set_main_option('script_location', str(BACKEND / 'alembic'))
                command.upgrade(config, 'head')
            finally:
                connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': MIGRATION_LOCK_KEY})
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
