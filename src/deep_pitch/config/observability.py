"""Exporta chaves da config para os.environ.

Por quê existe: LangChain (init_chat_model, ChatAnthropic, tracing do LangSmith)
lê credenciais de os.environ. Nossa Settings pode vir de um arquivo .env que o
LangChain não conhece. Esta função faz a ponte — chamada uma vez no startup do
agente/app, antes de construir o modelo.
"""

from __future__ import annotations

import os

from .settings import Settings, get_settings

_PROVIDER_ENV = {
    "ANTHROPIC_API_KEY": "anthropic_api_key",
    "GOOGLE_API_KEY": "google_api_key",
    "GROQ_API_KEY": "groq_api_key",
    "OPENROUTER_API_KEY": "openrouter_api_key",
    "NVIDIA_API_KEY": "nvidia_api_key",
    "TAVILY_API_KEY": "tavily_api_key",
    "FOOTBALL_DATA_API_KEY": "football_data_api_key",
}


def configure_environment(settings: Settings | None = None) -> None:
    """Escreve as chaves presentes na Settings em os.environ."""
    settings = settings or get_settings()

    for env_name, field in _PROVIDER_ENV.items():
        value = getattr(settings, field)
        if value:
            os.environ[env_name] = value

    # LangSmith: só liga o tracing se houver key.
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_TRACING"] = "true" if settings.langsmith_tracing else "false"
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    else:
        # Sem key: força tracing OFF. Senão um LANGSMITH_TRACING=true herdado do
        # .env/shell ligaria o tracer sem key → 401/403 a cada chamada de LLM.
        os.environ["LANGSMITH_TRACING"] = "false"
