"""Gradio Space (Hugging Face) — UI BYOK do deep-pitch.

Reusa o core (service.run_prediction). O usuário escolhe o provider e cola a
própria key (BYOK) — usada só na requisição, nunca armazenada. Este arquivo é o
entrypoint do HF Space (sdk: gradio). A API FastAPI (deep_pitch.api) continua
disponível para outros hosts.
"""

from __future__ import annotations

import os
import sys

# torna o pacote deep_pitch importável no Space (código em src/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import gradio as gr  # noqa: E402

from deep_pitch.config import get_settings  # noqa: E402
from deep_pitch.config.models import _PROVIDER_KEY  # noqa: E402
from deep_pitch.domain import MatchRequest  # noqa: E402
from deep_pitch.service import run_prediction  # noqa: E402

_PROVIDERS = ["anthropic", "google", "groq", "openrouter", "nvidia"]


def _byok_settings(provider: str, api_key: str):
    field, _ = _PROVIDER_KEY[provider]
    return get_settings().model_copy(update={"model_provider": provider, field: api_key})


def _predict(home, away, neutral, context, provider, api_key):
    if not (home and away):
        return "⚠️ Informe os dois times (nomes em inglês)."
    if not api_key:
        return "⚠️ Cole sua API key do provider escolhido (BYOK)."
    try:
        p = run_prediction(
            MatchRequest(home=home, away=away, neutral=neutral, context=context or None),
            _byok_settings(provider, api_key),
        )
    except Exception as exc:  # provider/key inválido, rede, etc.
        return f"❌ Erro: {exc}"

    pr = p.probabilities
    fatores = "\n".join(f"- {f}" for f in p.key_factors)
    fontes = ", ".join(p.sources[:8])
    return (
        f"## {p.winner} — {p.scoreline}\n"
        f"**Confiança:** {p.confidence:.0%}\n\n"
        f"| {p.home} | Empate | {p.away} |\n|:--:|:--:|:--:|\n"
        f"| {pr.home_win:.0%} | {pr.draw:.0%} | {pr.away_win:.0%} |\n\n"
        f"**Fatores decisivos:**\n{fatores}\n\n---\n{p.rationale}\n\n**Fontes:** {fontes}"
    )


with gr.Blocks(title="deep-pitch") as demo:
    gr.Markdown(
        "# ⚽ deep-pitch\n"
        "Deep Agent que prevê os mata-matas da **Copa 2026** juntando modelo estatístico "
        "(Dixon-Coles), dados ao vivo e notícia — e explica o porquê."
    )
    with gr.Row():
        home = gr.Textbox(label="Mandante (inglês)", value="Argentina")
        away = gr.Textbox(label="Visitante (inglês)", value="Switzerland")
    with gr.Row():
        context = gr.Textbox(label="Contexto (opcional)", placeholder="ex.: quarterfinal")
        neutral = gr.Checkbox(label="Sede neutra", value=True)
    with gr.Row():
        provider = gr.Dropdown(_PROVIDERS, label="Provider (seu modelo)", value="anthropic")
        api_key = gr.Textbox(label="Sua API key (BYOK)", type="password")
    gr.Markdown("🔒 Sua chave é usada só nesta requisição — nunca armazenada nem logada.")
    btn = gr.Button("Prever", variant="primary")
    out = gr.Markdown()
    btn.click(_predict, [home, away, neutral, context, provider, api_key], out)

demo.queue()

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
