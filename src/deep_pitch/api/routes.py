"""Rotas HTTP. A lógica vive no service; a rota só mede tempo e embrulha."""

from __future__ import annotations

import time

from fastapi import APIRouter

from ..config import describe_model
from ..domain import MatchRequest, PredictionResponse
from ..service import run_prediction

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/predict", response_model=PredictionResponse)
def predict(request: MatchRequest) -> PredictionResponse:
    """Previsão completa via Deep Agent (baseline + ao vivo + busca + síntese)."""
    started = time.perf_counter()
    prediction = run_prediction(request)
    return PredictionResponse(
        prediction=prediction,
        model_used=describe_model("main"),
        latency_seconds=round(time.perf_counter() - started, 2),
    )
