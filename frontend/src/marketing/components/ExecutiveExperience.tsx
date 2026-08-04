import { useState } from "react";
import {
  Building2, ShieldCheck, Wrench, ClipboardCheck, Activity,
  Truck, Cpu, TrendingUp,
} from "lucide-react";
import { DemoDisclaimer } from "./DemoDisclaimer";
import { track } from "../lib/analytics";

/**
 * Persona-driven executive demonstration surface (Phase 2, objectives 3 + 4).
 *
 * 100% SYNTHETIC demonstration data — no production data, no PHI. Each persona
 * reframes the SAME governed-evidence story for a different buyer and highlights
 * the KPIs that role cares about. Language stays assistive / human-reviewed and
 * makes no outcome, accuracy, regulatory, or savings claims.
 */

type KpiKey =
  | "volume" | "reviewRate" | "baseline" | "evidence"
  | "vendor" | "health" | "sites" | "turnaround";

interface Kpi {
  key: KpiKey;
  label: string;
  value: string;
  hint: string;
}

// Illustrative, round, obviously-synthetic figures.
const KPIS: Kpi[] = [
  { key: "volume", label: "Inspections (30d)", value: "1,240", hint: "Synthetic demo volume" },
  { key: "reviewRate", label: "Review-required rate", value: "18%", hint: "Routed to a human reviewer" },
  { key: "baseline", label: "Baseline coverage", value: "76%", hint: "Instruments with an approved baseline" },
  { key: "evidence", label: "Evidence completeness", value: "98%", hint: "Records with image + metadata + decision" },
  { key: "vendor", label: "Vendor trend signal", value: "3 flagged", hint: "Vendors with rising review rate" },
  { key: "health", label: "Instrument health", value: "92% nominal", hint: "Digital-twin status across fleet" },
  { key: "sites", label: "Sites compared", value: "4 sites", hint: "Cross-site review-rate variance" },
  { key: "turnaround", label: "Median documentation time", value: "≈ 40s", hint: "Capture → governed record (demo)" },
];

interface Persona {
  id: string;
  name: string;
  Icon: typeof Building2;
  headline: string;
  message: string;
  highlight: KpiKey[];
}

const PERSONAS: Persona[] = [
  {
    id: "ceo", name: "Hospital CEO", Icon: Building2,
    headline: "Governed inspection evidence, at a glance.",
    message: "A defensible, audit-ready record for internal-channel inspection — with human accountability preserved at every decision.",
    highlight: ["evidence", "reviewRate", "sites", "baseline"],
  },
  {
    id: "spd", name: "SPD Director", Icon: Wrench,
    headline: "See every inspection, and who reviewed it.",
    message: "Volume, review routing, and baseline coverage in one place — so the department can show its work, not just its throughput.",
    highlight: ["volume", "reviewRate", "baseline", "turnaround"],
  },
  {
    id: "tech", name: "Sterile Processing Technician", Icon: Activity,
    headline: "Assistive analysis, human decision.",
    message: "Suggested finding categories speed documentation; a qualified person still owns every disposition. Nothing is auto-passed.",
    highlight: ["turnaround", "reviewRate", "evidence", "volume"],
  },
  {
    id: "quality", name: "Quality Director", Icon: ClipboardCheck,
    headline: "Audit-ready evidence, not spreadsheets.",
    message: "Every record carries image, metadata, rationale, and a hash-chained audit trail — traceable end to end for review.",
    highlight: ["evidence", "baseline", "reviewRate", "sites"],
  },
  {
    id: "ip", name: "Infection Prevention", Icon: ShieldCheck,
    headline: "Structured visibility into channel inspection.",
    message: "Consistent, reviewable evidence supports quality review. LumenAI supports — it does not replace — infection-prevention judgment or IFUs.",
    highlight: ["reviewRate", "evidence", "health", "sites"],
  },
  {
    id: "vendor", name: "Vendor Representative", Icon: Truck,
    headline: "Instrument-level trend intelligence.",
    message: "Anonymized, synthetic trend signals show where review rates move over time — a basis for structured vendor conversations.",
    highlight: ["vendor", "health", "volume", "baseline"],
  },
  {
    id: "biomed", name: "Biomedical Engineering", Icon: Cpu,
    headline: "A digital twin per instrument.",
    message: "Identity, inspection history, baseline history, and maintenance context travel with the instrument across its lifecycle.",
    highlight: ["health", "baseline", "evidence", "volume"],
  },
  {
    id: "investor", name: "Investor", Icon: TrendingUp,
    headline: "An evidence-governance platform, demonstrated.",
    message: "A concept demonstration of the workflow, governance model, and role-based value — built on synthetic data, with honest scope.",
    highlight: ["sites", "vendor", "evidence", "reviewRate"],
  },
];

export function ExecutiveExperience() {
  const [active, setActive] = useState(PERSONAS[0]);

  return (
    <div className="space-y-6">
      {/* Persistent synthetic-data notice */}
      <DemoDisclaimer />

      {/* Persona selector */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">View the demo as</h3>
        <div role="group" aria-label="Choose a demonstration persona" className="mt-2 flex flex-wrap gap-2">
          {PERSONAS.map((p) => {
            const isActive = p.id === active.id;
            return (
              <button
                key={p.id}
                type="button"
                aria-pressed={isActive}
                onClick={() => { setActive(p); track("exec_persona_select", { persona: p.id }); }}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 ${
                  isActive
                    ? "border-primary bg-primary text-white"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                <p.Icon size={14} aria-hidden /> {p.name}
              </button>
            );
          })}
        </div>
      </div>

      {/* Persona message */}
      <div aria-live="polite" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-primary">
          <active.Icon size={18} aria-hidden />
          <span className="text-xs font-semibold uppercase tracking-widest">{active.name}</span>
        </div>
        <h2 className="mt-2 text-2xl font-bold text-slate-900">{active.headline}</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">{active.message}</p>
      </div>

      {/* KPI grid — the highlighted tiles for this persona lead */}
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" aria-label="Synthetic executive KPIs">
        {[...KPIS].sort((a, b) => Number(active.highlight.includes(b.key)) - Number(active.highlight.includes(a.key))).map((k) => {
          const emphasized = active.highlight.includes(k.key);
          return (
            <li
              key={k.key}
              className={`rounded-xl border p-4 shadow-sm ${
                emphasized ? "border-primary/40 bg-primary-subtle" : "border-slate-200 bg-white"
              }`}
            >
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{k.label}</p>
              <p className={`mt-1 text-2xl font-bold ${emphasized ? "text-primary" : "text-slate-900"}`}>{k.value}</p>
              <p className="mt-1 text-xs text-slate-500">{k.hint}</p>
            </li>
          );
        })}
      </ul>

      <p className="text-xs font-semibold text-warning">
        All figures above are synthetic demonstration data — not clinical results, benchmarks, or performance claims.
      </p>
    </div>
  );
}
