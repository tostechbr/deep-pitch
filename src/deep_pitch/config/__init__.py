"""Camada de configuração: settings, factory de modelo, observability."""

from .models import describe_model, get_model
from .observability import configure_environment
from .settings import Settings, get_settings

__all__ = [
    "Settings",
    "get_settings",
    "get_model",
    "describe_model",
    "configure_environment",
]
