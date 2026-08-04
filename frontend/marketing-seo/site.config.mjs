/**
 * SINGLE SOURCE OF TRUTH for the standalone marketing domain.
 *
 * Change `SITE_ORIGIN` here and everything downstream follows on the next
 * `npm run build:site`:
 *   - marketing.html canonical / og:url / og:image / twitter:image
 *     (the postbuild step replaces the `__SITE_ORIGIN__` placeholder).
 *   - dist-site/robots.txt   (generated)
 *   - dist-site/sitemap.xml  (generated from ROUTES below)
 *
 * No other file hard-codes the domain. To move to a different domain later,
 * edit ONLY this line (and the Render custom domain + DNS).
 */
export const SITE_ORIGIN = "https://lumenai.opsbridgesolution.com";

/**
 * Public marketing routes (root-relative), used to generate sitemap.xml.
 * Keep in sync with the routes in src/marketing/MarketingApp.tsx. Do NOT add
 * any authenticated application route here.
 */
export const ROUTES = [
  { path: "/", priority: "1.0" },
  { path: "/problem", priority: "0.8" },
  { path: "/workflow", priority: "0.8" },
  { path: "/platform", priority: "0.8" },
  { path: "/architecture", priority: "0.7" },
  { path: "/security", priority: "0.7" },
  { path: "/use-cases", priority: "0.7" },
  { path: "/executive", priority: "0.8" },
  { path: "/pricing", priority: "0.8" },
  { path: "/pilot", priority: "0.8" },
  { path: "/roi", priority: "0.6" },
  { path: "/trust", priority: "0.7" },
  { path: "/investors", priority: "0.6" },
  { path: "/video", priority: "0.6" },
  { path: "/about", priority: "0.6" },
  { path: "/contact", priority: "0.9" },
];
