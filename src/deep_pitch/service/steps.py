"""Extração CRUA de passos do stream do agente — sem personalizar.

O front mostra o que o agente realmente faz (nome do agente + nomes das tools,
como o framework emite), só organizado por profundidade. Funções puras: sem
estado, sem I/O, sem tradução/allow-list.
"""

from __future__ import annotations

from typing import Iterator, NamedTuple

# Tool interna que NÃO é passo: a saída estruturada (response_format) entra como
# uma tool call com o nome do schema — é marshalling do resultado, não trabalho.
_SKIP_TOOLS: frozenset[str] = frozenset({"Prediction"})


class Step(NamedTuple):
    """Um passo cru: qual agente chamou qual tool, e em que profundidade."""

    depth: int  # 0 = agente principal; 1 = dentro de um subagente
    agent: str  # nome do agente que emitiu (ex.: deep-pitch, scout, historian)
    tool: str  # nome cru da tool


def _tool_names(message: object) -> list[str]:
    """Nomes das tools chamadas numa AIMessage (tolerante a obj/dict)."""
    calls = getattr(message, "tool_calls", None)
    if calls is None and isinstance(message, dict):
        calls = message.get("tool_calls")
    names: list[str] = []
    for call in calls or []:
        name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
        if name:
            names.append(name)
    return names


def _agent_name(message: object) -> str:
    """Nome do agente que emitiu a mensagem (AIMessage.name); '' se ausente."""
    name = getattr(message, "name", None)
    if name is None and isinstance(message, dict):
        name = message.get("name")
    return name or ""


def steps_from_update(depth: int, update: dict) -> Iterator[Step]:
    """Extrai Steps crus de um chunk de `updates` (um ou mais nós)."""
    if not isinstance(update, dict):
        return
    for node_update in update.values():
        messages = node_update.get("messages", []) if isinstance(node_update, dict) else []
        for message in messages or []:
            agent = _agent_name(message)
            for tool in _tool_names(message):
                if tool in _SKIP_TOOLS:
                    continue
                yield Step(depth=depth, agent=agent, tool=tool)
