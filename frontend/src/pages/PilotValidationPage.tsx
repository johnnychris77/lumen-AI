import { useCallback, useEffect, useState } from "react";
import { useAuth, API_BASE } from "@/lib/auth";

/**
 * Phase 18 — Pilot Validation & Clinical Performance dashboard.
 * Reads real supervisor-review ground truth: agreement, false positives/negatives,
 * safety false-negative rates, zone + family performance, the safety review queue,
 * and the go/no-go readiness gate. No fabricated numbers — empty until reviews exist.
 */

type SafetyMetrics = Record<string, number | null>;
type ZoneRow = { zone: string; n: number; missed: number; overrides: number; disagreements: number; avg_confidence: number | null; miss_rate: number | null };
type Dashboard = {
  total_inspections_reviewed: number;
  ai_supervisor_agreement_rate: number | null;
  false_positives: number;
  false_negatives: number;
  high_risk_findings_detected: number;
  inconclusive_cases: number;
  override_rate: number | null;
  confidence_calibration: Record<string, { n: number; accuracy: number | null }>;
  safety_metrics: SafetyMetrics;
  zone_performance: {
    most_common_missed_zones: ZoneRow[];
    highest_risk_zones: ZoneRow[];
    lowest_confidence_zones: ZoneRow[];
    highest_override_zones: ZoneRow[];
  };
  instrument_family_performance: Record<string, { n: number; agreement_rate: number | null; accuracy: number | null }>;
};
type GoNoGo = {
  decision: string;
  blocking_issues: string[];
  measured: { total_reviews: number; supervisor_agreement_rate: number | null; worst_safety_false_negative_rate: number | null };
  thresholds: Record<string, number>;
};
type SafetyQueue = { count: number; queue: { review_id: number; inspection_id: number; finding_type: string; zone: string; ground_truth: string; ai_confidence: number | null; reasons: string[] }[] };

