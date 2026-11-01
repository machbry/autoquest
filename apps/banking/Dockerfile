# Build from the repo root (the uv workspace): docker build -f apps/banking/Dockerfile .
FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /bin/uv
# The venv path must match the final image: its scripts hard-code it.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /repo
COPY pyproject.toml uv.lock ./
COPY apps/banking apps/banking
RUN uv sync --locked --no-dev --no-editable --package banking

FROM python:3.13-slim
RUN useradd --system --uid 10001 banking
COPY --from=build /app/.venv /app/.venv
COPY apps/banking/alembic.ini /app/alembic.ini
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
USER banking
EXPOSE 8000
# Cloud Run sets PORT.
CMD ["sh", "-c", "exec uvicorn banking.main:app --host 0.0.0.0 --port \"$PORT\""]
