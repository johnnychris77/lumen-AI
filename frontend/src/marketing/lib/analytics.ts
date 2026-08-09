/**
 * Analytics abstraction for the marketing site.
 *
 * No tracking keys are embedded in source. A provider is only active when the
 * host configures `VITE_ANALYTICS_PROVIDER` (and any provider key) at build
 * time. With nothing configured, events are buffered to `window.__lumenEvents`
 * in dev for inspection and are otherwise a no-op — safe to ship publicly.
 *
 * Standard events the site emits:
 *   page_view, workflow_demo_step, workflow_demo_complete, video_play,
 *   demo_request_click, contact_submit, cta_click
 */
export type AnalyticsEvent =
  | "page_view"
  | "workflow_demo_step"
  | "workflow_demo_complete"
  | "video_play"
  | "demo_request_click"
  | "contact_submit"
  | "exec_persona_select"
  | "cta_click";

type Props = Record<string, string | number | boolean | undefined>;

const provider = (import.meta.env.VITE_ANALYTICS_PROVIDER as string | undefined) || "none";
const debug = import.meta.env.DEV;

declare global {
  interface Window {
    __lumenEvents?: Array<{ event: string; props?: Props; ts: number }>;
    plausible?: (event: string, opts?: { props?: Props }) => void;
    gtag?: (...args: unknown[]) => void;
  }
}

export function track(event: AnalyticsEvent, props?: Props): void {
  if (typeof window === "undefined") return;

  // Always buffer in dev so demos/tests can assert on emitted events without
  // any third-party network calls.
  if (debug) {
    window.__lumenEvents = window.__lumenEvents ?? [];
    window.__lumenEvents.push({ event, props, ts: Date.now() });
  }

  try {
    if (provider === "plausible" && typeof window.plausible === "function") {
      window.plausible(event, props ? { props } : undefined);
    } else if (provider === "gtag" && typeof window.gtag === "function") {
      window.gtag("event", event, props ?? {});
    }
    // provider === "none" → intentional no-op.
  } catch {
    /* analytics must never break the page */
  }
}
