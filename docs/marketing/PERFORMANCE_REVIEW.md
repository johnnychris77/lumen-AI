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
- **Charts code-split — DONE.** recharts/d3 (~137 kB gzip) were previously
  eager-preloaded on every page. `DashboardPreview` is now `React.lazy`-loaded and
  the manual `vendor-charts` chunk grouping was removed, so charts fold into an
  async chunk that loads **only** on the Platform page. Initial critical JS drops
  from ~204 kB → ~113 kB gzip (verified: `index.html` no longer preloads any
  charts chunk).
- SVG social card + WEBVTT are the only media; no large raster hero images. PASS.
- Fonts: verify `font-display: swap` on any custom font (system stack is otherwise fine).
- No render-blocking third-party scripts (analytics stays inert; `VITE_ANALYTICS_PROVIDER=none`).

**Status:** acceptable for launch; charts code-splitting is the one worthwhile follow-up.
