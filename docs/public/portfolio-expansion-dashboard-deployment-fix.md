# LumenAI Dashboard Deployment Rewrite Fix

## Issue

The public portfolio pages deployed correctly, but the direct deployed dashboard route did not open:

- `/dashboard`

## Cause

The dashboard is a React/Vite client-side route. Static hosting requires a rewrite so direct requests to `/dashboard` return the frontend `index.html`.

## Fix

Added frontend static rewrite file:

- `frontend/public/_redirects`

Routes covered:

- `/dashboard`
- `/dashboard/*`

## Expected Result

After deployment, the public dashboard route should open:

- `https://lumen-ai-1.onrender.com/dashboard`
