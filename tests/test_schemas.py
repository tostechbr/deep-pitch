"""Testes dos contratos de domínio + loader de prompts."""

import pytest
from pydantic import ValidationError

from deep_pitch.domain import MatchRequest, Prediction, Probabilities
from deep_pitch.prompts import load_prompt


def _prediction(**over) -> Prediction:
    base = dict(
        home="Norway",
        away="England",
        winner="England",
        scoreline="1-2",
        confidence=0.55,
        probabilities=Probabilities(home_win=0.30, draw=0.27, away_win=0.43),
        key_factors=["prior estatístico", "forma recente"],
        baseline_summary="England 43%",
        live_summary="virose no elenco inglês",
        rationale="England favorito, mas a virose aproxima o jogo.",
    )
    base.update(over)
    return Prediction(**base)


def test_prediction_valid():
    p = _prediction()
    assert p.winner == "England"
    assert p.sources == []
    assert 0 <= p.confidence <= 1


def test_probabilities_bounds():
    with pytest.raises(ValidationError):
        Probabilities(home_win=1.5, draw=0.0, away_win=0.0)


def test_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        _prediction(confidence=2.0)


def test_match_request_defaults_neutral_true():
    r = MatchRequest(home="Brazil", away="Argentina")
    assert r.neutral is True
    assert r.context is None


def test_prompts_load():
    for name in ("system", "scout", "historian"):
        assert len(load_prompt(name)) > 50
    assert "reconcil" in load_prompt("system").lower()
    assert "web_search" in load_prompt("scout")
    assert "baseline_prediction" in load_prompt("historian")
