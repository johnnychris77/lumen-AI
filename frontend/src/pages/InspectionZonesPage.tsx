import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

interface ZoneInfoEntry {
  risk: string;
  reason: string;
  manual_check: string;
}

interface ZoneTaxonomyResponse {
  zone_taxonomy: Record<string, string[]>;
  high_retention_zones: string[];
  zone_info: Record<string, ZoneInfoEntry>;
}

const RISK_STYLE: Record<string, string> = {
  low: "bg-slate-100 text-slate-600",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

export default function InspectionZonesPage() {
  const { headers } = useAuth();
  const [data, setData] = useState<ZoneTaxonomyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/instrument-zones`, { headers: headers() })
      .then((r) => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); })
      .then(setData)
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="p-6 space-y-8 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Inspection Zones</h1>
        <p className="text-sm text-slate-500 mt-1">
          The zone taxonomy LumenAI reasons over: instrument-zone categories, which zones are high-retention
          (residual soil is hard to remove), and the recommended manual check per zone.
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {!data && !error && <p className="text-sm text-slate-400">Loading…</p>}

      {data && (
        <>
          <section>
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Zone categories</h2>
            <div className="grid md:grid-cols-2 gap-4">
              {Object.entries(data.zone_taxonomy).map(([category, zones]) => (
                <div key={category} className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="font-semibold text-slate-900 capitalize">{category.replace(/_/g, " ")}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {zones.map((z) => (
                      <span key={z} className="inline-block text-xs bg-slate-100 text-slate-700 rounded px-2 py-0.5">{z}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-900 mb-3">
              High-retention zones <span className="text-sm font-normal text-slate-500">({data.high_retention_zones.length})</span>
            </h2>
            <p className="text-sm text-slate-500 mb-3">
              Zones where residual soil commonly persists after manual cleaning — escalate contamination findings here.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {data.high_retention_zones.map((z) => (
                <span key={z} className="inline-block text-xs bg-red-50 text-red-700 rounded px-2 py-1">{z}</span>
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Per-zone reference</h2>
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-400 border-b border-slate-100">
                    <th className="py-2 px-3 font-medium">Zone</th>
                    <th className="py-2 px-3 font-medium">Risk</th>
                    <th className="py-2 px-3 font-medium">Reason</th>
                    <th className="py-2 px-3 font-medium">Recommended manual check</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.zone_info).map(([zone, info]) => (
                    <tr key={zone} className="border-t border-slate-100 align-top">
                      <td className="py-2 px-3 font-medium capitalize text-slate-800">{zone}</td>
                      <td className="py-2 px-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${RISK_STYLE[info.risk] ?? "bg-slate-100"}`}>{info.risk}</span>
                      </td>
                      <td className="py-2 px-3 text-slate-600">{info.reason}</td>
                      <td className="py-2 px-3 text-slate-600">{info.manual_check}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
        ⚠ Zone assignment is deterministic pilot logic from instrument type/tagged views — not pixel-level
        computer-vision localization. See the <a href="/anatomy-library" className="underline">Anatomy Library</a> for
        which zones apply to a given instrument family.
      </p>
    </div>
  );
}
