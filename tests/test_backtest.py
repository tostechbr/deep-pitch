"""Testes do backtest (RPS puro + backtest em df sintético, sem rede)."""

import itertools

import pandas as pd

from deep_pitch.backtest import rps, run_backtest


def test_rps_perfect_is_zero():
    assert rps((1.0, 0.0, 0.0), 0) == 0.0


def test_rps_worst_is_one():
    assert rps((1.0, 0.0, 0.0), 2) == 1.0


def test_rps_uniform_around_quarter():
    assert 0.25 < rps((1 / 3, 1 / 3, 1 / 3), 0) < 0.30


_TEAMS = ["A", "B", "C", "D"]
# set de placares variado o bastante p/ o MLE do Dixon-Coles convergir
_SCORES = [(2, 0), (1, 1), (0, 1), (3, 1), (1, 0), (2, 2), (0, 0), (1, 2)]


def _synthetic() -> pd.DataFrame:
    rows, base, i = [], pd.Timestamp("2020-01-01"), 0
    for _ in range(12):  # pré-Copa (mais jogos → fit bem-condicionado)
        for home, away in itertools.permutations(_TEAMS, 2):
            hs, as_ = _SCORES[i % len(_SCORES)]
            i += 1
            rows.append(
                {
                    "date": base + pd.Timedelta(days=i * 7),
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
    for home, away, hs, as_ in [("A", "B", 2, 0), ("C", "D", 1, 1)]:  # Copa 2026 decididos
        rows.append(
            {
                "date": pd.Timestamp("2026-07-01"),
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
                "tournament": "FIFA World Cup",
                "city": "x",
                "country": "X",
                "neutral": True,
            }
        )
    return pd.DataFrame(rows)


def test_run_backtest_synthetic(make_settings):
    r = run_backtest(settings=make_settings(), df=_synthetic())
    assert r.n == 2
    assert 0.0 <= r.hit_rate <= 1.0
    assert 0.0 <= r.mean_rps <= 1.0
    assert r.trained_on > 0


def test_backtest_train_excludes_world_cup_no_leakage(make_settings):
    # a tese central: treino usa SÓ jogos pré-Copa. Uma regressão de leakage
    # (trocar `date < wc.min()` por `<=`) incluiria os jogos da Copa e quebraria isto.
    df = _synthetic()
    r = run_backtest(settings=make_settings(history_years=50), df=df)  # janela cobre tudo
    pre_copa = df[df["tournament"] != "FIFA World Cup"]
    assert r.trained_on == len(pre_copa)
