"""
Aplicación FastAPI del asistente.
"""

from __future__ import annotations

from fastapi import FastAPI

from asistente import __version__
from asistente.api.routes import query

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Asistente personal",
        version=__version__,
        description=(
            "Entrada única: GET `/query?message=...`. "
            "Clima, hora y respuestas se resuelven en el servidor."
        ),
    )

    app.include_router(query.router, prefix=API_PREFIX)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
