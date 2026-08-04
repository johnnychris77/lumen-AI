import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Check, Minus, ShieldCheck, Lock, UserCheck, FileCheck2, Database, Server, Cpu, Scale } from "lucide-react";
import { mlink } from "./lib/base";
import { useSeo } from "./lib/seo";
import { Section, SectionHeading, Panel, CtaRow } from "./components/primitives";
import { DemoDisclaimer } from "./components/DemoDisclaimer";
import { track } from "./lib/analytics";

/**
 * Commercial-launch pages (Phase: Commercial Readiness, increment 1).
 * Presentation layer only; synthetic/illustrative content; claims-safe.
 * No real pricing, no unearned certifications, projections labeled illustrative.
 */

/* ─────────────────────────── Pricing ─────────────────────────── */
const TIERS = [
  { name: "Starter", blurb: "A single department evaluating governed inspection evidence.", cta: "Contact Sales" },
  { name: "Professional", blurb: "A hospital standardizing inspection workflow and review.", cta: "Contact Sales", featured: true },
  { name: "Enterprise", blurb: "Multi-site health systems needing cross-site governance.", cta: "Contact Sales" },
  { name: "Manufacturer", blurb: "Device manufacturers using anonymized trend intelligence.", cta: "Contact Sales" },
  { name: "Government", blurb: "Public health and government facilities.", cta: "Contact Sales" },
];

const FEATURES: { label: string; tiers: boolean[] }[] = [
  { label: "Governed inspection workflow", tiers: [true, true, true, true, true] },
  { label: "Assistive analysis + human review", tiers: [true, true, true, true, true] },
  { label: "Approved baseline comparison", tiers: [true, true, true, true, true] },
  { label: "Hash-chained evidence & audit trail", tiers: [true, true, true, true, true] },
  { label: "Reports & operational dashboards", tiers: [false, true, true, true, true] },
  { label: "Multi-site governance & comparison", tiers: [false, false, true, true, true] },
  { label: "Anonymized vendor/instrument trends", tiers: [false, false, true, true, false] },
  { label: "Role-based access & tenant isolation", tiers: [true, true, true, true, true] },
];

