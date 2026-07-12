"""Orquestração transport-agnostic: recebe um MatchRequest, roda o agente,
devolve uma Prediction. CLI e API (Etapa 5) chamam isto — sem saber de HTTP.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Iterator, NamedTuple

from ..agent import build_agent
from ..config.settings import Settings
from ..domain import MatchRequest, Prediction
from .steps import steps_from_update


class StreamEvent(NamedTuple):
    """Evento do stream: um passo CRU do agente OU o resultado final.

    Passo: (depth, agent, tool) direto do framework — sem personalizar. O front
    organiza (indenta por depth, agrupa por agente). Result: a Prediction final.
    """

    kind: str  # "step" | "result"
    depth: int = 0
    agent: str = ""
    tool: str = ""
    prediction: Prediction | None = None


def _unpack_stream_item(item) -> tuple[tuple, str, object]:
    """Normaliza o item do stream para (ns, mode, data).

    Com `subgraphs=True` + lista de modes o LangGraph emite (ns, mode, data).
    Formas defensivas: 2-tupla pode ser (mode, data) [sem subgraph] ou (ns, data)
    [subgraph + modo único].
    """
    if isinstance(item, tuple):
        if len(item) == 3:
            return item
        if len(item) == 2:
            first, second = item
            if isinstance(first, str):  # (mode, data)
                return (), first, second
            if isinstance(first, tuple):  # (ns, data) — modo único
                return first, "updates", second
    return (), "updates", item


@lru_cache
def _default_agent():
    """Agente padrão (key do servidor), construído 1× por processo."""
    return build_agent()


def _build_content(request: MatchRequest) -> str:
    """Monta o prompt do confronto (compartilhado por invoke e stream)."""
    content = (
        f"Preveja o confronto de mata-mata da Copa 2026: {request.home} (mandante) "
        f"vs {request.away} (visitante). Sede neutra: {request.neutral}."
    )
    if request.context:
        content += f" Contexto: {request.context}."
    return content


def _config(callbacks: list | None) -> dict:
    config: dict = {"configurable": {"thread_id": f"predict-{uuid.uuid4().hex[:8]}"}}
    if callbacks:
        config["callbacks"] = callbacks
    return config


def run_prediction(
    request: MatchRequest,
    settings: Settings | None = None,
    callbacks: list | None = None,
) -> Prediction:
    """Roda o Deep Agent para o confronto e retorna a previsão estruturada.

    Se `settings` for dado (BYOK: provider + key do usuário), constrói um agente
    FRESCO com ela — sem cache, sem estado partilhado entre usuários. Senão usa
    o agente padrão do servidor. `callbacks` (ex.: tracer LangSmith do usuário)
    entram só neste invoke — por-request, sem estado global.
    """
    agent = build_agent(settings) if settings is not None else _default_agent()
    content = _build_content(request)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": content}]}, config=_config(callbacks)
    )
    prediction = result.get("structured_response")
    if prediction is None:
        raise RuntimeError("O agente não retornou uma Prediction estruturada.")
    return prediction


def stream_prediction(
    request: MatchRequest,
    settings: Settings | None = None,
    callbacks: list | None = None,
) -> Iterator[StreamEvent]:
    """Igual a `run_prediction`, mas emite os passos do agente em tempo real.

    Gera `StreamEvent(kind="step", depth, agent, tool)` conforme o agente e os
    subagentes chamam cada tool (nomes CRUS, do framework) e, no fim,
    `StreamEvent(kind="result", prediction=...)`. Usa `subgraphs=True` p/ enxergar os
    passos internos dos subagentes (scout/historian), e `stream_mode=["updates",
    "values"]`: `updates` traz as chamadas à medida que acontecem; `values` carrega o
    estado — o último tem a saída estruturada. Mesma segurança BYOK do invoke (nada
    global; callbacks por-request).
    """
    agent = build_agent(settings) if settings is not None else _default_agent()
    content = _build_content(request)

    final_pred: Prediction | None = None
    for item in agent.stream(
        {"messages": [{"role": "user", "content": content}]},
        config=_config(callbacks),
        stream_mode=["updates", "values"],
        subgraphs=True,
    ):
        ns, mode, data = _unpack_stream_item(item)
        if mode == "values":
            if isinstance(data, dict) and data.get("structured_response") is not None:
                final_pred = data["structured_response"]
            continue
        for step in steps_from_update(len(ns), data):
            yield StreamEvent(kind="step", depth=step.depth, agent=step.agent, tool=step.tool)

    if final_pred is None:
        raise RuntimeError("O agente não retornou uma Prediction estruturada.")
    yield StreamEvent(kind="result", prediction=final_pred)
