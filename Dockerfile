FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS base

LABEL maintainer="pol.lopez.cano@gmail.com" \
      description="FastAPI Template Application" \
      version="0.1.0"

WORKDIR /app

RUN groupadd -r app && useradd -r -g app -m -d /home/app app

FROM base AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

ARG INSTALL_DEV=false

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    if [ "$INSTALL_DEV" = "true" ]; then \
        uv sync --locked --no-install-project; \
    else \
        uv sync --locked --no-install-project --no-dev; \
    fi

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$INSTALL_DEV" = "true" ]; then \
        uv sync --locked; \
    else \
        uv sync --locked --no-dev; \
    fi

FROM base AS runner

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    ENVIRONMENT=production

USER app

EXPOSE 80
