"""Grafo compilado para o `langgraph.json` (langgraph dev / Studio / deploy).

Import deste módulo constrói o agente — requer um provider de LLM configurado.
"""

from .builder import build_agent

graph = build_agent()
