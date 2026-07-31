import { mlink } from "../lib/base";
/** Small, reusable presentational primitives for the marketing site. */
import * as React from "react";
import { Link } from "react-router-dom";
import { Maturity, MATURITY_LABEL } from "../lib/content";
import { track } from "../lib/analytics";

export function Container({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`mx-auto w-full max-w-6xl px-5 sm:px-8 ${className}`}>{children}</div>;
}

export function Section({
  children,
  className = "",
  tone = "default",
  id,
}: {
  children: React.ReactNode;
  className?: string;
  tone?: "default" | "muted" | "brand";
  id?: string;
}) {
  const bg =
    tone === "muted" ? "bg-slate-50" : tone === "brand" ? "bg-primary text-white" : "bg-white";
  return (
    <section id={id} className={`py-16 sm:py-20 ${bg} ${className}`}>
      <Container>{children}</Container>
    </section>
  );
}

export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-primary">{children}</p>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  intro,
  center,
  as = "h2",
}: {
  eyebrow?: string;
  title: string;
  intro?: string;
  center?: boolean;
  /**
   * Heading level for the title. Defaults to "h2" for in-page section titles.
   * Pass "h1" on the FIRST heading of a route so every page has exactly one
   * top-level heading (accessibility + the one-h1-per-page rule in
   * docs/marketing/WEBSITE_OVERVIEW.md). The HomePage hero already renders its
   * own h1, so its SectionHeadings stay h2.
   */
  as?: "h1" | "h2";
}) {
  const Heading = as;
  return (
    <div className={`${center ? "mx-auto max-w-2xl text-center" : "max-w-3xl"} mb-10`}>
      {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
      <Heading className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{title}</Heading>
      {intro ? <p className="mt-4 text-base leading-relaxed text-slate-600">{intro}</p> : null}
    </div>
  );
}

export function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

const MATURITY_STYLE: Record<Maturity, string> = {
  supported: "bg-success-subtle text-success",
  demonstrated: "bg-info-subtle text-info",
  concept: "bg-warning-subtle text-warning",
};

export function MaturityBadge({ maturity }: { maturity: Maturity }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${MATURITY_STYLE[maturity]}`}
    >
      {MATURITY_LABEL[maturity]}
    </span>
  );
}

/** Primary + secondary CTA row used across pages. */
export function CtaRow({ align = "start" }: { align?: "start" | "center" }) {
  return (
    <div className={`flex flex-wrap gap-3 ${align === "center" ? "justify-center" : ""}`}>
      <Link
        to={mlink("/contact")}
        onClick={() => track("demo_request_click", { placement: "cta_row" })}
        className="inline-flex h-11 items-center justify-center rounded-md bg-primary px-6 text-base font-medium text-white transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
      >
        Request a demonstration
      </Link>
      <Link
        to={mlink("/workflow")}
        onClick={() => track("cta_click", { placement: "cta_row", target: "workflow" })}
        className="inline-flex h-11 items-center justify-center rounded-md border border-slate-300 bg-white px-6 text-base font-medium text-slate-700 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
      >
        View the workflow
      </Link>
    </div>
  );
}
