import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchJSON(path: string) {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

type ReadinessState =
  | "READY_FOR_PACKAGING"
  | "REQUIRES_RECLEANING"
  | "REQUIRES_SUPERVISOR_REVIEW"
  | "REQUIRES_REPAIR"
  | "REMOVED_FROM_SERVICE"
  | "PENDING_ANALYSIS";

interface ClinicalInspectionReadiness {
  total_inspections: number;
  ready_for_packaging: number;
  readiness_rate: number | null;
  mean_readiness_score: number | null;
  by_state: Record<ReadinessState, number>;
}

interface Tray {
  tray_id: string;
  instrument_count: number;
  tray_readiness_state: ReadinessState;
  ready_for_packaging: boolean;
  blocking_instruments: { instrument_type: string; readiness_state: ReadinessState }[];
}

interface Instrument {
  instrument_identity: string;
  instrument_type: string;
  tray_id: string | null;
  readiness_state: ReadinessState;
  readiness_score: number | null;
  confirmed: boolean;
  last_inspected_at: string | null;
}

interface Facility {
  facility: string;
  total_inspections: number;
  readiness_rate: number | null;
  trend: "improving" | "declining" | "stable" | "insufficient_data";
  by_state: Record<ReadinessState, number>;
}

interface HighRiskFinding {
  inspection_id: number;
  instrument_type: string;
  detected_issue: string;
  readiness_state: ReadinessState;
  risk_score: number;
  facility: string | null;
  tray_id: string | null;
}

interface SupervisorReviewItem {
  inspection_id: number;
  instrument_type: string;
  detected_issue: string;
  recommended_action: string | null;
  risk_score: number;
}

interface MissingZoneItem {
  inspection_id: number;
  instrument_type: string;
  coverage_quality: string;
  overall_coverage: number | null;
  missing_required_zones: string[];
}

interface BaselineCoverage {
  total_imaged_inspections: number;
  with_approved_baseline: number;
  baseline_coverage_rate: number | null;
  instrument_types_missing_baseline: { instrument_type: string; inspection_count: number }[];
}

interface RepairRemoveQueue {
  repair_candidates: { count: number; cases: HighRiskFinding[] };
  removed_from_service: { count: number; cases: HighRiskFinding[] };
}

interface ExecutiveRiskDashboard {
  readiness_summary: ClinicalInspectionReadiness;
  high_risk_findings_count: number;
  supervisor_review_backlog: number;
  repair_candidates_count: number;
  removed_from_service_count: number;
  baseline_coverage_rate: number | null;
  instrument_types_missing_baseline: number;
  facility_rollup: Facility[];
  anatomy_zone_failure_trend: { zone: string; missed_count: number; case_count: number }[];
}

interface Dashboard {
  clinical_inspection_readiness: ClinicalInspectionReadiness;
  tray_readiness: Tray[];
  instrument_readiness: Instrument[];
  facility_readiness: Facility[];
  high_risk_findings_queue: HighRiskFinding[];
  supervisor_review_queue: SupervisorReviewItem[];
  missing_zone_coverage_queue: MissingZoneItem[];
  baseline_coverage: BaselineCoverage;
  repair_remove_queue: RepairRemoveQueue;
  executive_risk_dashboard: ExecutiveRiskDashboard;
}

const PERSONAS = [
  "SPD Technician",
  "SPD Supervisor",
  "SPD Manager",
  "Market Director",
  "Infection Prevention",
  "Executive Leadership",
] as const;
type Persona = (typeof PERSONAS)[number];

// Which of the ten modules each persona sees by default — same API payload,
// different operational lens.
const PERSONA_MODULES: Record<Persona, string[]> = {
  "SPD Technician": ["missing_zone_coverage", "high_risk_findings", "instrument_readiness"],
  "SPD Supervisor": ["supervisor_review_queue", "high_risk_findings", "tray_readiness", "instrument_readiness"],
  "SPD Manager": [
    "readiness_summary", "tray_readiness", "facility_readiness", "high_risk_findings",
    "supervisor_review_queue", "missing_zone_coverage", "baseline_coverage", "repair_remove_queue",
  ],
  "Market Director": ["facility_readiness", "executive_risk", "baseline_coverage"],
  "Infection Prevention": ["high_risk_findings", "executive_risk", "missing_zone_coverage"],
  "Executive Leadership": ["readiness_summary", "executive_risk", "facility_readiness"],
};

const STATE_LABEL: Record<ReadinessState, string> = {
  READY_FOR_PACKAGING: "Ready for packaging",
  REQUIRES_RECLEANING: "Requires recleaning",
  REQUIRES_SUPERVISOR_REVIEW: "Requires supervisor review",
  REQUIRES_REPAIR: "Requires repair",
  REMOVED_FROM_SERVICE: "Removed from service",
  PENDING_ANALYSIS: "Pending analysis",
};

const STATE_TONE: Record<ReadinessState, string> = {
  READY_FOR_PACKAGING: "border-green-300 bg-green-50 text-green-800",
  REQUIRES_RECLEANING: "border-amber-300 bg-amber-50 text-amber-800",
  REQUIRES_SUPERVISOR_REVIEW: "border-amber-300 bg-amber-50 text-amber-800",
  REQUIRES_REPAIR: "border-red-300 bg-red-50 text-red-800",
  REMOVED_FROM_SERVICE: "border-red-300 bg-red-50 text-red-800",
  PENDING_ANALYSIS: "border-gray-200 bg-gray-50 text-gray-600",
};

function pct(v: number | null): string {
  return v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`;
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}

function KPI({ label, value, tone }: { label: string; value: string | number; tone?: "danger" | "warning" | "ok" }) {
  const toneClass =
    tone === "danger" ? "border-red-300 bg-red-50 text-red-800"
    : tone === "warning" ? "border-amber-300 bg-amber-50 text-amber-800"
    : tone === "ok" ? "border-green-300 bg-green-50 text-green-800"
    : "border-gray-200 bg-white text-gray-900";
  return (
    <div className={`rounded-lg border p-4 ${toneClass}`}>
      <p className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}

function StatePill({ state }: { state: ReadinessState }) {
  return (
    <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded border ${STATE_TONE[state]}`}>
      {STATE_LABEL[state]}
    </span>
  );
}

