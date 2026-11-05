"""Health, session-authenticated student and teacher APIs, and shared authentication."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

import companion_routes
import practice_routes
import progress_routes
from auth.routes import add_no_store, router as auth_router
from auth.settings import AuthSettings
from study_lessons.routes import router as study_router
from teacher_materials.routes import router as teacher_router
from teacher_notes.routes import router as teacher_notes_router
from teacher_mcqs.routes import router as teacher_mcqs_router
from teacher_publications.routes import router as publications_router
from errors import ApiError

app = FastAPI(title="learnSWE Preview API", version="0.1.0")
app.include_router(auth_router)
app.include_router(practice_routes.router)
app.include_router(teacher_router)
app.include_router(teacher_notes_router)
app.include_router(teacher_mcqs_router)
app.include_router(companion_routes.router)
app.include_router(study_router)
app.include_router(progress_routes.router)
app.include_router(publications_router)
app.add_exception_handler(ApiError, practice_routes.error_response)
app.middleware("http")(add_no_store)


@app.exception_handler(SQLAlchemyError)
def database_unavailable(request: Request, _: SQLAlchemyError):
    """Database failures answer a fixed 503: no SQL or paths, and no unauthenticated fallback."""
    return practice_routes.error_response(request, ApiError(503, "service_unavailable", "The service is unavailable."))


# Credentialed CORS only for explicitly listed origins; never a wildcard.
_origins = list(AuthSettings.load().allowed_origins)
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )


@app.get('/api/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/health/ready')
def readiness() -> dict[str, str]:
    """Process readiness, not database or AI service readiness."""
    return {'status': 'ready'}
