import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { apiFetch } from "@/lib/api";

// v2.5 — Clinical Reasoning Graph & Decision Intelligence ("Project Cortex").

interface AppliedRule {
  id?: string;
  title: string;
  description: string;
  severity: string;
  spd_risk: string;
  recommendation: string[];
  source: "spd_rule_library" | "supervisor_rule_builder";
}

interface ReasoningStep {
  step: string;
  detail: string;
}

interface Confidence {
  vision_confidence: number | null;
  reasoning_confidence: number;
  overall_clinical_confidence: number;
  basis: string;
}

interface FinalRecommendation {
  recommendation: string[];
  severity: string;
  spd_risk: string;
  driven_by_rule: string | null;
}

interface Decision {
  inspection_id: number;
  evidence: {
    instrument_type: string;
    instrument_family: string;
    finding_type: string;
    zone: string;
    high_risk_zone: boolean;
    repeat_finding: boolean;
    repeat_occurrences: number;
  };
  reasoning_path: ReasoningStep[];
  applied_rules: AppliedRule[];
  clinical_rationale: string;
  final_recommendation: FinalRecommendation;
  confidence: Confidence;
}

interface SupervisorOutcome {
  reviewer_name: string;
  reviewer_role: string;
  agreement: string;
  override_action: string;
  final_disposition: string;
  rationale: string;
  created_at: string | null;
}

interface Replay {
  input: {
    instrument_type: string;
    finding_type: string;
    zone: string;
    risk_score: number;
    risk_level: string | null;
    created_at: string | null;
  };
  supervisor_outcome: SupervisorOutcome[];
  note: string;
}

const RISK_CLASS: Record<string, string> = {
  Low: "bg-emerald-100 text-emerald-800 border-emerald-200",
  Moderate: "bg-amber-100 text-amber-800 border-amber-200",
  High: "bg-orange-100 text-orange-800 border-orange-200",
  Critical: "bg-red-100 text-red-800 border-red-200",
};

function ConfidenceBar({ label, value }: { label: string; value: number | null }) {
  const pct = value == null ? null : Math.round(value * 100);
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-500 mb-1">
        <span>{label}</span>
        <span>{pct == null ? "—" : `${pct}%`}</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${pct ?? 0}%` }} />
      </div>
    </div>
  );
}

export default function DecisionReasoningPage() {
  const { id } = useParams();
  const [decision, setDecision] = useState<Decision | null>(null);
  const [replay, setReplay] = useState<Replay | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      apiFetch<Decision>(`/api/inspections/${id}/decision`),
      apiFetch<Replay>(`/api/inspections/${id}/decision-replay`),
    ])
      .then(([d, r]) => { setDecision(d); setReplay(r); })
      .catch(() => setError("Failed to load the explainable decision for this inspection."));
  }, [id]);

  if (error) return <p className="max-w-4xl mx-auto px-4 py-6 text-sm text-red-600">{error}</p>;
  if (!decision) return <p className="max-w-4xl mx-auto px-4 py-6 text-sm text-slate-400">Loading…</p>;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Explainable Decision — Inspection #{decision.inspection_id}</h1>
        <p className="text-sm text-slate-500 mt-1">
          Evidence → reasoning path → applied rules → clinical rationale → final recommendation.
        </p>
      </div>

      {/* Final recommendation banner */}
      <div className={`rounded-lg border px-4 py-3 ${RISK_CLASS[decision.final_recommendation.spd_risk] ?? RISK_CLASS.Moderate}`}>
        <p className="text-xs font-medium uppercase tracking-wide mb-1">Final Recommendation — {decision.final_recommendation.spd_risk} SPD Risk</p>
        <ul className="list-disc list-inside text-sm space-y-0.5">
          {decision.final_recommendation.recommendation.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
        {decision.final_recommendation.driven_by_rule && (
          <p className="text-xs mt-2 opacity-80">Driven by rule: {decision.final_recommendation.driven_by_rule}</p>
        )}
      </div>

      {/* Confidence — reported separately, never collapsed into one number */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Recommendation Confidence</p>
        <ConfidenceBar label="Vision Confidence" value={decision.confidence.vision_confidence} />
        <ConfidenceBar label="Reasoning Confidence" value={decision.confidence.reasoning_confidence} />
        <ConfidenceBar label="Overall Clinical Confidence" value={decision.confidence.overall_clinical_confidence} />
        <p className="text-xs text-slate-400 pt-1">{decision.confidence.basis}</p>
      </div>

      {/* Reasoning path */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Reasoning Path</p>
        <div className="space-y-2">
          {decision.reasoning_path.map((step, i) => (
            <div key={i} className="flex items-start gap-2 text-sm">
              <span className="shrink-0 rounded-full bg-slate-100 text-slate-600 text-xs font-medium px-2 py-0.5">{step.step}</span>
              <span className="text-slate-600">{step.detail}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Applied rules */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Applied Rules</p>
        {decision.applied_rules.length === 0 ? (
          <p className="text-sm text-slate-400">No SPD or supervisor-authored rule matched this evidence bundle.</p>
        ) : (
          <div className="space-y-2">
            {decision.applied_rules.map((rule, i) => (
              <div key={i} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-slate-700">{rule.title}</p>
                  <span className={`text-xs font-medium rounded-full border px-2 py-0.5 ${RISK_CLASS[rule.spd_risk] ?? RISK_CLASS.Moderate}`}>{rule.spd_risk}</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">{rule.description}</p>
                <p className="text-xs text-slate-400 mt-1">Source: {rule.source === "spd_rule_library" ? "SPD Rule Library" : "Supervisor Rule Builder"}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Clinical rationale */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Clinical Rationale</p>
        <p className="text-sm text-slate-600">{decision.clinical_rationale}</p>
      </div>

      {/* Decision Replay — supervisor outcome */}
      {replay && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Decision Replay — Supervisor Outcome</p>
          {replay.supervisor_outcome.length === 0 ? (
            <p className="text-sm text-slate-400">No supervisor review recorded yet for this inspection.</p>
          ) : (
            <div className="space-y-2">
              {replay.supervisor_outcome.map((o, i) => (
                <div key={i} className="text-sm text-slate-600 rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <p><span className="font-medium">{o.reviewer_name || "Supervisor"}</span> ({o.reviewer_role}) — {o.agreement}{o.override_action ? ` — overrode: ${o.override_action}` : ""}</p>
                  {o.rationale && <p className="text-xs text-slate-500 mt-1">{o.rationale}</p>}
                </div>
              ))}
            </div>
          )}
          <p className="text-xs text-slate-400 mt-3 italic">{replay.note}</p>
        </div>
      )}

      <p className="text-xs text-slate-400 text-center pb-4">
        This recommendation emerges from structured clinical reasoning — never a claim of causation.
        Human review required before clinical action.{" "}
        <Link to="/knowledge-graph" className="text-blue-600 hover:underline">View the Clinical Reasoning Graph →</Link>
      </p>
    </div>
  );
}
