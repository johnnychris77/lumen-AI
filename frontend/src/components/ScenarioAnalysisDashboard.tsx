/**
 * v2.5 — Project Sentinel: Predictive Simulation & Clinical Scenario Engine.
 * Decision Comparison Dashboard — evaluates multiple possible inspection
 * dispositions (reclean / supervisor override / repair evaluation / remove
 * from service) before recommending a path, with confidence, evidence, and
 * reasoning for each option. Advisory only — see disclaimer below.
 */
import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface ScenarioProjection {
  scenario_key: string;
  scenario_label: string;
  likely_consequence: string;
  rationale: string;
  quality_risk: number;
  operational_impact: number;
  repeat_inspection_probability: number;
  repair_likelihood: number;
  supervisor_workload_impact: number;
  confidence_level: number;
  is_recommended: boolean;
}

interface EvidenceNode {
  node: string;
  value: unknown;
  detail?: string;
}

interface SimulationRun {
  id: number;
  inspection_id: number;
  recommended_scenario: string;
  recommended_confidence: number;
  reasoning: string;
  evidence: EvidenceNode[];
  recommended: ScenarioProjection;
  alternatives: ScenarioProjection[];
  scenarios: ScenarioProjection[];
  human_review_required: boolean;
  disclaimer: string;
}

interface WorkflowImpact {
  scenario_key: string;
  inspection_queue_impact_hours: number;
  or_readiness_impact: string;
  repair_backlog_impact: number;
  technician_workload_impact: number;
  supervisor_workload_impact: number;
  instrument_availability_impact: number;
  narrative: string;
}

interface InstrumentHealth {
  instrument_identity: string;
  instrument_type: string;
  health_trend: string;
  corrosion_progression: string;
  damage_progression: string;
  inspection_frequency_days: number | null;
  repair_frequency_days: number | null;
  expected_remaining_service_life_days: number | null;
  confidence_level: number;
}

interface EducationalComparison {
  comparisons: { scenario_key: string; scenario_label: string; narrative: string }[];
  historical_case_count: number;
  historical_outcome_distribution: Record<string, number>;
}

interface Analytics {
  most_common_scenarios: Record<string, number>;
  most_effective_recommendation: string | null;
  prediction_accuracy: number | null;
  prediction_sample_size: number;
  override_outcomes: Record<string, number>;
  repair_outcomes: number;
}

const TABS = ["Recommendation", "Workflow Impact", "Instrument Health", "Educational Mode", "Analytics"] as const;
type Tab = (typeof TABS)[number];

function pct(n: number): string {
  return `${Math.round(n * 100)}%`;
}

