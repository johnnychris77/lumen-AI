/**
 * v3.4 — Project Horizon: Federated Clinical Intelligence & Global
 * Learning Network. Research Portal (Section 7) — global trend
 * summaries, published knowledge, emerging risks, and released research
 * datasets, all de-identified. Every participant retains ownership of
 * its own operational data; only approved, anonymized, aggregated
 * knowledge appears here.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface FederatedSignal {
  id: number;
  signal_category: string;
  scope_key: string;
  tenant_count: number;
  value: number | null;
  trend_direction: string;
}

interface Benchmark {
  metric_name: string;
  n_facilities: number;
  suppressed: boolean;
  p50: number | null;
  p90: number | null;
}

interface EmergingTrend {
  id: number;
  trend_type: string;
  description: string;
  tenant_count: number;
  severity: string;
  status: string;
}

interface Contribution {
  id: number;
  contribution_type: string;
  title: string;
  category: string;
  version: number;
}

interface ResearchPortal {
  global_trend_summaries: FederatedSignal[];
  global_benchmarks: Benchmark[];
  emerging_risks: EmergingTrend[];
  published_knowledge: Contribution[];
  released_datasets: { id: number; title: string; dataset_type: string; n_facilities_contributing: number }[];
  disclaimer: string;
}

const TABS = ["Global Trends", "Benchmarks", "Emerging Risks", "Published Knowledge", "Datasets"] as const;
type Tab = (typeof TABS)[number];

function severityColor(sev: string): string {
  switch (sev) {
    case "high": return "bg-orange-100 text-orange-800";
    case "critical": return "bg-red-100 text-red-800";
    default: return "bg-amber-100 text-amber-800";
  }
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

export default function ResearchPortalDashboard() {
  const [tab, setTab] = useState<Tab>("Global Trends");
  const [busy, setBusy] = useState(false);
  const [portal, setPortal] = useState<ResearchPortal | null>(null);

  async function loadPortal() {
    setBusy(true);
    try {
      const result = await api.get<ResearchPortal>("/api/horizon/research/portal");
      setPortal(result);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadPortal();
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Research Portal</h2>
        <p className="text-sm text-slate-500">
          Project Horizon — a federated clinical intelligence network for sterile processing. Every dataset here is
          de-identified, aggregated, and governance-approved; no organization's identity, patients, or raw data are
          ever exposed. Every participant retains full ownership of its own operational data.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium rounded-t-md ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {busy && !portal && <p className="text-sm text-slate-400">Loading research portal…</p>}

      {tab === "Global Trends" && portal && (
        <Section title="Global Trend Summaries">
          <ul className="space-y-1 text-sm">
            {portal.global_trend_summaries.map((s) => (
              <li key={s.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium capitalize">{s.signal_category.replace(/_/g, " ")}: {s.scope_key}</span>
                <span className="text-xs text-slate-500">{s.value ?? "—"} · {s.tenant_count} orgs · {s.trend_direction}</span>
              </li>
            ))}
            {portal.global_trend_summaries.length === 0 && <p className="text-slate-400">No published federated signals yet</p>}
          </ul>
        </Section>
      )}

      {tab === "Benchmarks" && portal && (
        <Section title="Global Benchmarking (percentiles, never raw org data)">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 uppercase">
                  <th className="pb-2 pr-4">Metric</th>
                  <th className="pb-2 pr-4">Organizations</th>
                  <th className="pb-2 pr-4">p50</th>
                  <th className="pb-2">p90</th>
                </tr>
              </thead>
              <tbody>
                {portal.global_benchmarks.map((b) => (
                  <tr key={b.metric_name} className="border-t border-slate-100">
                    <td className="py-1.5 pr-4 font-medium capitalize">{b.metric_name.replace(/_/g, " ")}</td>
                    <td className="py-1.5 pr-4">{b.n_facilities}</td>
                    <td className="py-1.5 pr-4">{b.suppressed ? "suppressed (k-anonymity)" : b.p50}</td>
                    <td className="py-1.5">{b.suppressed ? "—" : b.p90}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {tab === "Emerging Risks" && portal && (
        <Section title="Emerging Inspection Science Risks">
          <ul className="space-y-2 text-sm">
            {portal.emerging_risks.map((t) => (
              <li key={t.id} className="border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${severityColor(t.severity)}`}>{t.severity}</span>
                  <span className="font-medium capitalize">{t.trend_type.replace(/_/g, " ")}</span>
                </div>
                <p className="text-slate-700 mt-1">{t.description}</p>
              </li>
            ))}
            {portal.emerging_risks.length === 0 && <p className="text-slate-400">No emerging risks detected yet</p>}
          </ul>
        </Section>
      )}

      {tab === "Published Knowledge" && portal && (
        <Section title="Published Knowledge Contributions">
          <ul className="space-y-1 text-sm">
            {portal.published_knowledge.map((c) => (
              <li key={c.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{c.title}</span>
                <span className="text-xs text-slate-500">{c.contribution_type.replace(/_/g, " ")} · v{c.version}</span>
              </li>
            ))}
            {portal.published_knowledge.length === 0 && <p className="text-slate-400">No approved contributions yet</p>}
          </ul>
        </Section>
      )}

      {tab === "Datasets" && portal && (
        <Section title="Released Research Datasets">
          <ul className="space-y-1 text-sm">
            {portal.released_datasets.map((d) => (
              <li key={d.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{d.title}</span>
                <span className="text-xs text-slate-500">{d.dataset_type} · {d.n_facilities_contributing} orgs</span>
              </li>
            ))}
            {portal.released_datasets.length === 0 && <p className="text-slate-400">No datasets released yet</p>}
          </ul>
        </Section>
      )}

      {portal && <p className="text-xs text-slate-400 italic">{portal.disclaimer}</p>}
    </div>
  );
}
