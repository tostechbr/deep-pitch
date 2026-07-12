"""Orquestração transport-agnostic: recebe um MatchRequest, roda o agente,
devolve uma Prediction. CLI e API (Etapa 5) chamam isto — sem saber de HTTP.
"""

from __future__ import annotations

import uuid
from functools import lru_cache

from ..agent import build_agent
from ..config.settings import Settings
from ..domain import MatchRequest, Prediction


@lru_cache
def _default_agent():
    """Agente padrão (key do servidor), construído 1× por processo."""
    return build_agent()


def run_prediction(request: MatchRequest, settings: Settings | None = None) -> Prediction:
    """Roda o Deep Agent para o confronto e retorna a previsão estruturada.

    Se `settings` for dado (BYOK: provider + key do usuário), constrói um agente
    FRESCO com ela — sem cache, sem estado partilhado entre usuários. Senão usa
    o agente padrão do servidor.
    """
    agent = build_agent(settings) if settings is not None else _default_agent()
    content = (
        f"Preveja o confronto de mata-mata da Copa 2026: {request.home} (mandante) "
        f"vs {request.away} (visitante). Sede neutra: {request.neutral}."
    )
    if request.context:
        content += f" Contexto: {request.context}."

    result = agent.invoke(
        {"messages": [{"role": "user", "content": content}]},
        config={"configurable": {"thread_id": f"predict-{uuid.uuid4().hex[:8]}"}},
    )
    prediction = result.get("structured_response")
    if prediction is None:
        raise RuntimeError("O agente não retornou uma Prediction estruturada.")
    return prediction
