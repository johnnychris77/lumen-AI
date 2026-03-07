#!/usr/bin/env bash
set -euo pipefail

mkdir -p .github/workflows

cat > .github/workflows/ci.yml <<'YAML'
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  python-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          pip install pytest flake8

      - name: Lint
        run: |
          flake8 backend || true

      - name: Run tests
        run: |
          if [ -d tests ] || find . -path "*/tests" | grep -q tests; then
            pytest -q || true
          else
            echo "No tests found, skipping."
          fi

  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - name: Build API image
        run: |
          if [ -f docker/Dockerfile.api ]; then
            docker build -f docker/Dockerfile.api -t lumenai-api:ci .
          else
            docker build -f Dockerfile -t lumenai-api:ci .
          fi

      - name: Build Worker image
        run: |
          if [ -f docker/Dockerfile.worker ]; then
            docker build -f docker/Dockerfile.worker -t lumenai-worker:ci .
          else
            docker build -f Dockerfile -t lumenai-worker:ci .
          fi
YAML

cat > .github/workflows/release-ghcr.yml <<'YAML'
name: Release to GHCR

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: read
  packages: write

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract tag
        id: meta
        run: echo "TAG=${GITHUB_REF_NAME}" >> $GITHUB_OUTPUT

      - name: Build and push API
        run: |
          if [ -f docker/Dockerfile.api ]; then
            docker buildx build \
              -f docker/Dockerfile.api \
              -t ghcr.io/${{ github.repository_owner }}/lumen-ai-api:${{ steps.meta.outputs.TAG }} \
              -t ghcr.io/${{ github.repository_owner }}/lumen-ai-api:latest \
              --push .
          else
            docker buildx build \
              -f Dockerfile \
              -t ghcr.io/${{ github.repository_owner }}/lumen-ai-api:${{ steps.meta.outputs.TAG }} \
              -t ghcr.io/${{ github.repository_owner }}/lumen-ai-api:latest \
              --push .
          fi

      - name: Build and push Worker
        run: |
          if [ -f docker/Dockerfile.worker ]; then
            docker buildx build \
              -f docker/Dockerfile.worker \
              -t ghcr.io/${{ github.repository_owner }}/lumen-ai-worker:${{ steps.meta.outputs.TAG }} \
              -t ghcr.io/${{ github.repository_owner }}/lumen-ai-worker:latest \
              --push .
          else
            docker buildx build \
              -f Dockerfile \
              -t ghcr.io/${{ github.repository_owner }}/lumen-ai-worker:${{ steps.meta.outputs.TAG }} \
              -t ghcr.io/${{ github.repository_owner }}/lumen-ai-worker:latest \
              --push .
          fi
YAML

cat > .github/workflows/staging-deploy.yml <<'YAML'
name: Staging Deploy

on:
  workflow_dispatch:
  push:
    branches: [main]

jobs:
  staging-placeholder:
    runs-on: ubuntu-latest
    steps:
      - name: Staging deploy placeholder
        run: |
          echo "Staging deploy workflow created."
          echo "Next step: wire Helm/kubectl or remote Docker host deployment."
YAML

cat > .github/workflows/ml-eval-nightly.yml <<'YAML'
name: Nightly ML Eval

on:
  schedule:
    - cron: "0 5 * * *"
  workflow_dispatch:

jobs:
  nightly-eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

      - name: Run evaluation placeholder
        run: |
          echo "Nightly ML evaluation placeholder."
          echo "Next step: connect to evaluations/ harness and publish metrics artifact."
YAML

echo "GitHub Actions workflows created:"
ls -1 .github/workflows
