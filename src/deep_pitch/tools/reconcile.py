"""Reconciliação DETERMINÍSTICA do prior com ajustes QUALITATIVOS.

O eval mostrou dois problemas: o LLM erra a aritmética (narra "+4pp" e o número
vai pro lado oposto) e emite falsa precisão ("-6.3pp", "confiança 0.52").

Fix: o LLM só CLASSIFICA — cada fator favorece um lado com um impacto
minor/moderate/major, e os pênaltis favorecem home/away/even. O CÓDIGO mapeia
tier→pontos percentuais, aplica sobre o prior, normaliza e deriva a confiança.
LLM julga (o que faz bem); código computa (determinístico, testável).
"""

from __future__ import annotations

from typing import Literal

from langchain.tools import tool
from pydantic import BaseModel, Field

# Tier de impacto → deslocamento em pontos percentuais.
_IMPACT_PP = {"minor": 3.0, "moderate": 7.0, "major": 12.0}
# Quem tende a vencer os pênaltis → P(mandante vence a disputa).
_SHOOTOUT = {"home": 0.60, "away": 0.40, "even": 0.50}


class Adjustment(BaseModel):
    """Um fator qualitativo que favorece um dos lados."""

    favors: Literal["home", "away"] = Field(description="Que lado o fator favorece.")
    impact: Literal["minor", "moderate", "major"] = Field(description="Peso do fator.")
    reason: str = Field(description="Justificativa curta, idealmente com a fonte.")


def apply_adjustments(
    home_win: float,
    draw: float,
    away_win: float,
    adjustments: list[Adjustment],
    shootout: Literal["home", "away", "even"] = "even",
) -> dict:
    """Aplica os ajustes (tier→pp) ao prior, normaliza e deriva quem avança.

    Valida a fronteira LLM→código: o prior é normalizado para somar 1 ANTES de
    aplicar os ajustes (em pp). Assim funciona quer o LLM mande 0-1 quer mande %
    (erro clássico) — sem isso, um prior em escala % engoliria o ajuste em silêncio.
    """
    prior_total = home_win + draw + away_win
    if prior_total <= 0:
        raise ValueError("Prior inválido: home_win + draw + away_win deve ser > 0.")
    # normaliza o prior p/ soma 1 → ajustes em pp têm magnitude relativa correta
    probs = {"home": home_win / prior_total, "draw": draw / prior_total, "away": away_win / prior_total}
    for adj in adjustments:
        probs[adj.favors] += _IMPACT_PP[adj.impact] / 100.0

    probs = {k: max(v, 0.0) for k, v in probs.items()}
    total = sum(probs.values()) or 1.0
    probs = {k: v / total for k, v in probs.items()}

    # P(avançar) = vitória no tempo normal + empate × P(vencer nos pênaltis)
    hs = _SHOOTOUT[shootout]
    adv_home = probs["home"] + probs["draw"] * hs
    adv_away = probs["away"] + probs["draw"] * (1.0 - hs)

    return {
        "probs": probs,
        "advances": "home" if adv_home >= adv_away else "away",
        "confidence": max(adv_home, adv_away),
        "normal_result": max(probs, key=probs.get),
    }


_LABEL = {"home": "vitória do mandante", "draw": "empate", "away": "vitória do visitante"}


@tool
def reconcile(
    home_win: float,
    draw: float,
    away_win: float,
    adjustments: list[Adjustment],
    shootout: Literal["home", "away", "even"] = "even",
) -> str:
    """Recalcula probabilidades + confiança a partir do prior e de ajustes QUALITATIVOS.

    Você NÃO emite números: passe o prior do baseline (0-1) e, para cada fator
    relevante, quem ele favorece (home/away) e o impacto (minor/moderate/major);
    e quem tende a vencer nos pênaltis (home/away/even). O código faz toda a
    conta. Use a saída na sua Prediction — não recalcule nem "ajuste na mão".
    """
    r = apply_adjustments(home_win, draw, away_win, adjustments, shootout)
    p = r["probs"]
    ledger = "\n".join(f"  favorece {a.favors} ({a.impact}) — {a.reason}" for a in adjustments)
    advances = "mandante" if r["advances"] == "home" else "visitante"
    return (
        "Probabilidades recalculadas (tempo normal, somam 1.00):\n"
        f"- mandante: {p['home']:.0%} | empate: {p['draw']:.0%} | visitante: {p['away']:.0%}\n"
        f"Ajustes aplicados:\n{ledger or '  (nenhum)'}\n"
        f"Resultado mais provável no tempo normal: {_LABEL[r['normal_result']]}.\n"
        f"Quem avança: {advances} · confiança P(avança) = {r['confidence']:.0%}.\n"
        "Use estes números na Prediction — não recalcule."
    )
