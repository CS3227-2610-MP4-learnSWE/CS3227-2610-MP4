"""Process health only. No database, authentication or application APIs yet."""
from fastapi import FastAPI

app = FastAPI(title="learnSWE Preview API", version="0.1.0")


@app.get('/api/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/health/ready')
def readiness() -> dict[str, str]:
    """Process readiness, not database or AI service readiness."""
    return {'status': 'ready'}
