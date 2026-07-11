"""Testes de configure_environment (ponte .env → os.environ)."""

import os

from deep_pitch.config.observability import configure_environment


def test_exports_provider_keys(make_settings):
    configure_environment(make_settings(anthropic_api_key="ak", groq_api_key="gk"))
    assert os.environ["ANTHROPIC_API_KEY"] == "ak"
    assert os.environ["GROQ_API_KEY"] == "gk"


def test_tracing_forced_off_without_key(make_settings, monkeypatch):
    # cenário do bug: TRACING=true herdado, mas sem key → deve virar false
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    configure_environment(make_settings(langsmith_api_key=None))
    assert os.environ["LANGSMITH_TRACING"] == "false"


def test_tracing_on_with_key(make_settings):
    configure_environment(make_settings(langsmith_api_key="lk", langsmith_tracing=True))
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_API_KEY"] == "lk"
