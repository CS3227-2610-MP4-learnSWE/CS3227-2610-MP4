FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN npm ci
COPY src/frontend/ ./
ENV VITE_ENABLE_DEMO_ACCESS=false
RUN npm run build

FROM python:3.12-slim-bookworm AS backend
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv
WORKDIR /app/backend
COPY src/backend/pyproject.toml src/backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY src/backend/ ./
COPY --from=frontend /build/dist /app/frontend-dist
RUN useradd --uid 10001 --create-home app
ENV PATH="/app/backend/.venv/bin:$PATH" \
    APP_ENV=production \
    SESSION_COOKIE_SECURE=true \
    SESSION_COOKIE_SAMESITE=lax \
    TRUST_PROXY_HEADERS=false \
    FRONTEND_DIST_DIR=/app/frontend-dist \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
USER 10001
EXPOSE 8000
CMD ["python", "-m", "deployment.start"]
