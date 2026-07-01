import { Fragment, useCallback, useEffect, useState } from "react";
import { useAuth, API_BASE } from "@/lib/auth";
import SupervisorNotes from "@/components/SupervisorNotes";

type InspectionRecord = {
  id: number;
  created_at: string | null;
  instrument_type: string;
  facility_name: string | null;
  site_name: string;
  detected_issue: string;
  risk_score: number;
  inspection_score: number | null;
  score_status: string;
  baseline_status: string;
  baseline_source: string | null;
  supervisor_review_required: boolean;
  has_image: boolean;
  status: string;
  // SPD risk-weighted verdict persisted with the inspection
  risk_level: string | null;
  recommended_action: string | null;
  overall_cleaning_assessment: string | null;
};

const RISK_LEVEL_STYLE: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-800",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

const CLEANING_STYLE: Record<string, string> = {
  Clean: "text-emerald-700",
  "Residual contamination suspected": "text-amber-700",
  "Cleaning failure": "text-red-700 font-semibold",
  "Supervisor review required": "text-orange-700",
};

function scoreColor(score: number | null): string {
  if (score == null) return "bg-slate-100 text-slate-500";
  if (score >= 85) return "bg-emerald-100 text-emerald-800";
  if (score >= 65) return "bg-amber-100 text-amber-800";
  if (score >= 40) return "bg-orange-100 text-orange-800";
  return "bg-red-100 text-red-800";
}

function riskLabel(score: number | null): string {
  if (score == null) return "—";
  if (score >= 85) return "Low";
  if (score >= 65) return "Medium";
  if (score >= 40) return "High";
  return "Critical";
}

export default function InspectionResultsHistory() {
  const { headers, role } = useAuth();
  const [items, setItems] = useState<InspectionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const canReview = role === "admin" || role === "spd_manager";

  async function openPdf(id: number) {
    try {
      const res = await fetch(`${API_BASE}/api/inspections/${id}/clinical-report.pdf`, {
        headers: { Authorization: headers()["Authorization"] },
      });
      if (!res.ok) return;
      const url = URL.createObjectURL(await res.blob());
      window.open(url, "_blank", "noopener,noreferrer");
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch {
      /* ignore — best-effort */
    }
  }

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/history?limit=50`, { headers: headers() });
      if (!res.ok) {
        setError(`Failed to load inspection results (${res.status}).`);
        setItems([]);
        return;
      }
      const data = await res.json();
      setItems(Array.isArray(data.items) ? data.items : []);
    } catch {
      setError("Unable to reach the server.");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Inspection Results</h3>
          <p className="text-xs text-slate-500">Every inspection run through the New Inspection workflow, with its AI analysis result.</p>
        </div>
        <button
          onClick={load}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          Refresh
        </button>
      </div>

      {loading && (
        <div className="px-5 py-10 text-center text-sm text-slate-400">Loading inspection results…</div>
      )}

      {!loading && error && (
        <div className="px-5 py-6 text-center">
          <p className="text-sm text-red-600">{error}</p>
          <button onClick={load} className="mt-2 text-xs text-blue-600 underline">Try again</button>
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="px-5 py-10 text-center text-sm text-slate-400">
          No inspections have been run yet. Submit one from the New Inspection page.
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-5 py-2 font-medium">#</th>
                <th className="px-5 py-2 font-medium">Date</th>
                <th className="px-5 py-2 font-medium">Instrument</th>
                <th className="px-5 py-2 font-medium">Facility</th>
                <th className="px-5 py-2 font-medium">Score</th>
                <th className="px-5 py-2 font-medium">Risk</th>
                <th className="px-5 py-2 font-medium">Cleaning</th>
                <th className="px-5 py-2 font-medium">Finding</th>
                <th className="px-5 py-2 font-medium">Baseline</th>
                <th className="px-5 py-2 font-medium">Status</th>
                <th className="px-5 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <Fragment key={r.id}>
                <tr className="border-b border-slate-50 hover:bg-slate-50/60">
                  <td className="px-5 py-2.5 text-slate-500">{r.id}</td>
                  <td className="px-5 py-2.5 text-slate-600 whitespace-nowrap">
                    {r.created_at ? new Date(r.created_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-5 py-2.5 capitalize text-slate-800">{r.instrument_type.replace(/_/g, " ")}</td>
                  <td className="px-5 py-2.5 text-slate-600">{r.facility_name || r.site_name || "—"}</td>
                  <td className="px-5 py-2.5">
                    {r.supervisor_review_required ? (
                      <span className="text-xs text-amber-600 italic">pending review</span>
                    ) : (
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-bold ${scoreColor(r.inspection_score)}`}>
                        {r.inspection_score ?? "—"}
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-2.5 text-slate-700">
                    {r.risk_level ? (
                      <span
                        title={r.recommended_action ?? undefined}
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-bold capitalize ${RISK_LEVEL_STYLE[r.risk_level] ?? "bg-slate-100 text-slate-600"}`}
                      >
                        {r.risk_level}
                      </span>
                    ) : r.supervisor_review_required ? (
                      "—"
                    ) : (
                      riskLabel(r.inspection_score)
                    )}
                  </td>
                  <td className={`px-5 py-2.5 text-xs ${r.overall_cleaning_assessment ? (CLEANING_STYLE[r.overall_cleaning_assessment] ?? "text-slate-600") : "text-slate-400"}`}>
                    {r.overall_cleaning_assessment ?? "—"}
                  </td>
                  <td className="px-5 py-2.5 capitalize text-slate-600">
                    {r.detected_issue === "unknown" || r.detected_issue === ""
                      ? "AI analysis"
                      : r.detected_issue.replace(/_/g, " ")}
                  </td>
                  <td className="px-5 py-2.5 capitalize text-slate-600">
                    {r.baseline_source ? (
                      <>
                        {r.baseline_source.replace(/_/g, " ")}
                        {r.baseline_source !== "manufacturer" && (
                          <span className="ml-1 text-xs text-amber-600 normal-case">(fallback)</span>
                        )}
                      </>
                    ) : (
                      r.baseline_status.replace(/_/g, " ")
                    )}
                  </td>
                  <td className="px-5 py-2.5">
                    {r.supervisor_review_required ? (
                      <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                        Supervisor review
                      </span>
                    ) : (
                      <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 capitalize">
                        {r.score_status.replace(/_/g, " ")}
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-2.5 whitespace-nowrap">
                    <button onClick={() => openPdf(r.id)} className="text-xs text-blue-600 underline">PDF</button>
                    {canReview && (
                      <button
                        onClick={() => setExpanded(expanded === r.id ? null : r.id)}
                        className="ml-3 text-xs text-blue-600 underline"
                      >
                        {expanded === r.id ? "Close" : "Review"}
                      </button>
                    )}
                  </td>
                </tr>
                {expanded === r.id && canReview && (
                  <tr className="bg-slate-50/60">
                    <td colSpan={11} className="px-5 py-3">
                      <SupervisorNotes inspectionId={r.id} onSubmitted={() => setExpanded(null)} />
                    </td>
                  </tr>
                )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
