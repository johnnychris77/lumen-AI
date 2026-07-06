import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

interface RecentInspection {
  inspection_id: number;
  instrument_type: string;
  coverage_score: number | null;
  coverage_status: string;
  missing: string[];
  created_at: string | null;
}

interface CoverageDashboard {
  total_inspections_with_image: number;
  assessed_count: number;
  not_assessed_count: number;
  average_coverage: number | null;
  coverage_status_breakdown: Record<string, number>;
  average_coverage_by_family: Record<string, number>;
  most_commonly_missing_zones: { zone: string; missed_count: number }[];
  recent_inspections: RecentInspection[];
  note: string;
}

const STATUS_STYLE: Record<string, string> = {
  complete: "bg-emerald-100 text-emerald-800",
  acceptable: "bg-amber-100 text-amber-800",
  incomplete: "bg-orange-100 text-orange-800",
  insufficient: "bg-red-100 text-red-800",
  not_assessed: "bg-slate-100 text-slate-500",
};

function StatTile({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
    </div>
  );
}

export default function CoverageDashboardPage() {
  const { headers } = useAuth();
  const [data, setData] = useState<CoverageDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/coverage-dashboard/summary`, { headers: headers() })
      .then((r) => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); })
      .then(setData)
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="p-6 space-y-8 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Inspection Coverage Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1">
          Real aggregate coverage stats computed from stored inspections — how completely required anatomy zones
          are being imaged before AI analysis, across the fleet.
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {!data && !error && <p className="text-sm text-slate-400">Loading…</p>}

      {data && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatTile label="Average Coverage" value={data.average_coverage != null ? `${data.average_coverage}%` : "Not enough data"} />
            <StatTile label="Assessed Inspections" value={data.assessed_count} />
            <StatTile label="Not Assessed" value={data.not_assessed_count} />
            <StatTile label="Total (with image)" value={data.total_inspections_with_image} />
          </div>

          <section>
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Coverage status breakdown</h2>
            <div className="flex flex-wrap gap-3">
              {Object.entries(data.coverage_status_breakdown).map(([status, count]) => (
                <span key={status} className={`rounded-full px-3 py-1.5 text-sm font-medium capitalize ${STATUS_STYLE[status] ?? "bg-slate-100"}`}>
                  {status}: {count}
                </span>
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Average coverage by instrument family</h2>
            {Object.keys(data.average_coverage_by_family).length === 0 ? (
              <p className="text-sm text-slate-400">No assessed inspections yet.</p>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
                {Object.entries(data.average_coverage_by_family).map(([family, avg]) => (
                  <div key={family} className="rounded-lg border border-slate-200 bg-white p-3 flex items-center justify-between">
                    <span className="text-sm font-medium capitalize text-slate-800">{family.replace(/_/g, " ")}</span>
                    <span className="text-sm font-bold text-slate-900">{avg}%</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Most commonly missing zones</h2>
            {data.most_commonly_missing_zones.length === 0 ? (
              <p className="text-sm text-slate-400">No missing-zone data yet.</p>
            ) : (
              <ul className="space-y-1">
                {data.most_commonly_missing_zones.map((z) => (
                  <li key={z.zone} className="flex items-center justify-between text-sm rounded border border-slate-100 bg-white px-3 py-1.5">
                    <span className="capitalize text-slate-700">{z.zone}</span>
                    <span className="text-slate-500">{z.missed_count} inspection{z.missed_count === 1 ? "" : "s"}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Recent inspections</h2>
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-400 border-b border-slate-100">
                    <th className="py-2 px-3 font-medium">ID</th>
                    <th className="py-2 px-3 font-medium">Instrument type</th>
                    <th className="py-2 px-3 font-medium">Coverage</th>
                    <th className="py-2 px-3 font-medium">Status</th>
                    <th className="py-2 px-3 font-medium">Missing</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_inspections.map((r) => (
                    <tr key={r.inspection_id} className="border-t border-slate-100 align-top">
                      <td className="py-2 px-3 text-slate-500">#{r.inspection_id}</td>
                      <td className="py-2 px-3 capitalize text-slate-800">{r.instrument_type}</td>
                      <td className="py-2 px-3">{r.coverage_score != null ? `${r.coverage_score}%` : "—"}</td>
                      <td className="py-2 px-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_STYLE[r.coverage_status] ?? "bg-slate-100"}`}>{r.coverage_status}</span>
                      </td>
                      <td className="py-2 px-3 capitalize text-slate-600">{r.missing.length ? r.missing.join(", ") : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <p className="text-xs text-slate-400">{data.note}</p>
        </>
      )}
    </div>
  );
}
