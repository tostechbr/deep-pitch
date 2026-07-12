"""Configura o tracing do LangSmith via os.environ.

Por quê existe: o LangSmith lê LANGSMITH_* de os.environ. As chaves de PROVIDER
de LLM NÃO passam por aqui — elas vão direto no construtor do modelo (api_key=),
por request, para não vazar entre usuários num servidor (ver config/models.py).
"""

from __future__ import annotations

import os

from .settings import Settings, get_settings


def configure_environment(settings: Settings | None = None) -> None:
    """Liga/desliga o tracing do LangSmith conforme a Settings."""
    settings = settings or get_settings()

    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_TRACING"] = "true" if settings.langsmith_tracing else "false"
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    else:
        # Sem key: força OFF. Senão um LANGSMITH_TRACING=true herdado ligaria o
        # tracer sem credencial → 401/403 a cada chamada de LLM.
        os.environ["LANGSMITH_TRACING"] = "false"
