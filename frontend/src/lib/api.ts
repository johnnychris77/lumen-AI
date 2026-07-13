/**
 * Central API client.
 *
 * Every network call to the LumenAI backend should go through `apiFetch` (or a
 * verb helper below) instead of calling `fetch` directly. This gives us ONE
 * place to control:
 *
 *   - the base URL (no more per-file `import.meta.env.VITE_API_BASE_URL || "…"`),
 *   - how auth is attached (bearer header today; httpOnly cookie tomorrow),
 *   - `credentials` (so the cookie migration is a one-line flip here),
 *   - Content-Type (JSON by default, but never forced onto FormData uploads),
 *   - and 401 handling (single sign-out path instead of 43 copies).
 *
 * MIGRATION NOTE (localStorage token -> httpOnly cookie):
 *   The token is still read from localStorage for backward compatibility, but
 *   NOTHING outside this file needs to know that. When the SPA and API move to
 *   a single origin and the backend issues an httpOnly session cookie, set
 *   VITE_AUTH_TRANSPORT=cookie. This wrapper then stops attaching the bearer
 *   header and relies on the cookie (already sent because credentials:"include").
 *   No component changes required.
 */

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

// "bearer" (default, current behavior) or "cookie" (post-migration).
const AUTH_TRANSPORT = (
  import.meta.env.VITE_AUTH_TRANSPORT || "bearer"
).toLowerCase();

const USE_COOKIE_AUTH = AUTH_TRANSPORT === "cookie";

/** Read the current bearer token. Single source of truth for the localStorage key. */
export function getToken(): string {
  try {
    return (
      localStorage.getItem("token") ||
      (import.meta.env.VITE_AUTH_TOKEN as string | undefined) ||
      ""
    );
  } catch {
    return "";
  }
}

export function getRole(): string {
  try {
    return localStorage.getItem("role") || "viewer";
  } catch {
    return "viewer";
  }
}

export function getActor(): string {
  try {
    return localStorage.getItem("actor") || "";
  } catch {
    return "";
  }
}

/** Optional hook so the AuthProvider can react to a global 401 (e.g. sign out). */
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  /** Plain object -> JSON.stringify'd; FormData/Blob/string passed through untouched. */
  body?: unknown;
  /** Skip attaching auth (e.g. the login call itself). */
  auth?: boolean;
  /** Return the raw Response instead of parsed JSON (downloads, streaming). */
  raw?: boolean;
  /**
   * Set false for best-effort/background calls (widget KPIs, notifications)
   * whose own 401 shouldn't sign out a session other concurrent calls just
   * proved valid -- e.g. an endpoint gated by a different auth path than the
   * one that issued the token. Default true.
   */
  signOutOn401?: boolean;
}

function isPlainJsonBody(body: unknown): boolean {
  if (body == null) return false;
  if (typeof body === "string") return false;
  if (body instanceof FormData) return false;
  if (body instanceof Blob) return false;
  if (body instanceof ArrayBuffer) return false;
  if (body instanceof URLSearchParams) return false;
  return true;
}

function buildUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path; // already absolute
  return `${API_BASE}${path.startsWith("/") ? "" : "/"}${path}`;
}

/**
 * The one wrapper. Attaches base URL, auth, credentials, and JSON handling;
 * throws ApiError on non-2xx; returns parsed JSON by default.
 *
 * Overloads: with `raw: true` the caller gets the raw `Response` (so existing
 * `response.ok` / `response.json()` code keeps working); otherwise the parsed
 * JSON body typed as `T`.
 */
