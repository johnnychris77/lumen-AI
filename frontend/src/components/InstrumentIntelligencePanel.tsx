/**
 * Phase 15 — Instrument Intelligence: coverage score, missing-image guidance,
 * and a text/card instrument risk map. Reads the anatomy-aware fields the
 * analysis now returns. No fabricated visual overlays.
 */
type Coverage = {
  assessed?: boolean;
  overall_coverage: number | null;
  required_zones: string[];
  inspected: string[];
  missing: string[];
  quality: string;
  message: string | null;
};
type RiskRow = {
  zone: string; zone_category: string; zone_risk: string; retention_risk: string;
  required: boolean; inspected: boolean; findings: string[]; recommended_manual_check: string;
};
export type InstrumentIntel = {
  instrument_anatomy?: { family: string; category: string; high_risk_zones: string[]; recommended_image_angles: string[]; min_images: number };
  inspection_coverage?: Coverage;
  missing_image_guidance?: string[];
  risk_map?: RiskRow[];
};

const QUALITY_STYLE: Record<string, string> = {
  complete: "bg-emerald-100 text-emerald-800",
  acceptable: "bg-amber-100 text-amber-800",
  incomplete: "bg-orange-100 text-orange-800",
  insufficient: "bg-red-100 text-red-800",
  not_assessed: "bg-slate-100 text-slate-500",
};
const ZONE_RISK_STYLE: Record<string, string> = {
  low: "text-slate-500", medium: "text-amber-600", high: "text-orange-600", critical: "text-red-600 font-semibold",
};

export default function InstrumentIntelligencePanel({ intel }: { intel: InstrumentIntel }) {
  const cov = intel.inspection_coverage;
  const rmap = intel.risk_map ?? [];
  const guidance = intel.missing_image_guidance ?? [];
  if (!cov && rmap.length === 0) return null;

  return (
    <div className="space-y-4">
      {/* Inspection Coverage */}
      {cov && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Inspection Coverage</p>
            <span className={`rounded-full px-2 py-0.5 text-xs font-bold capitalize ${QUALITY_STYLE[cov.quality] ?? "bg-slate-100"}`}>{cov.quality}</span>
          </div>
          {cov.assessed === false || cov.overall_coverage == null ? (
            <p className="text-sm text-slate-500">{cov.message ?? "Coverage not assessed — tag inspected zones to enable."}</p>
          ) : (
            <div className="flex items-center gap-3">
              <div className="text-2xl font-bold text-slate-900">{cov.overall_coverage}%</div>
              <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                <div className={`h-full ${cov.overall_coverage >= 80 ? "bg-emerald-500" : cov.overall_coverage >= 50 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${cov.overall_coverage}%` }} />
              </div>
            </div>
          )}
          {cov.assessed !== false && (
            <>
              <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-xs text-slate-500 mb-0.5">Inspected</div>
                  <div className="flex flex-wrap gap-1">
                    {cov.inspected.length ? cov.inspected.map((z) => <span key={z} className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700 capitalize">{z}</span>) : <span className="text-xs text-slate-400">none tagged</span>}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-0.5">Missing (required)</div>
                  <div className="flex flex-wrap gap-1">
                    {cov.missing.length ? cov.missing.map((z) => <span key={z} className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-700 capitalize">{z}</span>) : <span className="text-xs text-emerald-600">all required zones covered</span>}
                  </div>
                </div>
              </div>
              {cov.message && <p className="mt-2 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">{cov.message}</p>}
            </>
          )}
        </div>
      )}

      {/* Missing image guidance */}
      {guidance.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-1.5">Still needed before final decision</p>
          <ul className="space-y-0.5 text-sm text-slate-700">
            {guidance.map((g, i) => <li key={i} className="flex items-start gap-1.5"><span className="text-amber-500">•</span><span>{g}</span></li>)}
          </ul>
        </div>
      )}

      {/* Instrument risk map */}
      {rmap.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
            Instrument Risk Map {intel.instrument_anatomy && <span className="normal-case text-slate-400">· {intel.instrument_anatomy.category}</span>}
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-slate-400">
                  <th className="py-1 pr-3 font-medium">Zone</th>
                  <th className="py-1 px-2 font-medium">Zone Risk</th>
                  <th className="py-1 px-2 font-medium">Required</th>
                  <th className="py-1 px-2 font-medium">Inspected</th>
                  <th className="py-1 px-2 font-medium">Findings</th>
                  <th className="py-1 px-2 font-medium">Manual check</th>
                </tr>
              </thead>
              <tbody>
                {rmap.map((r) => (
                  <tr key={r.zone} className="border-t border-slate-100 align-top">
                    <td className="py-1 pr-3 font-medium capitalize text-slate-700">{r.zone}</td>
                    <td className={`py-1 px-2 capitalize ${ZONE_RISK_STYLE[r.zone_risk] ?? ""}`}>{r.zone_risk}</td>
                    <td className="py-1 px-2">{r.required ? "Yes" : "—"}</td>
                    <td className="py-1 px-2">{r.inspected ? <span className="text-emerald-600">Yes</span> : <span className="text-slate-400">No</span>}</td>
                    <td className="py-1 px-2 capitalize">{r.findings.length ? r.findings.join(", ") : "—"}</td>
                    <td className="py-1 px-2 text-slate-500">{r.recommended_manual_check}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-slate-400">Text/card risk map. Visual anatomy maps, clickable zones, and heatmaps are a future computer-vision release (not fabricated).</p>
        </div>
      )}
    </div>
  );
}
