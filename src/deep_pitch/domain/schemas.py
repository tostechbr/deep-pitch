"""Contratos Pydantic do domínio.

`Prediction` é a saída estruturada do agente (via response_format do
create_deep_agent): as descrições dos campos guiam o LLM a preencher cada um.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Probabilities(BaseModel):
    """Distribuição de resultado no tempo normal (soma ~1)."""

    home_win: float = Field(ge=0, le=1, description="Probabilidade de vitória do mandante (0-1).")
    draw: float = Field(ge=0, le=1, description="Probabilidade de empate no tempo normal (0-1).")
    away_win: float = Field(ge=0, le=1, description="Probabilidade de vitória do visitante (0-1).")


class MatchRequest(BaseModel):
    """Pedido de previsão de um confronto."""

    home: str = Field(description="Time mandante (nome do país em inglês).")
    away: str = Field(description="Time visitante (nome do país em inglês).")
    neutral: bool = Field(default=True, description="Sede neutra (padrão em mata-mata de Copa).")
    context: str | None = Field(default=None, description="Contexto opcional: fase, sede, etc.")


class Prediction(BaseModel):
    """Previsão final do analista para um confronto."""

    home: str
    away: str
    winner: str = Field(
        description="Vencedor previsto: nome do time, ou 'Empate' se for o mais provável no tempo normal."
    )
    scoreline: str = Field(description="Placar mais provável, ex.: '2-1'.")
    confidence: float = Field(ge=0, le=1, description="Confiança na previsão do vencedor (0-1).")
    probabilities: Probabilities
    key_factors: list[str] = Field(
        description="3-5 fatores decisivos (forma, lesão, H2H, prior estatístico)."
    )
    baseline_summary: str = Field(
        description="O que o modelo estatístico (Dixon-Coles) indicou, resumido."
    )
    live_summary: str = Field(
        description="Estado ao vivo + contexto qualitativo (lesões, forma, escalação) encontrado."
    )
    rationale: str = Field(
        description="Relatório em markdown (PT-BR) explicando o porquê, reconciliando o "
        "prior estatístico com o contexto ao vivo."
    )
    sources: list[str] = Field(
        default_factory=list, description="URLs das fontes usadas no scouting."
    )
