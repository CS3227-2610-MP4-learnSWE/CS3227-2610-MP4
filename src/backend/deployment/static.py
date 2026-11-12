"""Serve public build artifacts without turning API failures into HTML."""
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request
from starlette.responses import FileResponse
from starlette.routing import Match


def attach_frontend(app: FastAPI, directory: Path) -> None:
    root = directory.resolve()

    @app.api_route('/{path:path}', methods=['GET', 'HEAD'], include_in_schema=False)
    def frontend(request: Request, path: str):
        decoded = unquote(path)
        parts = decoded.replace('\\', '/').split('/')
        if parts[0] == 'api':
            for route in app.router.routes:
                match, _ = route.matches(request.scope)
                if match == Match.PARTIAL:
                    methods = getattr(route, 'methods', None) or set()
                    raise HTTPException(405, 'Method Not Allowed', headers={'Allow': ', '.join(sorted(methods))})
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
