FROM python:3.13-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends git libgomp1 && \
    rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir uv==0.11.32

FROM base AS core-dependencies

COPY pyproject.toml uv.lock setup.py README.md ./

RUN uv sync --frozen --no-dev --no-install-project

FROM core-dependencies AS core

COPY . .

RUN uv sync --frozen --no-dev

CMD ["python", "-m", "src.pipeline.run_pipeline", "--config", "config/default.yaml"]

FROM core AS test

RUN uv sync --frozen --extra dev

FROM base AS legacy-dependencies

COPY pyproject.toml uv.lock setup.py README.md ./

RUN uv sync --frozen --no-dev --extra legacy --no-install-project

FROM legacy-dependencies AS legacy

COPY . .

RUN uv sync --frozen --no-dev --extra legacy

CMD ["python", "-m", "src.pipeline.run_pipeline", "--config", "config/default.yaml"]

# Keep the default Docker build focused on the canonical agent-first runtime.
FROM core AS runtime
