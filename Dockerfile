# SafeRoute-RAG — Hugging Face Spaces (Docker + uv)
# https://huggingface.co/docs/hub/spaces-sdks-docker

FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    HF_HOME=/app/.cache/huggingface \
    PYTHONPATH=/app

# Install dependencies first (layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Application code + demo corpus
COPY . .

# Pre-download ruri-small + ingest manifest into chroma_db (baked into image)
RUN uv run python scripts/bootstrap_kb.py

EXPOSE 7860

CMD ["uv", "run", "streamlit", "run", "app.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
