# LumenAI CORS Hardening Plan v1

## Status

Ready for engineering implementation.

## Purpose

This document defines the LumenAI production CORS hardening approach.

CORS must be restricted so only trusted frontend origins can call the LumenAI backend API from browsers.

## Current Risk

If production CORS allows wildcard origins or broad unknown origins, untrusted websites may call LumenAI backend APIs from a browser context.

## Production Allowed Origin

The production frontend origin should be:

- `https://lumen-ai-1.onrender.com`

## Development Allowed Origins

Development may allow:

- `http://localhost:5173`
- `http://localhost:5174`
- `http://localhost:5175`
- `http://localhost:5176`
- `http://localhost:5177`
- `http://localhost:5178`

## Engineering Standard

Production:

- No wildcard CORS
- No broad unknown origins
- Only trusted production frontend origins

Development:

- Localhost Vite ports may be allowed
- Development origins should not be used in production unless explicitly required

## Acceptance Criteria

- Production `ALLOWED_ORIGINS` is set to `https://lumen-ai-1.onrender.com`
- Backend CORS middleware reads allowed origins from environment config
- Wildcard origin is not used in production
- Public module status endpoint still works from the frontend
- Protected enterprise APIs remain protected by auth and RBAC

## Final Statement

LumenAI CORS hardening reduces browser-based API exposure risk and supports enterprise-grade deployment readiness.
