# LumenAI GitHub Pages Setup

## Purpose

This publishes the LumenAI public demo landing page from:

docs/public-demo/

to GitHub Pages using GitHub Actions.

## GitHub Repository Settings

In GitHub:

1. Open the LumenAI repository.
2. Go to Settings.
3. Go to Pages.
4. Under Build and deployment, set Source to GitHub Actions.
5. Save.

## Workflow

The workflow file is:

.github/workflows/github-pages-demo.yml

It runs when files under docs/public-demo/ change, or when manually triggered.

## Expected Public URL

After GitHub Pages is enabled, the public site should be available at:

https://johnnychris77.github.io/lumen-AI/

## Local Preview

If port 9091 is free:

python -m http.server 9091 -d docs/public-demo

Then open:

http://127.0.0.1:9091

If 9091 is already in use, try:

python -m http.server 9092 -d docs/public-demo

Then open:

http://127.0.0.1:9092