function riskColor(n: number): string {
  if (n >= 0.6) return "text-red-600";
  if (n >= 0.3) return "text-amber-600";
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

function ScenarioCard({ s }: { s: ScenarioProjection }) {
  return (
    <div
      className={`rounded-lg border p-4 ${
        s.is_recommended ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <p className="text-sm font-semibold text-slate-900">{s.scenario_label}</p>
        {s.is_recommended && (
          <span className="rounded-full bg-emerald-600 px-2 py-0.5 text-xs font-semibold text-white">
            Recommended
          </span>
        )}
      </div>
      <p className="text-sm text-slate-700 mb-2">{s.likely_consequence}</p>
      <p className="text-xs text-slate-500 mb-3 italic">{s.rationale}</p>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-slate-500">Quality risk: </span>
          <span className={`font-semibold ${riskColor(s.quality_risk)}`}>{pct(s.quality_risk)}</span>
        </div>
        <div>
          <span className="text-slate-500">Operational impact: </span>
          <span className={`font-semibold ${riskColor(s.operational_impact)}`}>{pct(s.operational_impact)}</span>
        </div>
        <div>
          <span className="text-slate-500">Repeat inspection: </span>
          <span className="font-semibold text-slate-800">{pct(s.repeat_inspection_probability)}</span>
        </div>
        <div>
          <span className="text-slate-500">Repair likelihood: </span>
          <span className="font-semibold text-slate-800">{pct(s.repair_likelihood)}</span>
        </div>
        <div>
          <span className="text-slate-500">Supervisor workload: </span>
          <span className="font-semibold text-slate-800">{pct(s.supervisor_workload_impact)}</span>
        </div>
        <div>
          <span className="text-slate-500">Confidence: </span>
          <span className="font-semibold text-slate-800">{pct(s.confidence_level)}</span>
        </div>
      </div>
    </div>
  );
}

export default function ScenarioAnalysisDashboard() {
  const { role } = useAuth();
  const canRecordOutcome = role === "admin" || role === "spd_manager";

  const [tab, setTab] = useState<Tab>("Recommendation");
  const [inspectionId, setInspectionId] = useState("");
  const [run, setRun] = useState<SimulationRun | null>(null);
  const [workflowImpact, setWorkflowImpact] = useState<WorkflowImpact | null>(null);
  const [instrumentBarcode, setInstrumentBarcode] = useState("");
  const [instrumentHealth, setInstrumentHealth] = useState<InstrumentHealth | null>(null);
  const [eduInstrumentType, setEduInstrumentType] = useState("");
  const [eduFindingType, setEduFindingType] = useState("");
  const [educational, setEducational] = useState<EducationalComparison | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [actualDisposition, setActualDisposition] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    if (!inspectionId.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.post<SimulationRun>(`/api/scenario-analysis/${inspectionId}/generate`);
      setRun(result);
    } catch {
      setError("Could not generate scenarios for that inspection.");
    } finally {
      setBusy(false);
    }
  }

  async function loadWorkflowImpact() {
    if (!run) return;
    setBusy(true);
    try {
      const result = await api.get<WorkflowImpact>(`/api/scenario-analysis/${run.inspection_id}/workflow-impact`);
      setWorkflowImpact(result);
    } catch {
      setError("Could not load workflow impact.");
    } finally {
      setBusy(false);
    }
  }

  async function loadInstrumentHealth() {
    if (!instrumentBarcode.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.get<InstrumentHealth>(
        `/api/scenario-analysis/instrument-health?instrument_barcode=${encodeURIComponent(instrumentBarcode)}`
      );
      setInstrumentHealth(result);
    } catch {
      setError("No inspection history found for that instrument.");
    } finally {
      setBusy(false);
    }
  }

  async function loadEducational() {
    if (!eduInstrumentType.trim() || !eduFindingType.trim()) return;
    setBusy(true);
    try {
      const result = await api.get<EducationalComparison>(
        `/api/scenario-analysis/education/compare?instrument_type=${encodeURIComponent(eduInstrumentType)}&finding_type=${encodeURIComponent(eduFindingType)}`
      );
      setEducational(result);
    } finally {
      setBusy(false);
    }
  }

  async function loadAnalytics() {
    setBusy(true);
    try {
      const result = await api.get<Analytics>(`/api/scenario-analysis/analytics`);
      setAnalytics(result);
    } finally {
      setBusy(false);
    }
  }

  async function recordOutcome() {
    if (!run || !actualDisposition.trim()) return;
    setBusy(true);
    try {
      await api.post(`/api/scenario-analysis/${run.id}/actual-outcome`, { actual_disposition: actualDisposition });
      setActualDisposition("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Scenario Analysis</h2>
        <p className="text-sm text-slate-500">
          Predictive simulation of inspection outcomes — evaluates the safest operational path across multiple
          evidence-based scenarios before recommending one.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
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

      {error && <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>}

      {tab === "Recommendation" && (
        <div className="space-y-4">
          <Section title="Generate Scenario Analysis">
            <div className="flex gap-2">
              <input
                value={inspectionId}
                onChange={(e) => setInspectionId(e.target.value)}
                placeholder="Inspection ID"
                className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
              />
              <button
                onClick={generate}
                disabled={busy}
                className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
              >
                {busy ? "Generating…" : "Generate"}
              </button>
            </div>
          </Section>

          {run && (
            <>
              <Section title="Reasoning">
                <p className="text-sm text-slate-700">{run.reasoning}</p>
                <p className="mt-1 text-xs text-slate-500">
                  Recommended confidence: <span className="font-semibold">{pct(run.recommended_confidence)}</span>
                </p>
              </Section>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {run.scenarios.map((s) => (
                  <ScenarioCard key={s.scenario_key} s={s} />
                ))}
              </div>

              <Section title="Evidence">
                <ul className="space-y-1 text-sm text-slate-700">
                  {run.evidence.map((e, i) => (
                    <li key={i}>
                      <span className="font-medium">{e.node}:</span> {String(e.value)}
                      {e.detail ? ` — ${e.detail}` : ""}
                    </li>
                  ))}
                </ul>
              </Section>

              {canRecordOutcome && (
                <Section title="Outcome Learning — Record Actual Disposition">
                  <div className="flex gap-2">
                    <input
                      value={actualDisposition}
                      onChange={(e) => setActualDisposition(e.target.value)}
                      placeholder="e.g. Reclean, Repair Evaluation, Remove From Service"
                      className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
                    />
                    <button
                      onClick={recordOutcome}
                      disabled={busy}
                      className="rounded-md bg-slate-700 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
                    >
                      Record
                    </button>
                  </div>
                </Section>
              )}

              <p className="text-xs text-slate-400 italic">{run.disclaimer}</p>
            </>
          )}
        </div>
      )}

      {tab === "Workflow Impact" && (
        <div className="space-y-3">
          <Section title="Workflow Impact Analysis">
            <button
              onClick={loadWorkflowImpact}
              disabled={!run || busy}
              className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {run ? "Load Workflow Impact" : "Generate a scenario analysis first"}
            </button>
          </Section>
          {workflowImpact && (
            <Section title={`Projected Impact — ${workflowImpact.scenario_key.replace(/_/g, " ")}`}>
              <p className="text-sm text-slate-700 mb-2">{workflowImpact.narrative}</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                <div><div className="text-xs text-slate-500">Queue impact</div><div className="font-medium">{workflowImpact.inspection_queue_impact_hours}h</div></div>
                <div><div className="text-xs text-slate-500">OR readiness</div><div className="font-medium capitalize">{workflowImpact.or_readiness_impact.replace(/_/g, " ")}</div></div>
                <div><div className="text-xs text-slate-500">Repair backlog</div><div className="font-medium">{pct(workflowImpact.repair_backlog_impact)}</div></div>
                <div><div className="text-xs text-slate-500">Technician workload</div><div className="font-medium">{pct(workflowImpact.technician_workload_impact)}</div></div>
                <div><div className="text-xs text-slate-500">Supervisor workload</div><div className="font-medium">{pct(workflowImpact.supervisor_workload_impact)}</div></div>
                <div><div className="text-xs text-slate-500">Instrument availability</div><div className="font-medium">{pct(workflowImpact.instrument_availability_impact)}</div></div>
              </div>
            </Section>
          )}
        </div>
      )}

      {tab === "Instrument Health" && (
        <div className="space-y-3">
          <Section title="Instrument Health Projection">
            <div className="flex gap-2">
              <input
                value={instrumentBarcode}
                onChange={(e) => setInstrumentBarcode(e.target.value)}
                placeholder="Instrument barcode"
                className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
              />
              <button
                onClick={loadInstrumentHealth}
                disabled={busy}
                className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
              >
                Project
              </button>
            </div>
          </Section>
          {instrumentHealth && (
            <Section title={instrumentHealth.instrument_type}>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                <div><div className="text-xs text-slate-500">Health trend</div><div className="font-medium capitalize">{instrumentHealth.health_trend.replace(/_/g, " ")}</div></div>
                <div><div className="text-xs text-slate-500">Corrosion progression</div><div className="font-medium capitalize">{instrumentHealth.corrosion_progression.replace(/_/g, " ")}</div></div>
                <div><div className="text-xs text-slate-500">Damage progression</div><div className="font-medium capitalize">{instrumentHealth.damage_progression.replace(/_/g, " ")}</div></div>
                <div><div className="text-xs text-slate-500">Inspection frequency</div><div className="font-medium">{instrumentHealth.inspection_frequency_days ?? "—"} days</div></div>
                <div><div className="text-xs text-slate-500">Repair frequency</div><div className="font-medium">{instrumentHealth.repair_frequency_days ?? "—"} days</div></div>
                <div><div className="text-xs text-slate-500">Expected remaining life</div><div className="font-medium">{instrumentHealth.expected_remaining_service_life_days ?? "—"} days</div></div>
              </div>
            </Section>
          )}
        </div>
      )}

      {tab === "Educational Mode" && (
        <div className="space-y-3">
          <Section title="Compare What-If Scenarios">
            <div className="flex gap-2 mb-2">
              <input
                value={eduInstrumentType}
                onChange={(e) => setEduInstrumentType(e.target.value)}
                placeholder="Instrument type (e.g. kerrison_rongeur)"
                className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
              />
              <input
                value={eduFindingType}
                onChange={(e) => setEduFindingType(e.target.value)}
                placeholder="Finding type (e.g. corrosion)"
                className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
              />
              <button
                onClick={loadEducational}
                disabled={busy}
                className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
              >
                Compare
              </button>
            </div>
          </Section>
          {educational && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {educational.comparisons.map((c) => (
                  <Section key={c.scenario_key} title={c.scenario_label}>
                    <p className="text-sm text-slate-700">{c.narrative}</p>
                  </Section>
                ))}
              </div>
              <Section title={`Historical Cases (${educational.historical_case_count})`}>
                <ul className="text-sm text-slate-700">
                  {Object.entries(educational.historical_outcome_distribution).map(([outcome, count]) => (
                    <li key={outcome}>{outcome || "unspecified"}: {count}</li>
                  ))}
                </ul>
              </Section>
            </>
          )}
        </div>
      )}

      {tab === "Analytics" && (
        <div className="space-y-3">
          <Section title="Enterprise Scenario Analytics">
            <button
              onClick={loadAnalytics}
              disabled={busy}
              className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              Load Analytics
            </button>
          </Section>
          {analytics && (
            <>
              <Section title="Most Common Scenarios">
                <ul className="text-sm text-slate-700">
                  {Object.entries(analytics.most_common_scenarios).map(([key, count]) => (
                    <li key={key}>{key.replace(/_/g, " ")}: {count}</li>
                  ))}
                </ul>
              </Section>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Section title="Prediction Accuracy">
                  <p className="text-2xl font-bold text-slate-900">
                    {analytics.prediction_accuracy !== null ? pct(analytics.prediction_accuracy) : "—"}
                  </p>
                  <p className="text-xs text-slate-500">n={analytics.prediction_sample_size}</p>
                </Section>
                <Section title="Most Effective Recommendation">
                  <p className="text-sm font-medium text-slate-800">
                    {analytics.most_effective_recommendation?.replace(/_/g, " ") ?? "—"}
                  </p>
                </Section>
                <Section title="Repair Outcomes">
                  <p className="text-2xl font-bold text-slate-900">{analytics.repair_outcomes}</p>
                </Section>
              </div>
              <Section title="Override Outcomes">
                <ul className="text-sm text-slate-700">
                  {Object.entries(analytics.override_outcomes).map(([action, count]) => (
                    <li key={action}>{action.replace(/_/g, " ")}: {count}</li>
                  ))}
                </ul>
              </Section>
            </>
          )}
        </div>
      )}

      <p className="text-xs text-slate-400 italic">
        Project Sentinel is a decision-support simulation — it evaluates evidence-based scenarios and projects
        possible operational and clinical outcomes. It does not make autonomous clinical decisions and does not
        establish causation. Human review is required before any operational action.
      </p>
    </div>
  );
}
