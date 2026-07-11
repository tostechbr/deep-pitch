"""App FastAPI do deep-pitch. Um consumidor do core, como o CLI."""

from __future__ import annotations

from fastapi import FastAPI

from .routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="deep-pitch",
        description="Deep Agent que prevê mata-matas da Copa 2026 "
        "(modelo estatístico + dados ao vivo + contexto qualitativo).",
        version="0.1.0",
    )
    app.include_router(router)
    return app


app = create_app()
