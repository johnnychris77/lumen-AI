/**
 * v2.8 — LumenAI OR Connect: Perioperative Coordination Engine (Project Symphony).
 * Case Intelligence Dashboard — coordinates surgical case scheduling,
 * vendor tray logistics, instrument inspection, repair status, and
 * supervisor approval into one explainable Case Readiness Score.
 * Advisory only — does not replace Epic, ReadySet, supply chain, or
 * clinical engineering systems.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface CaseSummary {
  case_id: number;
  case_ref: string;
  procedure: string;
  scheduled_start: string;
  readiness_score: number;
  open_risk_count: number;
}

interface DashboardSummary {
  date: string;
  total_cases: number;
  cases: CaseSummary[];
  high_risk_cases: CaseSummary[];
  vendor_tray_status: Record<string, number>;
  inspection_completion_pct: number | null;
  outstanding_blockers: { id: number; risk_type: string; severity: string; message: string }[];
  projected_delays: CaseSummary[];
}

interface CaseDetail {
  id: number;
  case_ref: string;
  procedure: string;
  service_line: string;
  surgeon: string;
  facility_name: string;
  operating_room: string;
  scheduled_start: string;
  vendor_name: string;
  vendor_trays: Record<string, unknown>[];
  hospital_trays: Record<string, unknown>[];
  digital_twins: string[];
  inspection_status: string;
  clinical_readiness: string;
  repair_status: string;
  supervisor_approval: string;
}

interface ReadinessScore {
  score: number;
  rationale: string;
  factors: Record<string, { weight: number; value: number; points: number }>;
}

interface TimelineStep {
  step: string;
  completed: boolean;
  timestamp: string | null;
}

interface Timeline {
  steps: TimelineStep[];
  blockers: { step: string; reason: string; delayed: boolean }[];
  past_due: boolean;
}

interface RiskAlert {
  id: number;
  risk_type: string;
  severity: string;
  message: string;
}

interface RepairRequest {
  id: number;
  status: string;
  repair_type: string;
  expected_return_date: string | null;
  instrument_identity: string;
}

interface ClinicalEngineeringSummary {
  open_repairs: RepairRequest[];
  total_repairs: number;
  avg_turnaround_days: number | null;
  replacement_available_count: number;
}

interface ExecutiveDashboard {
  case_readiness_trend: { date: string; avg_score: number }[];
  delay_causes: Record<string, number>;
  vendor_performance: Record<string, { total: number; on_time_pct: number | null }>;
  inspection_turnaround_hours: number | null;
  repair_impact: { cases_with_open_repairs: number; avg_repair_turnaround_days: number | null };
  quality_alerts: number;
  operational_bottlenecks: { service_line: string; risk_count: number }[];
}

const TABS = ["Today's Cases", "Case Detail", "Clinical Engineering", "Executive Dashboard"] as const;
type Tab = (typeof TABS)[number];

function severityColor(sev: string): string {
  switch (sev) {
    case "critical": return "bg-red-100 text-red-800";
    case "high": return "bg-orange-100 text-orange-800";
    case "medium": return "bg-amber-100 text-amber-800";
    default: return "bg-slate-100 text-slate-700";
  }
}

function scoreColor(score: number): string {
  if (score >= 85) return "text-emerald-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

export default function CaseIntelligenceDashboard() {
  const { role } = useAuth();
  const canApprove = role === "admin" || role === "spd_manager";

  const [tab, setTab] = useState<Tab>("Today's Cases");
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [caseIdInput, setCaseIdInput] = useState("");
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [readiness, setReadiness] = useState<ReadinessScore | null>(null);
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [risks, setRisks] = useState<RiskAlert[]>([]);
  const [clinicalEngineering, setClinicalEngineering] = useState<ClinicalEngineeringSummary | null>(null);
  const [executive, setExecutive] = useState<ExecutiveDashboard | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard() {
    setBusy(true);
    try {
      const result = await api.get<DashboardSummary>(`/api/or-connect/dashboard`);
      setDashboard(result);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadCase() {
    if (!caseIdInput.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const [detail, score, tl, riskList] = await Promise.all([
        api.get<CaseDetail>(`/api/or-connect/cases/${caseIdInput}`),
        api.get<ReadinessScore>(`/api/or-connect/cases/${caseIdInput}/readiness-score`),
        api.get<Timeline>(`/api/or-connect/cases/${caseIdInput}/timeline`),
        api.get<{ risks: RiskAlert[] }>(`/api/or-connect/cases/${caseIdInput}/risks`),
      ]);
      setCaseDetail(detail);
      setReadiness(score);
      setTimeline(tl);
      setRisks(riskList.risks);
    } catch {
      setError("Could not load that case. Check the case ID.");
      setCaseDetail(null);
    } finally {
      setBusy(false);
    }
  }

  async function generateNotifications() {
    if (!caseDetail) return;
    setBusy(true);
    try {
      await api.post(`/api/or-connect/cases/${caseDetail.id}/notifications/generate`);
    } finally {
      setBusy(false);
    }
  }

  async function approveCase() {
    if (!caseDetail) return;
    setBusy(true);
    try {
      await api.post(`/api/or-connect/cases/${caseDetail.id}/approve`, { approved: true });
      await loadCase();
    } finally {
      setBusy(false);
    }
  }

  async function loadClinicalEngineering() {
    setBusy(true);
    try {
      const result = await api.get<ClinicalEngineeringSummary>(`/api/or-connect/clinical-engineering`);
      setClinicalEngineering(result);
    } finally {
      setBusy(false);
    }
  }

  async function loadExecutiveDashboard() {
    setBusy(true);
    try {
      const result = await api.get<ExecutiveDashboard>(`/api/or-connect/executive-dashboard`);
      setExecutive(result);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Case Intelligence — LumenAI OR Connect</h2>
        <p className="text-sm text-slate-500">
          Coordinates surgical scheduling, vendor tray logistics, inspection status, repair status, and
          supervisor approval into one explainable Case Readiness Score. Advisory only — LumenAI does not
          replace Epic, ReadySet, supply chain, or clinical engineering systems.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              if (t === "Clinical Engineering") loadClinicalEngineering();
              if (t === "Executive Dashboard") loadExecutiveDashboard();
            }}
            className={`px-4 py-2 text-sm font-medium rounded-t-md ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {error && <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>}

      {tab === "Today's Cases" && dashboard && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Section title="Total Cases"><p className="text-2xl font-bold text-slate-900">{dashboard.total_cases}</p></Section>
            <Section title="High-Risk Cases"><p className="text-2xl font-bold text-red-600">{dashboard.high_risk_cases.length}</p></Section>
            <Section title="Inspection Completion">
              <p className="text-2xl font-bold text-slate-900">{dashboard.inspection_completion_pct ?? "—"}%</p>
            </Section>
            <Section title="Projected Delays"><p className="text-2xl font-bold text-amber-600">{dashboard.projected_delays.length}</p></Section>
          </div>

          <Section title="Today's Cases">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-400">
                  <th className="py-1 pr-3">Case</th>
                  <th className="py-1 pr-3">Procedure</th>
                  <th className="py-1 pr-3">Scheduled</th>
                  <th className="py-1 pr-3">Readiness</th>
                  <th className="py-1 pr-3">Open Risks</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.cases.map((c) => (
                  <tr key={c.case_id} className="border-t border-slate-100">
                    <td className="py-1 pr-3 font-medium">{c.case_ref}</td>
                    <td className="py-1 pr-3">{c.procedure}</td>
                    <td className="py-1 pr-3 text-slate-500">{new Date(c.scheduled_start).toLocaleString()}</td>
                    <td className={`py-1 pr-3 font-semibold ${scoreColor(c.readiness_score)}`}>{c.readiness_score}</td>
                    <td className="py-1 pr-3">{c.open_risk_count}</td>
                  </tr>
                ))}
                {dashboard.cases.length === 0 && (
                  <tr><td colSpan={5} className="py-4 text-center text-slate-400">No cases scheduled today</td></tr>
                )}
              </tbody>
            </table>
          </Section>

          <Section title="Vendor Tray Status">
            <ul className="text-sm text-slate-700">
              {Object.entries(dashboard.vendor_tray_status).map(([status, count]) => (
                <li key={status}>{status}: {count}</li>
              ))}
            </ul>
          </Section>

          <Section title="Outstanding Blockers">
            {dashboard.outstanding_blockers.length === 0 && <p className="text-sm text-slate-400">No open blockers</p>}
            <ul className="space-y-1">
              {dashboard.outstanding_blockers.map((b) => (
                <li key={b.id} className="flex items-center gap-2 text-sm">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${severityColor(b.severity)}`}>{b.severity}</span>
                  {b.message}
                </li>
              ))}
            </ul>
          </Section>
        </div>
      )}

      {tab === "Case Detail" && (
        <div className="space-y-3">
          <Section title="Load a Case">
            <div className="flex gap-2">
              <input
                value={caseIdInput}
                onChange={(e) => setCaseIdInput(e.target.value)}
                placeholder="Case ID"
                className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
              />
              <button onClick={loadCase} disabled={busy} className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
                Load
              </button>
            </div>
          </Section>

          {caseDetail && readiness && timeline && (
            <>
              <Section title={`${caseDetail.case_ref} — ${caseDetail.procedure}`}>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm mb-3">
                  <div><div className="text-xs text-slate-500">Surgeon</div><div className="font-medium">{caseDetail.surgeon || "—"}</div></div>
                  <div><div className="text-xs text-slate-500">OR</div><div className="font-medium">{caseDetail.operating_room || "—"}</div></div>
                  <div><div className="text-xs text-slate-500">Service Line</div><div className="font-medium">{caseDetail.service_line || "—"}</div></div>
                  <div><div className="text-xs text-slate-500">Vendor</div><div className="font-medium">{caseDetail.vendor_name || "—"}</div></div>
                  <div><div className="text-xs text-slate-500">Inspection Status</div><div className="font-medium">{caseDetail.inspection_status}</div></div>
                  <div><div className="text-xs text-slate-500">Clinical Readiness</div><div className="font-medium capitalize">{caseDetail.clinical_readiness.replace(/_/g, " ")}</div></div>
                  <div><div className="text-xs text-slate-500">Repair Status</div><div className="font-medium capitalize">{caseDetail.repair_status.replace(/_/g, " ")}</div></div>
                  <div><div className="text-xs text-slate-500">Supervisor Approval</div><div className="font-medium capitalize">{caseDetail.supervisor_approval}</div></div>
                </div>
                {canApprove && caseDetail.supervisor_approval !== "approved" && (
                  <button onClick={approveCase} disabled={busy} className="rounded-md bg-emerald-600 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
                    Approve Case
                  </button>
                )}
              </Section>

              <Section title={`Case Readiness Score — ${readiness.score}/100`}>
                <p className="text-sm text-slate-700 mb-2">{readiness.rationale}</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  {Object.entries(readiness.factors).map(([name, f]) => (
                    <div key={name}>
                      <div className="text-slate-500">{name.replace(/_/g, " ")}</div>
                      <div className="font-medium">{Math.round(f.value * 100)}% ({f.points}/{f.weight} pts)</div>
                    </div>
                  ))}
                </div>
              </Section>

              <Section title="Intelligent Readiness Timeline">
                <div className="flex flex-wrap gap-2">
                  {timeline.steps.map((s) => (
                    <div key={s.step} className={`rounded-md px-3 py-2 text-xs ${s.completed ? "bg-emerald-50 border border-emerald-300" : "bg-slate-50 border border-slate-300"}`}>
                      <div className="font-medium">{s.step}</div>
                      <div className={s.completed ? "text-emerald-700" : "text-slate-400"}>{s.completed ? "Complete" : "Pending"}</div>
                    </div>
                  ))}
                </div>
                {timeline.blockers.length > 0 && (
                  <div className="mt-2 text-xs text-amber-700">
                    Blockers: {timeline.blockers.map((b) => b.step).join(", ")}
                    {timeline.past_due && " — case is past its scheduled start"}
                  </div>
                )}
              </Section>

              <Section title="Operational Risks">
                {risks.length === 0 && <p className="text-sm text-slate-400">No open risks detected</p>}
                <ul className="space-y-1">
                  {risks.map((r) => (
                    <li key={r.id} className="flex items-center gap-2 text-sm">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${severityColor(r.severity)}`}>{r.severity}</span>
                      {r.message}
                    </li>
                  ))}
                </ul>
                <button onClick={generateNotifications} disabled={busy} className="mt-2 rounded-md bg-slate-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">
                  Notify Stakeholders
                </button>
              </Section>
            </>
          )}
        </div>
      )}

      {tab === "Clinical Engineering" && clinicalEngineering && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <Section title="Total Repairs"><p className="text-2xl font-bold text-slate-900">{clinicalEngineering.total_repairs}</p></Section>
            <Section title="Avg Turnaround"><p className="text-2xl font-bold text-slate-900">{clinicalEngineering.avg_turnaround_days ?? "—"} days</p></Section>
            <Section title="Replacements Available"><p className="text-2xl font-bold text-slate-900">{clinicalEngineering.replacement_available_count}</p></Section>
          </div>
          <Section title="Open Repair Requests">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-400">
                  <th className="py-1 pr-3">Instrument</th>
                  <th className="py-1 pr-3">Type</th>
                  <th className="py-1 pr-3">Status</th>
                  <th className="py-1 pr-3">Expected Return</th>
                </tr>
              </thead>
              <tbody>
                {clinicalEngineering.open_repairs.map((r) => (
                  <tr key={r.id} className="border-t border-slate-100">
                    <td className="py-1 pr-3">{r.instrument_identity}</td>
                    <td className="py-1 pr-3">{r.repair_type || "—"}</td>
                    <td className="py-1 pr-3 capitalize">{r.status.replace(/_/g, " ")}</td>
                    <td className="py-1 pr-3 text-slate-500">
                      {r.expected_return_date ? new Date(r.expected_return_date).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))}
                {clinicalEngineering.open_repairs.length === 0 && (
                  <tr><td colSpan={4} className="py-4 text-center text-slate-400">No open repair requests</td></tr>
                )}
              </tbody>
            </table>
          </Section>
        </div>
      )}

      {tab === "Executive Dashboard" && executive && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Section title="Quality Alerts"><p className="text-2xl font-bold text-red-600">{executive.quality_alerts}</p></Section>
            <Section title="Inspection Turnaround"><p className="text-2xl font-bold text-slate-900">{executive.inspection_turnaround_hours ?? "—"}h</p></Section>
            <Section title="Cases with Open Repairs"><p className="text-2xl font-bold text-slate-900">{executive.repair_impact.cases_with_open_repairs}</p></Section>
            <Section title="Avg Repair Turnaround"><p className="text-2xl font-bold text-slate-900">{executive.repair_impact.avg_repair_turnaround_days ?? "—"} days</p></Section>
          </div>
          <Section title="Case Readiness Trend">
            <ul className="text-sm text-slate-700">
              {executive.case_readiness_trend.map((t) => <li key={t.date}>{t.date}: avg {t.avg_score}</li>)}
              {executive.case_readiness_trend.length === 0 && <p className="text-slate-400">No data yet</p>}
            </ul>
          </Section>
          <Section title="Delay Causes">
            <ul className="text-sm text-slate-700">
              {Object.entries(executive.delay_causes).map(([cause, count]) => <li key={cause}>{cause.replace(/_/g, " ")}: {count}</li>)}
            </ul>
          </Section>
          <Section title="Vendor Performance">
            <ul className="text-sm text-slate-700">
              {Object.entries(executive.vendor_performance).map(([vendor, perf]) => (
                <li key={vendor}>{vendor}: {perf.total} trays, {perf.on_time_pct ?? "—"}% on time</li>
              ))}
            </ul>
          </Section>
          <Section title="Operational Bottlenecks">
            <ul className="text-sm text-slate-700">
              {executive.operational_bottlenecks.map((b) => <li key={b.service_line}>{b.service_line}: {b.risk_count} risks</li>)}
            </ul>
          </Section>
        </div>
      )}

      <p className="text-xs text-slate-400 italic">
        LumenAI OR Connect coordinates quality intelligence across scheduling, vendor, and clinical-engineering
        systems — it does not replace them and does not make autonomous operational or clinical decisions.
        Human review is required before any operational action.
      </p>
    </div>
  );
}
