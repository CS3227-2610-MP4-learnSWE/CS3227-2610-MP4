"""App wiring: health, in-memory student practice, and PostgreSQL teacher materials. No real authentication yet."""
from fastapi import FastAPI

import practice_routes
from teacher_materials.routes import router as teacher_router
from errors import ApiError

app = FastAPI(title="learnSWE Preview API", version="0.1.0")
app.include_router(practice_routes.router)
app.include_router(teacher_router)
app.add_exception_handler(ApiError, practice_routes.error_response)


@app.get('/api/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/health/ready')
def readiness() -> dict[str, str]:
    """Process readiness, not database or AI service readiness."""
    return {'status': 'ready'}
