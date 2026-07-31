/**
 * Lightweight, dependency-free SEO helper for the public marketing site.
 *
 * The app does not ship react-helmet; rather than add a dependency to the
 * frozen frontend, this imperatively sets document.title, the meta
 * description, canonical URL, and Open Graph / Twitter tags, then restores
 * them on unmount. Marketing pages call `useSeo(...)` once at the top level.
 */
import { useEffect } from "react";

export interface SeoConfig {
  title: string;
  description: string;
  /** Path only, e.g. "/site/workflow". Combined with the origin at runtime. */
  path?: string;
  /** Absolute or root-relative image for social sharing. */
  image?: string;
}

const SITE_NAME = "LumenAI";
const DEFAULT_IMAGE = "/site/social-card.svg";

function setMeta(selector: string, attr: "name" | "property", key: string, content: string) {
  let el = document.head.querySelector<HTMLMetaElement>(selector);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
  return el;
}

function setLink(rel: string, href: string) {
  let el = document.head.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`);
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", rel);
    document.head.appendChild(el);
  }
  el.setAttribute("href", href);
  return el;
}

export function useSeo({ title, description, path, image }: SeoConfig): void {
  useEffect(() => {
    const previousTitle = document.title;
    const fullTitle = title.includes(SITE_NAME) ? title : `${title} — ${SITE_NAME}`;
    document.title = fullTitle;

    const origin = typeof window !== "undefined" ? window.location.origin : "";
    const url = path ? `${origin}${path}` : origin;
    const img = image ?? DEFAULT_IMAGE;

    setMeta('meta[name="description"]', "name", "description", description);
    setMeta('meta[property="og:title"]', "property", "og:title", fullTitle);
    setMeta('meta[property="og:description"]', "property", "og:description", description);
    setMeta('meta[property="og:type"]', "property", "og:type", "website");
    setMeta('meta[property="og:site_name"]', "property", "og:site_name", SITE_NAME);
    setMeta('meta[property="og:url"]', "property", "og:url", url);
    setMeta('meta[property="og:image"]', "property", "og:image", `${origin}${img}`);
    setMeta('meta[name="twitter:card"]', "name", "twitter:card", "summary_large_image");
    setMeta('meta[name="twitter:title"]', "name", "twitter:title", fullTitle);
    setMeta('meta[name="twitter:description"]', "name", "twitter:description", description);
    setLink("canonical", url);

    return () => {
      document.title = previousTitle;
    };
  }, [title, description, path, image]);
}
