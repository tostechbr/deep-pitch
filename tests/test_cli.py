"""Testes do CLI (Typer CliRunner, predict_match mockado — sem rede)."""

from typer.testing import CliRunner

from deep_pitch import cli
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
