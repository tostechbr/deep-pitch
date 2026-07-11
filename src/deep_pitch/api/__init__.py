"""Camada HTTP (FastAPI) — consome o mesmo core que o CLI."""

from .main import app, create_app

__all__ = ["app", "create_app"]
