"""Teste LIVE do agente completo — faz chamada REAL de LLM (e rede).

Por que existe: os outros 67 testes mockam o `invoke` do agente, então o grafo
(create_deep_agent + subagents + response_format) nunca é exercido de verdade —
um bump de deepagents/langchain poderia quebrá-lo sem nenhum teste acusar. Este
é o verify-loop pass/fail que falta: roda o pipeline ponta a ponta contra um
modelo real e confirma que sai uma `Prediction` estruturada e sã.

Gated de duas formas:
- Excluído do run default (`addopts = -m "not live"` no pyproject): `uv run pytest`
  continua rápido, keyless e grátis.
- Auto-skip sem ANTHROPIC_API_KEY real: CI sem segredo não quebra.

Rodar explicitamente:  uv run pytest -m live -s
"""

from __future__ import annotations

import pytest

from deep_pitch.config.settings import get_settings
from deep_pitch.domain import MatchRequest, Prediction


def _real_settings():
    """Recarrega o .env (o fixture clean_env limpou o os.environ) e devolve Settings."""
    get_settings.cache_clear()  # força load_dotenv(override=True) de novo
    return get_settings()


@pytest.mark.live
def test_run_prediction_live_end_to_end():
    """O grafo real produz uma Prediction estruturada e sã (não valida acurácia)."""
    settings = _real_settings()
    if not settings.anthropic_api_key:
        pytest.skip("sem ANTHROPIC_API_KEY real — teste live pulado")

    from deep_pitch.service import run_prediction

    p = run_prediction(
        MatchRequest(home="Brazil", away="England", context="quarterfinal")
    )

    # 1) É a saída estruturada esperada (o response_format funcionou de ponta a ponta).
    assert isinstance(p, Prediction)

    # 2) Probabilidades dentro de [0,1]. NÃO exigimos soma exata ~1 aqui: a coerência
    #    dura (soma, confidence >= prob do vencedor) ainda não é validada na fronteira
    #    (gap conhecido no service). Bound largo só p/ pegar saída totalmente quebrada.
    probs = p.probabilities
    for v in (probs.home_win, probs.draw, probs.away_win):
        assert 0.0 <= v <= 1.0
    assert 0.8 <= (probs.home_win + probs.draw + probs.away_win) <= 1.2

    # 3) Campos de texto que sustentam a tese "explica o porquê" vêm preenchidos.
    assert 0.0 <= p.confidence <= 1.0
    assert p.winner.strip()
    assert p.rationale.strip()
    assert p.baseline_summary.strip()
    assert p.live_summary.strip()
