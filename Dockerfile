# deep-pitch — imagem de produção (FastAPI serve frontend + API).
# Deploy: Railway / Render / Fly / qualquer host Docker (request longo OK).
FROM python:3.12-slim

# uv (gerenciador de deps)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# build-essential garante compilar penaltyblog (Cython) se não houver wheel linux
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# deps primeiro (cache de layer)
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

ENV PORT=8000
EXPOSE 8000

# host 0.0.0.0 + porta do provedor ($PORT) — shell form p/ expandir a env
CMD uv run uvicorn deep_pitch.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
