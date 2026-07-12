"""Testes da factory de modelo (dispatch, papel, chave ausente)."""

import os

import pytest

from deep_pitch.config.models import _resolve, describe_model, get_model

_DISPATCH = {
    "anthropic": ("anthropic_api_key", "ChatAnthropic"),
    "google": ("google_api_key", "ChatGoogleGenerativeAI"),
    "groq": ("groq_api_key", "ChatGroq"),
    "openrouter": ("openrouter_api_key", "ChatOpenAI"),
    "nvidia": ("nvidia_api_key", "ChatOpenAI"),
}


@pytest.mark.parametrize("provider,field,cls", [(p, f, c) for p, (f, c) in _DISPATCH.items()])
def test_dispatch_each_provider(make_settings, provider, field, cls):
    s = make_settings(model_provider=provider, **{field: "dummy-key"})
    assert type(get_model("main", s)).__name__ == cls


def test_missing_key_raises_clear_error(make_settings):
    s = make_settings(model_provider="groq")  # sem GROQ_API_KEY
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        get_model("main", s)


def test_per_role_override(make_settings):
    s = make_settings(
        model_provider="anthropic", anthropic_api_key="d1",
        subagent_provider="google", google_api_key="d2",
    )
    assert _resolve("main", s)[0] == "anthropic"
    assert _resolve("subagent", s)[0] == "google"
    assert type(get_model("subagent", s)).__name__ == "ChatGoogleGenerativeAI"


def test_model_name_not_leaked_across_providers(make_settings):
    # MODEL_NAME do provider base (anthropic) não deve vazar pro subagent google.
    s = make_settings(
        model_provider="anthropic", model_name="claude-x", anthropic_api_key="d1",
        subagent_provider="google", google_api_key="d2",
    )
    provider, name = _resolve("subagent", s)
    assert provider == "google"
    assert name != "claude-x"  # usa o default do google, não o nome do anthropic


def test_describe_model(make_settings):
    s = make_settings(model_provider="groq", groq_api_key="d")
    assert describe_model("main", s).startswith("groq:")


def test_get_model_does_not_leak_key_to_env(make_settings, monkeypatch):
    # segurança BYOK: a key vai por kwarg no construtor, NUNCA pro os.environ
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    get_model("main", make_settings(model_provider="groq", groq_api_key="secret-key"))
    assert os.environ.get("GROQ_API_KEY") != "secret-key"
