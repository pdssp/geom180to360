# -*- coding: utf-8 -*-
# geom180to360 - Conversion tool of geometries from longitudes [-180, 180] to [0, 360]
# Copyright (C) 2026 - CNES (Jean-Christophe MALAPERT for P)
# This file is part of geom180to360 <https://gitlab.cnes.fr/pdssp/common/geom180to360>
# SPDX-License-Identifier: Apache-2.0
ARG BASE_IMAGE_REPO
ARG PYTHON_VERSION=3.12
FROM ${BASE_IMAGE_REPO:-ghcr.io}/astral-sh/uv:0.11.10-python${PYTHON_VERSION}-trixie AS builder

# hadolint ignore=DL3008
RUN --mount=type=secret,id=ca_cert,required=false \
      apt-get update -qq \
      && apt-get upgrade --yes \
      && apt-get -y --no-install-recommends install ca-certificates build-essential git \
      && if [ -f /run/secrets/ca_cert ]; then \
      cp /run/secrets/ca_cert /usr/local/share/ca-certificates/custom-ca.crt; \
      fi \
      && update-ca-certificates \
      && apt-get clean \
      && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
      UV_LINK_MODE=copy \
      UV_NO_CACHE=1 \
      UV_SYSTEM_CERTS=true

WORKDIR /app

COPY pyproject.toml README.md ./
RUN --mount=type=secret,id=pip_index_url,required=false \
      if [ -f /run/secrets/pip_index_url ]; then \
      PIP_INDEX_URL="$(cat /run/secrets/pip_index_url)"; \
      export PIP_INDEX_URL; \
      fi \
      && uv sync --no-dev --no-install-project

COPY src/ ./src/

RUN --mount=type=secret,id=pip_index_url,required=false \
      if [ -f /run/secrets/pip_index_url ]; then \
      PIP_INDEX_URL="$(cat /run/secrets/pip_index_url)"; \
      export PIP_INDEX_URL; \
      fi \
      && uv sync --no-dev

FROM ${BASE_IMAGE_REPO:-docker.io}/python:${PYTHON_VERSION}-trixie AS runtime

ARG VERSION=0.1.0
ARG BUILD_DATE="unknown"

LABEL org.opencontainers.image.title="geom180to360" \
      org.opencontainers.image.description="Conversion tool of geometries from longitudes [-180, 180] to [0, 360]" \
      org.opencontainers.image.authors="Jean-Christophe MALAPERT <jean-christophe.malapert@cnes.fr>" \
      org.opencontainers.image.vendor="CNES" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://gitlab.cnes.fr/pdssp/common/geom180to360" \
      org.opencontainers.image.documentation="https://pdssp.pages.cnes.fr/common/geom180to360" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.ref.name="pdssp/geom180to360"

# hadolint ignore=DL3008
RUN apt-get update -qq \
      && apt-get upgrade --yes \
      && apt-get clean \
      && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app /app

USER 1000:1000

WORKDIR /app

ENTRYPOINT ["/app/.venv/bin/geom180to360"]