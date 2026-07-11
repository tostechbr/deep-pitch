"""Subagent historian — prior estatístico + histórico."""

from __future__ import annotations

from deepagents.middleware.subagents import SubAgent

from ..config import get_model
from ..config.settings import Settings, get_settings
from ..prompts import load_prompt
from ..tools import baseline_prediction, head_to_head


def historian_subagent(settings: Settings | None = None) -> SubAgent:
    settings = settings or get_settings()
    return {
        "name": "historian",
        "description": (
            "Fornece o prior estatístico defensável de um confronto: "
            "probabilidades Dixon-Coles + retrospecto de confrontos diretos."
        ),
        "system_prompt": load_prompt("historian"),
        "tools": [baseline_prediction, head_to_head],
        "model": get_model("subagent", settings),
    }
