"""Subagent scout — estado ao vivo + contexto qualitativo."""

from __future__ import annotations

from deepagents.middleware.subagents import SubAgent

from ..config import get_model
from ..config.settings import Settings, get_settings
from ..prompts import load_prompt
from ..tools import live_feed, web_search


def scout_subagent(settings: Settings | None = None) -> SubAgent:
    settings = settings or get_settings()
    return {
        "name": "scout",
        "description": (
            "Levanta o estado ATUAL de um confronto: forma recente, lesões, "
            "suspensões, provável escalação e notícia. Delegue os dois times."
        ),
        "system_prompt": load_prompt("scout"),
        "tools": [web_search, live_feed],
        "model": get_model("subagent", settings),
    }
