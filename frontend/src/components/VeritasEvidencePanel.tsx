/**
 * LumenAI AI Specialist — Project Veritas, Section 12: Inspection Evidence
 * Panel.
 *
 * A compact panel intended to be embedded in an inspection results view,
 * showing the resolved baseline, match classification, image quality,
 * coverage, evidence readiness, limitations, and next action -- the exact
 * fields the brief's Section 12 example specifies.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Json = Record<string, unknown>;

const READINESS_LABELS: Record<string, string> = {
  strong_evidence: "Strong",
  moderate_evidence: "Moderate",
  limited_evidence: "Limited",
  insufficient_evidence: "Insufficient",
};

export default function VeritasEvidencePanel({ inspectionId }: { inspectionId: number }) {
  const [assessment, setAssessment] = useState<Json | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api
      .post(`/api/veritas/assess/${inspectionId}`, {})
      .then(setAssessment)
      .catch(() => setAssessment(null))
      .finally(() => setLoading(false));
  }, [inspectionId]);

  if (loading) return <div className="text-xs text-slate-400">Assessing evidence...</div>;
  if (!assessment) return null;

  const readinessLabel = READINESS_LABELS[assessment.readiness_category as string] || (assessment.readiness_category as string);
  const missingZones = (assessment.missing_zones as string[]) || [];
  const limitations = (assessment.limitations as string[]) || [];

  return (
    <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 text-sm text-slate-700">
      <h4 className="mb-2 text-sm font-semibold text-indigo-900">Veritas Evidence</h4>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1">
        <dt className="text-slate-500">Baseline Match</dt>
        <dd className="capitalize">{assessment.match_classification as string}</dd>

        <dt className="text-slate-500">Image Quality</dt>
        <dd className="capitalize">{assessment.image_quality_status as string}</dd>

        <dt className="text-slate-500">Coverage</dt>
        <dd>{assessment.coverage_pct != null ? `${assessment.coverage_pct}%` : (assessment.coverage_status as string)}</dd>

        {missingZones.length > 0 && (
          <>
            <dt className="text-slate-500">Missing Zone(s)</dt>
            <dd>{missingZones.join(", ")}</dd>
          </>
        )}

        <dt className="text-slate-500">Evidence Readiness</dt>
        <dd>{readinessLabel} — {assessment.readiness_score as number}/100</dd>
      </dl>

      {limitations.length > 0 && (
        <p className="mt-2 text-xs text-amber-700">
          <span className="font-semibold">Limitation:</span> {limitations.join(" ")}
        </p>
      )}

      <p className="mt-2 text-xs text-slate-600">
        <span className="font-semibold">Next Action:</span> {assessment.next_action as string}
      </p>
    </div>
  );
}
