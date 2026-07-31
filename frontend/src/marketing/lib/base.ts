/**
 * Path base for the marketing site so the SAME code serves two ways:
 *  - Mounted inside the app at `/site/*` (default) — the in-app build.
 *  - Rooted at `/` on a dedicated marketing domain — the standalone build
 *    (`npm run build:site`), which defines `__MARKETING_BASE__ = ""`.
 *
 * `__MARKETING_BASE__` is a Vite `define` replacement injected only by the
 * standalone config; in the normal build it is undefined, so `typeof` (safe on
 * an undeclared global) falls back to the env var or "/site".
 */
declare const __MARKETING_BASE__: string;

const RAW =
  typeof __MARKETING_BASE__ !== "undefined"
    ? __MARKETING_BASE__
    : (import.meta.env.VITE_MARKETING_BASE as string | undefined) ?? "/site";

/** Normalized base with no trailing slash. "" means rooted at the domain root. */
export const MARKETING_BASE = RAW.replace(/\/+$/, "");

/** Build an internal marketing href, e.g. mlink("/workflow"). */
export function mlink(path = "/"): string {
  if (!path || path === "/") return MARKETING_BASE || "/";
  return `${MARKETING_BASE}${path.startsWith("/") ? "" : "/"}${path}`;
}
