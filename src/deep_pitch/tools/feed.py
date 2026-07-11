"""Feed ao vivo da Copa 2026 (football-data.org v4) — o que o scout usa p/ o
estado atual do torneio: últimos resultados e próximo jogo de um time.

Precisa de FOOTBALL_DATA_API_KEY (registro grátis, free tier cobre a Copa 2026,
10 req/min). Sem token, degrada com mensagem — o scout recorre à busca web e o
agente segue funcionando.
"""

from __future__ import annotations

import httpx
from langchain.tools import tool

from ..config.settings import Settings, get_settings

_BASE = "https://api.football-data.org/v4"
_RECENT = 3  # quantos resultados recentes mostrar


def _fetch_matches(settings: Settings) -> list[dict]:
    headers = {"X-Auth-Token": settings.football_data_api_key or ""}
    url = f"{_BASE}/competitions/{settings.football_data_competition}/matches"
    resp = httpx.get(url, headers=headers, timeout=settings.request_timeout)
    resp.raise_for_status()
    return resp.json().get("matches", [])


def _involves(match: dict, team: str) -> bool:
    names = (match.get("homeTeam", {}).get("name", ""), match.get("awayTeam", {}).get("name", ""))
    return any(team.lower() in (n or "").lower() for n in names)


def _format_match(match: dict) -> str:
    date = (match.get("utcDate") or "")[:10]
    stage = (match.get("stage") or "").replace("_", " ").title()
    home = match.get("homeTeam", {}).get("name", "?")
    away = match.get("awayTeam", {}).get("name", "?")
    if match.get("status") == "FINISHED":
        ft = match.get("score", {}).get("fullTime", {})
        return f"  {date} [{stage}] {home} {ft.get('home')}-{ft.get('away')} {away}"
    return f"  {date} [{stage}] {home} vs {away} (agendado)"


def _feed_for_team(matches: list[dict], team: str) -> str:
    involved = [m for m in matches if _involves(m, team)]
    if not involved:
        return f"{team} não encontrado nos jogos da Copa 2026 (confira o nome em inglês)."

    finished = [m for m in involved if m.get("status") == "FINISHED"]
    upcoming = [m for m in involved if m.get("status") != "FINISHED"]
    finished.sort(key=lambda m: m.get("utcDate") or "")
    upcoming.sort(key=lambda m: m.get("utcDate") or "")

    lines = [f"{team} na Copa 2026 (football-data.org):"]
    if finished:
        lines.append("Últimos resultados:")
        lines += [_format_match(m) for m in finished[-_RECENT:]]
    if upcoming:
        lines.append("Próximo:")
        lines.append(_format_match(upcoming[0]))
    return "\n".join(lines)


def live_feed_for(team: str, settings: Settings | None = None) -> str:
    """Núcleo testável: estado do time na Copa (ou mensagem de degradação)."""
    settings = settings or get_settings()
    if not settings.football_data_api_key:
        return (
            "Feed ao vivo indisponível (FOOTBALL_DATA_API_KEY não setada). "
            "Registre grátis em football-data.org, ou use web_search para o estado atual."
        )
    try:
        matches = _fetch_matches(settings)
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code == 429:
            return "Feed ao vivo: rate limit (free = 10 req/min). Aguarde ou use web_search."
        return f"Feed ao vivo indisponível (HTTP {code}). Use web_search."
    except httpx.HTTPError as exc:
        return f"Feed ao vivo indisponível (rede: {type(exc).__name__}). Use web_search."

    return _feed_for_team(matches, team)


@tool
def live_feed(team: str) -> str:
    """Estado ao vivo de um time na Copa 2026: últimos resultados e próximo jogo.

    Fonte: football-data.org (dado estruturado do torneio). Use o nome do país
    em inglês (ex.: 'England'). Complementa a busca web com fatos do bracket.
    """
    return live_feed_for(team)
