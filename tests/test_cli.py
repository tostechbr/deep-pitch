"""Testes do CLI (Typer CliRunner, predict_match mockado — sem rede)."""

from typer.testing import CliRunner

import deep_pitch.service as service_pkg
from deep_pitch import cli
from deep_pitch.domain import Prediction, Probabilities
from deep_pitch.tools.baseline import BaselineResult, UnknownTeamError

runner = CliRunner()


def test_cli_baseline_ok(monkeypatch):
    fake = BaselineResult("Norway", "England", 0.28, 0.27, 0.44, 1.2, 1.5, 1, 1, 7803, 2018)
    monkeypatch.setattr(cli, "predict_match", lambda *a, **k: fake)
    res = runner.invoke(cli.app, ["baseline", "Norway", "England"])
    assert res.exit_code == 0
    assert "Norway 28%" in res.output
    assert "England 44%" in res.output


def test_cli_baseline_unknown_team(monkeypatch):
    def _raise(*a, **k):
        raise UnknownTeamError("Zzz", ["Norway"])

    monkeypatch.setattr(cli, "predict_match", _raise)
    res = runner.invoke(cli.app, ["baseline", "Zzz", "England"])
    assert res.exit_code == 1
    assert "não está no histórico" in res.output


def test_cli_predict_agent(monkeypatch):
    fake = Prediction(
        home="Norway",
        away="England",
        winner="England",
        scoreline="1-2",
        confidence=0.55,
        probabilities=Probabilities(home_win=0.32, draw=0.28, away_win=0.40),
        key_factors=["prior"],
        baseline_summary="b",
        live_summary="l",
        rationale="Análise detalhada do confronto.",
    )
    # o comando faz `from .service import run_prediction` em runtime → mockamos no pacote
    monkeypatch.setattr(service_pkg, "run_prediction", lambda req: fake)
    res = runner.invoke(cli.app, ["predict", "Norway", "England"])
    assert res.exit_code == 0
    assert "England 40%" in res.output
    assert "Análise detalhada" in res.output
