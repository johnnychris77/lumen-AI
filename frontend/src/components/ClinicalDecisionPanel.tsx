import { useState } from "react";
import { useAuth, API_BASE } from "@/lib/auth";
import SupervisorNotes from "@/components/SupervisorNotes";

/**
 * Phase 13 — Explainable AI Clinical Decision Support panel.
 * Renders the `clinical_decision` payload as clinician-readable cards:
 * decision summary, score breakdown, cleaning + integrity assessments,
 * reasoning, recommendation, evidence, executive summary, audit, roadmap,
 * and a printable PDF report.
 */
type Finding = {
  type: string; label: string; detected: boolean;
  probability_pct: number; confidence_pct: number;
  severity: string; spd_risk: string; spd_risk_impact: string;
};
type ClinicalDecision = {
  overall_result: string;
  summary: {
    inspection_score: number | null; cleaning_assessment: string | null;
    integrity_assessment: string | null; overall_risk: string | null;
    confidence: string | null; confidence_pct: number; baseline_source: string | null;
  };
  score_breakdown: { baseline_match_points: number | null; items: { label: string; points: number }[]; final_score: number | null; note: string };
  cleaning: { items: Finding[]; overall_status: string | null };
  integrity: { items: Finding[]; overall_status: string | null };
  clinical_reasoning: string[];
  ai_clinical_review: { outcome: string; reasoning: string[]; interpretation: string };
  evidence_strength: { level: string; stars: number; reason: string };
  baseline_difference: { baseline_match_pct: number | null; differences: string[]; category: string; localization_note: string };
  recommendation: { result: string; action?: string; action_text?: string };
  evidence: { baseline_comparison_label?: string; baseline_source?: string | null; baseline_match_pct: number | null; highest_risk_drivers: string[]; confidence?: string | null; image_evidence_note: string };
  executive_summary: string[];
  audit: Record<string, unknown>;
  roadmap: string[];
  // Phase 14 — Clinical Mentor
  clinical_interpretation?: string[];
  why_this_matters?: { finding: string; why_it_matters: string }[];
  next_actions?: string[];
  standards_guidance?: string;
  learning_mode?: {
    finding: string; detected: boolean; definition: string; typical_causes: string;
    clinical_significance: string; spd_response: string; supervisor_tips: string;
    example_images_note: string;
  }[];
  contamination_risk?: string;
  integrity_risk?: string;
  ai_mentor?: {
    what_was_detected: string[]; why_it_matters: string; how_confident: string;
    standard_practice: string; what_should_happen_next: string[];
  };
};

const RISK_BADGE: Record<string, string> = {
  Low: "bg-emerald-100 text-emerald-800",
  Medium: "bg-amber-100 text-amber-800",
  High: "bg-orange-100 text-orange-800",
  Critical: "bg-red-100 text-red-800",
};

const RESULT_STYLE: Record<string, string> = {
  PASS: "bg-emerald-600",
  MONITOR: "bg-amber-500",
  "SUPERVISOR REVIEW": "bg-orange-600",
  REPROCESS: "bg-red-500",
  "REMOVE FROM SERVICE": "bg-red-600",
};
const IMPACT_STYLE: Record<string, string> = {
  Clear: "bg-emerald-100 text-emerald-800",
  Monitor: "bg-amber-100 text-amber-800",
  Review: "bg-orange-100 text-orange-800",
  Reprocess: "bg-red-100 text-red-800",
};

function FindingsTable({ items }: { items: Finding[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-slate-400">
            <th className="py-1 pr-3 font-medium">Finding</th>
            <th className="py-1 px-2 font-medium">Detected</th>
            <th className="py-1 px-2 font-medium">Prob</th>
            <th className="py-1 px-2 font-medium">Severity</th>
            <th className="py-1 px-2 font-medium">Confidence</th>
            <th className="py-1 px-2 font-medium">SPD Risk</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.type} className="border-t border-slate-100">
              <td className="py-1 pr-3 font-medium text-slate-700 capitalize">{it.label}</td>
              <td className="py-1 px-2">{it.detected ? "Yes" : "No"}</td>
              <td className="py-1 px-2">{it.probability_pct}%</td>
              <td className="py-1 px-2 capitalize">{it.severity}</td>
              <td className="py-1 px-2">{it.confidence_pct}%</td>
              <td className="py-1 px-2">
                <span className={`rounded-full px-2 py-0.5 font-medium ${IMPACT_STYLE[it.spd_risk_impact] ?? "bg-slate-100 text-slate-600"}`}>
                  {it.spd_risk_impact}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{title}</p>
      {children}
    </div>
  );
}

