# Deploy

O app é um FastAPI (Docker) que serve o frontend BYOK + a API. Precisa de um host
que rode **Python + request longo** (uma previsão leva 30s–2min). Serverless de
frontend (Vercel/Netlify) **não** serve — use um host de container.

## Opção recomendada: Hugging Face Gradio Space (grátis)

O SDK **Docker** do HF virou **pago**; o **Gradio** é grátis (free tier 16 GB,
URL pública `*.hf.space`). O `app.py` é uma UI Gradio que reusa o core com BYOK;
o script `scripts/deploy-hf.sh` automatiza o push.

1. huggingface.co/new-space → nome `deep-pitch` → **SDK: Gradio** → template
   **Blank** → **Public** → Create.
2. Na raiz do repo:
   ```bash
   bash scripts/deploy-hf.sh <seu-usuario>
   ```
   Copia `app.py` + `requirements.txt` + `src/`, gera o README com frontmatter
   `sdk: gradio`, e faz push (pede usuário HF + token **Write**).
3. HF builda (~5 min). Em **Settings → Variables and secrets**, opcional
   server-side: `FOOTBALL_DATA_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_TRACING=true`.
   **BYOK não exige key de LLM no servidor** (o usuário traz a dele no form).

A API FastAPI (`deep_pitch.api`, Dockerfile) continua para hosts que suportam
container (Fly / VPS / pago).

## Alternativas

| Host | Grátis? | Domínio custom | Nota |
|---|---|---|---|
| **HF Gradio Space** | ✅ (16 GB) | ❌ (`*.hf.space`) | Docker SDK é pago; Gradio é free |
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
