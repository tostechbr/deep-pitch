"""Fixtures compartilhadas: ambiente hermético + factory de Settings.

Testes NÃO devem herdar chaves do shell nem do .env. `clean_env` remove nossas
env vars antes de cada teste; `make_settings` cria Settings ignorando o .env
(`_env_file=None`), então cada teste declara só o que precisa.
"""

from __future__ import annotations

import pytest

from deep_pitch.config.settings import Settings

_OUR_ENV = [
    "MODEL_PROVIDER", "MODEL_NAME",
    "MAIN_PROVIDER", "MAIN_MODEL_NAME", "SUBAGENT_PROVIDER", "SUBAGENT_MODEL_NAME",
    "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY",
    "TAVILY_API_KEY", "FOOTBALL_DATA_API_KEY",
    "LANGSMITH_API_KEY", "LANGSMITH_TRACING", "LANGSMITH_PROJECT",
    "FREE_CHAIN",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Remove nossas env vars para isolar cada teste do shell/.env."""
    for key in _OUR_ENV:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def make_settings():
    """Factory de Settings que ignora o .env (hermético)."""
    def _make(**overrides) -> Settings:
        return Settings(_env_file=None, **overrides)

    return _make
