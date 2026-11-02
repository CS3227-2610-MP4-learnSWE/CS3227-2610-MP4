"""Health, student practice/companion and persistent teacher materials; no real authentication."""
from fastapi import FastAPI

import companion_routes
import practice_routes
from teacher_materials.routes import router as teacher_router
from teacher_notes.routes import router as teacher_notes_router
from teacher_mcqs.routes import router as teacher_mcqs_router
from errors import ApiError

app = FastAPI(title="learnSWE Preview API", version="0.1.0")
app.include_router(practice_routes.router)
app.include_router(teacher_router)
app.include_router(teacher_notes_router)
app.include_router(teacher_mcqs_router)
app.include_router(companion_routes.router)
app.add_exception_handler(ApiError, practice_routes.error_response)


@app.get('/api/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/health/ready')
def readiness() -> dict[str, str]:
    """Process readiness, not database or AI service readiness."""
    return {'status': 'ready'}
