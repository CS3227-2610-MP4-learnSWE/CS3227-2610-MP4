"""Serve public build artifacts without turning API failures into HTML."""
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request
from fastapi.routing import APIRoute
from starlette.responses import FileResponse
from starlette.routing import Match


class FrontendRoute(APIRoute):
    """Leave API matching and slash redirects entirely to the existing router."""

    def matches(self, scope):
        path = unquote(scope.get('path', '')).replace('\\', '/').lstrip('/')
        if path == 'api' or path.startswith('api/'):
            return Match.NONE, {}
        return super().matches(scope)


def attach_frontend(app: FastAPI, directory: Path) -> None:
    root = directory.resolve()

    def frontend(request: Request, path: str):
        decoded = unquote(path)
        parts = decoded.replace('\\', '/').split('/')
        if parts[0] == 'api':
            raise HTTPException(404, 'Not Found')
        if any(part in ('.', '..') for part in parts):
            raise HTTPException(404, 'Not Found')
        candidate = (root / decoded).resolve()
        if not candidate.is_relative_to(root):
            raise HTTPException(404, 'Not Found')
        if candidate.is_file():
            return FileResponse(candidate)
        accepts = request.headers.get('accept', '')
        html = 'text/html' in accepts or (not decoded and '*/*' in accepts)
        if (parts[0] == 'assets' or any('.' in part for part in parts)
                or not html or not (root / 'index.html').is_file()):
            raise HTTPException(404, 'Not Found')
        return FileResponse(root / 'index.html', headers={'Cache-Control': 'no-cache'})

    app.router.add_api_route('/{path:path}', frontend, methods=['GET', 'HEAD'],
                             include_in_schema=False, route_class_override=FrontendRoute)
