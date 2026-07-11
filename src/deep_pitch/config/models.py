"""Factory de modelo — o coração do "model-agnostic".

Um único ponto troca o cérebro do agente via .env, sem tocar no resto do
código. Suporta providers pago (anthropic) e grátis (google/groq/openrouter/
nvidia), e escolhe por PAPEL: `main` (síntese, forte) vs `subagent`
(scout/historian, pode ser barato/rápido).

Por quê factory: isola a decisão de provider num lugar só. Subagents, agente
principal e testes pedem `get_model(role)` e não sabem qual provider está ativo.
Zero lock-in.
"""

from __future__ import annotations

import os
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from .settings import Provider, Settings, get_settings

Role = Literal["main", "subagent"]

# Default por provider (override via MODEL_NAME / *_MODEL_NAME no .env).
DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-5-20250929",  # melhor tool-calling → trace limpo
    "google": "gemini-2.5-flash",               # free tier, tool-calling decente
    "groq": "llama-3.3-70b-versatile",          # free tier, rápido
    "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
    "nvidia": "meta/llama-3.3-70b-instruct",    # NVIDIA NIM (build.nvidia.com)
}

# Mapeia nosso provider → prefixo do init_chat_model do LangChain.
_INIT_CHAT_PROVIDER: dict[str, str] = {
    "anthropic": "anthropic",
    "google": "google_genai",
    "groq": "groq",
}

# Providers que falam protocolo OpenAI → ChatOpenAI com base_url custom.
_OPENAI_COMPAT_BASE: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
}

# Provider → (campo na Settings, nome da env var) da chave obrigatória.
_PROVIDER_KEY: dict[str, tuple[str, str]] = {
    "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
    "google": ("google_api_key", "GOOGLE_API_KEY"),
    "groq": ("groq_api_key", "GROQ_API_KEY"),
    "openrouter": ("openrouter_api_key", "OPENROUTER_API_KEY"),
    "nvidia": ("nvidia_api_key", "NVIDIA_API_KEY"),
}

# Temperatura baixa: previsão quer consistência, não criatividade.
_TEMPERATURE = 0.2


def _resolve(role: Role, settings: Settings) -> tuple[Provider, str]:
    """Resolve (provider, modelo) para o papel, aplicando overrides por papel."""
    if role == "main":
        provider = settings.main_provider or settings.model_provider
        name = settings.main_model_name
    else:
        provider = settings.subagent_provider or settings.model_provider
        name = settings.subagent_model_name

    if name is None:
        # herda MODEL_NAME só se o provider do papel == provider base; senão default.
        name = settings.model_name if provider == settings.model_provider else None
    if name is None:
        name = DEFAULT_MODELS[provider]
    return provider, name


def _build(provider: Provider, name: str, settings: Settings) -> BaseChatModel:
    """Instancia um chat model concreto (sem chamada de rede)."""
    field, env_name = _PROVIDER_KEY[provider]
    key = getattr(settings, field)
    if not key:
        raise ValueError(f"Provider {provider!r} escolhido mas {env_name} está vazio. Preencha no .env.")
    os.environ[env_name] = key  # garante que o SDK do provider acha a chave

    if provider in _OPENAI_COMPAT_BASE:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=name,
            api_key=key,
            base_url=_OPENAI_COMPAT_BASE[provider],
            temperature=_TEMPERATURE,
        )

    return init_chat_model(f"{_INIT_CHAT_PROVIDER[provider]}:{name}", temperature=_TEMPERATURE)


def get_model(role: Role = "main", settings: Settings | None = None) -> BaseChatModel:
    """Constrói o chat model para o papel ('main' ou 'subagent')."""
    settings = settings or get_settings()
    provider, name = _resolve(role, settings)
    return _build(provider, name, settings)


def describe_model(role: Role = "main", settings: Settings | None = None) -> str:
    """String legível 'provider:modelo' — usada no PredictionResponse e logs."""
    settings = settings or get_settings()
    provider, name = _resolve(role, settings)
    return f"{provider}:{name}"