export default function PreSterilizationCommandCenter() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [persona, setPersona] = useState<Persona>("SPD Manager");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchJSON("/api/pre-sterilization-command-center/dashboard")
      .then(setDashboard)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-gray-500">Loading pre-sterilization command center…</div>;
  if (error) return <div className="p-6 text-red-600">Failed to load command center data: {error}</div>;
  if (!dashboard) return null;

  const visible = new Set(PERSONA_MODULES[persona]);
  const readiness = dashboard.clinical_inspection_readiness;

  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pre-Sterilization Command Center</h1>
        <p className="text-sm text-gray-500 mt-1">
          Are these instruments clinically ready to move forward to packaging and sterilization —
          and if not, why not, where, and what should SPD do next?
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {PERSONAS.map((p) => (
          <button
            key={p}
            onClick={() => setPersona(p)}
            className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
              persona === p
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {visible.has("readiness_summary") && (
        <section>
          <SectionHeader title="Clinical Inspection Readiness" subtitle="Module 1 — packaging readiness across all reviewed inspections." />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPI label="Total inspections" value={readiness.total_inspections} />
            <KPI
              label="Ready for packaging"
              value={pct(readiness.readiness_rate)}
              tone={readiness.readiness_rate !== null && readiness.readiness_rate >= 0.85 ? "ok" : "warning"}
            />
            <KPI label="Mean readiness score" value={readiness.mean_readiness_score ?? "—"} />
            <KPI
              label="Requiring repair / removed"
              value={(readiness.by_state.REQUIRES_REPAIR || 0) + (readiness.by_state.REMOVED_FROM_SERVICE || 0)}
              tone="danger"
            />
          </div>
        </section>
      )}

      {visible.has("tray_readiness") && (
        <section>
          <SectionHeader title="Tray Readiness" subtitle="Module 2 — a tray is only ready when every instrument in it is ready (weakest link)." />
          <div className="overflow-x-auto bg-white border rounded-lg">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
                <tr>
                  <th className="text-left px-3 py-2">Tray</th>
                  <th className="text-right px-3 py-2">Instruments</th>
                  <th className="text-left px-3 py-2">Status</th>
                  <th className="text-left px-3 py-2">Blocking</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.tray_readiness.map((t) => (
                  <tr key={t.tray_id} className="border-t">
                    <td className="px-3 py-2 font-medium text-gray-900">{t.tray_id}</td>
                    <td className="px-3 py-2 text-right">{t.instrument_count}</td>
                    <td className="px-3 py-2"><StatePill state={t.tray_readiness_state} /></td>
                    <td className="px-3 py-2 text-gray-600">
                      {t.blocking_instruments.map((b) => b.instrument_type).join(", ") || "—"}
                    </td>
                  </tr>
                ))}
                {dashboard.tray_readiness.length === 0 && (
                  <tr><td colSpan={4} className="px-3 py-6 text-center text-gray-400">No tray-tagged inspections yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {visible.has("instrument_readiness") && (
        <section>
          <SectionHeader title="Instrument Readiness" subtitle="Module 3 — current state of each identified instrument's most recent inspection." />
          <div className="overflow-x-auto bg-white border rounded-lg">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
                <tr>
                  <th className="text-left px-3 py-2">Instrument</th>
                  <th className="text-left px-3 py-2">Type</th>
                  <th className="text-left px-3 py-2">Status</th>
                  <th className="text-right px-3 py-2">Score</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.instrument_readiness.slice(0, 25).map((i) => (
                  <tr key={i.instrument_identity} className="border-t">
                    <td className="px-3 py-2 font-mono text-xs text-gray-600">{i.instrument_identity}</td>
                    <td className="px-3 py-2">{i.instrument_type}</td>
                    <td className="px-3 py-2"><StatePill state={i.readiness_state} /></td>
                    <td className="px-3 py-2 text-right">{i.readiness_score ?? "—"}</td>
                  </tr>
                ))}
                {dashboard.instrument_readiness.length === 0 && (
                  <tr><td colSpan={4} className="px-3 py-6 text-center text-gray-400">No inspections yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {visible.has("facility_readiness") && (
        <section>
          <SectionHeader title="Facility Readiness" subtitle="Module 4 — packaging readiness rate and trend by facility." />
          <div className="overflow-x-auto bg-white border rounded-lg">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
                <tr>
                  <th className="text-left px-3 py-2">Facility</th>
                  <th className="text-right px-3 py-2">Inspections</th>
                  <th className="text-right px-3 py-2">Readiness rate</th>
                  <th className="text-left px-3 py-2">Trend</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.facility_readiness.map((f) => (
                  <tr key={f.facility} className="border-t">
                    <td className="px-3 py-2 font-medium text-gray-900">{f.facility}</td>
                    <td className="px-3 py-2 text-right">{f.total_inspections}</td>
                    <td className="px-3 py-2 text-right">{pct(f.readiness_rate)}</td>
                    <td className="px-3 py-2 capitalize text-gray-600">{f.trend.replace("_", " ")}</td>
                  </tr>
                ))}
                {dashboard.facility_readiness.length === 0 && (
                  <tr><td colSpan={4} className="px-3 py-6 text-center text-gray-400">No facility-tagged inspections yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {visible.has("high_risk_findings") && (
        <section>
          <SectionHeader title="High-Risk Findings Queue" subtitle="Module 5 — unresolved critical findings (blood, tissue, bone, crack, insulation damage)." />
          <div className="rounded-lg border bg-white divide-y">
            {dashboard.high_risk_findings_queue.slice(0, 15).map((h) => (
              <div key={h.inspection_id} className="p-3 flex items-center justify-between text-sm">
                <div>
                  <span className="font-medium text-gray-900">#{h.inspection_id}</span>{" "}
                  <span className="text-gray-600">{h.instrument_type} — {h.detected_issue}</span>
                  {h.facility && <span className="text-gray-400"> · {h.facility}</span>}
                </div>
                <StatePill state={h.readiness_state} />
              </div>
            ))}
            {dashboard.high_risk_findings_queue.length === 0 && (
              <div className="p-6 text-center text-gray-400">No unresolved high-risk findings.</div>
            )}
          </div>
        </section>
      )}

      {visible.has("supervisor_review_queue") && (
        <section>
          <SectionHeader title="Supervisor Review Queue" subtitle="Module 6 — inspections pending supervisor confirmation." />
          <div className="rounded-lg border bg-white divide-y">
            {dashboard.supervisor_review_queue.slice(0, 15).map((s) => (
              <div key={s.inspection_id} className="p-3 text-sm">
                <span className="font-medium text-gray-900">#{s.inspection_id}</span>{" "}
                <span className="text-gray-600">{s.instrument_type} — {s.recommended_action || s.detected_issue}</span>
              </div>
            ))}
            {dashboard.supervisor_review_queue.length === 0 && (
              <div className="p-6 text-center text-gray-400">Supervisor review queue is empty.</div>
            )}
          </div>
        </section>
      )}

      {visible.has("missing_zone_coverage") && (
        <section>
          <SectionHeader title="Missing Anatomy Zone Coverage" subtitle="Module 7 — inspections missing required high-risk zone images." />
          <div className="rounded-lg border bg-white divide-y">
            {dashboard.missing_zone_coverage_queue.slice(0, 15).map((m) => (
              <div key={m.inspection_id} className="p-3 text-sm">
                <span className="font-medium text-gray-900">#{m.inspection_id}</span>{" "}
                <span className="text-gray-600">{m.instrument_type} — {m.coverage_quality}</span>
                {m.missing_required_zones.length > 0 && (
                  <span className="text-gray-400"> · missing: {m.missing_required_zones.join(", ")}</span>
                )}
              </div>
            ))}
            {dashboard.missing_zone_coverage_queue.length === 0 && (
              <div className="p-6 text-center text-gray-400">No coverage gaps detected.</div>
            )}
          </div>
        </section>
      )}

      {visible.has("baseline_coverage") && (
        <section>
          <SectionHeader title="Baseline Coverage" subtitle="Module 8 — how many inspections had an approved baseline to compare against." />
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
            <KPI label="Imaged inspections" value={dashboard.baseline_coverage.total_imaged_inspections} />
            <KPI label="With approved baseline" value={dashboard.baseline_coverage.with_approved_baseline} />
            <KPI label="Coverage rate" value={pct(dashboard.baseline_coverage.baseline_coverage_rate)} />
          </div>
          <div className="rounded-lg border bg-white divide-y">
            {dashboard.baseline_coverage.instrument_types_missing_baseline.slice(0, 10).map((g) => (
              <div key={g.instrument_type} className="p-3 text-sm flex justify-between">
                <span className="text-gray-900">{g.instrument_type}</span>
                <span className="text-gray-500">{g.inspection_count} inspection(s)</span>
              </div>
            ))}
            {dashboard.baseline_coverage.instrument_types_missing_baseline.length === 0 && (
              <div className="p-6 text-center text-gray-400">No baseline gaps detected.</div>
            )}
          </div>
        </section>
      )}

      {visible.has("repair_remove_queue") && (
        <section>
          <SectionHeader title="Repair / Remove From Service Queue" subtitle="Module 9 — structural defects split into repairable vs. retired." />
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-semibold text-amber-800 mb-2">Repair candidates ({dashboard.repair_remove_queue.repair_candidates.count})</p>
              <div className="rounded-lg border bg-white divide-y">
                {dashboard.repair_remove_queue.repair_candidates.cases.slice(0, 10).map((c) => (
                  <div key={c.inspection_id} className="p-2 text-sm">#{c.inspection_id} — {c.instrument_type} ({c.detected_issue})</div>
                ))}
                {dashboard.repair_remove_queue.repair_candidates.count === 0 && (
                  <div className="p-4 text-center text-gray-400 text-sm">None.</div>
                )}
              </div>
            </div>
            <div>
              <p className="text-sm font-semibold text-red-800 mb-2">Removed from service ({dashboard.repair_remove_queue.removed_from_service.count})</p>
              <div className="rounded-lg border bg-white divide-y">
                {dashboard.repair_remove_queue.removed_from_service.cases.slice(0, 10).map((c) => (
                  <div key={c.inspection_id} className="p-2 text-sm">#{c.inspection_id} — {c.instrument_type} ({c.detected_issue})</div>
                ))}
                {dashboard.repair_remove_queue.removed_from_service.count === 0 && (
                  <div className="p-4 text-center text-gray-400 text-sm">None.</div>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      {visible.has("executive_risk") && (
        <section>
          <SectionHeader title="Executive Risk Dashboard" subtitle="Module 10 — the roll-up view across readiness, safety queues, and zone trends." />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <KPI label="High-risk findings" value={dashboard.executive_risk_dashboard.high_risk_findings_count} tone="danger" />
            <KPI label="Supervisor backlog" value={dashboard.executive_risk_dashboard.supervisor_review_backlog} tone="warning" />
            <KPI label="Repair candidates" value={dashboard.executive_risk_dashboard.repair_candidates_count} />
            <KPI label="Removed from service" value={dashboard.executive_risk_dashboard.removed_from_service_count} tone="danger" />
          </div>
          <p className="text-sm font-medium text-gray-700 mb-2">Highest anatomy-zone failure trend (from pilot validation ground truth)</p>
          <div className="rounded-lg border bg-white divide-y">
            {dashboard.executive_risk_dashboard.anatomy_zone_failure_trend.map((z) => (
              <div key={z.zone} className="p-2 text-sm flex justify-between">
                <span>{z.zone}</span>
                <span className="text-gray-500">{z.missed_count} missed / {z.case_count} cases</span>
              </div>
            ))}
            {dashboard.executive_risk_dashboard.anatomy_zone_failure_trend.length === 0 && (
              <div className="p-4 text-center text-gray-400 text-sm">No pilot validation zone data yet.</div>
            )}
          </div>
        </section>
      )}

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
        ⚠ This is a pre-sterilization clinical inspection readiness gate. It reports packaging/inspection
        readiness only — it does not monitor, measure, or validate the sterilization cycle itself, and every
        escalation requires SPD supervisor review before disposition.
      </p>
    </div>
  );
}
