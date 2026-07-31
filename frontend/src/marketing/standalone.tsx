/**
 * Standalone entry for deploying the marketing site on its OWN domain, rooted
 * at "/". Built via `npm run build:site` (vite.marketing.config.ts), which sets
 * `__MARKETING_BASE__ = ""` so internal links are root-relative.
 *
 * The in-app mount (at /site/*) uses src/main.tsx instead; this file is only
 * the entry for the dedicated-domain build. No app state, no auth, no API.
 */
import "../index.css";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import MarketingApp from "./MarketingApp";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <MarketingApp />
  </BrowserRouter>,
);
