import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface EvidencePanel {
  instrument_identity: string;
  instrument_type: string;
  inspection_coverage_pct: number | null;
  coverage_quality: string | null;
  detected_issue: string | null;
  severity: string | null;
  baseline_used: string | null;
  supervisor_status: string;
  supervisor_agreement: string | null;
  readiness_score: number | null;
  readiness_status: string;
  recommended_disposition: string;
  clinical_rationale: string;
}

interface RiskStratification {
  risk_tier: string;
  points: number;
  reasons: string[];
}

interface TimelineStep {
  step: string;
  completed: boolean;
  timestamp: string | null;
  value?: string;
}

const ACTIONS = [
  { value: "approve", label: "Approve" },
  { value: "modify", label: "Modify" },
  { value: "escalate", label: "Escalate" },
  { value: "reclean", label: "Request Reclean" },
  { value: "repair", label: "Request Repair" },
  { value: "remove_from_service", label: "Remove From Service" },
  { value: "manufacturer_review", label: "Require Manufacturer Review" },
];

const RISK_STYLE: Record<string, string> = {
  "Low Risk": "bg-emerald-100 text-emerald-800",
  "Moderate Risk": "bg-amber-100 text-amber-800",
  "High Risk": "bg-orange-100 text-orange-800",
  "Critical": "bg-red-100 text-red-800",
};

export default function ReadinessDispositionPanel({ inspectionId }: { inspectionId?: number }) {
  const { role } = useAuth();
  const isLeadership = role === "admin" || role === "spd_manager";
  const [evidence, setEvidence] = useState<EvidencePanel | null>(null);
  const [risk, setRisk] = useState<RiskStratification | null>(null);
  const [timeline, setTimeline] = useState<TimelineStep[] | null>(null);
  const [showTimeline, setShowTimeline] = useState(false);
  const [action, setAction] = useState("approve");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const load = useCallback(() => {
    if (!inspectionId) return;
    apiFetch<EvidencePanel>(`/api/inspections/${inspectionId}/evidence-panel`).then(setEvidence);
    apiFetch<RiskStratification>(`/api/inspections/${inspectionId}/risk-stratification`).then(setRisk);
  }, [inspectionId]);

  useEffect(() => { load(); }, [load]);

  async function loadTimeline() {
    if (!inspectionId) return;
    const data = await apiFetch<{ steps: TimelineStep[] }>(`/api/inspections/${inspectionId}/readiness-timeline`);
    setTimeline(data.steps);
    setShowTimeline(true);
  }

  async function submitAction() {
    if (!inspectionId || !evidence) return;
    setBusy(true);
    try {
      await apiFetch(`/api/inspections/${inspectionId}/disposition-action`, {
        method: "POST",
        body: {
          action,
          ai_recommended_disposition: evidence.recommended_disposition,
          reason,
        },
      });
      setSubmitted(true);
      setReason("");
      load();
    } finally {
      setBusy(false);
    }
  }

  async function downloadReport() {
    if (!inspectionId) return;
    const res = await apiFetch(`/api/inspections/${inspectionId}/readiness-report.pdf`, { raw: true });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank", "noopener,noreferrer");
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  }

  if (!inspectionId || !evidence) return null;

  const reasonRequired = action !== "approve";

  return (
    <div className="rounded-lg border border-teal-200 bg-teal-50/50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">Clinical Service Readiness</p>
        <button onClick={downloadReport} className="text-xs text-teal-700 underline">
          Export Readiness Report (PDF)
        </button>
      </div>

      {/* Disposition Evidence Panel */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
        <div><div className="text-xs text-slate-500">Coverage</div><div className="font-medium">{evidence.inspection_coverage_pct ?? "—"}%</div></div>
        <div><div className="text-xs text-slate-500">Readiness Score</div><div className="font-medium">{evidence.readiness_score ?? "—"}</div></div>
        <div><div className="text-xs text-slate-500">Readiness Status</div><div className="font-medium">{evidence.readiness_status}</div></div>
        <div><div className="text-xs text-slate-500">Supervisor Status</div><div className="font-medium capitalize">{evidence.supervisor_status}</div></div>
      </div>
      <div className="text-sm">
        <span className="text-slate-500">Findings:</span> {evidence.detected_issue || "None"}
        {" · "}<span className="text-slate-500">Severity:</span> {evidence.severity || "—"}
        {" · "}<span className="text-slate-500">Baseline:</span> {evidence.baseline_used || "—"}
      </div>

      <div className="rounded border border-teal-300 bg-white px-3 py-2">
        <p className="text-sm font-semibold text-teal-900">Recommended Disposition: {evidence.recommended_disposition}</p>
        <p className="text-sm text-slate-700">{evidence.clinical_rationale}</p>
      </div>

      {risk && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Risk Stratification:</span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${RISK_STYLE[risk.risk_tier] ?? "bg-slate-100"}`}>
            {risk.risk_tier}
          </span>
        </div>
      )}

      <button onClick={loadTimeline} className="text-xs text-teal-700 underline">
        {showTimeline ? "Hide" : "Show"} Readiness Timeline
      </button>
      {showTimeline && timeline && (
        <ol className="space-y-1 text-sm">
          {timeline.map((s, i) => (
            <li key={i} className="flex items-center gap-2">
              <span className={s.completed ? "text-emerald-600" : "text-slate-300"}>{s.completed ? "✓" : "○"}</span>
              <span className={s.completed ? "text-slate-800" : "text-slate-400"}>{s.step}</span>
              {s.value && <span className="text-xs text-slate-500">({s.value})</span>}
            </li>
          ))}
        </ol>
      )}

      {/* Supervisor Disposition Workspace */}
      {isLeadership && (
        <div className="rounded border border-slate-200 bg-white p-3 space-y-2">
          <p className="text-xs font-semibold text-slate-600">Supervisor Disposition Workspace</p>
          <select
            value={action}
            onChange={(e) => setAction(e.target.value)}
            className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
          >
            {ACTIONS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
          {reasonRequired && (
            <input
              type="text"
              placeholder="Reason (required for this action)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
            />
          )}
          <button
            onClick={submitAction}
            disabled={busy || (reasonRequired && !reason.trim())}
            className="text-xs font-semibold px-3 py-1.5 rounded bg-teal-600 text-white disabled:opacity-50"
          >
            {busy ? "Submitting…" : "Submit"}
          </button>
          {submitted && <p className="text-xs text-emerald-700">Disposition action recorded.</p>}
        </div>
      )}
    </div>
  );
}
