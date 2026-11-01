# Renders apps/*/docs/architecture.py to PNG. Graphviz lives here so devs only need Docker.
FROM ghcr.io/astral-sh/uv:0.13.6-python3.14-trixie-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends graphviz \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN uv pip install --system --no-cache --require-hashes -r /tmp/requirements.txt