export function PricingPage() {
  useSeo({
    title: "Pricing",
    description:
      "LumenAI plans for departments, hospitals, health systems, manufacturers, and government. Contact Sales for a scoped quote and pilot program. Illustrative feature comparison; no pricing published.",
    path: mlink("/pricing"),
  });
  return (
    <>
      <Section>
        <SectionHeading
          as="h1"
          eyebrow="Pricing"
          title="Plans scoped to your organization."
          intro="LumenAI is sold as a scoped engagement — plans below describe who each tier fits. Pricing is provided by Sales after a short scoping conversation; we do not publish list prices."
        />
        <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
          {TIERS.map((t) => (
            <div
              key={t.name}
              className={`flex flex-col rounded-xl border p-5 shadow-sm ${
                t.featured ? "border-primary bg-primary-subtle" : "border-slate-200 bg-white"
              }`}
            >
              <h3 className="text-base font-semibold text-slate-900">{t.name}</h3>
              <p className="mt-1 flex-1 text-sm leading-relaxed text-slate-600">{t.blurb}</p>
              <p className="mt-3 text-lg font-bold text-slate-900">Contact Sales</p>
              <Link
                to={mlink("/contact")}
                onClick={() => track("pricing_interaction", { tier: t.name })}
                className="mt-3 inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-white hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              >
                {t.cta}
              </Link>
            </div>
          ))}
        </div>
      </Section>

      <Section tone="muted">
        <SectionHeading eyebrow="Compare" title="What's included by tier." intro="Illustrative capability mapping — final scope is confirmed during pilot planning." />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr>
                <th scope="col" className="border-b border-slate-200 p-3 text-left font-semibold text-slate-700">Capability</th>
                {TIERS.map((t) => (
                  <th key={t.name} scope="col" className="border-b border-slate-200 p-3 text-center font-semibold text-slate-700">{t.name}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {FEATURES.map((f) => (
                <tr key={f.label}>
                  <th scope="row" className="border-b border-slate-100 p-3 text-left font-medium text-slate-700">{f.label}</th>
                  {f.tiers.map((on, i) => (
                    <td key={i} className="border-b border-slate-100 p-3 text-center">
                      {on
                        ? <Check size={16} className="mx-auto text-success" aria-label="Included" />
                        : <Minus size={16} className="mx-auto text-slate-300" aria-label="Not included" />}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-8"><CtaRow /></div>
      </Section>
    </>
  );
}

/* ─────────────────────────── Pilot Program ─────────────────────────── */
export function PilotProgramPage() {
  useSeo({
    title: "Pilot Program",
    description:
      "A structured, low-risk LumenAI pilot: objectives, timeline, success criteria, responsibilities, deliverables, and exit criteria. Evaluate governed inspection evidence in your environment.",
    path: mlink("/pilot"),
  });
  const cols = [
    { h: "LumenAI provides", items: ["Guided configuration & onboarding", "Technician & reviewer enablement", "Governed workflow + evidence + reporting", "A written pilot readout"] },
    { h: "Your team provides", items: ["A named SPD lead + reviewer(s) + quality sponsor", "A bounded set of instrument types", "Time for capture, review, and feedback", "Synthetic or de-identified data unless a data agreement is in place"] },
  ];
  return (
    <>
      <Section>
        <SectionHeading as="h1" eyebrow="Pilot program" title="Evaluate LumenAI in your environment — safely." intro="A pilot is a bounded validation, not a production rollout. It never connects the public demonstration to production data." />
        <div className="grid gap-4 md:grid-cols-3">
          {[
            { h: "Objectives", body: "Confirm the workflow fits your process, evidence records are complete, and human-review routing matches local policy." },
            { h: "Timeline", body: "A defined evaluation window agreed up front — typically a small number of weeks, scoped to instrument types and roles." },
            { h: "Success criteria", body: "Qualitative first: technicians document quickly and consistently; reviewers act on routed findings; quality assembles audit-ready records." },
          ].map((c) => (
            <Panel key={c.h}><h3 className="text-base font-semibold text-slate-900">{c.h}</h3><p className="mt-2 text-sm text-slate-600">{c.body}</p></Panel>
          ))}
        </div>
      </Section>
      <Section tone="muted">
        <SectionHeading eyebrow="Responsibilities" title="A shared, well-defined engagement." />
        <div className="grid gap-4 md:grid-cols-2">
          {cols.map((c) => (
            <Panel key={c.h}>
              <h3 className="text-base font-semibold text-slate-900">{c.h}</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-600">
                {c.items.map((i) => <li key={i} className="flex gap-2"><Check size={16} className="mt-0.5 shrink-0 text-success" aria-hidden /> {i}</li>)}
              </ul>
            </Panel>
          ))}
        </div>
        <p className="mt-6 max-w-2xl text-sm text-slate-600">
          <strong>Deliverables & exit:</strong> a written readout of what worked, what to change, and a clear go / no-go for wider rollout.
          Out of scope for a pilot: any claim of clinical outcome, infection reduction, or diagnostic performance.
        </p>
        <div className="mt-8"><CtaRow /></div>
      </Section>
    </>
  );
}

/* ─────────────────────────── ROI / operational estimator ─────────────────────────── */
function num(v: string, fallback: number) { const n = Number(v); return Number.isFinite(n) && n >= 0 ? n : fallback; }

export function RoiPage() {
  useSeo({
    title: "Operational Estimator",
    description:
      "An interactive, illustrative estimator of LumenAI's operational shape for your organization — governed records, review-routed cases, and documentation time. Illustrative assumptions only; not a guarantee.",
    path: mlink("/roi"),
  });
  const [sites, setSites] = useState("3");
  const [volume, setVolume] = useState("1200"); // inspections / month across org
  const [instruments, setInstruments] = useState("500");
  const [staff, setStaff] = useState("20");

  const out = useMemo(() => {
    const v = num(volume, 0);
    const reviewRate = 0.18;          // illustrative assumption
    const minutesPerRecord = 1.5;     // illustrative assumption (capture → governed record)
    return {
      records: Math.round(v),
      routed: Math.round(v * reviewRate),
      baselineTargets: Math.round(num(instruments, 0)),
      docMinutes: Math.round(v * minutesPerRecord),
      perTech: num(staff, 0) > 0 ? Math.round(v / num(staff, 1)) : 0,
    };
  }, [volume, instruments, staff]);

  const field = (id: string, label: string, val: string, set: (s: string) => void) => (
    <label className="block">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</span>
      <input
        id={id} type="number" min={0} inputMode="numeric" value={val}
        onChange={(e) => { set(e.target.value); track("roi_calculator_use", { field: id }); }}
        className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      />
    </label>
  );

  return (
    <Section>
      <SectionHeading as="h1" eyebrow="Operational estimator" title="See the operational shape — illustratively." intro="Enter your scale to see an illustrative picture of how governed inspection would flow. These are assumption-based estimates, not guarantees, benchmarks, or financial ROI." />
      <DemoDisclaimer className="mb-4" />
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          {field("sites", "Sites", sites, setSites)}
          {field("volume", "Inspections / month", volume, setVolume)}
          {field("instruments", "Instruments", instruments, setInstruments)}
          {field("staff", "SPD staff", staff, setStaff)}
        </div>
        <ul className="grid gap-4 sm:grid-cols-2" aria-live="polite" aria-label="Illustrative estimates">
          {[
            { l: "Governed records / month", v: out.records.toLocaleString(), h: "One governed record per inspection" },
            { l: "Human-review-routed / month", v: out.routed.toLocaleString(), h: "≈18% assumed review rate" },
            { l: "Baseline targets", v: out.baselineTargets.toLocaleString(), h: "Instruments that could carry an approved baseline" },
            { l: "Documentation minutes / month", v: out.docMinutes.toLocaleString(), h: "≈1.5 min/record assumption" },
            { l: "Records / technician / month", v: out.perTech.toLocaleString(), h: "Volume ÷ staff" },
            { l: "Sites in scope", v: sites, h: "Cross-site governance" },
          ].map((c) => (
            <li key={c.l} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{c.l}</p>
              <p className="mt-1 text-2xl font-bold text-primary">{c.v}</p>
              <p className="mt-1 text-xs text-slate-500">{c.h}</p>
            </li>
          ))}
        </ul>
      </div>
      <p className="mt-4 text-xs font-semibold text-warning">
        Illustrative estimates only. Assumptions are documented in docs/marketing/ROI_ASSUMPTIONS.md. LumenAI makes no
        cost-savings, labor-savings, accuracy, or outcome guarantees.
      </p>
      <div className="mt-8"><CtaRow /></div>
    </Section>
  );
}

/* ─────────────────────────── Trust Center ─────────────────────────── */
const TRUST = [
  { Icon: Lock, h: "Authentication", body: "Access requires authenticated identity; no shared dev tokens in production." },
  { Icon: ShieldCheck, h: "Authorization", body: "Role-based access is enforced server-side; the client is never trusted for authorization." },
  { Icon: Database, h: "Tenant isolation", body: "Tenants cannot see each other's raw data; isolation is enforced in the data layer." },
  { Icon: Server, h: "Encryption", body: "Transport is HTTPS; secrets are held in environment configuration, never in source." },
  { Icon: FileCheck2, h: "Audit logging", body: "Evidence, decisions, and actions are appended to a hash-chained audit trail." },
  { Icon: FileCheck2, h: "Evidence integrity", body: "Each stage adds to the record rather than overwriting it; baselines are governed records." },
  { Icon: Cpu, h: "Responsible AI", body: "Analysis is assistive and non-autonomous; correlation outputs carry a human-review requirement." },
  { Icon: UserCheck, h: "Human oversight", body: "Uncertain or higher-risk findings route to a qualified reviewer; people own final decisions." },
  { Icon: Scale, h: "Data governance", body: "No PHI in demonstrations; production data handling is governed by your organization's agreements." },
];

export function TrustCenterPage() {
  useSeo({
    title: "Trust Center",
    description:
      "How LumenAI approaches authentication, authorization, tenant isolation, encryption, audit logging, evidence integrity, responsible AI, and human oversight. No certifications are claimed that have not been obtained.",
    path: mlink("/trust"),
  });
  return (
    <Section>
      <SectionHeading as="h1" eyebrow="Trust center" title="Security, governance, and responsible AI." intro="How LumenAI is designed around healthcare security and evidence-governance principles. These describe design intent and implemented controls — not third-party attestations." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {TRUST.map((t) => (
          <Panel key={t.h}>
            <div className="flex items-center gap-2 text-primary"><t.Icon size={18} aria-hidden /><h3 className="text-base font-semibold text-slate-900">{t.h}</h3></div>
            <p className="mt-2 text-sm text-slate-600">{t.body}</p>
          </Panel>
        ))}
      </div>
      <Panel className="mx-auto mt-8 max-w-3xl border-warning/30 bg-warning-subtle">
        <h3 className="text-base font-semibold text-slate-900">What we do not claim</h3>
        <p className="mt-2 text-sm text-slate-700">
          LumenAI does not claim FDA clearance, HIPAA compliance, SOC 2, or any cybersecurity or regulatory
          certification. Any compliance posture is established with your organization and the appropriate authorities.
        </p>
      </Panel>
    </Section>
  );
}

/* ─────────────────────────── Investor ─────────────────────────── */
export function InvestorPage() {
  useSeo({
    title: "For Investors",
    description:
      "LumenAI investor overview: vision, problem, market, solution, technology, roadmap, and business model. Projections are illustrative and not a forecast or guarantee.",
    path: mlink("/investors"),
  });
  const blocks = [
    { h: "Vision", body: "Make internal-channel inspection produce governed, reviewable evidence — the system of record for what was inspected, by whom, and why." },
    { h: "Problem", body: "Inspection evidence today is loose images, spreadsheets, and tribal knowledge — hard to compare, review, or audit." },
    { h: "Market", body: "Sterile processing and infection prevention across hospitals, health systems, and device manufacturers. (Sizing is illustrative, not a forecast.)" },
    { h: "Solution", body: "An AI-assisted, human-reviewed workflow that turns each inspection into a governed evidence record with a hash-chained audit trail." },
    { h: "Technology", body: "A workflow engine, assistive analysis, baseline comparison, an evidence/audit layer, and role-based multi-tenant governance." },
    { h: "Competitive advantage", body: "Evidence governance and human accountability by design — not image storage or a black-box classifier." },
    { h: "Business model", body: "Scoped SaaS engagements by organization size (see Pricing), plus manufacturer trend intelligence." },
    { h: "Roadmap", body: "Current: demo-ready v1.0. Next: guided tours, deeper reporting. Future/Research: clearly labeled — see the roadmap doc." },
  ];
  return (
    <>
      <Section>
        <SectionHeading as="h1" eyebrow="For investors" title="An evidence-governance platform for medical instrument inspection." intro="A concept demonstration with honest scope. All figures on the site are synthetic; any market or growth statements are illustrative and not a forecast or guarantee." />
        <div className="grid gap-4 sm:grid-cols-2">
          {blocks.map((b) => (
            <Panel key={b.h}><h3 className="text-base font-semibold text-slate-900">{b.h}</h3><p className="mt-2 text-sm text-slate-600">{b.body}</p></Panel>
          ))}
        </div>
      </Section>
      <Section tone="muted">
        <Panel className="mx-auto max-w-3xl border-warning/30 bg-warning-subtle">
          <h3 className="text-base font-semibold text-slate-900">Illustrative-only notice</h3>
          <p className="mt-2 text-sm text-slate-700">
            Any projections, market sizes, or roadmap dates shown are <strong>illustrative</strong> and provided for
            discussion only. They are not a forecast, an offer, or a guarantee, and no regulatory clearance or
            certification is claimed.
          </p>
        </Panel>
        <div className="mt-8"><CtaRow /></div>
      </Section>
    </>
  );
}
