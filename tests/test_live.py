"""Smoke test LIVE — faz chamada real de LLM (roda o agente de ponta a ponta).

Gated pelo marker `live` (o run default é `-m 'not live'`). Rode com:
    uv run pytest -m live
Requer um provider de LLM configurado no .env (ex.: ANTHROPIC_API_KEY).
"""

import pytest

from deep_pitch.domain import MatchRequest
from deep_pitch.service import run_prediction


@pytest.mark.live
def test_predict_real_semifinal_is_coherent():
    p = run_prediction(
        MatchRequest(home="Argentina", away="Switzerland", neutral=True, context="semifinal")
    )
    total = p.probabilities.home_win + p.probabilities.draw + p.probabilities.away_win
    win = max(p.probabilities.home_win, p.probabilities.away_win)

    assert abs(total - 1.0) < 0.02  # reconcile normaliza
    assert p.confidence >= win - 0.01  # confidence = P(avança) >= vitória no tempo normal
    assert p.winner
    assert len(p.rationale) > 100
    assert p.sources  # o scout deve ter trazido fontes
