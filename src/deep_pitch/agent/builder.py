"""Monta o Deep Agent: main + subagents scout/historian.

O agente principal planeja, delega aos subagents (prior estatístico + estado ao
vivo), reconcilia e devolve uma `Prediction` estruturada (response_format).
"""

from __future__ import annotations

from deepagents import create_deep_agent

from ..config import configure_environment, get_model
from ..config.settings import Settings, get_settings
from ..domain import Prediction
from ..prompts import load_prompt
from ..subagents import historian_subagent, scout_subagent


def build_agent(settings: Settings | None = None):
    """Constrói o agente compilado. Não faz chamada de rede (só instancia)."""
    settings = settings or get_settings()
    configure_environment(settings)  # exporta chaves p/ os SDKs

    return create_deep_agent(
        model=get_model("main", settings),
        subagents=[scout_subagent(settings), historian_subagent(settings)],
        system_prompt=load_prompt("system"),
        response_format=Prediction,
        name="deep-pitch",
    )
