"""Testes da reconciliação determinística (tier→pp, normalização, confiança)."""

import pytest

from deep_pitch.tools.reconcile import Adjustment, apply_adjustments, reconcile


def test_no_adjustments_normalizes_to_one():
    r = apply_adjustments(0.28, 0.27, 0.44, [])
    assert abs(sum(r["probs"].values()) - 1.0) < 1e-9
    assert r["normal_result"] == "away"  # visitante era o maior


def test_favored_side_moves_up_and_stays_normalized():
    base = apply_adjustments(0.28, 0.27, 0.44, [])
    adj = apply_adjustments(
        0.28, 0.27, 0.44, [Adjustment(favors="home", impact="major", reason="virose adversária")]
    )
    assert adj["probs"]["home"] > base["probs"]["home"]
    assert abs(sum(adj["probs"].values()) - 1.0) < 1e-9


def test_impact_tiers_are_ordered():
    def home(tier):
        return apply_adjustments(
            0.3, 0.3, 0.4, [Adjustment(favors="home", impact=tier, reason="x")]
        )["probs"]["home"]

    assert home("minor") < home("moderate") < home("major")


def test_confidence_includes_penalty_edge():
    # empate alto + pênaltis favorecem o mandante → confiança > prob normal dele
    r = apply_adjustments(0.30, 0.40, 0.30, [], shootout="home")
    assert r["advances"] == "home"
    assert r["confidence"] > r["probs"]["home"]


def test_probs_never_negative():
    r = apply_adjustments(
        0.05, 0.05, 0.90, [Adjustment(favors="away", impact="major", reason="x")]
    )
    assert all(v >= 0 for v in r["probs"].values())


def test_percent_prior_normalized_like_unit():
    # prior em % (erro clássico do LLM) deve dar o MESMO que em 0-1 — a fronteira normaliza
    adj = [Adjustment(favors="home", impact="major", reason="x")]
    unit = apply_adjustments(0.28, 0.27, 0.44, adj)
    pct = apply_adjustments(28.0, 27.0, 44.0, adj)
    assert abs(unit["probs"]["home"] - pct["probs"]["home"]) < 1e-9
    # ajuste 'major' realmente moveu o mandante (~0.28 → ~0.36), não sumiu na escala %
    assert pct["probs"]["home"] > 0.34


def test_zero_prior_raises():
    with pytest.raises(ValueError):
        apply_adjustments(0.0, 0.0, 0.0, [])


def test_reconcile_tool_output():
    out = reconcile.invoke(
        {
            "home_win": 0.28,
            "draw": 0.27,
            "away_win": 0.44,
            "adjustments": [{"favors": "home", "impact": "major", "reason": "virose"}],
            "shootout": "even",
        }
    )
    assert "somam 1.00" in out
    assert "não recalcule" in out
