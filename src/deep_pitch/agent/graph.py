"""Grafo compilado para o `langgraph.json` (langgraph dev / Studio / deploy).

Import deste módulo constrói o agente — requer um provider de LLM configurado.
"""

# Import absoluto (não relativo): o langgraph dev carrega este arquivo pelo
# caminho, fora do pacote — import relativo quebraria.
from deep_pitch.agent.builder import build_agent

graph = build_agent()
