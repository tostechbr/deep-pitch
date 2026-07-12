"""Testes de configure_environment (ponte .env → os.environ)."""

import os

from deep_pitch.config.observability import configure_environment


def test_provider_key_never_leaks_to_env(make_settings, monkeypatch):
    # segurança BYOK: a key de provider NUNCA vai pro os.environ (vazaria entre
    # usuários num servidor). configure_environment só mexe no LangSmith.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    configure_environment(make_settings(anthropic_api_key="secret-provider-key"))
    assert os.environ.get("ANTHROPIC_API_KEY") != "secret-provider-key"


def test_tracing_forced_off_without_key(make_settings, monkeypatch):
    # cenário do bug: TRACING=true herdado, mas sem key → deve virar false
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    configure_environment(make_settings(langsmith_api_key=None))
    assert os.environ["LANGSMITH_TRACING"] == "false"


def test_tracing_on_with_key(make_settings):
    configure_environment(make_settings(langsmith_api_key="lk", langsmith_tracing=True))
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_API_KEY"] == "lk"