const pct = (v: number | null | undefined) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${tone ?? "text-slate-900"}`}>{value}</p>
    </div>
  );
}

export default function PilotValidationPage() {
  const { headers } = useAuth();
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [gng, setGng] = useState<GoNoGo | null>(null);
  const [queue, setQueue] = useState<SafetyQueue | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const h = headers();
      const [d, g, q] = await Promise.all([
        fetch(`${API_BASE}/api/pilot-validation/dashboard`, { headers: h }),
        fetch(`${API_BASE}/api/pilot-validation/go-no-go`, { headers: h }),
        fetch(`${API_BASE}/api/pilot-validation/safety-queue`, { headers: h }),
      ]);
      if (d.ok) setDash(await d.json());
      if (g.ok) setGng(await g.json());
      if (q.ok) setQueue(await q.json());
      if (!d.ok) setError("Unable to load pilot validation metrics.");
    } catch {
      setError("Unable to reach the server.");
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => { load(); }, [load]);

  const SAFETY_LABELS: Record<string, string> = {
    blood_false_negative_rate: "Blood",
    tissue_false_negative_rate: "Tissue",
    organic_residue_false_negative_rate: "Organic residue",
    crack_false_negative_rate: "Crack",
    missing_component_false_negative_rate: "Missing component",
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Pilot Validation & Clinical Performance</h1>
          <p className="text-sm text-slate-500 mt-1">
            How well LumenAI agrees with trained SPD supervisors — especially for high-risk findings and
            high-retention zones. Computed from real supervisor reviews; nothing is fabricated.
          </p>
        </div>
        <button onClick={load} disabled={loading}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50">
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div className="rounded border border-amber-300 bg-amber-50 px-4 py-2 text-xs text-amber-800">
        Decision-support evidence. All outputs require human review. No claim of FDA clearance or regulatory approval.
      </div>

      {error && <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>}

      {dash && dash.total_inspections_reviewed === 0 && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
          No supervisor reviews yet. Metrics populate as supervisors validate AI inspections.
        </div>
      )}

      {/* Go / No-Go */}
      {gng && (
        <div className={`rounded-lg border p-4 ${gng.decision === "GO" ? "border-emerald-300 bg-emerald-50" : "border-orange-300 bg-orange-50"}`}>
          <div className="flex items-center gap-3">
            <span className={`rounded-full px-3 py-1 text-sm font-bold ${gng.decision === "GO" ? "bg-emerald-600 text-white" : "bg-orange-600 text-white"}`}>
              {gng.decision}
            </span>
            <span className="text-sm text-slate-700">Readiness gate (advisory — a human owns the final decision)</span>
          </div>
          {gng.blocking_issues.length > 0 && (
            <ul className="mt-2 space-y-0.5 text-sm text-orange-800">
              {gng.blocking_issues.map((b, i) => <li key={i} className="flex gap-1.5"><span>•</span><span>{b}</span></li>)}
            </ul>
          )}
        </div>
      )}

      {/* Headline stats */}
      {dash && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Stat label="Inspections reviewed" value={dash.total_inspections_reviewed} />
          <Stat label="AI / supervisor agreement" value={pct(dash.ai_supervisor_agreement_rate)} tone="text-blue-700" />
          <Stat label="False negatives" value={dash.false_negatives} tone={dash.false_negatives ? "text-red-600" : "text-emerald-600"} />
          <Stat label="False positives" value={dash.false_positives} tone={dash.false_positives ? "text-amber-600" : "text-emerald-600"} />
          <Stat label="High-risk findings detected" value={dash.high_risk_findings_detected} tone="text-emerald-700" />
          <Stat label="Inconclusive" value={dash.inconclusive_cases} />
          <Stat label="Override rate" value={pct(dash.override_rate)} />
          <Stat label="Worst safety FNR" value={pct(dash.safety_metrics.worst_safety_false_negative_rate)} tone="text-red-600" />
        </div>
      )}

      {/* Safety-critical false-negative rates */}
      {dash && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Critical safety false-negative rates</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(SAFETY_LABELS).map(([key, label]) => (
              <div key={key} className="rounded border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs text-slate-500">{label}</p>
                <p className={`text-lg font-semibold mt-0.5 ${dash.safety_metrics[key] ? "text-red-600" : "text-slate-800"}`}>
                  {pct(dash.safety_metrics[key])}
                </p>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-400">A missed contamination or structural finding is the primary safety risk; these gate go/no-go.</p>
        </div>
      )}

      {/* Zone performance */}
      {dash && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ZoneList title="Most commonly missed zones" rows={dash.zone_performance.most_common_missed_zones} metric={(r) => `${r.missed} missed`} />
          <ZoneList title="Highest-risk zones (miss rate)" rows={dash.zone_performance.highest_risk_zones} metric={(r) => pct(r.miss_rate)} />
          <ZoneList title="Lowest-confidence zones" rows={dash.zone_performance.lowest_confidence_zones} metric={(r) => pct(r.avg_confidence)} />
          <ZoneList title="Highest-override zones" rows={dash.zone_performance.highest_override_zones} metric={(r) => `${r.overrides} overrides`} />
        </div>
      )}

      {/* Instrument-family performance */}
      {dash && Object.keys(dash.instrument_family_performance).length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Instrument-family performance</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-slate-400 text-xs">
                <th className="py-1 pr-3">Family</th><th className="py-1 px-2">Reviews</th><th className="py-1 px-2">Agreement</th><th className="py-1 px-2">Accuracy</th>
              </tr></thead>
              <tbody>
                {Object.entries(dash.instrument_family_performance).map(([fam, v]) => (
                  <tr key={fam} className="border-t border-slate-100">
                    <td className="py-1 pr-3 capitalize text-slate-700">{fam.replace(/_/g, " ")}</td>
                    <td className="py-1 px-2">{v.n}</td>
                    <td className="py-1 px-2">{pct(v.agreement_rate)}</td>
                    <td className="py-1 px-2">{pct(v.accuracy)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Safety review queue */}
      {queue && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Safety review queue <span className="text-slate-400 font-normal">({queue.count})</span></h2>
          {queue.count === 0 ? (
            <p className="text-sm text-emerald-600">No inspections currently require a safety review.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-slate-400 text-xs">
                  <th className="py-1 pr-3">Inspection</th><th className="py-1 px-2">Finding</th><th className="py-1 px-2">Zone</th><th className="py-1 px-2">Ground truth</th><th className="py-1 px-2">Confidence</th><th className="py-1 px-2">Reasons</th>
                </tr></thead>
                <tbody>
                  {queue.queue.map((q) => (
                    <tr key={q.review_id} className="border-t border-slate-100 align-top">
                      <td className="py-1 pr-3">#{q.inspection_id}</td>
                      <td className="py-1 px-2 capitalize">{q.finding_type || "—"}</td>
                      <td className="py-1 px-2 capitalize">{q.zone}</td>
                      <td className="py-1 px-2"><span className={q.ground_truth === "false_negative" ? "text-red-600 font-medium" : "text-slate-600"}>{q.ground_truth.replace(/_/g, " ")}</span></td>
                      <td className="py-1 px-2">{pct(q.ai_confidence)}</td>
                      <td className="py-1 px-2 text-xs text-slate-500">{q.reasons.map((r) => r.replace(/_/g, " ")).join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ZoneList({ title, rows, metric }: { title: string; rows: ZoneRow[]; metric: (r: ZoneRow) => React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-700 mb-2">{title}</h3>
      {rows.length === 0 ? (
        <p className="text-xs text-slate-400">No data yet.</p>
      ) : (
        <ul className="space-y-1 text-sm">
          {rows.slice(0, 6).map((r) => (
            <li key={r.zone} className="flex justify-between gap-2">
              <span className="capitalize text-slate-700">{r.zone}</span>
              <span className="text-slate-500">{metric(r)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
