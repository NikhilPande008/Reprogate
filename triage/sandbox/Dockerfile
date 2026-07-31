FROM python:3.12-slim-bookworm AS python

FROM node:22-bookworm-slim

ARG UV_VERSION=0.7.20
ARG POETRY_VERSION=2.1.3

COPY --from=python /usr/local /usr/local

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir "uv==${UV_VERSION}" "poetry==${POETRY_VERSION}" \
    && npm install -g @openai/codex

WORKDIR /workspace/repo
