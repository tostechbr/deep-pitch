"""Testes do service.run_prediction (agente mockado — sem chamada de rede)."""

import pytest

from deep_pitch.domain import MatchRequest, Prediction, Probabilities
from deep_pitch.service import predict as svc


class _FakeAgent:
    def __init__(self, response):
        self._response = response

    def invoke(self, *args, **kwargs):
        return self._response


class _AIMsg:
    def __init__(self, name, tool_calls):
        self.name = name
        self.tool_calls = tool_calls


class _FakeStreamAgent:
    """Agente que reproduz o formato real do stream (subgraphs → ns, mode, data)."""

    def __init__(self, chunks):
        self._chunks = chunks

    def stream(self, *args, **kwargs):
        yield from self._chunks


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


def _stream_chunks():
    """Replica o formato real (subgraphs=True): (ns, mode, data).

    main (deep-pitch, depth 0) → subagentes historian/scout (depth 1) → reconcile.
    """
    main = _AIMsg("deep-pitch", [{"name": "write_todos"}, {"name": "task"}, {"name": "task"}])
    hist = _AIMsg("historian", [{"name": "baseline_prediction"}, {"name": "head_to_head"}])
    scout = _AIMsg("scout", [{"name": "live_feed"}, {"name": "web_search"}])
    reconcile = _AIMsg("deep-pitch", [{"name": "reconcile"}])
    pred = _AIMsg("deep-pitch", [{"name": "Prediction"}])  # marshalling → pulado
    return [
        ((), "values", {"messages": []}),
        ((), "updates", {"model": {"messages": [main]}}),
        (("tools:h1",), "updates", {"model": {"messages": [hist]}}),
        (("tools:s1",), "updates", {"model": {"messages": [scout]}}),
        ((), "updates", {"model": {"messages": [reconcile]}}),
        ((), "updates", {"model": {"messages": [pred]}}),
        ((), "values", {"messages": [], "structured_response": _pred(), "todos": []}),
    ]


def test_stream_prediction_emits_raw_steps_then_result(monkeypatch):
    monkeypatch.setattr(svc, "_default_agent", lambda: _FakeStreamAgent(_stream_chunks()))
    events = list(svc.stream_prediction(MatchRequest(home="A", away="B")))

    steps = [e for e in events if e.kind == "step"]
    results = [e for e in events if e.kind == "result"]

    # nomes CRUS, sem tradução; agente e profundidade preservados
    main_tools = [s.tool for s in steps if s.agent == "deep-pitch"]
    assert main_tools == ["write_todos", "task", "task", "reconcile"]  # Prediction pulado
    hist = [s for s in steps if s.agent == "historian"]
    assert [s.tool for s in hist] == ["baseline_prediction", "head_to_head"]
    assert all(s.depth == 1 for s in hist)  # subagente = profundidade 1
    scout = [s for s in steps if s.agent == "scout"]
    assert [s.tool for s in scout] == ["live_feed", "web_search"]
    assert not any(s.tool == "Prediction" for s in steps)

    assert len(results) == 1
    assert events[-1].kind == "result"
    assert results[0].prediction.winner == "A"


def test_stream_prediction_missing_structured_raises(monkeypatch):
    chunks = [((), "values", {"messages": []})]  # nenhum structured_response
    monkeypatch.setattr(svc, "_default_agent", lambda: _FakeStreamAgent(chunks))
    with pytest.raises(RuntimeError):
        list(svc.stream_prediction(MatchRequest(home="A", away="B")))


def test_unpack_stream_item_normalizes_shapes():
    # subgraphs + lista de modes → 3-tupla (ns, mode, data)
    assert svc._unpack_stream_item((("ns",), "values", {"x": 1})) == (("ns",), "values", {"x": 1})
    # sem subgraph → (mode, data)
    assert svc._unpack_stream_item(("updates", {"x": 1})) == ((), "updates", {"x": 1})
    # subgraph + modo único → (ns, data)
    assert svc._unpack_stream_item((("ns",), {"x": 1})) == (("ns",), "updates", {"x": 1})
