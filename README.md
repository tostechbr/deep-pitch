# ⚽ deep-pitch

**Deep Agent que prevê os mata-matas da Copa do Mundo 2026 — e explica o *porquê*.**

Não é "mais um modelo de xG". É um agente que raciocina como analista: parte de
um prior estatístico defensável, ajusta com o estado atual do torneio (lesões,
forma, escalação) e diz exatamente qual fator moveu a previsão.

> Construído com **Deep Agents** (LangChain) · **model-agnostic** (Claude, Gemini,
> Groq, OpenRouter, NVIDIA) · observável via **LangSmith / LangGraph Studio**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## A tese

Um modelo estatístico puro (Dixon-Coles, Elo) não enxerga uma virose no elenco na
véspera do jogo. Um LLM puro chuta com confiança e erra a conta. **deep-pitch junta
os dois:**

```
historian ──▶ prior estatístico   (Dixon-Coles sobre 49k jogos reais)
scout     ──▶ estado ao vivo       (football-data.org + busca: lesão/forma/notícia)
                     │
                     ▼
          reconcile (código) ──▶ probabilidades + confiança
                     │
                     ▼
        agente principal ──▶ Prediction + rationale explicado
```

O agente **classifica** (qual fator, quão forte); o **código calcula** (aplica ao
prior, normaliza, deriva a confiança). LLM raciocina, código computa.

## Funciona hoje

Baseline estatístico, sem LLM:

```console
$ deep-pitch baseline "Norway" "England"
Norway 28%  |  empate 27%  |  England 44%
placar provável 1-1 (xG 1.2–1.5) · 7803 jogos desde 2018
```

Previsão completa via Deep Agent (reconcilia estatística + ao vivo + notícia):

```console
$ deep-pitch predict "Norway" "England" --context semifinal
Norway 35%  |  empate 20%  |  England 45%
Vencedor: England (1-2) · confiança 57%

## Ponto de partida (prior Dixon-Coles)
England favorita (44%)...
## Ajuste ao vivo
Surto de virose no elenco inglês (Rice, Guehi em dúvida) [fonte: metro.co.uk]...
```

## Rodando

```bash
uv sync                              # instala (Python 3.12)
cp .env.example .env                 # configure 1 provider de LLM (p/ o agente)
uv run pytest                        # 73 testes, ~96% de cobertura
uv run deep-pitch baseline "Argentina" "Switzerland"   # não precisa de LLM
uv run deep-pitch predict  "Argentina" "Switzerland"   # agente completo
uv run deep-pitch serve                                # API em :8000
```

O `baseline` roda sem chave. O `predict`/API precisam de um provider — Gemini,
Groq, OpenRouter e NVIDIA têm free tier (ver `.env.example`).

### API

```bash
curl -X POST localhost:8000/predict \
  -H 'content-type: application/json' \
  -d '{"home":"Norway","away":"England","neutral":true,"context":"semifinal"}'
```

### Ver o agente pensar (LangGraph Studio)

```bash
uv run langgraph dev
```

Abre o **LangGraph Studio** no browser: o grafo do agente, rodável dali, com o
passo a passo — planejamento → delegação a `scout`/`historian` → cada tool
(`baseline_prediction`, `web_search`, `live_feed`, `reconcile`) → `Prediction`.
Com `LANGSMITH_API_KEY` setada, cada run também vira um trace no LangSmith.

## Arquitetura

```
config/    settings + factory de modelo (5 providers + modo 'free' com fallback) + observability
data/      loader do dataset martj42 (cache, degradação graciosa)
tools/     baseline Dixon-Coles · head_to_head · web_search · live_feed · reconcile (determinístico)
prompts/   system / scout / historian (.md, fora do código)
subagents/ scout (ao vivo) · historian (estatística)
agent/     build_agent (create_deep_agent) + graph (langgraph.json)
domain/    contratos Pydantic (Prediction, ...)
service/   run_prediction — transport-agnostic
api/       FastAPI · cli.py — CLI Typer
```

Núcleo transport-agnostic: **CLI, API e `langgraph dev` consomem o mesmo `service`.**

## Model-agnostic

Escolha por `.env` (`MODEL_PROVIDER`): `anthropic` (melhor tool-calling) · `google`
· `groq` · `openrouter` · `nvidia` · **`free`** (cadeia de fallback entre os grátis —
sobrevive a rate limit). Modelo diferente por papel (main forte, subagents baratos).

## Desenvolvido com eval

Este agente foi refinado por um **eval comportamental** (juízes LLM avaliando o
raciocínio, não o placar). O eval flagrou que o LLM **errava a aritmética** dos
ajustes ("+4pp" mas o número ia pro lado oposto) e emitia **falsa precisão**. Fix:
a tool `reconcile` tirou toda a conta do LLM — ele só classifica (`favors`,
`impact`, `shootout`), o código aplica e normaliza. Bug eliminado por construção,
coberto por unit test.

## Fontes de dados (open-source)

- [martj42/international_results](https://github.com/martj42/international_results) — resultados de seleções desde 1872 (CC0), inclui a Copa 2026
- [penaltyblog](https://github.com/martineastwood/penaltyblog) — Dixon-Coles / Poisson / Elo (MIT)
- [football-data.org](https://www.football-data.org/) — feed ao vivo (free tier cobre a Copa)

## Roadmap

- [x] Config model-agnostic (5 providers + `free`)
- [x] Baseline Dixon-Coles + tools ao vivo
- [x] Deep Agent (scout + historian + reconcile) + eval comportamental
- [x] API FastAPI + CLI + LangGraph Studio
- [ ] Backtest vs Opta Supercomputer / benchmarks
- [ ] Elo como segundo prior

## Licença

MIT — veja [LICENSE](LICENSE).
