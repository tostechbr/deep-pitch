"""Rotas HTTP. A lógica vive no service; a rota mede tempo, faz BYOK e embrulha."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import Field

from ..config import describe_model, get_settings
from ..config.models import _PROVIDER_KEY
from ..config.settings import Provider, Settings
from ..domain import MatchRequest, PredictionResponse
from ..service import run_prediction

router = APIRouter()

_INDEX_HTML = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")


@router.get("/", response_class=HTMLResponse)
def index() -> str:
    """Página BYOK: form (times + provider + key) que chama POST /predict."""
    return _INDEX_HTML


class PredictRequest(MatchRequest):
    """Confronto + credencial opcional do usuário (BYOK)."""

    provider: Provider | None = Field(
        default=None, description="Provider de LLM (BYOK). Ausente → usa o do servidor."
    )
    api_key: str | None = Field(
        default=None,
        description="Sua chave do provider (BYOK). Usada só neste request, nunca armazenada.",
    )


def _byok_settings(provider: Provider, api_key: str) -> Settings:
    """Settings efêmera com a credencial do usuário (não persiste, não vaza)."""
    field, _ = _PROVIDER_KEY[provider]
    return get_settings().model_copy(update={"model_provider": provider, field: api_key})


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/predict", response_model=PredictionResponse)
def predict(req: PredictRequest) -> PredictionResponse:
    """Previsão completa via Deep Agent (baseline + ao vivo + busca + síntese)."""
    if bool(req.provider) ^ bool(req.api_key):
        raise HTTPException(422, "Informe provider E api_key juntos (BYOK), ou nenhum.")

    settings = _byok_settings(req.provider, req.api_key) if req.provider else None
    started = time.perf_counter()
    prediction = run_prediction(req, settings)
    return PredictionResponse(
        prediction=prediction,
        model_used=describe_model("main", settings),
        latency_seconds=round(time.perf_counter() - started, 2),
    )
