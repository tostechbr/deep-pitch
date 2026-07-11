"""Carrega prompts de arquivos .md (versionáveis, editáveis fora do código)."""

from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Lê prompts/<name>.md. Ex.: load_prompt('system')."""
    return (_DIR / f"{name}.md").read_text(encoding="utf-8")
