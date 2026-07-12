"""Testes da API FastAPI (run_prediction mockado — sem chamada de rede)."""

from fastapi.testclient import TestClient

from deep_pitch.api import app
from deep_pitch.api import routes
from deep_pitch.domain import Prediction, Probabilities

client = TestClient(app)


def _pred() -> Prediction:
    return Prediction(
        home="Norway",
        away="England",
        winner="England",
        scoreline="1-2",
        confidence=0.55,
        probabilities=Probabilities(home_win=0.32, draw=0.28, away_win=0.40),
        key_factors=["prior", "virose"],
        baseline_summary="England 40%",
        live_summary="surto no elenco inglês",
        rationale="England favorito, virose aproxima.",
        sources=["https://ex.com/news"],
    )


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_index_page_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "deep-pitch" in r.text
    assert "api_key" in r.text  # o form BYOK


def test_predict_endpoint(monkeypatch):
    monkeypatch.setattr(routes, "run_prediction", lambda req, settings=None, callbacks=None: _pred())
    r = client.post("/predict", json={"home": "Norway", "away": "England", "neutral": True})
    assert r.status_code == 200
    body = r.json()
    assert body["prediction"]["winner"] == "England"
    assert body["prediction"]["probabilities"]["away_win"] == 0.40
    assert "model_used" in body
    assert body["latency_seconds"] is not None


def test_predict_validation_error():
    r = client.post("/predict", json={"home": "Norway"})  # falta 'away'
    assert r.status_code == 422


def test_predict_byok(monkeypatch):
    monkeypatch.setattr(routes, "run_prediction", lambda req, settings=None, callbacks=None: _pred())
    r = client.post(
        "/predict",
        json={"home": "Argentina", "away": "Switzerland", "provider": "groq", "api_key": "user-key"},
    )
    assert r.status_code == 200
    assert r.json()["model_used"].startswith("groq:")  # refletiu o provider do usuário


def test_predict_byok_requires_both(monkeypatch):
    monkeypatch.setattr(routes, "run_prediction", lambda req, settings=None, callbacks=None: _pred())
    r = client.post(
        "/predict",
        json={"home": "Argentina", "away": "Switzerland", "provider": "groq"},  # sem api_key
    )
    assert r.status_code == 422
