"""A bounded database probe, with at most one outstanding probe per process."""
import threading

from sqlalchemy import text
from starlette.responses import JSONResponse

from auth.db import engine_for
from auth.settings import load_settings

_probe_lock = threading.Lock()
DATABASE_TIMEOUT_SECONDS = 5


def database_health() -> dict[str, str]:
    """Never let a slow database consume unbounded health-check threads."""
    if not _probe_lock.acquire(blocking=False):
        return JSONResponse({'status': 'unavailable'}, status_code=503)
    finished = threading.Event()
    ready = []

    def probe():
        try:
            with engine_for(load_settings().database_url).connect() as connection:
                connection.execute(text('SELECT 1'))
            ready.append(True)
        except Exception:
            pass  # Public health responses never contain driver/configuration errors.
        finally:
            _probe_lock.release()
            finished.set()

    threading.Thread(target=probe, daemon=True, name='database-health').start()
    finished.wait(DATABASE_TIMEOUT_SECONDS)
    if not ready:
        return JSONResponse({'status': 'unavailable'}, status_code=503)
    return {'status': 'ready'}
