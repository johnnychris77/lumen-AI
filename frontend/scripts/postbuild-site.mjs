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
 *   3. Copies root SEO files (robots.txt, sitemap.xml) into the domain root.
 *      Source is `marketing-seo/` (marketing-only, so the app's own build never
 *      serves the marketing sitemap), falling back to `public/` for an operator
 *      override. The standalone config disables publicDir, so without this step
 *      these files would never reach the domain root.
 *   4. Writes dist-site/_redirects with a single SPA catch-all so client routes
 *      (/workflow, /contact, …) fall back to index.html on hosts that read it
 *      (Netlify/Render/Cloudflare Pages).
 *   5. Writes dist-site/404.html as a copy of index.html — the SPA fallback for
 *      hosts that DON'T read _redirects (notably GitHub Pages), so deep links
 *      and hard refreshes on client routes resolve instead of 404ing.
 *
 * Single source of truth: site assets are copied from public/site, never
 * duplicated in the repo.
 */
import { cp, rename, writeFile, readdir, copyFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const frontend = path.resolve(here, "..");
const publicDir = path.join(frontend, "public");
const seoDir = path.join(frontend, "marketing-seo");
const distSite = path.join(frontend, "dist-site");

// 1. marketing.html -> index.html
await rename(path.join(distSite, "marketing.html"), path.join(distSite, "index.html"));

// 2. Copy only public/site/* (the marketing-referenced assets).
const publicSite = path.join(publicDir, "site");
if (existsSync(publicSite)) {
  await cp(publicSite, path.join(distSite, "site"), { recursive: true });
}

// 3. Copy root SEO files (marketing-seo/ preferred; public/ as override).
for (const name of ["robots.txt", "sitemap.xml"]) {
  const src = existsSync(path.join(seoDir, name))
    ? path.join(seoDir, name)
    : path.join(publicDir, name);
  if (existsSync(src)) await copyFile(src, path.join(distSite, name));
}

// 4. SPA catch-all redirect (Netlify/Render/Cloudflare Pages style).
await writeFile(path.join(distSite, "_redirects"), "/*    /index.html    200\n", "utf8");

// 5. 404.html SPA fallback for hosts that ignore _redirects (e.g. GitHub Pages).
await copyFile(path.join(distSite, "index.html"), path.join(distSite, "404.html"));

// Report what shipped so the build log makes the surface explicit.
const shipped = await readdir(distSite);
console.log(`[build:site] dist-site root: ${shipped.sort().join(", ")}`);
