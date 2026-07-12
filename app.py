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
from deep_pitch.config.tracing import build_tracer  # noqa: E402
from deep_pitch.domain import MatchRequest  # noqa: E402
from deep_pitch.service import stream_prediction  # noqa: E402

_PROVIDERS = ["anthropic", "google", "groq", "openrouter", "nvidia"]

# Modelos sugeridos por provider (dropdown). "" = usa o padrão do provider.
_MODELS = {
    "anthropic": ["claude-sonnet-5", "claude-opus-4-8", "claude-haiku-4-5-20251001"],
    "google": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"],
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
    "openrouter": ["meta-llama/llama-3.3-70b-instruct:free", "deepseek/deepseek-chat"],
    "nvidia": ["meta/llama-3.3-70b-instruct", "deepseek-ai/deepseek-r1"],
}


def _byok_settings(provider: str, api_key: str, model: str = ""):
    field, _ = _PROVIDER_KEY[provider]
    update = {"model_provider": provider, field: api_key}
    if model.strip():
        update["model_name"] = model.strip()
    return get_settings().model_copy(update=update)


def _tree_md(events, done: bool = False) -> str:
    """Árvore ao vivo dos passos CRUS do agente (igual Studio) — só organizada.

    Agrupa por (profundidade, agente) na ordem de 1ª aparição e deduplica tools.
    Nada é personalizado: nomes de agente/tool vêm direto do framework.
    """
    head = "### Raciocínio do agente\n" if done else "### Analisando (ao vivo)\n"
    if not events:
        return head + "\n- iniciando…"

    groups: list[list] = []  # [depth, agent, [tools]]
    index: dict[tuple, int] = {}
    for ev in events:
        key = (ev.depth, ev.agent)
        if key not in index:
            index[key] = len(groups)
            groups.append([ev.depth, ev.agent, []])
        tools = groups[index[key]][2]
        if ev.tool not in tools:
            tools.append(ev.tool)

    lines: list[str] = []
    for depth, agent, tools in groups:
        pad = "&nbsp;&nbsp;&nbsp;&nbsp;" * depth
        lines.append(f"{pad}**{agent or 'agente'}**  ")
        for tool in tools:
            lines.append(f"{pad}- `{tool}`  ")
    return head + "\n" + "\n".join(lines)


def _result_md(p) -> str:
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


def _predict(home, away, neutral, context, provider, model, api_key, langsmith_key):
    # generator: mostra os passos do agente em tempo real (stream), depois o resultado
    if not (home and away):
        yield "Informe os dois times (nomes em inglês)."
        return
    if not api_key:
        yield "Cole sua API key do provider escolhido (BYOK)."
        return

    events: list = []
    yield _tree_md(events)
    prediction = None
    try:
        tracer = build_tracer(langsmith_key)  # trace no LangSmith do usuário, se der a key
        for event in stream_prediction(
            MatchRequest(home=home, away=away, neutral=neutral, context=context or None),
            _byok_settings(provider, api_key, model),
            callbacks=[tracer] if tracer else None,
        ):
            if event.kind == "step":
                events.append(event)
                yield _tree_md(events)
            elif event.kind == "result":
                prediction = event.prediction
    except Exception as exc:  # provider/key inválido, rede, etc.
        yield f"Erro: {exc}"
        return

    if prediction is None:
        yield "Erro: o agente não retornou uma previsão."
        return

    # resultado + o rastro do que o agente fez (transparência estilo Studio)
    yield _tree_md(events, done=True) + "\n\n---\n\n" + _result_md(prediction)


with gr.Blocks(title="deep-pitch") as demo:
    gr.Markdown(
        "# deep-pitch\n"
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
        provider = gr.Dropdown(_PROVIDERS, label="Provider", value="anthropic")
        model = gr.Dropdown(
            [""] + _MODELS["anthropic"],
            value="",
            label="Modelo (vazio = padrão do provider)",
            allow_custom_value=True,  # dá pra digitar um id fora da lista
        )
    api_key = gr.Textbox(label="Sua API key (BYOK)", type="password")
    langsmith_key = gr.Textbox(
        label="LangSmith key (opcional)",
        type="password",
        placeholder="lsv2_... → veja o trace do agente no SEU dashboard LangSmith",
    )
    gr.Markdown("Suas chaves são usadas só nesta requisição — nunca armazenadas nem logadas.")
    btn = gr.Button("Prever", variant="primary")
    out = gr.Markdown()

    # troca a lista de modelos conforme o provider
    provider.change(
        lambda p: gr.update(choices=[""] + _MODELS.get(p, []), value=""), provider, model
    )
    btn.click(
        _predict,
        [home, away, neutral, context, provider, model, api_key, langsmith_key],
        out,
    )

demo.queue()

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
