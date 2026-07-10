/**
 * v4.5 — LumenAI OS: Project Orbit — Perioperative Intelligence &
 * Surgical Readiness Platform.
 *
 * This page previously rendered a thin, mostly client-side heuristic
 * "Surgical Readiness" demo (hard-coded tray rows, fabricated fallback
 * numbers on fetch failure) built on P25's `/api/infrastructure`
 * instrument-quality endpoints. It is rewritten here in place to be
 * Orbit's real, case-scoped Surgical Readiness Platform, backed entirely
 * by `/api/orbit/*` — the `/surgical-readiness` route is kept, but the
 * page underneath it is now a different, real system. See
 * `app/models/orbit_readiness.py`'s naming-disambiguation note.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface CaseSummary {
  id: number;
  case_ref: string;
  procedure: string;
  scheduled_start: string;
}

interface ReadinessDimensionEntry {
  weight: number;
  value: number;
  points: number;
}

interface SurgicalReadiness {
  case_id: number;
  case_ref: string;
  overall_score: number;
  dimensions: Record<string, ReadinessDimensionEntry>;
  rationale: string;
  or_connect_readiness_score: number;
}

interface RiskAlert {
  id: number;
  risk_type: string;
  severity: string;
  message: string;
  recommended_action: string;
  resolved_at: string | null;
}

interface TimelineStep {
  step: string;
  completed: boolean | null;
  timestamp: string | null;
  note?: string;
}

interface ExecutiveSummary {
  date: string;
  cases_today: number;
  readiness_pct: number | null;
  delayed_cases: number;
  inspection_holds: number;
  repair_holds: number;
  digital_twin_risk: { utilization_pct: number; high_risk_alert_count: number };
  top_operational_risks: { risk_type: string; count: number }[];
}

const TABS = ["OR Readiness", "Case Intelligence", "Timeline", "Alerts", "Coordination", "Executive", "Simulation"] as const;
type Tab = (typeof TABS)[number];

function scoreColor(score: number): string {
  if (score >= 80) return "text-emerald-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {children}
    </div>
  );
}

export default function SurgicalReadinessDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("OR Readiness");
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);

  const [readiness, setReadiness] = useState<SurgicalReadiness | null>(null);
  const [intelligence, setIntelligence] = useState<Record<string, unknown> | null>(null);
  const [timeline, setTimeline] = useState<{ steps: TimelineStep[] } | null>(null);
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [coordination, setCoordination] = useState<{ timeline: Record<string, unknown>[]; departments: string[] } | null>(null);
  const [executive, setExecutive] = useState<ExecutiveSummary | null>(null);
  const [simulations, setSimulations] = useState<Record<string, unknown>[]>([]);
  const [hoursShift, setHoursShift] = useState("1");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get<{ cases: CaseSummary[] }>("/api/orbit/cases").then((r) => {
      setCases(r.cases);
      if (r.cases.length && selectedCaseId === null) setSelectedCaseId(r.cases[0].id);
    }).catch(() => {});
    api.get<ExecutiveSummary>("/api/orbit/executive").then(setExecutive).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedCaseId === null) return;
    setLoading(true);
    Promise.allSettled([
      api.get<SurgicalReadiness>(`/api/orbit/case-readiness/${selectedCaseId}`).then(setReadiness),
      api.get<Record<string, unknown>>(`/api/orbit/cases/${selectedCaseId}/intelligence`).then(setIntelligence),
      api.get<{ steps: TimelineStep[] }>(`/api/orbit/cases/${selectedCaseId}/timeline`).then(setTimeline),
      api.get<{ alerts: RiskAlert[] }>(`/api/orbit/readiness-alerts/${selectedCaseId}`).then((r) => setAlerts(r.alerts)),
      api.get<{ timeline: Record<string, unknown>[]; departments: string[] }>(`/api/orbit/cases/${selectedCaseId}/coordination`).then(setCoordination),
      api.get<{ simulations: Record<string, unknown>[] }>(`/api/orbit/cases/${selectedCaseId}/simulations`).then((r) => setSimulations(r.simulations)),
    ]).finally(() => setLoading(false));
  }, [selectedCaseId]);

  async function runTimeShiftSimulation() {
    if (selectedCaseId === null) return;
    await api.post(`/api/orbit/cases/${selectedCaseId}/simulate/time-shift`, { hours_shift: Number(hoursShift) });
    const r = await api.get<{ simulations: Record<string, unknown>[] }>(`/api/orbit/cases/${selectedCaseId}/simulations`);
    setSimulations(r.simulations);
  }

  const selectedCase = cases.find((c) => c.id === selectedCaseId);

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-800">Surgical Readiness Platform</h1>
        <select
          className="rounded border border-slate-300 p-1 text-sm"
          value={selectedCaseId ?? ""}
          onChange={(e) => setSelectedCaseId(Number(e.target.value))}
        >
          {cases.map((c) => (
            <option key={c.id} value={c.id}>{c.case_ref} — {c.procedure}</option>
          ))}
        </select>
      </div>

      <div className="flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`rounded px-3 py-1 text-sm ${activeTab === t ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {loading && <p className="text-xs text-slate-400">Loading case data…</p>}

      {activeTab === "OR Readiness" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Section title="Cases Today">
            <p className="text-2xl font-bold">{executive?.cases_today ?? "—"}</p>
          </Section>
          <Section title="Readiness %">
            <p className={`text-2xl font-bold ${executive ? scoreColor(executive.readiness_pct ?? 0) : ""}`}>
              {executive?.readiness_pct ?? "—"}%
            </p>
          </Section>
          <Section title="Delayed Cases">
            <p className="text-2xl font-bold text-amber-600">{executive?.delayed_cases ?? "—"}</p>
          </Section>
          <Section title="Repair Holds">
            <p className="text-2xl font-bold text-red-600">{executive?.repair_holds ?? "—"}</p>
          </Section>
          <Section title="Today's Cases">
            <ul className="space-y-1 text-sm text-slate-600">
              {cases.map((c) => (
                <li key={c.id} className="flex justify-between">
                  <span>{c.case_ref} — {c.procedure}</span>
                  <span className="text-slate-400">{new Date(c.scheduled_start).toLocaleTimeString()}</span>
                </li>
              ))}
            </ul>
          </Section>
          <Section title="Digital Twin Risk">
            <p className="text-sm text-slate-600">
              Utilization: {executive?.digital_twin_risk?.utilization_pct ?? "—"}% · High-risk alerts: {executive?.digital_twin_risk?.high_risk_alert_count ?? "—"}
            </p>
          </Section>
        </div>
      )}

      {activeTab === "Case Intelligence" && selectedCase && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title={`${selectedCase.case_ref} — Surgical Readiness Score`}>
            {readiness ? (
              <>
                <p className={`text-3xl font-bold ${scoreColor(readiness.overall_score)}`}>{readiness.overall_score}</p>
                <p className="mt-2 text-xs text-slate-500">{readiness.rationale}</p>
                <ul className="mt-2 space-y-1 text-xs text-slate-600">
                  {Object.entries(readiness.dimensions).map(([name, d]) => (
                    <li key={name} className="flex justify-between">
                      <span>{name.replace(/_/g, " ")}</span>
                      <span>{Math.round(d.value * 100)}%</span>
                    </li>
                  ))}
                </ul>
              </>
            ) : <p className="text-xs text-slate-400">No readiness data yet.</p>}
          </Section>
          <Section title="Case Detail">
            {intelligence ? (
              <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs text-slate-600">
                {JSON.stringify({
                  procedure: intelligence.procedure, digital_twins: intelligence.digital_twins,
                  clinical_readiness: intelligence.clinical_readiness, supervisor_holds: intelligence.supervisor_holds,
                  implants: intelligence.implants, loaner_equipment: intelligence.loaner_equipment,
                }, null, 2)}
              </pre>
            ) : <p className="text-xs text-slate-400">No case selected.</p>}
          </Section>
        </div>
      )}

      {activeTab === "Timeline" && (
        <Section title="Surgical Timeline">
          <ol className="space-y-2">
            {(timeline?.steps ?? []).map((s, i) => (
              <li key={i} className="flex items-center gap-2 text-sm">
                <span className={`h-2 w-2 rounded-full ${s.completed ? "bg-emerald-500" : s.completed === null ? "bg-slate-300" : "bg-slate-200"}`} />
                <span className={s.completed ? "text-slate-800" : "text-slate-400"}>{s.step}</span>
                {s.note && <span className="text-xs text-slate-400">— {s.note}</span>}
              </li>
            ))}
          </ol>
        </Section>
      )}

      {activeTab === "Alerts" && (
        <Section title="Readiness Alerts">
          {alerts.length ? (
            <ul className="space-y-2">
              {alerts.map((a) => (
                <li key={a.id} className="rounded border border-slate-200 p-2 text-sm">
                  <div className="flex justify-between">
                    <span className="font-medium">{a.risk_type.replace(/_/g, " ")}</span>
                    <span className="text-xs uppercase text-slate-400">{a.severity}</span>
                  </div>
                  <p className="text-xs text-slate-600">{a.message}</p>
                  <p className="mt-1 text-xs text-indigo-600">→ {a.recommended_action}</p>
                </li>
              ))}
            </ul>
          ) : <p className="text-xs text-slate-400">No open alerts for this case.</p>}
        </Section>
      )}

      {activeTab === "Coordination" && (
        <Section title="Cross-Department Coordination">
          <p className="mb-2 text-xs text-slate-500">Departments: {coordination?.departments.join(", ")}</p>
          <ul className="space-y-1 text-xs text-slate-600">
            {(coordination?.timeline ?? []).map((e, i) => (
              <li key={i}>{String(e.timestamp)} — {String(e.kind)}: {String(e.message)}</li>
            ))}
          </ul>
        </Section>
      )}

      {activeTab === "Executive" && executive && (
        <Section title="Executive Surgical Operations Dashboard">
          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <div>Cases Today: <b>{executive.cases_today}</b></div>
            <div>Readiness %: <b className={scoreColor(executive.readiness_pct ?? 0)}>{executive.readiness_pct}%</b></div>
            <div>Delayed: <b>{executive.delayed_cases}</b></div>
            <div>Inspection Holds: <b>{executive.inspection_holds}</b></div>
          </div>
          <h4 className="mb-1 mt-3 text-xs font-semibold text-slate-600">Top Operational Risks</h4>
          <ul className="text-xs text-slate-600">
            {executive.top_operational_risks.map((r, i) => (
              <li key={i}>{r.risk_type.replace(/_/g, " ")}: {r.count}</li>
            ))}
          </ul>
        </Section>
      )}

      {activeTab === "Simulation" && (
        <Section title="Readiness Simulation">
          <div className="mb-3 flex items-center gap-2">
            <label className="text-xs text-slate-600">Shift case start by (hours):</label>
            <input
              type="number" value={hoursShift} onChange={(e) => setHoursShift(e.target.value)}
              className="w-20 rounded border border-slate-300 p-1 text-sm"
            />
            <button className="rounded bg-indigo-600 px-3 py-1 text-xs text-white" onClick={runTimeShiftSimulation}>
              Run Simulation
            </button>
          </div>
          <ul className="space-y-2 text-xs text-slate-600">
            {simulations.map((s, i) => (
              <li key={i} className="rounded border border-slate-200 p-2">
                <div className="font-medium">{String(s.scenario_type)}</div>
                <div>{String(s.rationale)}</div>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-slate-400">
            Every simulation is a transparent recomputation over this case's real current data — decision support only, human review required.
          </p>
        </Section>
      )}
    </div>
  );
}