function Stars({ n }: { n: number }) {
  return (
    <span className="text-amber-500 text-lg tracking-tight" aria-label={`${n} of 5`}>
      {"★".repeat(n)}<span className="text-slate-300">{"☆".repeat(Math.max(0, 5 - n))}</span>
    </span>
  );
}

export default function ClinicalDecisionPanel({
  cd,
  inspectionId,
}: {
  cd: ClinicalDecision;
  inspectionId?: number;
}) {
  const { headers, role } = useAuth();
  const [pdfBusy, setPdfBusy] = useState(false);
  const [learning, setLearning] = useState(false);
  const result = cd.overall_result;
  const canReview = role === "admin" || role === "spd_manager";

  async function downloadPdf() {
    if (!inspectionId) return;
    setPdfBusy(true);
    try {
      const res = await fetch(`${API_BASE}/api/inspections/${inspectionId}/clinical-report.pdf`, {
        headers: { Authorization: headers()["Authorization"] },
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } finally {
      setPdfBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* 13.1 Clinical Decision Summary */}
      <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
        <div className={`px-5 py-4 text-white ${RESULT_STYLE[result] ?? "bg-slate-600"}`}>
          <div className="text-xs uppercase tracking-wide opacity-80">Clinical Decision</div>
          <div className="text-2xl font-extrabold tracking-wide">{result}</div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 p-4 text-sm">
          <div><div className="text-xs text-slate-500">Score</div><div className="text-xl font-bold text-slate-900">{cd.summary.inspection_score ?? "—"}</div></div>
          <div><div className="text-xs text-slate-500">Cleaning</div><div className="font-medium text-slate-800">{cd.summary.cleaning_assessment ?? "—"}</div></div>
          <div><div className="text-xs text-slate-500">Integrity</div><div className="font-medium text-slate-800">{cd.summary.integrity_assessment ?? "—"}</div></div>
          <div><div className="text-xs text-slate-500">Risk</div><div className="font-medium text-slate-800 capitalize">{cd.summary.overall_risk ?? "—"}</div></div>
          <div><div className="text-xs text-slate-500">Confidence</div><div className="font-medium text-slate-800">{cd.summary.confidence ?? "—"} ({cd.summary.confidence_pct}%)</div></div>
          <div><div className="text-xs text-slate-500">Baseline</div><div className="font-medium text-slate-800 capitalize">{cd.summary.baseline_source ?? "—"}</div></div>
        </div>
      </div>

      {/* AI Clinical Review — outcome + interpretation + evidence strength */}
      <Card title="AI Clinical Review">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="text-sm">
            <span className="text-slate-500">Inspection outcome: </span>
            <span className="font-semibold text-slate-900">{cd.ai_clinical_review.outcome}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Evidence Strength</span>
            <Stars n={cd.evidence_strength.stars} />
            <span className="text-sm font-medium text-slate-700">{cd.evidence_strength.level}</span>
          </div>
        </div>
        <p className="mt-2 text-sm text-slate-700">{cd.ai_clinical_review.interpretation}</p>
        <p className="mt-1 text-xs text-slate-400">{cd.evidence_strength.reason}</p>
      </Card>

      {/* Baseline Difference */}
      <Card title="Baseline Difference">
        <p className="text-sm text-slate-700 mb-1">
          Baseline match <span className="font-semibold">{cd.baseline_difference.baseline_match_pct ?? "—"}%</span>
          {" · "}differences are <span className="font-medium capitalize">{cd.baseline_difference.category}</span>-related
        </p>
        <ul className="space-y-0.5 text-sm text-slate-700">
          {cd.baseline_difference.differences.map((d, i) => (
            <li key={i} className="flex items-start gap-1.5">
              <span className={d.toLowerCase().startsWith("no ") ? "text-emerald-500" : "text-amber-500"}>•</span>
              <span>{d}</span>
            </li>
          ))}
        </ul>
        <div className="mt-2 rounded border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-500">
          {cd.baseline_difference.localization_note}
        </div>
      </Card>

      {/* 14.14 AI Mentor — signature synthesis */}
      {cd.ai_mentor && (
        <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 mb-2">AI Mentor</p>
          <div className="space-y-1.5 text-sm text-slate-700">
            <p><span className="font-semibold text-slate-900">What was detected:</span> {cd.ai_mentor.what_was_detected.join(", ")}</p>
            <p><span className="font-semibold text-slate-900">Why it matters:</span> {cd.ai_mentor.why_it_matters}</p>
            <p><span className="font-semibold text-slate-900">How confident:</span> {cd.ai_mentor.how_confident}</p>
            <p><span className="font-semibold text-slate-900">Standard practice:</span> {cd.ai_mentor.standard_practice}</p>
            <p><span className="font-semibold text-slate-900">What should happen next:</span> {cd.ai_mentor.what_should_happen_next.join("; ")}</p>
          </div>
        </div>
      )}

      {/* 14.1 Clinical Interpretation */}
      {cd.clinical_interpretation && cd.clinical_interpretation.length > 0 && (
        <Card title="Clinical Interpretation">
          <ul className="space-y-0.5 text-sm text-slate-700">
            {cd.clinical_interpretation.map((l, i) => <li key={i}>• {l}</li>)}
          </ul>
        </Card>
      )}

      {/* 14.9 Risk Separation */}
      {(cd.contamination_risk || cd.integrity_risk) && (
        <Card title="Risk Assessment (separated)">
          <div className="flex flex-wrap gap-6">
            <div>
              <div className="text-xs text-slate-500">Contamination Risk</div>
              <span className={`mt-1 inline-flex rounded-full px-2.5 py-1 text-sm font-bold ${RISK_BADGE[cd.contamination_risk ?? ""] ?? "bg-slate-100"}`}>{cd.contamination_risk ?? "—"}</span>
            </div>
            <div>
              <div className="text-xs text-slate-500">Instrument Integrity Risk</div>
              <span className={`mt-1 inline-flex rounded-full px-2.5 py-1 text-sm font-bold ${RISK_BADGE[cd.integrity_risk ?? ""] ?? "bg-slate-100"}`}>{cd.integrity_risk ?? "—"}</span>
            </div>
            <div>
              <div className="text-xs text-slate-500">Overall</div>
              <span className="mt-1 inline-flex rounded-full bg-slate-800 px-2.5 py-1 text-sm font-bold text-white">{result}</span>
            </div>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Contamination and structural integrity are scored independently — a clean instrument can still be removed for structural damage.
          </p>
        </Card>
      )}

      {/* 14.2 Why This Matters */}
      {cd.why_this_matters && cd.why_this_matters.length > 0 && (
        <Card title="Why This Matters">
          <div className="space-y-2">
            {cd.why_this_matters.map((w, i) => (
              <div key={i}>
                <p className="text-sm font-semibold capitalize text-slate-800">{w.finding}</p>
                <p className="text-sm text-slate-600">{w.why_it_matters}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 14.4 Standards & Guidance */}
      {cd.standards_guidance && (
        <Card title="Standards & Guidance">
          <p className="text-sm text-slate-700">{cd.standards_guidance}</p>
          <p className="mt-1 text-xs text-slate-400">Summary of accepted sterile-processing practice — not a quotation of copyrighted standards.</p>
        </Card>
      )}

      {/* 14.5 Learning Mode */}
      {cd.learning_mode && cd.learning_mode.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Learning Mode</p>
            <button onClick={() => setLearning((v) => !v)} className="text-xs text-blue-600 underline">
              {learning ? "Hide" : "Show educational detail"}
            </button>
          </div>
          {learning && (
            <div className="space-y-2">
              {cd.learning_mode.map((l, i) => (
                <details key={i} className="rounded border border-slate-200 px-3 py-2">
                  <summary className="cursor-pointer text-sm font-medium capitalize text-slate-800">
                    {l.finding} {l.detected && <span className="ml-1 text-xs text-amber-600">(detected)</span>}
                  </summary>
                  <div className="mt-1.5 space-y-1 text-sm text-slate-600">
                    <p><span className="text-slate-500">Definition:</span> {l.definition}</p>
                    <p><span className="text-slate-500">Typical causes:</span> {l.typical_causes}</p>
                    <p><span className="text-slate-500">Clinical significance:</span> {l.clinical_significance}</p>
                    <p><span className="text-slate-500">SPD response:</span> {l.spd_response}</p>
                    <p><span className="text-slate-500">Supervisor tips:</span> {l.supervisor_tips}</p>
                    <p className="text-xs text-slate-400">{l.example_images_note}</p>
                  </div>
                </details>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 13.9 Executive Summary */}
      {cd.executive_summary.length > 0 && (
        <Card title="Executive Summary">
          <ul className="space-y-0.5 text-sm text-slate-700">
            {cd.executive_summary.map((l, i) => <li key={i}>• {l}</li>)}
          </ul>
        </Card>
      )}

      {/* 13.2 Score Breakdown */}
      <Card title="Score Breakdown">
        <div className="space-y-1 text-sm">
          <div className="flex justify-between"><span className="text-slate-600">Baseline match</span><span className="font-medium text-emerald-700">+{cd.score_breakdown.baseline_match_points ?? "—"}</span></div>
          {cd.score_breakdown.items.map((it) => (
            <div key={it.label} className="flex justify-between">
              <span className="capitalize text-slate-600">{it.label}</span>
              <span className={it.points < 0 ? "font-medium text-red-600" : "text-slate-400"}>{it.points < 0 ? it.points : "0 penalty"}</span>
            </div>
          ))}
          <div className="flex justify-between border-t border-slate-200 pt-1 font-semibold text-slate-900">
            <span>Final Score</span><span>{cd.score_breakdown.final_score ?? "—"}</span>
          </div>
        </div>
        <p className="mt-1.5 text-xs text-slate-400">{cd.score_breakdown.note}</p>
      </Card>

      {/* 13.3 Cleaning Assessment */}
      {cd.cleaning.items.length > 0 && (
        <Card title={`Cleaning Assessment — ${cd.cleaning.overall_status ?? "—"}`}>
          <FindingsTable items={cd.cleaning.items} />
        </Card>
      )}

      {/* 13.4 Instrument Integrity Assessment */}
      {cd.integrity.items.length > 0 && (
        <Card title={`Instrument Integrity — ${cd.integrity.overall_status ?? "—"}`}>
          <FindingsTable items={cd.integrity.items} />
        </Card>
      )}

      {/* 13.5 Clinical Reasoning */}
      <Card title="Clinical Reasoning">
        <ul className="space-y-0.5 text-sm text-slate-700">
          {cd.clinical_reasoning.map((l, i) => (
            <li key={i} className="flex items-start gap-1.5">
              <span className={l.startsWith("No ") ? "text-emerald-500" : "text-amber-500"}>•</span>
              <span>{l}</span>
            </li>
          ))}
        </ul>
      </Card>

      {/* 13.6 Recommendation */}
      <div className={`rounded-lg border px-4 py-3 ${result === "PASS" ? "border-emerald-300 bg-emerald-50" : "border-orange-300 bg-orange-50"}`}>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-1">Recommendation</p>
        <p className="text-sm font-semibold text-slate-900">{cd.recommendation.result}</p>
        <p className="text-sm text-slate-700">{cd.recommendation.action_text ?? cd.recommendation.action}</p>
        {cd.next_actions && cd.next_actions.length > 0 && (
          <ul className="mt-2 space-y-0.5 text-sm text-slate-700">
            {cd.next_actions.map((a, i) => (
              <li key={i} className="flex items-start gap-1.5"><span className="text-slate-400">→</span><span>{a}</span></li>
            ))}
          </ul>
        )}
      </div>

      {/* Supervisor Review Notes — admin/spd_manager only */}
      {canReview && <SupervisorNotes inspectionId={inspectionId} />}

      {/* 13.7 Evidence */}
      <Card title="Evidence Used">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-sm text-slate-700">
          <p><span className="text-slate-500">Baseline:</span> {cd.evidence.baseline_comparison_label ?? cd.evidence.baseline_source ?? "—"}</p>
          <p><span className="text-slate-500">Baseline match:</span> {cd.evidence.baseline_match_pct ?? "—"}%</p>
          <p className="sm:col-span-2"><span className="text-slate-500">Highest risk drivers:</span> {(cd.evidence.highest_risk_drivers || []).join(", ") || "—"}</p>
          <p><span className="text-slate-500">Confidence:</span> {cd.evidence.confidence ?? "—"}</p>
        </div>
        <div className="mt-2 rounded border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-500">
          {cd.evidence.image_evidence_note} (heatmaps / bounding boxes not fabricated)
        </div>
      </Card>

      {/* 13.8 PDF + 13.11 Roadmap */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={downloadPdf}
          disabled={!inspectionId || pdfBusy}
          className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-900 disabled:opacity-50"
        >
          {pdfBusy ? "Generating…" : "Download Clinical Report (PDF)"}
        </button>
      </div>

      <details className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <summary className="cursor-pointer text-sm font-semibold text-slate-700">AI Roadmap (upcoming)</summary>
        <ul className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-x-4 text-sm text-slate-600">
          {cd.roadmap.map((r) => <li key={r}>• {r}</li>)}
        </ul>
      </details>

      <p className="text-xs text-slate-400 italic">
        Explainable pilot decision support — advisory only, not validated for production diagnostic accuracy, no FDA
        clearance claimed. Qualified human review is required.
      </p>
    </div>
  );
}
