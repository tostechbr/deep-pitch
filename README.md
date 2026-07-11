# ⚽ deep-pitch

**Deep Agent que prevê os mata-matas da Copa 2026** e explica o *porquê* de cada previsão.

A ideia: raciocinar como analista, não como "mais um modelo de xG". Partir de um
prior estatístico (Dixon-Coles), ajustar com o estado do torneio (lesões, forma,
escalação) e comparar com benchmarks (Opta Supercomputer, Hicruben).

**Stack:** Deep Agents (LangChain) · model-agnostic (Claude, Gemini, Groq, OpenRouter, NVIDIA) · observável via LangSmith.

---

## Funciona hoje

O baseline estatístico já roda — ajustado em **~49k resultados reais de seleções**
(martj42, desde 1872, atualizado diariamente), com decaimento temporal. Exemplo
real (semifinal, dado de 11/07/2026):

```
$ deep-pitch baseline "Norway" "England"
Norway 28%  |  empate 27%  |  England 44%
placar provável 1-1 (xG 1.2–1.5) · 7803 jogos desde 2018
```

## Rodando

```bash
uv sync                       # instala (Python 3.12)
cp .env.example .env          # configure ao menos 1 provider de LLM (p/ o agente)
uv run pytest                 # 33 testes, ~98% de cobertura
uv run deep-pitch baseline "Argentina" "Switzerland"
```

O baseline não precisa de chave de LLM. O agente completo (abaixo) precisa de
um provider — veja `.env.example` (Gemini/Groq/OpenRouter/NVIDIA têm free tier).

## Arquitetura

```
config/    settings + factory de modelo (5 providers + fallback grátis) + observability
data/      loader do dataset martj42 (cache, degradação graciosa)
tools/     baseline Dixon-Coles (o "modelo pequeno") + H2H  [em breve: busca, feed ao vivo]
```

Camada `core` transport-agnostic; API (FastAPI) e CLI consomem o mesmo núcleo.

## Roadmap

- [x] Camada de config model-agnostic (Claude/Gemini/Groq/OpenRouter/NVIDIA + modo `free`)
- [x] Loader do dataset martj42 + baseline Dixon-Coles
- [ ] Tools ao vivo: football-data.org (bracket/forma) + busca qualitativa
- [ ] Deep Agent: subagents `scout` + `historian` reconciliando prior + estado ao vivo
- [ ] API FastAPI + previsão estruturada
- [ ] Backtest vs Opta / Hicruben

> 🚧 Em construção, por etapas. A parte "Deep Agent" acima ainda está sendo montada;
> o que roda hoje é o baseline estatístico.

## Licença

MIT — veja [LICENSE](LICENSE).
