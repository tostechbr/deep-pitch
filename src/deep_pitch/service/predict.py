"""Orquestração transport-agnostic: recebe um MatchRequest, roda o agente,
devolve uma Prediction. CLI e API (Etapa 5) chamam isto — sem saber de HTTP.
"""

from __future__ import annotations

import uuid
from functools import lru_cache

from ..agent import build_agent
from ..domain import MatchRequest, Prediction


@lru_cache
def _agent():
    """Constrói o agente uma vez por processo (a construção não chama a rede)."""
    return build_agent()


def run_prediction(request: MatchRequest) -> Prediction:
    """Roda o Deep Agent para o confronto e retorna a previsão estruturada."""
    content = (
        f"Preveja o confronto de mata-mata da Copa 2026: {request.home} (mandante) "
        f"vs {request.away} (visitante). Sede neutra: {request.neutral}."
    )
    if request.context:
        content += f" Contexto: {request.context}."

    result = _agent().invoke(
        {"messages": [{"role": "user", "content": content}]},
        config={"configurable": {"thread_id": f"predict-{uuid.uuid4().hex[:8]}"}},
    )
    prediction = result.get("structured_response")
    if prediction is None:
        raise RuntimeError("O agente não retornou uma Prediction estruturada.")
    return prediction
