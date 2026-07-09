/**
 * v3.1 — Project Atlas: Enterprise Intelligence & Multi-Site Operations.
 * Cross-facility rollup for health-system leadership — every score here
 * aggregates counts/rates already computed per facility. Never patient-
 * identifying data. Advisory only; human review governs any resulting
 * action, and each facility's own governance retains full authority.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface FacilitySnapshot {
  facility_id: string;
  facility_name: string;
  market_id: string;
  tenant_id: string;
  quality_score: number | null;
  risk_score: number | null;
  health_score: number | null;
  digital_twin_health_pct: number | null;
  supervisor_agreement_rate: number | null;
  training_index: number | null;
  knowledge_index: number | null;
}

interface EnterpriseDashboard {
  system_id: string;
  facility_count: number;
  enterprise_quality_score: number | null;
  enterprise_risk_score: number | null;
  inspection_volume: number;
  pass_rate_pct: number | null;
  coverage_quality_pct: number | null;
  ai_confidence_avg: number | null;
  supervisor_agreement_rate: number | null;
  digital_twin_health_pct: number | null;
  knowledge_growth: number | null;
  facility_comparison: FacilitySnapshot[];
  disclaimer: string;
}

interface FacilityBenchmark {
  facility_id: string;
  facility_name: string;
  inspection_quality_pct: number | null;
  coverage_pct: number | null;
  blood_finding_count: number;
  bone_finding_count: number;
  corrosion_finding_count: number;
  damage_finding_count: number;
  repeat_finding_count: number;
  supervisor_override_rate_pct: number | null;
  knowledge_contributions: number;
  training_progress_pct: number | null;
}

interface WatchlistEntry {
  id: number;
  entity_type: string;
  entity_value: string;
  direction: string;
  score: number;
  reason: string;
}

interface SharedArticle {
  id: number;
  title: string;
  category: string;
  owner: string;
  sharing_scope: string;
  version: number;
  active: boolean;
}

interface EnterpriseAlert {
  id: number;
  title: string;
  narrative: string;
  recommendation: string;
  reasoning: string;
  severity: string;
  affected_facility_count: number;
  acknowledged: boolean;
}

interface ExecutiveReport {
  id: number;
  report_ref: string;
  audience: string;
  cadence: string;
  period_label: string;
  title: string;
}

const TABS = ["Enterprise Overview", "Benchmarking", "Watchlists", "Knowledge Sharing", "Alerts", "Reports"] as const;
type Tab = (typeof TABS)[number];

function severityColor(sev: string): string {
  switch (sev) {
    case "critical": return "bg-red-100 text-red-800";
    case "high": return "bg-orange-100 text-orange-800";
    case "medium": return "bg-amber-100 text-amber-800";
    default: return "bg-slate-100 text-slate-700";
  }
}

function riskScoreColor(score: number): string {
  if (score >= 70) return "text-red-600";
  if (score >= 40) return "text-amber-600";
  return "text-emerald-600";
}

function directionColor(direction: string): string {
  return direction === "improvement" ? "text-emerald-600" : "text-red-600";
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

export default function AtlasDashboard() {
  const [systemId, setSystemId] = useState("");
  const [tab, setTab] = useState<Tab>("Enterprise Overview");
  const [busy, setBusy] = useState(false);

  const [dashboard, setDashboard] = useState<EnterpriseDashboard | null>(null);
  const [benchmarks, setBenchmarks] = useState<FacilityBenchmark[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [articles, setArticles] = useState<SharedArticle[]>([]);
  const [alerts, setAlerts] = useState<EnterpriseAlert[]>([]);
  const [reports, setReports] = useState<ExecutiveReport[]>([]);

  async function loadDashboard() {
    if (!systemId) return;
    setBusy(true);
    try {
      const result = await api.get<EnterpriseDashboard>(`/api/atlas/dashboard/${systemId}`);
      setDashboard(result);
    } finally {
      setBusy(false);
    }
  }

  async function loadBenchmarks() {
    if (!systemId) return;
    setBusy(true);
    try {
      const result = await api.get<{ facilities: FacilityBenchmark[] }>(`/api/atlas/benchmarking/${systemId}`);
      setBenchmarks(result.facilities);
    } finally {
      setBusy(false);
    }
  }

  async function loadWatchlist() {
    if (!systemId) return;
    setBusy(true);
    try {
      const result = await api.get<{ watchlist: WatchlistEntry[] }>(`/api/atlas/watchlist/${systemId}`);
      setWatchlist(result.watchlist);
    } finally {
      setBusy(false);
    }
  }

  async function refreshWatchlist() {
    if (!systemId) return;
    setBusy(true);
    try {
      const result = await api.post<{ watchlist: WatchlistEntry[] }>(`/api/atlas/watchlist/${systemId}/refresh`);
      setWatchlist(result.watchlist);
    } finally {
      setBusy(false);
    }
  }

  async function loadArticles() {
    if (!systemId) return;
    setBusy(true);
    try {
      const result = await api.get<{ articles: SharedArticle[] }>(`/api/atlas/knowledge/${systemId}`);
      setArticles(result.articles);
    } finally {
      setBusy(false);
    }
  }

  async function loadAlerts() {
    if (!systemId) return;
    setBusy(true);
    try {
      const result = await api.get<{ alerts: EnterpriseAlert[] }>(`/api/atlas/alerts/${systemId}`);
      setAlerts(result.alerts);
    } finally {
      setBusy(false);
    }
  }

  async function generateAlerts() {
    if (!systemId) return;
    setBusy(true);
    try {
      const result = await api.post<{ alerts: EnterpriseAlert[] }>(`/api/atlas/alerts/${systemId}/generate`);
      setAlerts(result.alerts);
    } finally {
      setBusy(false);
    }
  }

  async function acknowledgeAlert(id: number) {
    if (!systemId) return;
    setBusy(true);
    try {
      await api.post(`/api/atlas/alerts/${systemId}/${id}/acknowledge`);
      await loadAlerts();
    } finally {
      setBusy(false);
    }
  }

  async function loadReports() {
    if (!systemId) return;
    setBusy(true);
    try {
      const result = await api.get<{ reports: ExecutiveReport[] }>(`/api/atlas/reports/${systemId}`);
      setReports(result.reports);
    } finally {
      setBusy(false);
    }
  }

  async function generateReport(audience: string, cadence: string) {
    if (!systemId) return;
    setBusy(true);
    try {
      await api.post(`/api/atlas/reports/${systemId}/generate`, { audience, cadence });
      await loadReports();
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (systemId) loadDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [systemId]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Project Atlas</h2>
          <p className="text-sm text-slate-500">
            Enterprise intelligence and multi-site operations — cross-facility benchmarking, watchlists, knowledge
            sharing, and executive reporting for health-system leadership. Every comparison is a potential
            association for leadership awareness, not a causal determination; each facility retains full local
            governance authority.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={systemId}
            onChange={(e) => setSystemId(e.target.value)}
            placeholder="Health system ID"
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          />
          <button onClick={loadDashboard} disabled={busy || !systemId} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 whitespace-nowrap">
            {busy ? "Loading…" : "Load System"}
          </button>
        </div>
      </div>

      <div className="flex gap-1 border-b border-slate-200 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              if (t === "Benchmarking") loadBenchmarks();
              if (t === "Watchlists") loadWatchlist();
              if (t === "Knowledge Sharing") loadArticles();
              if (t === "Alerts") loadAlerts();
              if (t === "Reports") loadReports();
            }}
            className={`px-4 py-2 text-sm font-medium rounded-t-md ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {!systemId && <p className="text-sm text-slate-400">Enter a health system ID above to load enterprise intelligence.</p>}

      {tab === "Enterprise Overview" && dashboard && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Section title="Enterprise Quality Score"><p className="text-3xl font-bold text-slate-900">{dashboard.enterprise_quality_score ?? "—"}</p></Section>
            <Section title="Enterprise Risk Score">
              <p className={`text-3xl font-bold ${dashboard.enterprise_risk_score != null ? riskScoreColor(dashboard.enterprise_risk_score) : "text-slate-900"}`}>
                {dashboard.enterprise_risk_score ?? "—"}
              </p>
            </Section>
            <Section title="Inspection Volume"><p className="text-3xl font-bold text-slate-900">{dashboard.inspection_volume}</p></Section>
            <Section title="Pass Rate"><p className="text-3xl font-bold text-slate-900">{dashboard.pass_rate_pct ?? "—"}%</p></Section>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Section title="Coverage Quality"><p className="text-2xl font-bold text-slate-900">{dashboard.coverage_quality_pct ?? "—"}%</p></Section>
            <Section title="AI Confidence"><p className="text-2xl font-bold text-slate-900">{dashboard.ai_confidence_avg ?? "—"}</p></Section>
            <Section title="Supervisor Agreement"><p className="text-2xl font-bold text-slate-900">{dashboard.supervisor_agreement_rate ?? "—"}%</p></Section>
            <Section title="Digital Twin Health"><p className="text-2xl font-bold text-slate-900">{dashboard.digital_twin_health_pct ?? "—"}%</p></Section>
          </div>

          <Section title={`Facility Comparison (${dashboard.facility_count} facilities)`}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 uppercase">
                    <th className="pb-2 pr-4">Facility</th>
                    <th className="pb-2 pr-4">Quality</th>
                    <th className="pb-2 pr-4">Risk</th>
                    <th className="pb-2 pr-4">Health</th>
                    <th className="pb-2 pr-4">Digital Twin</th>
                    <th className="pb-2 pr-4">Supervisor Agreement</th>
                    <th className="pb-2 pr-4">Training</th>
                    <th className="pb-2">Knowledge</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.facility_comparison.map((f) => (
                    <tr key={f.facility_id} className="border-t border-slate-100">
                      <td className="py-1.5 pr-4 font-medium">{f.facility_name}</td>
                      <td className="py-1.5 pr-4">{f.quality_score ?? "—"}</td>
                      <td className={`py-1.5 pr-4 font-semibold ${f.risk_score != null ? riskScoreColor(f.risk_score) : ""}`}>{f.risk_score ?? "—"}</td>
                      <td className="py-1.5 pr-4">{f.health_score ?? "—"}</td>
                      <td className="py-1.5 pr-4">{f.digital_twin_health_pct ?? "—"}%</td>
                      <td className="py-1.5 pr-4">{f.supervisor_agreement_rate ?? "—"}%</td>
                      <td className="py-1.5 pr-4">{f.training_index ?? "—"}</td>
                      <td className="py-1.5">{f.knowledge_index ?? "—"}</td>
                    </tr>
                  ))}
                  {dashboard.facility_comparison.length === 0 && (
                    <tr><td colSpan={8} className="py-2 text-slate-400">No facilities found for this system.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Section>

          <p className="text-xs text-slate-400 italic">{dashboard.disclaimer}</p>
        </div>
      )}

      {tab === "Benchmarking" && (
        <Section title="Cross-Facility Benchmark">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 uppercase">
                  <th className="pb-2 pr-4">Facility</th>
                  <th className="pb-2 pr-4">Quality</th>
                  <th className="pb-2 pr-4">Coverage</th>
                  <th className="pb-2 pr-4">Blood</th>
                  <th className="pb-2 pr-4">Bone</th>
                  <th className="pb-2 pr-4">Corrosion</th>
                  <th className="pb-2 pr-4">Damage</th>
                  <th className="pb-2 pr-4">Repeat</th>
                  <th className="pb-2 pr-4">Override Rate</th>
                  <th className="pb-2 pr-4">Knowledge</th>
                  <th className="pb-2">Training</th>
                </tr>
              </thead>
              <tbody>
                {benchmarks.map((b) => (
                  <tr key={b.facility_id} className="border-t border-slate-100">
                    <td className="py-1.5 pr-4 font-medium">{b.facility_name}</td>
                    <td className="py-1.5 pr-4">{b.inspection_quality_pct ?? "—"}%</td>
                    <td className="py-1.5 pr-4">{b.coverage_pct ?? "—"}%</td>
                    <td className="py-1.5 pr-4">{b.blood_finding_count}</td>
                    <td className="py-1.5 pr-4">{b.bone_finding_count}</td>
                    <td className="py-1.5 pr-4">{b.corrosion_finding_count}</td>
                    <td className="py-1.5 pr-4">{b.damage_finding_count}</td>
                    <td className="py-1.5 pr-4">{b.repeat_finding_count}</td>
                    <td className="py-1.5 pr-4">{b.supervisor_override_rate_pct ?? "—"}%</td>
                    <td className="py-1.5 pr-4">{b.knowledge_contributions}</td>
                    <td className="py-1.5">{b.training_progress_pct ?? "—"}%</td>
                  </tr>
                ))}
                {benchmarks.length === 0 && (
                  <tr><td colSpan={11} className="py-2 text-slate-400">No benchmark data yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {tab === "Watchlists" && (
        <div className="space-y-3">
          <button onClick={refreshWatchlist} disabled={busy || !systemId} className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
            Refresh Watchlists
          </button>
          <Section title="Active Enterprise Watchlist Entries">
            <ul className="space-y-1 text-sm">
              {watchlist.map((w) => (
                <li key={w.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                  <span>
                    <span className="font-medium capitalize">{w.entity_type.replace(/_/g, " ")}</span>: {w.entity_value} — {w.reason}
                  </span>
                  <span className={`font-semibold ${directionColor(w.direction)}`}>{w.direction === "improvement" ? "▲" : "▼"} {Math.round(w.score * 100)}%</span>
                </li>
              ))}
              {watchlist.length === 0 && <p className="text-slate-400">No active watchlist entries</p>}
            </ul>
          </Section>
        </div>
      )}

      {tab === "Knowledge Sharing" && (
        <Section title="Shared Knowledge Articles">
          <ul className="space-y-1 text-sm">
            {articles.map((a) => (
              <li key={a.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{a.title}</span>
                <span className="text-xs text-slate-500">{a.category.replace(/_/g, " ")} · {a.sharing_scope.replace(/_/g, " ")} · v{a.version} · {a.owner}</span>
              </li>
            ))}
            {articles.length === 0 && <p className="text-slate-400">No shared articles yet</p>}
          </ul>
        </Section>
      )}

      {tab === "Alerts" && (
        <div className="space-y-3">
          <button onClick={generateAlerts} disabled={busy || !systemId} className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
            Generate Alerts
          </button>
          <Section title="Enterprise Alerts">
            <ul className="space-y-2 text-sm">
              {alerts.map((a) => (
                <li key={a.id} className="border-b border-slate-100 pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${severityColor(a.severity)}`}>{a.severity}</span>
                      <span className="font-medium">{a.title}</span>
                    </div>
                    {!a.acknowledged && (
                      <button onClick={() => acknowledgeAlert(a.id)} disabled={busy} className="rounded-md bg-slate-700 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50">
                        Acknowledge
                      </button>
                    )}
                  </div>
                  <p className="text-slate-700 mt-1">{a.narrative}</p>
                  <p className="text-slate-500 text-xs mt-1">Reasoning: {a.reasoning}</p>
                  <p className="text-slate-500 text-xs mt-1">Recommendation: {a.recommendation}</p>
                </li>
              ))}
              {alerts.length === 0 && <p className="text-slate-400">No open alerts</p>}
            </ul>
          </Section>
        </div>
      )}

      {tab === "Reports" && (
        <div className="space-y-3">
          <div className="flex gap-2 flex-wrap">
            {["ceo", "coo", "spd_director", "market_director", "hospital_summary"].map((audience) => (
              <button
                key={audience}
                onClick={() => generateReport(audience, "monthly")}
                disabled={busy || !systemId}
                className="rounded-md bg-slate-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
              >
                Generate {audience.replace(/_/g, " ")} report
              </button>
            ))}
          </div>
          <Section title="Executive Reports">
            <ul className="space-y-1 text-sm">
              {reports.map((r) => (
                <li key={r.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                  <span className="font-medium">{r.title}</span>
                  <span className="flex items-center gap-2 text-xs text-slate-500">
                    {r.period_label}
                    <a className="underline" href={`/api/atlas/reports/${systemId}/${r.id}.csv`}>CSV</a>
                    <a className="underline" href={`/api/atlas/reports/${systemId}/${r.id}.xlsx`}>XLSX</a>
                    <a className="underline" href={`/api/atlas/reports/${systemId}/${r.id}.pdf`}>PDF</a>
                  </span>
                </li>
              ))}
              {reports.length === 0 && <p className="text-slate-400">No reports generated yet</p>}
            </ul>
          </Section>
        </div>
      )}

      <p className="text-xs text-slate-400 italic">
        Project Atlas aggregates counts and rates already computed per facility — it never exposes patient-
        identifying data. Every enterprise comparison, benchmark, watchlist entry, and recommendation is a potential
        association for leadership awareness, not a causal or clinical determination; human review governs any
        resulting action, and each facility's own supervisors and local governance retain full authority over
        their own operations.
      </p>
    </div>
  );
}
