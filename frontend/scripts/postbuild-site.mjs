/**
 * Post-build step for the STANDALONE marketing site (`npm run build:site`).
 *
 * The marketing Vite config sets `publicDir: false` so the app's `public/`
 * directory is NOT copied wholesale — that directory contains unrelated static
 * demo pages (public/portfolio/*, public/dashboard/*) that embed internal
 * backend hostnames and would be published on the public marketing domain.
 *
 * This script assembles only what the marketing site actually serves:
 *   1. Renames the Vite entry  dist-site/marketing.html -> dist-site/index.html
 *      so it is served at the domain root.
 *   2. Copies public/site/*  (social-card.svg, lumenai-explainer.vtt) ->
 *      dist-site/site/  — the only public assets the marketing pages reference.
 *   3. Writes dist-site/_redirects with a single SPA catch-all so client routes
 *      (/workflow, /contact, …) fall back to index.html on the static host.
 *
 * Single source of truth: site assets are copied from public/site, never
 * duplicated in the repo.
 */
import { cp, rename, writeFile, readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const frontend = path.resolve(here, "..");
const distSite = path.join(frontend, "dist-site");

// 1. marketing.html -> index.html
await rename(path.join(distSite, "marketing.html"), path.join(distSite, "index.html"));

// 2. Copy only public/site/* (the marketing-referenced assets).
const publicSite = path.join(frontend, "public", "site");
if (existsSync(publicSite)) {
  await cp(publicSite, path.join(distSite, "site"), { recursive: true });
}

// 3. SPA catch-all redirect (Netlify/Render/Cloudflare Pages style).
await writeFile(path.join(distSite, "_redirects"), "/*    /index.html    200\n", "utf8");

// Report what shipped so the build log makes the surface explicit.
const shipped = await readdir(distSite);
console.log(`[build:site] dist-site root: ${shipped.sort().join(", ")}`);