export async function apiFetch(
  path: string,
  options: ApiFetchOptions & { raw: true }
): Promise<Response>;
export async function apiFetch<T = unknown>(
  path: string,
  options?: ApiFetchOptions & { raw?: false }
): Promise<T>;
export async function apiFetch<T = unknown>(
  path: string,
  options: ApiFetchOptions = {}
): Promise<T | Response> {
  const { body, auth = true, raw = false, signOutOn401 = true, headers, ...rest } = options;

  const finalHeaders = new Headers(headers as HeadersInit | undefined);

  // JSON content-type ONLY for plain-object bodies. FormData must set its own
  // multipart boundary, so we must not touch Content-Type for uploads.
  const jsonBody = isPlainJsonBody(body);
  if (jsonBody && !finalHeaders.has("Content-Type")) {
    finalHeaders.set("Content-Type", "application/json");
  }

  if (auth) {
    // Advisory identity labels (backend does NOT trust these for authz; it
    // resolves role/actor from the validated token). Kept for audit context.
    if (!finalHeaders.has("X-LumenAI-Role")) finalHeaders.set("X-LumenAI-Role", getRole());
    const actor = getActor();
    if (actor && !finalHeaders.has("X-LumenAI-Actor")) {
      finalHeaders.set("X-LumenAI-Actor", actor);
    }

    if (!USE_COOKIE_AUTH) {
      const token = getToken();
      if (token && !finalHeaders.has("Authorization")) {
        finalHeaders.set("Authorization", `Bearer ${token}`);
      }
    }
  }

  const res = await fetch(buildUrl(path), {
    ...rest,
    headers: finalHeaders,
    // Send cookies same-origin today; required for httpOnly-cookie auth later.
    // Harmless with bearer auth. On a single origin this is same-origin anyway.
    credentials: rest.credentials ?? "include",
    body: jsonBody ? JSON.stringify(body) : (body as BodyInit | null | undefined),
  });

  if (res.status === 401 && auth && signOutOn401) {
    // Central sign-out on expired/invalid session, instead of 43 local handlers.
    try {
      onUnauthorized?.();
    } catch {
      /* never let the handler mask the original error */
    }
  }

  if (raw) return res;

  if (!res.ok) {
    let parsed: unknown = null;
    let message = `Request failed (${res.status})`;
    try {
      const text = await res.text();
      if (text) {
        try {
          parsed = JSON.parse(text);
          const detail = (parsed as { detail?: unknown })?.detail;
          if (typeof detail === "string") message = detail;
        } catch {
          parsed = text;
          message = text.slice(0, 200);
        }
      }
    } catch {
      /* fall through with the generic message */
    }

    // v1.9 — fire-and-forget role-permission-failure logging. Inlined
    // (rather than importing errorLog.ts) to avoid a circular import, and
    // skipped for the logging endpoint itself so a permission failure can
    // never recurse into logging its own failure.
    if (res.status === 403 && !path.includes("/api/pilot-deployment/error-log")) {
      fetch(buildUrl("/api/pilot-deployment/error-log"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...Object.fromEntries(finalHeaders.entries()) },
        credentials: "include",
        body: JSON.stringify({ error_type: "role_permission_failure", detail: message.slice(0, 500) }),
      }).catch(() => { /* logging must never surface a second error */ });
    }

    throw new ApiError(res.status, message, parsed);
  }

  // 204 / empty body
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}

// Convenience verb helpers. These always parse JSON (type T). For a raw
// Response, call apiFetch(path, { raw: true }) directly.
export const api = {
  get: <T = unknown>(path: string, opts?: Omit<ApiFetchOptions, "raw" | "method">) =>
    apiFetch<T>(path, { ...opts, method: "GET" }),
  post: <T = unknown>(path: string, body?: unknown, opts?: Omit<ApiFetchOptions, "raw" | "method" | "body">) =>
    apiFetch<T>(path, { ...opts, method: "POST", body }),
  put: <T = unknown>(path: string, body?: unknown, opts?: Omit<ApiFetchOptions, "raw" | "method" | "body">) =>
    apiFetch<T>(path, { ...opts, method: "PUT", body }),
  patch: <T = unknown>(path: string, body?: unknown, opts?: Omit<ApiFetchOptions, "raw" | "method" | "body">) =>
    apiFetch<T>(path, { ...opts, method: "PATCH", body }),
  delete: <T = unknown>(path: string, opts?: Omit<ApiFetchOptions, "raw" | "method">) =>
    apiFetch<T>(path, { ...opts, method: "DELETE" }),
};
