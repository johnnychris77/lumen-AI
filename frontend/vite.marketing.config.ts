import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

/**
 * Standalone build config for deploying the PUBLIC MARKETING SITE on its own
 * dedicated domain, rooted at "/" (clean URLs like `example.com/workflow`
 * instead of `example.com/site/workflow`).
 *
 * Differences from the default app build (vite.config.ts):
 *  - Entry is `marketing.html` (loads src/marketing/standalone.tsx only) — the
 *    app, auth, and API client are NOT bundled.
 *  - `base: "/"` so assets and links resolve from the domain root.
 *  - `__MARKETING_BASE__ = ""` (Vite define) so `mlink()` emits root-relative
 *    internal links with no `/site` prefix.
 *  - Output goes to `dist-site/` to avoid clobbering the app's `dist/`.
 *
 * Run with: `npm run build:site` (which also renames dist-site/marketing.html
 * to dist-site/index.html so it is served at the domain root).
 */
export default defineConfig({
  base: "/",
  plugins: [react(), tailwindcss()],
  // Do NOT copy the app's public/ wholesale: it contains unrelated static demo
  // pages (public/portfolio/*, public/dashboard/*) that embed internal backend
  // hostnames and must never be published on the public marketing domain. The
  // postbuild script (scripts/postbuild-site.mjs) copies only public/site/*.
  publicDir: false,
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  define: {
    // Injected at build time; consumed by src/marketing/lib/base.ts so internal
    // marketing links are rooted at "/" instead of "/site".
    __MARKETING_BASE__: JSON.stringify(""),
  },
  build: {
    outDir: "dist-site",
    emptyOutDir: true,
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      input: path.resolve(__dirname, "marketing.html"),
      output: {
        manualChunks: (id) => {
          if (id.includes("node_modules/react") || id.includes("node_modules/react-dom")) {
            return "vendor-react";
          }
          if (id.includes("node_modules/react-router")) {
            return "vendor-router";
          }
          if (id.includes("node_modules/recharts") || id.includes("node_modules/d3")) {
            return "vendor-charts";
          }
        },
      },
    },
  },
});
