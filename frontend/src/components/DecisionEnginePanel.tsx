/**
 * Lumen Decision Engine & Observation Doctrine — Section 15 frontend panel.
 *
 * Renders the Result Contract (Section 14) as four clearly separated
 * panels: AI Observation, Evidence & Baseline Comparison, Applicable
 * Organization Policy, Recommended Next Action. Deliberately does not fold
 * everything into one generic score — the doctrine requires the technician
 * to see what was observed, why, under which policy, and what to do next
 * as distinct, explainable pieces.
 */
export type DecisionContract = {
  inspection_id?: number;
  observation: {
    category: string | null;
    display_label: string | null;
    confidence: number | null;
    status: string;
  };
  assessment: {
    image_quality: string;
    instrument_family: string;
    anatomy_zone: string;
    anatomy_zone_risk: string;
    baseline_similarity: number | null;
    baseline_deviation: number | null;
    baseline_source: string | null;
    baseline_version: string | null;
    digital_twin_trend: string;
  };
  policy: {
    policy_id: string;
    policy_version: string;
    scope: string;
    minimum_baseline_similarity: number | null;
  };
  recommendation: {
    action: string;
    supervisor_required: boolean;
    reason: string;
    escalation_condition: string;
  };
  limitations: string[];
  human_decision_required: boolean;
  unknown_finding?: { unknown_finding_review_id: number } | null;
  guidance?: {
    what_was_observed: string;
    where: string;
    why_this_matters: string;
    image_quality_feedback: string;
    baseline_comparison: string;
    applicable_policy: string;
    recommended_action: string;
    supervisor_help_required: string;
    evidence_limitations: string;
    learning_tip: string;
  };
};

const ACTION_LABELS: Record<string, string> = {
  continue_workflow: "Continue Workflow",
  focused_technician_reinspect: "Focused Technician Reinspect",
  capture_additional_image: "Capture Additional Image",
  reclean_and_reinspect: "Reclean and Reinspect",
  supervisor_attention_required: "Supervisor Attention Required",
  supervisor_approval_required: "Supervisor Approval Required",
  repair_evaluation: "Repair Evaluation",
  manufacturer_evaluation: "Manufacturer Evaluation",
  hold_from_further_processing: "Hold From Further Processing",
  remove_from_service_consideration: "Remove-From-Service Consideration",
};

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{title}</p>
      {children}
    </div>
  );
}

function pct(v: number | null): string {
  return v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`;
}

export default function DecisionEnginePanel({ decision }: { decision: DecisionContract }) {
  const { observation, assessment, policy, recommendation, limitations } = decision;
  const actionLabel = ACTION_LABELS[recommendation.action] ?? recommendation.action;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-indigo-200 bg-indigo-50/40 px-4 py-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
          LumenAI Observation Doctrine — Explainable Decision Support
        </p>
        <p className="text-xs text-slate-500">
          Probability-based visual observation, not a laboratory or diagnostic conclusion.
        </p>
      </div>

      {/* 1. AI Observation */}
      <Panel title="1. AI Observation">
        <p className="text-lg font-semibold text-slate-900">
          {observation.display_label ?? "Not evaluated by current model"}
        </p>
        <p className="text-sm text-slate-600">
          Confidence: {observation.confidence !== null ? `${Math.round(observation.confidence * 100)}%` : "not scored"}
          {" · "}Status: <span className="capitalize">{observation.status.replace(/_/g, " ")}</span>
        </p>
        {decision.unknown_finding && (
          <p className="mt-2 rounded border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-800">
            This finding is outside the model's validated taxonomy and has been queued for
            supervisor classification (review #{decision.unknown_finding.unknown_finding_review_id}).
          </p>
        )}
      </Panel>

      {/* 2. Evidence and Baseline Comparison */}
      <Panel title="2. Evidence and Baseline Comparison">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
          <div><div className="text-xs text-slate-500">Baseline similarity</div><div className="font-medium text-slate-800">{pct(assessment.baseline_similarity)}</div></div>
          <div><div className="text-xs text-slate-500">Baseline deviation</div><div className="font-medium text-slate-800">{pct(assessment.baseline_deviation)}</div></div>
          <div><div className="text-xs text-slate-500">Baseline source</div><div className="font-medium text-slate-800 capitalize">{assessment.baseline_source ?? "—"}</div></div>
          <div><div className="text-xs text-slate-500">Image quality</div><div className="font-medium text-slate-800 capitalize">{assessment.image_quality.replace(/_/g, " ")}</div></div>
          <div><div className="text-xs text-slate-500">Instrument family</div><div className="font-medium text-slate-800 capitalize">{assessment.instrument_family || "—"}</div></div>
          <div><div className="text-xs text-slate-500">Anatomy zone</div><div className="font-medium text-slate-800 capitalize">{assessment.anatomy_zone || "—"}</div></div>
          <div><div className="text-xs text-slate-500">Zone risk</div><div className="font-medium text-slate-800 capitalize">{assessment.anatomy_zone_risk || "—"}</div></div>
          <div><div className="text-xs text-slate-500">Digital Twin trend</div><div className="font-medium text-slate-800 capitalize">{assessment.digital_twin_trend.replace(/_/g, " ")}</div></div>
        </div>
        {limitations.length > 0 && (
          <ul className="mt-2 space-y-0.5 text-xs text-slate-400">
            {limitations.map((l, i) => <li key={i}>• {l}</li>)}
          </ul>
        )}
      </Panel>

      {/* 3. Applicable Organization Policy */}
      <Panel title="3. Applicable Organization Policy">
        <p className="text-sm text-slate-700">
          <span className="font-medium">{policy.policy_id || "lumenai-default-v1"}</span>
          {" "}(v{policy.policy_version || "1.0"}, {policy.scope || "lumenai_default"} scope)
        </p>
        <p className="text-sm text-slate-600">
          Minimum baseline similarity required: {pct(policy.minimum_baseline_similarity)}
        </p>
      </Panel>

      {/* 4. Recommended Next Action */}
      <div className={`rounded-lg border px-4 py-3 ${recommendation.supervisor_required ? "border-orange-300 bg-orange-50" : "border-emerald-300 bg-emerald-50"}`}>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-1">4. Recommended Next Action</p>
        <p className="text-lg font-semibold text-slate-900">{actionLabel}</p>
        <p className="text-sm text-slate-700 mt-1">{recommendation.reason}</p>
        <p className="mt-2 text-sm font-medium text-slate-800">
          Supervisor involvement: {recommendation.supervisor_required ? "Required" : "Not required for this step"}
        </p>
        <p className="text-xs text-slate-500 mt-1">Escalation: {recommendation.escalation_condition}</p>
      </div>

      <p className="text-xs text-slate-400 italic">
        This is a probability-based visual observation, not a laboratory-confirmed identification.
        Human review is required for every recommendation.
      </p>
    </div>
  );
}
