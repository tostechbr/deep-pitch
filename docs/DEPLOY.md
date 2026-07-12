# Deploy

O app é um FastAPI (Docker) que serve o frontend BYOK + a API. Precisa de um host
que rode **Python + request longo** (uma previsão leva 30s–2min). Serverless de
frontend (Vercel/Netlify) **não** serve — use um host de container.

## Opção recomendada: Hugging Face Spaces (grátis)

Free tier com 16 GB RAM (aguenta langchain + pandas + penaltyblog), Docker nativo,
URL pública compartilhável (`*.hf.space`).

1. huggingface.co → **New Space** → nome `deep-pitch` → **SDK: Docker** → Public.
2. O Space nasce com um `README.md` que tem o frontmatter abaixo — **mantenha-o**
   (é o que diz ao HF que é Docker na porta 7860):
   ```yaml
   ---
   title: deep-pitch
   emoji: ⚽
   sdk: docker
   app_port: 7860
   pinned: false
   ---
   ```
3. Suba o código para o repo do Space (mantendo o README do Space):
   ```bash
   git clone https://huggingface.co/spaces/<seu-usuario>/deep-pitch hf-space
   cp -r Dockerfile pyproject.toml uv.lock src hf-space/
   cd hf-space && git add . && git commit -m "deep-pitch" && git push
   ```
4. O HF builda o Dockerfile. Em **Settings → Variables and secrets**, adicione o
   que quiser server-side: `FOOTBALL_DATA_API_KEY`, `LANGSMITH_API_KEY`,
   `LANGSMITH_TRACING=true`. **BYOK não exige key de LLM no servidor** (o usuário
   traz a dele no form).

## Alternativas

| Host | Grátis? | Domínio custom | Nota |
|---|---|---|---|
| **HF Spaces** | ✅ (16 GB) | ❌ (`*.hf.space`) | melhor free p/ app pesado |
| **Render** | ✅ (512 MB, cold start) | ✅ grátis | 512 MB pode dar OOM no nosso stack |
| **Fly.io** | ~grátis (allowance) | ✅ | bom controle |
| **Railway** | ❌ (trial acabou, pago) | ✅ | ~US$5/mês |
| **Hostinger VPS** | ❌ (pago) | ✅ (domínio `ocaum`) | máximo controle; Docker + teu domínio num lugar |

## Domínio `ocaum` (Hostinger)

Custom domain precisa de host que suporte (Render/Fly/Railway/VPS — não o HF free).
No painel do host: adicione o domínio → ele dá um CNAME/A → no **Hostinger → DNS**,
crie o registro apontando `deep-pitch.ocaum.<tld>` para esse alvo. SSL é automático
na maioria dos hosts.

Se tiver um **VPS Hostinger**, é a opção de maior controle: Docker + domínio no
mesmo lugar que tu administras.

## Nota de produção (público)

Como é BYOK, ninguém gasta tua grana de LLM. Mas o `live_feed` usa **tua** key
football-data (10 req/min) — sob tráfego, considere **rate-limit por IP** no
`/predict`.
