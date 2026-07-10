/**
 * v3.0 — Project Sentinel: Autonomous Clinical Intelligence Orchestration.
 * Executive Sentinel Dashboard — continuously monitors inspections, Digital
 * Twins, Knowledge Graph, workflow, quality, and enterprise KPIs to
 * proactively surface risk. NOT autonomous clinical decision-making —
 * every signal, watchlist entry, alert, and recommendation is advisory
 * and requires human validation.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface DashboardSummary {
  enterprise_risk_score: number;
  critical_findings: { id: number; title: string; narrative: string }[];
  open_watchlists: { id: number; entity_type: string; entity_value: string; risk_score: number; reason: string }[];
  model_health: {
    ai_confidence_avg: number | null; supervisor_agreement_rate: number | null;
    false_positive_rate: number | null; false_negative_rate: number | null;
    drift_detected: boolean; drift_detail: string;
  };
  knowledge_growth: { date: string; kg_confidence: number | null; kg_sample_size: number }[];
  inspection_throughput: number;
  facility_comparison: { facility: string; total_inspections: number; pass_rate_pct: number | null }[];
  supervisor_workload: Record<string, number>;
  top_emerging_risks: { id: number; signal_type: string; scope: string; occurrences: number; severity: string }[];
  digital_twin_flags: { id: number; instrument_identity: string; tier: string; reason: string }[];
}

interface RiskSignal {
  id: number;
  signal_type: string;
  scope: string;
  occurrences: number;
  severity: string;
  detail: string;
}

interface WatchlistEntry {
  id: number;
  entity_type: string;
  entity_value: string;
  risk_score: number;
  reason: string;
}

interface Recommendation {
  id: number;
  recommendation_type: string;
  target_description: string;
  reasoning: string;
  status: string;
}

interface Alert {
  id: number;
  source: string;
  title: string;
  narrative: string;
  recommendation: string;
  severity: string;
  acknowledged: boolean;
}

interface SupervisorIntelligence {
  high_risk_instruments_awaiting_review: { instruments: WatchlistEntry[]; awaiting_review_count: number };
  recurring_technician_education_needs: { opportunity_type: string; scope_value: string; rationale: string }[];
  coverage_gaps: { incomplete_pct: number | null; incomplete_inspections: number };
  unusual_contamination_trends: RiskSignal[];
  repeated_repair_referrals: RiskSignal[];
  potential_ifu_conflicts: Recommendation[];
}

const TABS = ["Executive Overview", "Risk Signals", "Watchlists", "Recommendations", "Alerts", "Supervisor Intelligence"] as const;
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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

export default function SentinelDashboard() {
  const [tab, setTab] = useState<Tab>("Executive Overview");
  const [busy, setBusy] = useState(false);

  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [signals, setSignals] = useState<RiskSignal[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [supervisorIntel, setSupervisorIntel] = useState<SupervisorIntelligence | null>(null);

  async function loadDashboard() {
    setBusy(true);
    try {
      const result = await api.get<DashboardSummary>("/api/sentinel/dashboard");
      setDashboard(result);
    } finally {
      setBusy(false);
    }
  }

  async function runFullScan() {
    setBusy(true);
    try {
      await api.post("/api/sentinel/scan");
      await loadDashboard();
    } finally {
      setBusy(false);
    }
  }

  async function loadSignals() {
    setBusy(true);
    try {
      const result = await api.get<{ signals: RiskSignal[] }>("/api/sentinel/risk-signals");
      setSignals(result.signals);
    } finally {
      setBusy(false);
    }
  }

  async function detectSignals() {
    setBusy(true);
    try {
      const result = await api.post<{ signals: RiskSignal[] }>("/api/sentinel/risk-signals/detect");
      setSignals(result.signals);
    } finally {
      setBusy(false);
    }
  }

  async function loadWatchlist() {
    setBusy(true);
    try {
      const result = await api.get<{ watchlist: WatchlistEntry[] }>("/api/sentinel/watchlist");
      setWatchlist(result.watchlist);
    } finally {
      setBusy(false);
    }
  }

  async function refreshWatchlist() {
    setBusy(true);
    try {
      const result = await api.post<{ watchlist: WatchlistEntry[] }>("/api/sentinel/watchlist/refresh");
      setWatchlist(result.watchlist);
    } finally {
      setBusy(false);
    }
  }

  async function loadRecommendations() {
    setBusy(true);
    try {
      const result = await api.get<{ recommendations: Recommendation[] }>("/api/sentinel/recommendations");
      setRecommendations(result.recommendations);
    } finally {
      setBusy(false);
    }
  }

  async function generateRecommendations() {
    setBusy(true);
    try {
      const result = await api.post<{ recommendations: Recommendation[] }>("/api/sentinel/recommendations/generate");
      setRecommendations(result.recommendations);
    } finally {
      setBusy(false);
    }
  }

  async function actionRecommendation(id: number) {
    setBusy(true);
    try {
      await api.post(`/api/sentinel/recommendations/${id}/action`);
      await loadRecommendations();
    } finally {
      setBusy(false);
    }
  }

  async function loadAlerts() {
    setBusy(true);
    try {
      const result = await api.get<{ alerts: Alert[] }>("/api/sentinel/alerts");
      setAlerts(result.alerts);
    } finally {
      setBusy(false);
    }
  }

  async function generateAlerts() {
    setBusy(true);
    try {
      const result = await api.post<{ alerts: Alert[] }>("/api/sentinel/alerts/generate");
      setAlerts(result.alerts);
    } finally {
      setBusy(false);
    }
  }

  async function acknowledgeAlert(id: number) {
    setBusy(true);
    try {
      await api.post(`/api/sentinel/alerts/${id}/acknowledge`);
      await loadAlerts();
    } finally {
      setBusy(false);
    }
  }

  async function loadSupervisorIntel() {
    setBusy(true);
    try {
      const result = await api.get<SupervisorIntelligence>("/api/sentinel/supervisor-intelligence");
      setSupervisorIntel(result);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Project Sentinel</h2>
          <p className="text-sm text-slate-500">
            Continuously observes inspections, Digital Twins, the Knowledge Graph, workflow, and quality data to
            proactively surface risk before it reaches the operating room. Not autonomous clinical decision-making —
            human validation remains mandatory.
          </p>
        </div>
        <button onClick={runFullScan} disabled={busy} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 whitespace-nowrap">
          {busy ? "Scanning…" : "Run Full Scan"}
        </button>
      </div>

      <div className="flex gap-1 border-b border-slate-200 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              if (t === "Risk Signals") loadSignals();
              if (t === "Watchlists") loadWatchlist();
              if (t === "Recommendations") loadRecommendations();
              if (t === "Alerts") loadAlerts();
              if (t === "Supervisor Intelligence") loadSupervisorIntel();
            }}
            className={`px-4 py-2 text-sm font-medium rounded-t-md ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Executive Overview" && dashboard && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Section title="Enterprise Risk Score">
              <p className={`text-3xl font-bold ${riskScoreColor(dashboard.enterprise_risk_score)}`}>{dashboard.enterprise_risk_score}</p>
            </Section>
            <Section title="Critical Findings"><p className="text-3xl font-bold text-red-600">{dashboard.critical_findings.length}</p></Section>
            <Section title="Open Watchlists"><p className="text-3xl font-bold text-slate-900">{dashboard.open_watchlists.length}</p></Section>
            <Section title="Inspection Throughput"><p className="text-3xl font-bold text-slate-900">{dashboard.inspection_throughput}</p></Section>
          </div>

          <Section title="Model Health">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
              <div><div className="text-xs text-slate-500">AI Confidence</div><div className="font-medium">{dashboard.model_health.ai_confidence_avg ?? "—"}</div></div>
              <div><div className="text-xs text-slate-500">Supervisor Agreement</div><div className="font-medium">{dashboard.model_health.supervisor_agreement_rate ?? "—"}</div></div>
              <div><div className="text-xs text-slate-500">False Positive Rate</div><div className="font-medium">{dashboard.model_health.false_positive_rate ?? "—"}</div></div>
              <div><div className="text-xs text-slate-500">False Negative Rate</div><div className="font-medium">{dashboard.model_health.false_negative_rate ?? "—"}</div></div>
            </div>
            {dashboard.model_health.drift_detected && (
              <div className="mt-2 rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">
                Model drift detected: {dashboard.model_health.drift_detail}
              </div>
            )}
          </Section>

          <Section title="Top Emerging Risks">
            <ul className="space-y-1 text-sm">
              {dashboard.top_emerging_risks.map((r) => (
                <li key={r.id} className="flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${severityColor(r.severity)}`}>{r.severity}</span>
                  {r.signal_type.replace(/_/g, " ")} — {r.scope} ({r.occurrences})
                </li>
              ))}
              {dashboard.top_emerging_risks.length === 0 && <p className="text-slate-400">No emerging risks detected</p>}
            </ul>
          </Section>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Section title="Facility Comparison">
              <ul className="text-sm text-slate-700">
                {dashboard.facility_comparison.map((f) => (
                  <li key={f.facility}>{f.facility}: {f.total_inspections} inspections, {f.pass_rate_pct ?? "—"}% pass rate</li>
                ))}
              </ul>
            </Section>
            <Section title="Supervisor Workload">
              <ul className="text-sm text-slate-700">
                {Object.entries(dashboard.supervisor_workload).map(([role, count]) => <li key={role}>{role.replace(/_/g, " ")}: {count} unread</li>)}
              </ul>
            </Section>
          </div>
        </div>
      )}

      {tab === "Risk Signals" && (
        <div className="space-y-3">
          <button onClick={detectSignals} disabled={busy} className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
            Detect Risk Signals
          </button>
          <Section title="Open Risk Signals">
            <ul className="space-y-1 text-sm">
              {signals.map((s) => (
                <li key={s.id} className="flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${severityColor(s.severity)}`}>{s.severity}</span>
                  {s.detail}
                </li>
              ))}
              {signals.length === 0 && <p className="text-slate-400">No open risk signals</p>}
            </ul>
          </Section>
        </div>
      )}

      {tab === "Watchlists" && (
        <div className="space-y-3">
          <button onClick={refreshWatchlist} disabled={busy} className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
            Refresh Watchlists
          </button>
          <Section title="Active Watchlist Entries">
            <ul className="space-y-1 text-sm">
              {watchlist.map((w) => (
                <li key={w.id} className="flex items-center justify-between">
                  <span><span className="font-medium capitalize">{w.entity_type.replace(/_/g, " ")}</span>: {w.entity_value} — {w.reason}</span>
                  <span className={`font-semibold ${riskScoreColor(w.risk_score * 100)}`}>{Math.round(w.risk_score * 100)}%</span>
                </li>
              ))}
              {watchlist.length === 0 && <p className="text-slate-400">No active watchlist entries</p>}
            </ul>
          </Section>
        </div>
      )}

      {tab === "Recommendations" && (
        <div className="space-y-3">
          <button onClick={generateRecommendations} disabled={busy} className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
            Generate Recommendations
          </button>
          <Section title="Open Recommendations">
            <ul className="space-y-2 text-sm">
              {recommendations.map((r) => (
                <li key={r.id} className="border-b border-slate-100 pb-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium capitalize">{r.recommendation_type.replace(/_/g, " ")} — {r.target_description}</span>
                    {r.status === "open" && (
                      <button onClick={() => actionRecommendation(r.id)} disabled={busy} className="rounded-md bg-slate-700 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50">
                        Mark Actioned
                      </button>
                    )}
                  </div>
                  <p className="text-slate-500 text-xs mt-1">{r.reasoning}</p>
                </li>
              ))}
              {recommendations.length === 0 && <p className="text-slate-400">No open recommendations</p>}
            </ul>
          </Section>
        </div>
      )}

      {tab === "Alerts" && (
        <div className="space-y-3">
          <button onClick={generateAlerts} disabled={busy} className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
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
                  <p className="text-slate-500 text-xs mt-1">Recommendation: {a.recommendation}</p>
                </li>
              ))}
              {alerts.length === 0 && <p className="text-slate-400">No open alerts</p>}
            </ul>
          </Section>
        </div>
      )}

      {tab === "Supervisor Intelligence" && supervisorIntel && (
        <div className="space-y-3">
          <Section title="High-Risk Instruments Awaiting Review">
            <p className="text-sm text-slate-700 mb-2">{supervisorIntel.high_risk_instruments_awaiting_review.awaiting_review_count} inspections awaiting review</p>
            <ul className="text-sm text-slate-700">
              {supervisorIntel.high_risk_instruments_awaiting_review.instruments.map((i) => <li key={i.id}>{i.entity_value}: {i.reason}</li>)}
            </ul>
          </Section>
          <Section title="Recurring Technician Education Needs">
            <ul className="text-sm text-slate-700">
              {supervisorIntel.recurring_technician_education_needs.map((o, idx) => <li key={idx}>{o.scope_value}: {o.rationale}</li>)}
              {supervisorIntel.recurring_technician_education_needs.length === 0 && <p className="text-slate-400">None</p>}
            </ul>
          </Section>
          <Section title="Coverage Gaps">
            <p className="text-sm text-slate-700">
              {supervisorIntel.coverage_gaps.incomplete_inspections} incomplete-coverage inspections
              ({supervisorIntel.coverage_gaps.incomplete_pct ?? "—"}%)
            </p>
          </Section>
          <Section title="Unusual Contamination Trends">
            <ul className="text-sm text-slate-700">
              {supervisorIntel.unusual_contamination_trends.map((s) => <li key={s.id}>{s.detail}</li>)}
              {supervisorIntel.unusual_contamination_trends.length === 0 && <p className="text-slate-400">None</p>}
            </ul>
          </Section>
          <Section title="Repeated Repair Referrals">
            <ul className="text-sm text-slate-700">
              {supervisorIntel.repeated_repair_referrals.map((s) => <li key={s.id}>{s.detail}</li>)}
              {supervisorIntel.repeated_repair_referrals.length === 0 && <p className="text-slate-400">None</p>}
            </ul>
          </Section>
          <Section title="Potential IFU Conflicts">
            <ul className="text-sm text-slate-700">
              {supervisorIntel.potential_ifu_conflicts.map((r) => <li key={r.id}>{r.target_description}: {r.reasoning}</li>)}
              {supervisorIntel.potential_ifu_conflicts.length === 0 && <p className="text-slate-400">None</p>}
            </ul>
          </Section>
        </div>
      )}

      <p className="text-xs text-slate-400 italic">
        Project Sentinel continuously observes real inspection, Digital Twin, Knowledge Graph, workflow, and
        quality data to proactively surface risk. This is decision support, not autonomous clinical decision-making —
        every signal, watchlist entry, alert, and recommendation requires human validation before any action.
      </p>
    </div>
  );
}
