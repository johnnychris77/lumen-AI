# Hosted Backend Quickstart

## Purpose

This guide explains how to validate LumenAI after the backend is deployed to a real hosted service such as Render, Railway, or Fly.io.

## Local Test

Use local API:

export HOSTED_BASE_URL=http://127.0.0.1:18011
export TOKEN=dev-token

scripts/check-hosted-demo.sh

## Hosted Test

After deployment, replace the URL with your real hosted backend:

export HOSTED_BASE_URL=https://your-real-hosted-api-url
export TOKEN=your-demo-token

scripts/check-hosted-demo.sh

## Seed Hosted Demo

scripts/seed-hosted-demo.sh

## Update Public Demo Links

scripts/update-public-demo-links.sh
