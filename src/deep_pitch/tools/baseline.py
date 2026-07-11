"""Baseline estatístico — o "modelo pequeno" que o subagent historian consulta.

Ajusta um modelo Dixon-Coles (Poisson bivariado com correção de placares baixos)
sobre os resultados recentes de seleções (martj42), com decaimento temporal
(jogo antigo pesa menos). Devolve P(vitória mandante / empate / vitória
visitante), gols esperados e placar mais provável.

Por quê Dixon-Coles: é o padrão-ouro para prever placares de futebol a partir de
força ofensiva/defensiva por time; o time-decay mantém o prior atual sem jogar
fora o histórico. É determinístico e defensável — o oposto de "LLM chutando".
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
import pandas as pd
import penaltyblog as pb
from langchain.tools import tool

from ..config.settings import Settings, get_settings
from ..data import load_results, played_matches

_MAX_GOALS = 10  # tamanho da grade de placares (10x10 cobre a cauda com folga)


class UnknownTeamError(ValueError):
    """Time não encontrado no histórico de treino (nome fora do padrão martj42)."""

    def __init__(self, name: str, suggestions: list[str]):
        self.name = name
        self.suggestions = suggestions
        hint = f" Você quis dizer: {', '.join(suggestions)}?" if suggestions else ""
        super().__init__(f"Time '{name}' não está no histórico de treino.{hint}")


@dataclass(frozen=True)
class BaselineResult:
    home: str
    away: str
    p_home: float
    p_draw: float
    p_away: float
    xg_home: float
    xg_away: float
    likely_home_goals: int
    likely_away_goals: int
    n_train: int
    since_year: int


def _window(df: pd.DataFrame, years: int) -> pd.DataFrame:
    """Recorta os jogos dos últimos `years` anos (janela de treino recente)."""
    cut = df["date"].max() - pd.DateOffset(years=years)
    mask = (df["date"] >= cut) & df["home_team"].notna() & df["away_team"].notna()
    return df[mask].copy()


def fit_dixon_coles(window: pd.DataFrame) -> pb.models.DixonColesGoalModel:
    """Ajusta o Dixon-Coles na janela. Arrays copiados (Cython exige writable)."""
    def arr(series, dtype):
        return series.astype(dtype).to_numpy(copy=True)

    weights = np.asarray(pb.models.dixon_coles_weights(window["date"]), dtype=float).copy()
    model = pb.models.DixonColesGoalModel(
        arr(window["home_score"], int),
        arr(window["away_score"], int),
        arr(window["home_team"], str),
        arr(window["away_team"], str),
        weights=weights,
        neutral_venue=arr(window["neutral"], int),
    )
    model.fit()
    return model


class FittedBaseline(NamedTuple):
    """Estado ajustado do baseline (cacheado por janela de treino)."""

    model: pb.models.DixonColesGoalModel
    teams: set[str]
    n_train: int
    since_year: int


def _build_bundle(window: pd.DataFrame) -> FittedBaseline:
    model = fit_dixon_coles(window)
    all_teams = pd.concat([window["home_team"], window["away_team"]]).astype(str)
    since = int(window["date"].min().year)
    return FittedBaseline(model=model, teams=set(all_teams), n_train=len(window), since_year=since)


# Cache por processo: o fit leva ~4s; um por janela basta.
_CACHE: dict[tuple, FittedBaseline] = {}


def _get_bundle(settings: Settings, df: pd.DataFrame | None = None) -> FittedBaseline:
    if df is not None:  # caminho de teste: sem cache, sem rede
        return _build_bundle(_window(df, settings.history_years))
    key = ("default", settings.history_years)
    if key not in _CACHE:
        played = played_matches(load_results(settings))
        _CACHE[key] = _build_bundle(_window(played, settings.history_years))
    return _CACHE[key]


def _resolve_team(name: str, teams: set[str]) -> str:
    """Casa o nome ao padrão martj42 (exato → case-insensitive → fuzzy)."""
    if name in teams:
        return name
    lower = {t.lower(): t for t in teams}
    if name.lower() in lower:
        return lower[name.lower()]
    raise UnknownTeamError(name, difflib.get_close_matches(name, teams, n=3, cutoff=0.6))


def predict_match(
    home: str,
    away: str,
    neutral: bool = True,
    settings: Settings | None = None,
    df: pd.DataFrame | None = None,
) -> BaselineResult:
    """Prevê um confronto pelo baseline Dixon-Coles."""
    settings = settings or get_settings()
    model, teams, n_train, since = _get_bundle(settings, df)
    home_c = _resolve_team(home, teams)
    away_c = _resolve_team(away, teams)

    grid = model.predict(home_c, away_c, max_goals=_MAX_GOALS, neutral_venue=neutral)
    matrix = np.asarray(grid.grid)
    hg, ag = np.unravel_index(matrix.argmax(), matrix.shape)
    return BaselineResult(
        home=home_c,
        away=away_c,
        p_home=float(grid.home_win),
        p_draw=float(grid.draw),
        p_away=float(grid.away_win),
        xg_home=float(grid.home_goal_expectation),
        xg_away=float(grid.away_goal_expectation),
        likely_home_goals=int(hg),
        likely_away_goals=int(ag),
        n_train=n_train,
        since_year=since,
    )


@tool
def baseline_prediction(home: str, away: str, neutral: bool = True) -> str:
    """Prior estatístico (Dixon-Coles) de um confronto de seleções.

    Retorna P(vitória do mandante / empate / vitória do visitante), gols
    esperados e o placar mais provável, treinado nos resultados recentes de
    seleções com decaimento temporal. Use os nomes de país em inglês
    (ex.: 'Brazil', 'England', 'United States'). `neutral=True` para sede neutra
    (padrão em mata-mata de Copa).
    """
    try:
        r = predict_match(home, away, neutral)
    except UnknownTeamError as exc:
        return str(exc)
    return (
        f"Baseline Dixon-Coles ({r.n_train} jogos de seleção desde {r.since_year}, time-decay):\n"
        f"- {r.home}: {r.p_home:.0%}  |  Empate: {r.p_draw:.0%}  |  {r.away}: {r.p_away:.0%}\n"
        f"- Gols esperados: {r.home} {r.xg_home:.1f} — {r.xg_away:.1f} {r.away}\n"
        f"- Placar mais provável: {r.likely_home_goals}-{r.likely_away_goals}\n"
        f"- Venue neutro: {neutral}"
    )


@tool
def head_to_head(home: str, away: str, limit: int = 8) -> str:
    """Confrontos diretos entre dois times: retrospecto (V/E/D do 1º time) e os
    últimos jogos com placar. Use nomes de país em inglês.
    """
    df = played_matches(load_results())
    # Resolve nomes pelo mesmo caminho do baseline_prediction (exato →
    # case-insensitive → fuzzy). Sem isso, um nome variante cairia no ramo
    # vazio e afirmaria falsamente que os times nunca se enfrentaram.
    teams = set(pd.concat([df["home_team"], df["away_team"]]).dropna().astype(str))
    try:
        home = _resolve_team(home, teams)
        away = _resolve_team(away, teams)
    except UnknownTeamError as exc:
        return str(exc)

    mask = ((df["home_team"] == home) & (df["away_team"] == away)) | (
        (df["home_team"] == away) & (df["away_team"] == home)
    )
    h2h = df[mask].sort_values("date")
    if h2h.empty:
        return f"Sem confrontos diretos registrados entre {home} e {away}."

    wins = draws = losses = 0
    lines = []
    for _, row in h2h.iterrows():
        hs, as_ = (row["home_score"], row["away_score"])
        gf, ga = (hs, as_) if row["home_team"] == home else (as_, hs)
        if gf > ga:
            wins += 1
        elif gf == ga:
            draws += 1
        else:
            losses += 1
        year = row["date"].year
        lines.append(f"  {year}: {row['home_team']} {int(hs)}-{int(as_)} {row['away_team']}")

    recent = "\n".join(lines[-limit:])
    return (
        f"Confrontos diretos {home} x {away} ({len(h2h)} jogos): "
        f"{home} {wins}V {draws}E {losses}D.\nÚltimos:\n{recent}"
    )
