"""Testes do service.run_prediction (agente mockado — sem chamada de rede)."""

import pytest

from deep_pitch.domain import MatchRequest, Prediction, Probabilities
from deep_pitch.service import predict as svc


class _FakeAgent:
    def __init__(self, response):
        self._response = response

    def invoke(self, *args, **kwargs):
        return self._response


def _pred() -> Prediction:
    return Prediction(
        home="A",
        away="B",
        winner="A",
        scoreline="1-0",
        confidence=0.6,
        probabilities=Probabilities(home_win=0.6, draw=0.2, away_win=0.2),
        key_factors=["x"],
        baseline_summary="b",
        live_summary="l",
        rationale="r",
    )


def test_run_prediction_returns_structured(monkeypatch):
    monkeypatch.setattr(svc, "_default_agent", lambda: _FakeAgent({"structured_response": _pred()}))
    p = svc.run_prediction(MatchRequest(home="A", away="B"))
    assert p.winner == "A"


def test_run_prediction_missing_structured_raises(monkeypatch):
    monkeypatch.setattr(svc, "_default_agent", lambda: _FakeAgent({"messages": []}))
    with pytest.raises(RuntimeError):
        svc.run_prediction(MatchRequest(home="A", away="B"))


def test_run_prediction_byok_builds_fresh_agent(monkeypatch, make_settings):
    # com settings (BYOK) → constrói agente fresco (não usa o cache padrão)
    monkeypatch.setattr(svc, "build_agent", lambda s: _FakeAgent({"structured_response": _pred()}))
    p = svc.run_prediction(
        MatchRequest(home="A", away="B"),
        settings=make_settings(model_provider="groq", groq_api_key="user-key"),
    )
    assert p.winner == "A"
