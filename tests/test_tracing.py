"""Testes do tracer LangSmith por-request (BYOK)."""

from deep_pitch.config.tracing import build_tracer


def test_no_key_returns_none():
    assert build_tracer(None) is None
    assert build_tracer("") is None


def test_with_key_returns_tracer():
    tracer = build_tracer("dummy-lsv2", "deep-pitch")
    assert tracer is not None
    assert tracer.__class__.__name__ == "LangChainTracer"
