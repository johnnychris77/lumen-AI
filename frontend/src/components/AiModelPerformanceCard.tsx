import { useCallback, useEffect, useState } from "react";
import { useAuth, API_BASE } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

/**
 * AI model-performance monitoring card for the Executive Dashboard.
 * Shows real supervisor-agreement metrics; false +/- are surfaced as "n/a"
 * because they require adjudicated ground truth (never fabricated).
 * Silently hides for non-supervisor roles (endpoint is admin/spd_manager only).
 */
type Summary = {
  model_version?: string;
  dataset_version?: string;
  total_ai_predictions: number;
  supervisor_reviews: number;
  supervisor_agreement_rate: number | null;
  override_rate: number | null;
  false_positive_count: number | null;
  false_negative_count: number | null;
  disagreement_count: number;
  average_confidence: number | null;
  cases_requiring_review: number;
};

function pct(v: number | null): string {
  return v == null ? "—" : `${Math.round(v * 100)}%`;
}

export default function AiModelPerformanceCard() {
  const { headers, role } = useAuth();
  const [data, setData] = useState<Summary | null>(null);
  const [hidden, setHidden] = useState(false);
  const canView = role === "admin" || role === "spd_manager";

  const load = useCallback(async () => {
    try {
      const res = await apiFetch(`/api/model-performance/ai-summary`, { raw: true, headers: headers(), signOutOn401: false });
      if (res.status === 403) { setHidden(true); return; }
      if (!res.ok) return;
      setData(await res.json());
    } catch {
      /* non-fatal on a dashboard */
    }
  }, [headers]);

  useEffect(() => { if (canView) load(); }, [canView, load]);

  if (!canView || hidden) return null;

  const cells: { label: string; value: string }[] = [
    { label: "AI Predictions", value: data ? String(data.total_ai_predictions) : "—" },
    { label: "Supervisor Reviews", value: data ? String(data.supervisor_reviews) : "—" },
    { label: "Agreement Rate", value: pct(data?.supervisor_agreement_rate ?? null) },
    { label: "Override Rate", value: pct(data?.override_rate ?? null) },
    { label: "Avg Confidence", value: pct(data?.average_confidence ?? null) },
    { label: "Cases Needing Review", value: data ? String(data.cases_requiring_review) : "—" },
    { label: "Disagreements", value: data ? String(data.disagreement_count) : "—" },
    { label: "False +/− (adjudicated)", value: "n/a" },
  ];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-800">AI Model Performance</h3>
        <span className="text-xs text-slate-400">
          {data?.model_version ? `${data.model_version} · ${data.dataset_version}` : "supervisor-verified"}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {cells.map((c) => (
          <div key={c.label} className="rounded-lg bg-slate-50 px-3 py-2">
            <div className="text-lg font-bold text-slate-900">{c.value}</div>
            <div className="text-xs text-slate-500">{c.label}</div>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-400">
        Agreement/override computed from real supervisor reviews. False positive/negative
        counts require adjudicated ground truth and are not fabricated.
      </p>
    </div>
  );
}
