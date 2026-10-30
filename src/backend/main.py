"""App wiring: health endpoints, the practice attempt API and the study companion. No database or real authentication yet."""
from fastapi import FastAPI

import companion_routes
import practice_routes
from errors import ApiError

app = FastAPI(title="learnSWE Preview API", version="0.1.0")
app.include_router(practice_routes.router)
app.include_router(companion_routes.router)
app.add_exception_handler(ApiError, practice_routes.error_response)


@app.get('/api/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/health/ready')
def readiness() -> dict[str, str]:
    """Process readiness, not database or AI service readiness."""
    return {'status': 'ready'}
