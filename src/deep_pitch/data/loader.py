"""Carrega o dataset martj42 (resultados de seleções, CC0) com cache local.

Fonte: https://github.com/martj42/international_results — CSV com todo jogo de
seleção masculina desde 1872, atualizado diariamente, JÁ inclui a Copa 2026
(jogos disputados + fixtures pendentes com placar vazio).

Estratégia de cache: baixa 1× por TTL (default 12h). Se a rede cair mas houver
cache (mesmo velho), usa o cache — melhor dado velho que agente morto.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
import pandas as pd

from ..config.settings import Settings, get_settings

# Colunas que o CSV do martj42 precisa ter (validação de fronteira).
_REQUIRED_COLUMNS = {
    "date",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "tournament",
    "city",
    "country",
    "neutral",
}

_WORLD_CUP = "FIFA World Cup"
_WC2026_FROM = pd.Timestamp("2026-06-01")  # início da Copa 2026


def _cache_path(settings: Settings) -> Path:
    return settings.cache_dir / "international_results.csv"


def _is_fresh(path: Path, ttl_hours: int) -> bool:
    if not path.exists():
        return False
    age_seconds = time.time() - path.stat().st_mtime
    return age_seconds < ttl_hours * 3600


def _download(settings: Settings, dest: Path) -> None:
    """Baixa o CSV e grava ATOMICAMENTE (temp + os.replace).

    Atômico de propósito: nunca trunca o cache bom antes de ter o novo em mãos.
    Se o download vier vazio ou sem o header esperado, NÃO substitui — melhor
    manter o cache atual que gravar lixo (ex.: HTTP 200 com página de erro).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = httpx.get(settings.results_url, timeout=settings.request_timeout, follow_redirects=True)
    resp.raise_for_status()
    text = resp.text
    first_line = text.splitlines()[0] if text.strip() else ""
    if "home_team" not in first_line:
        raise RuntimeError("Download do martj42 veio vazio/inesperado — mantendo cache atual.")
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, dest)  # rename atômico na mesma pasta: cache bom intacto até aqui


def load_results(settings: Settings | None = None, *, force_refresh: bool = False) -> pd.DataFrame:
    """DataFrame completo de resultados (disputados + fixtures pendentes).

    Usa cache se fresco; senão baixa. Se o download falhar mas houver cache
    velho, usa o cache (degradação graciosa).
    """
    settings = settings or get_settings()
    path = _cache_path(settings)

    if force_refresh or not _is_fresh(path, settings.cache_ttl_hours):
        try:
            _download(settings, path)
        except (httpx.HTTPError, OSError, RuntimeError) as exc:
            if not path.exists():
                raise RuntimeError(
                    f"Falha ao baixar {settings.results_url} e não há cache local: {exc}"
                ) from exc
            # download falhou/veio ruim, mas há cache válido → segue com ele.

    df = pd.read_csv(path)

    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV do martj42 sem colunas esperadas: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")
    return df


def played_matches(df: pd.DataFrame) -> pd.DataFrame:
    """Só jogos com placar (disputados) — o que treina o baseline."""
    mask = df["home_score"].notna() & df["away_score"].notna()
    return df[mask].copy()


def wc2026_fixtures(df: pd.DataFrame) -> pd.DataFrame:
    """Fixtures da Copa 2026 ainda NÃO disputados (placar vazio)."""
    mask = (
        (df["tournament"] == _WORLD_CUP)
        & (df["date"] >= _WC2026_FROM)
        & (df["home_score"].isna() | df["away_score"].isna())
    )
    return df[mask].copy()


def wc2026_played(df: pd.DataFrame) -> pd.DataFrame:
    """Jogos da Copa 2026 já DISPUTADOS (placar preenchido) — usado no backtest."""
    mask = (
        (df["tournament"] == _WORLD_CUP)
        & (df["date"] >= _WC2026_FROM)
        & df["home_score"].notna()
        & df["away_score"].notna()
    )
    return df[mask].copy()
