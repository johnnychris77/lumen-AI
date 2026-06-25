import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  // Serve index.html for all routes in dev and preview (SPA hard-refresh fix).
  // The public/ dir contains real subdirectories (dashboard/, portfolio/) that
  // would otherwise intercept /dashboard etc. historyApiFallback ensures the
  // dev server always falls back to index.html for unknown paths.
  server: {
    historyApiFallback: true,
    fs: { strict: false },
  },
  preview: {
    historyApiFallback: true,
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // Stable vendor chunk names so their hash only changes when deps change,
        // not on every app rebuild — prevents stale-chunk 404 on hard refresh
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
