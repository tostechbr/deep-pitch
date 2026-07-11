"""Configuração central via variáveis de ambiente (.env).

Fonte única de verdade para chaves, provider de modelo e parâmetros.
Lê de os.environ E de .env (pydantic-settings), então funciona tanto com
shell exports quanto com arquivo .env.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["anthropic", "google", "groq", "openrouter", "nvidia", "free"]

# CSV canônico de resultados de seleções (martj42, CC0) — inclui a Copa 2026.
MARTJ42_RESULTS_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)


class Settings(BaseSettings):
    """Configuração imutável da aplicação (carregada uma vez)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Cérebro do agente (LLM) ---
    model_provider: Provider = "anthropic"
    model_name: str | None = None  # override global; senão default do provider

    # Override por PAPEL (opcional). Se None, herda model_provider/model_name.
    # main = síntese final (forte); subagent = scout/historian (barato/rápido).
    main_provider: Provider | None = None
    main_model_name: str | None = None
    subagent_provider: Provider | None = None
    subagent_model_name: str | None = None

    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    groq_api_key: str | None = None
    openrouter_api_key: str | None = None
    nvidia_api_key: str | None = None

    # --- Feed ao vivo / busca ---
    football_data_api_key: str | None = None
    football_data_competition: str = "WC"  # código da Copa em football-data.org v4
    tavily_api_key: str | None = None

    # Ordem da cadeia de fallback quando provider="free" (CSV). Só providers
    # com key setada entram na cadeia; um estoura rate limit → cai pro próximo.
    free_chain: str = "groq,google,nvidia,openrouter"

    # --- Observabilidade (LangSmith) ---
    langsmith_api_key: str | None = None
    langsmith_tracing: bool = False
    langsmith_project: str = "wc2026-analyst"

    # --- Dados / baseline ---
    results_url: str = MARTJ42_RESULTS_URL
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".cache" / "deep-pitch")
    cache_ttl_hours: int = 12
    history_years: int = 8  # janela de treino do Dixon-Coles (recência)

    # --- Rede ---
    request_timeout: float = 30.0

    @property
    def free_chain_list(self) -> list[str]:
        """Providers da cadeia free, na ordem (CSV parseado)."""
        return [p.strip() for p in self.free_chain.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    """Retorna a configuração (cacheada). Chame em vez de instanciar Settings().

    Carrega .env com override=True: o .env do projeto MANDA sobre variáveis de
    shell. Sem isso, uma ANTHROPIC_API_KEY velha exportada no shell mascararia a
    do .env (env de shell vence .env por padrão no pydantic-settings).
    """
    from dotenv import load_dotenv

    load_dotenv(override=True)
    return Settings()
