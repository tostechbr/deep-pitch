"""Busca web qualitativa — o que o subagent scout usa p/ lesão, forma,
escalação e notícia recente (o que o dado estruturado não captura).

Backend: Tavily se TAVILY_API_KEY estiver setada (melhor p/ agente), senão
DuckDuckGo via `ddgs` (keyless — roda out-of-the-box). Se o Tavily falhar,
cai pro DDG. Erros de busca degradam para mensagem, não derrubam o agente.
"""

from __future__ import annotations

import concurrent.futures

from langchain.tools import tool

from ..config.settings import Settings, get_settings

_MAX_SNIPPET = 240
# Parede dura: uma busca NUNCA segura o agente. Do IP de datacenter (ex.: HF Space)
# o DDG costuma pendurar/tentar vários backends; sem isto o run trava no scout.
_SEARCH_WALL_SECONDS = 10.0


def _ddg_search(query: str, max_results: int) -> list[dict[str, str]]:
    from ddgs import DDGS

    with DDGS() as ddgs:
        raw = list(ddgs.text(query, max_results=max_results))
    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
        for r in raw
    ]


def _tavily_search(query: str, max_results: int, api_key: str) -> list[dict[str, str]]:
    from langchain_tavily import TavilySearch

    result = TavilySearch(max_results=max_results, tavily_api_key=api_key).invoke({"query": query})
    items = result.get("results", []) if isinstance(result, dict) else []
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
        for r in items
    ]


def _search(query: str, max_results: int, settings: Settings) -> list[dict[str, str]]:
    """Busca pelo melhor backend disponível, com fallback pro DDG."""
    if settings.tavily_api_key:
        try:
            return _tavily_search(query, max_results, settings.tavily_api_key)
        except Exception:
            pass  # Tavily falhou → tenta DDG
    return _ddg_search(query, max_results)


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Busca na web por contexto qualitativo (lesões, forma, escalação, notícia).

    Use para o que o dado estruturado não tem: quem está lesionado/suspenso,
    momento do time, provável escalação, clima do confronto. Retorne queries
    específicas (ex.: 'England injuries squad news July 2026').
    """
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_search, query, max_results, get_settings())
            results = future.result(timeout=_SEARCH_WALL_SECONDS)
    except concurrent.futures.TimeoutError:
        return (
            f"Busca demorou demais (>{_SEARCH_WALL_SECONDS:.0f}s) e foi abortada — provável "
            "bloqueio do provedor de busca a partir deste servidor. Prossiga sem ela."
        )
    except Exception as exc:  # rate limit, rede, etc.
        return f"Busca indisponível no momento ({type(exc).__name__}). Tente reformular ou prossiga sem ela."

    if not results:
        return f"Sem resultados para: {query!r}"

    blocks = []
    for i, r in enumerate(results, 1):
        snippet = (r["snippet"] or "")[:_MAX_SNIPPET]
        blocks.append(f"[{i}] {r['title']}\n    {r['url']}\n    {snippet}")
    return "\n".join(blocks)
