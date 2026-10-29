"""Health endpoints plus the STU-02 practice attempt API (in-memory, placeholder identity)."""
from fastapi import FastAPI

from practice_routes import router as practice_router

app = FastAPI(title="learnSWE Preview API", version="0.1.0")
app.include_router(practice_router)


@app.get('/api/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/health/ready')
def readiness() -> dict[str, str]:
    """Process readiness, not database or AI service readiness."""
    return {'status': 'ready'}
