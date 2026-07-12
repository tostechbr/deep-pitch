"""Backtest/calibração do baseline Dixon-Coles na Copa 2026.

Honesto (sem leakage): ajusta o modelo SÓ com jogos ANTERIORES à Copa 2026 e
prevê os jogos já decididos do torneio, comparando com o real. Reporta taxa de
acerto (vencedor) e RPS (Rank Probability Score — mede calibração das
probabilidades; menor é melhor, ~0.25 é chute uniforme).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config.settings import Settings, get_settings
from .data import load_results, played_matches, wc2026_played
from .tools.baseline import UnknownTeamError, _resolve_team, _window, fit_dixon_coles


def rps(probs: tuple[float, float, float], outcome: int) -> float:
    """Rank Probability Score para [home, draw, away]. outcome: 0/1/2. Menor = melhor."""
    actual = [0.0, 0.0, 0.0]
    actual[outcome] = 1.0
    cum_p = cum_a = total = 0.0
    for i in range(2):  # r-1 = 2 termos
        cum_p += probs[i]
        cum_a += actual[i]
        total += (cum_p - cum_a) ** 2
    return total / 2.0


@dataclass(frozen=True)
class BacktestResult:
    n: int
    hits: int
    hit_rate: float
    mean_rps: float
    trained_on: int
    since_year: int


def _outcome(home_score: float, away_score: float) -> int:
    return 0 if home_score > away_score else (2 if away_score > home_score else 1)


def run_backtest(settings: Settings | None = None, df: pd.DataFrame | None = None) -> BacktestResult:
    """Ajusta em pré-Copa e mede acerto/RPS nos jogos decididos da Copa 2026."""
    settings = settings or get_settings()
    played = played_matches(load_results(settings)) if df is None else df

    wc = wc2026_played(played)  # só jogos da Copa 2026 já decididos
    if wc.empty:
        raise RuntimeError("Sem jogos decididos da Copa 2026 no dataset.")

    train = played[played["date"] < wc["date"].min()].copy()  # antes da Copa → sem leakage
    window = _window(train, settings.history_years)
    model = fit_dixon_coles(window)
    teams = set(pd.concat([window["home_team"], window["away_team"]]).astype(str))

    n = hits = 0
    rps_sum = 0.0
    for _, row in wc.iterrows():
        try:
            home = _resolve_team(str(row["home_team"]), teams)
            away = _resolve_team(str(row["away_team"]), teams)
        except UnknownTeamError:
            continue  # time sem histórico pré-Copa → fora do backtest
        grid = model.predict(home, away, neutral_venue=bool(row["neutral"]))
        probs = (float(grid.home_win), float(grid.draw), float(grid.away_win))
        pred = max(range(3), key=lambda i: probs[i])
        actual = _outcome(row["home_score"], row["away_score"])
        n += 1
        hits += int(pred == actual)
        rps_sum += rps(probs, actual)

    if n == 0:
        raise RuntimeError("Nenhum jogo da Copa 2026 pôde ser avaliado (times sem histórico).")
    return BacktestResult(
        n=n,
        hits=hits,
        hit_rate=hits / n,
        mean_rps=rps_sum / n,
        trained_on=len(window),
        since_year=int(window["date"].min().year),
    )
