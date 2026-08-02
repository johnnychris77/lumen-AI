# Marketing Website — Performance Review

**Date:** 2026-08-02 • Method: production `build:site` output. Lighthouse not run.

## Measured bundle (gzip) from `npm run build:site`
| Asset | Raw | Gzip |
|---|---:|---:|
| `vendor-charts-*.js` | 449.5 kB | **136.8 kB** |
| `marketing-*.js` | 151.7 kB | 41.9 kB |
| `vendor-react-*.js` | 68.4 kB | 24.5 kB |
| `marketing-*.css` | ~74.8 kB | ~13.4 kB |

## Observations & recommendations
- **Charts vendor is the largest cost (137 kB gzip).** It is only used on the
  Platform "dashboard preview" and the workflow demo report. **Recommendation
  (non-blocking):** route/lazy-load the charts so the Home/Problem/Security/About
  pages don't pay for it. Deferred — not required for launch.
- SVG social card + WEBVTT are the only media; no large raster hero images. PASS.
- Fonts: verify `font-display: swap` on any custom font (system stack is otherwise fine).
- No render-blocking third-party scripts (analytics stays inert; `VITE_ANALYTICS_PROVIDER=none`).

**Status:** acceptable for launch; charts code-splitting is the one worthwhile follow-up.
