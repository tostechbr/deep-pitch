"""Tracer LangSmith POR-REQUEST (BYOK) — sem tocar em os.environ.

Se o usuário trouxer a própria LangSmith key, o trace daquela previsão vai para
o dashboard DELE. A key vai num Client dedicado passado como callback só naquele
invoke — nunca em os.environ (que vazaria entre usuários no servidor).
"""

from __future__ import annotations

from typing import Any


def build_tracer(api_key: str | None, project: str = "deep-pitch") -> Any | None:
    """LangChainTracer apontando pro LangSmith do usuário, ou None se sem key."""
    if not api_key:
        return None
    from langchain_core.tracers import LangChainTracer
    from langsmith import Client

    return LangChainTracer(client=Client(api_key=api_key), project_name=project or "deep-pitch")
