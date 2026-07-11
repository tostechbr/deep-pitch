"""Testes do baseline Dixon-Coles (df sintético, sem rede)."""

import itertools

import pandas as pd
import pytest

from deep_pitch.tools import baseline as bl
from deep_pitch.tools.baseline import (
    BaselineResult,
    UnknownTeamError,
    baseline_prediction,
    head_to_head,
    predict_match,
)

_TEAMS = ["Aland", "Brava", "Cando", "Delta"]
_SCORES = [(2, 0), (1, 1), (0, 1), (3, 1), (1, 0), (2, 2), (0, 0), (1, 2)]


def _synthetic() -> pd.DataFrame:
    """Round-robin repetido — jogos suficientes p/ o Dixon-Coles convergir."""
    rows, base, i = [], pd.Timestamp("2021-01-01"), 0
    for _ in range(8):
        for home, away in itertools.permutations(_TEAMS, 2):
            hs, as_ = _SCORES[i % len(_SCORES)]
            i += 1
            rows.append(
                {
                    "date": base + pd.Timedelta(days=i * 20),
                    "home_team": home,
                    "away_team": away,
                    "home_score": hs,
                    "away_score": as_,
                    "tournament": "Friendly",
                    "city": "x",
                    "country": "X",
                    "neutral": False,
                }
            )
    return pd.DataFrame(rows)


def test_window_filters_by_years():
    df = _synthetic()
    w = bl._window(df, 1)
    assert (w["date"] >= df["date"].max() - pd.DateOffset(years=1)).all()


def test_resolve_team_exact_and_case_insensitive():
    teams = {"Aland", "Brava"}
    assert bl._resolve_team("Aland", teams) == "Aland"
    assert bl._resolve_team("aland", teams) == "Aland"


def test_resolve_team_unknown_raises():
    with pytest.raises(UnknownTeamError):
        bl._resolve_team("Zzzland", {"Aland", "Brava"})


def test_predict_match_probs_valid(make_settings):
    r = predict_match("Aland", "Brava", neutral=False, settings=make_settings(), df=_synthetic())
    assert isinstance(r, BaselineResult)
    assert abs(r.p_home + r.p_draw + r.p_away - 1.0) < 0.05
    assert r.n_train > 0
    assert 0 <= r.xg_home < 10


def test_predict_match_unknown_team(make_settings):
    with pytest.raises(UnknownTeamError):
        predict_match("Nowhere", "Brava", settings=make_settings(), df=_synthetic())


def test_baseline_prediction_tool_formats(monkeypatch):
    fake = BaselineResult("Aland", "Brava", 0.5, 0.3, 0.2, 1.5, 1.1, 2, 1, 100, 2019)
    monkeypatch.setattr(bl, "predict_match", lambda *a, **k: fake)
    out = baseline_prediction.invoke({"home": "Aland", "away": "Brava"})
    assert "Aland: 50%" in out
    assert "2-1" in out


def test_baseline_prediction_tool_unknown(monkeypatch):
    def _raise(*a, **k):
        raise UnknownTeamError("Zzz", ["Aland"])

    monkeypatch.setattr(bl, "predict_match", _raise)
    out = baseline_prediction.invoke({"home": "Zzz", "away": "Brava"})
    assert "não está no histórico" in out


def test_head_to_head_resolves_name_case_insensitive(monkeypatch):
    monkeypatch.setattr(bl, "load_results", lambda *a, **k: _synthetic())
    out = head_to_head.invoke({"home": "aland", "away": "Brava", "limit": 5})
    assert "Aland" in out
    assert "jogos" in out


def test_head_to_head_unknown_team_errors_not_empty(monkeypatch):
    # o fix: nome desconhecido → erro claro, NÃO "Sem confrontos" (afirmação falsa)
    monkeypatch.setattr(bl, "load_results", lambda *a, **k: _synthetic())
    out = head_to_head.invoke({"home": "Zzz", "away": "Brava"})
    assert "não está no histórico" in out
    assert "Sem confrontos" not in out
