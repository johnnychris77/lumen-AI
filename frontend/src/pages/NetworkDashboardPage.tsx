import { useState, useEffect } from "react";
import { Building2, TrendingUp, Activity, AlertTriangle, Package, Users } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface FacilitySnapshot {
  id: string;
  name: string;
  tier: "hospital" | "enterprise";
  healthScore: number;
  healthBand: "green" | "yellow" | "red";
  inspections: number;
  criticalFindings: number;
  baselineCoveragePct: number;
  activeUsers: number;
  daysOnPlatform: number;
  trend: "up" | "flat" | "down";
}

type SortKey = "healthScore" | "inspections" | "baselineCoveragePct" | "criticalFindings" | "activeUsers";

function bandColor(band: FacilitySnapshot["healthBand"]) {
  if (band === "green") return "text-emerald-700 bg-emerald-50 border-emerald-200";
  if (band === "yellow") return "text-amber-700 bg-amber-50 border-amber-200";
  return "text-red-700 bg-red-50 border-red-200";
}

function trendArrow(t: FacilitySnapshot["trend"]) {
  if (t === "up") return <span className="text-emerald-500 font-bold">↑</span>;
  if (t === "down") return <span className="text-red-500 font-bold">↓</span>;
  return <span className="text-slate-400">→</span>;
}

function networkScore(facilities: FacilitySnapshot[]) {
  if (facilities.length === 0) return 0;
  return Math.round(facilities.reduce((s, f) => s + f.healthScore, 0) / facilities.length);
}

export default function NetworkDashboardPage() {
  const [facilities, setFacilities] = useState<FacilitySnapshot[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>("healthScore");
  const [sortAsc, setSortAsc] = useState(false);
  const [loading, setLoading] = useState(true);
  // `/api/enterprise/network-snapshot` does not exist anywhere in the
  // backend today -- this page has no real cross-tenant data source yet.
  // Rather than silently substituting fabricated facility rows (as this
  // page previously did on every load, since the fetch always 404s), show
  // that plainly instead of a normal-looking dashboard.
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const token = localStorage.getItem("token") ?? "";
        const res = await apiFetch("/api/enterprise/network-snapshot", { raw: true,
          headers: { Authorization: `Bearer ${token}` }, signOutOn401: false,
        });
        if (!res.ok) throw new Error("Network snapshot API not available");
        const data = await res.json();
        if (!Array.isArray(data.facilities)) throw new Error("Network snapshot API returned no facility data");
        setFacilities(data.facilities);
      } catch {
        setFacilities([]);
        setUnavailable(true);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const sorted = [...facilities].sort((a, b) => {
    const diff = (a[sortKey] as number) - (b[sortKey] as number);
    return sortAsc ? diff : -diff;
  });

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(a => !a);
    else { setSortKey(key); setSortAsc(false); }
  };

  const netScore = networkScore(facilities);
  const totalInsp = facilities.reduce((s, f) => s + f.inspections, 0);
  const totalFindings = facilities.reduce((s, f) => s + f.criticalFindings, 0);
  const avgBaseline = facilities.length > 0 ? Math.round(facilities.reduce((s, f) => s + f.baselineCoveragePct, 0) / facilities.length) : 0;
  const totalUsers = facilities.reduce((s, f) => s + f.activeUsers, 0);
  const redFacilities = facilities.filter(f => f.healthBand === "red");

  const SortTh = ({ col, label }: { col: SortKey; label: string }) => (
    <th
      className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide cursor-pointer hover:text-slate-800 select-none"
      onClick={() => toggleSort(col)}
    >
      {label} {sortKey === col ? (sortAsc ? "↑" : "↓") : ""}
    </th>
  );

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Building2 className="h-7 w-7 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Network Dashboard</h1>
          <p className="text-sm text-slate-500">Cross-facility health, adoption, and quality — Enterprise view</p>
        </div>
      </div>

      {unavailable ? (
        <div className="rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center">
          <Building2 className="mx-auto h-8 w-8 text-slate-400 mb-3" />
          <p className="text-sm font-semibold text-slate-700">Not Available in Current Model — Network view is not yet available</p>
          <p className="text-xs text-slate-500 mt-2 max-w-md mx-auto">
            This dashboard requires a cross-tenant enterprise network-snapshot API that has not been implemented on the backend yet. No facility data is shown here until that API exists.
          </p>
        </div>
      ) : loading ? (
        <div className="text-center text-slate-400 py-12 text-sm animate-pulse">Loading network data…</div>
      ) : (
      <>
      {/* Network score hero */}
      <div className={`rounded-xl border-2 p-6 flex flex-col md:flex-row items-center gap-8 ${
        netScore >= 70 ? "bg-emerald-50 border-emerald-200" : netScore >= 45 ? "bg-amber-50 border-amber-200" : "bg-red-50 border-red-200"
      }`}>
        <div className="text-center">
          <div className={`text-5xl font-bold ${netScore >= 70 ? "text-emerald-700" : netScore >= 45 ? "text-amber-700" : "text-red-700"}`}>
            {loading ? "—" : netScore}
          </div>
          <div className="text-xs text-slate-500 mt-1">Network Health Score</div>
          <div className={`text-sm font-semibold mt-2 ${netScore >= 70 ? "text-emerald-700" : netScore >= 45 ? "text-amber-700" : "text-red-700"}`}>
            {netScore >= 70 ? "Network Healthy" : netScore >= 45 ? "Mixed Health" : "Intervention Required"}
          </div>
        </div>
        <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Facilities", value: facilities.length, icon: <Building2 className="h-4 w-4 text-indigo-500" /> },
            { label: "Total Inspections", value: totalInsp.toLocaleString(), icon: <Activity className="h-4 w-4 text-blue-500" /> },
            { label: "Critical Findings", value: totalFindings, icon: <AlertTriangle className="h-4 w-4 text-red-500" /> },
            { label: "Network Users", value: totalUsers, icon: <Users className="h-4 w-4 text-violet-500" /> },
          ].map(s => (
            <div key={s.label} className="bg-white/70 rounded-lg p-3 text-center">
              <div className="flex justify-center mb-1">{s.icon}</div>
              <div className="text-xl font-bold text-slate-800">{loading ? "—" : s.value}</div>
              <div className="text-xs text-slate-500">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* At-risk alert */}
      {redFacilities.length > 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 flex gap-3">
          <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-800 text-sm">
              {redFacilities.length} facilit{redFacilities.length > 1 ? "ies" : "y"} require immediate intervention
            </p>
            <p className="text-xs text-red-700 mt-0.5">
              {redFacilities.map(f => f.name).join(", ")} — Health Score Red. Emergency CS call recommended within 48 hours.
            </p>
          </div>
        </div>
      )}

      {/* Network KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Green Facilities", value: facilities.filter(f => f.healthBand === "green").length, color: "text-emerald-700 bg-emerald-50 border-emerald-200" },
          { label: "Yellow Facilities", value: facilities.filter(f => f.healthBand === "yellow").length, color: "text-amber-700 bg-amber-50 border-amber-200" },
          { label: "Red Facilities", value: redFacilities.length, color: redFacilities.length > 0 ? "text-red-700 bg-red-50 border-red-200" : "text-slate-500 bg-slate-50 border-slate-200" },
          { label: "Avg Baseline Coverage", value: `${avgBaseline}%`, color: avgBaseline >= 75 ? "text-emerald-700 bg-emerald-50 border-emerald-200" : "text-amber-700 bg-amber-50 border-amber-200" },
        ].map(s => (
          <div key={s.label} className={`rounded-lg border p-4 text-center ${s.color}`}>
            <div className="text-2xl font-bold">{loading ? "—" : s.value}</div>
            <div className="text-xs font-medium mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Facility table */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-800">Facility Comparison</h2>
          <p className="text-xs text-slate-500 mt-0.5">Click column headers to sort · Health scores are anonymized for cross-facility display</p>
        </div>
        {loading ? (
          <div className="text-center text-slate-400 py-12 text-sm animate-pulse">Loading network data…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-100">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Facility</th>
                  <SortTh col="healthScore" label="Health" />
                  <SortTh col="inspections" label="Inspections" />
                  <SortTh col="criticalFindings" label="Critical" />
                  <SortTh col="baselineCoveragePct" label="Baselines" />
                  <SortTh col="activeUsers" label="Users" />
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Days Live</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {sorted.map(f => (
                  <tr key={f.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800">{f.name}</div>
                      <div className="text-xs text-slate-400 capitalize">{f.tier} tier</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-semibold px-2 py-1 rounded-full border ${bandColor(f.healthBand)}`}>
                        {f.healthScore}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{f.inspections.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <span className={f.criticalFindings > 0 ? "text-red-600 font-semibold" : "text-slate-500"}>
                        {f.criticalFindings}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-100 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full ${f.baselineCoveragePct >= 75 ? "bg-emerald-500" : f.baselineCoveragePct >= 50 ? "bg-amber-500" : "bg-red-400"}`}
                            style={{ width: `${f.baselineCoveragePct}%` }}
                          />
                        </div>
                        <span className="text-slate-600">{f.baselineCoveragePct}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{f.activeUsers}</td>
                    <td className="px-4 py-3 text-slate-500">{f.daysOnPlatform}d</td>
                    <td className="px-4 py-3">{trendArrow(f.trend)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Network benchmarks */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="h-5 w-5 text-indigo-500" />
          <h2 className="font-semibold text-slate-800">Network Benchmarks</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          {[
            { label: "Inspections per facility (avg)", value: facilities.length > 0 ? Math.round(totalInsp / facilities.length) : 0, benchmark: 200, unit: "" },
            { label: "Avg baseline coverage", value: avgBaseline, benchmark: 75, unit: "%" },
            { label: "Avg network health score", value: netScore, benchmark: 70, unit: "" },
          ].map(b => (
            <div key={b.label} className="space-y-1.5">
              <div className="flex justify-between">
                <span className="text-slate-600">{b.label}</span>
                <span className="font-semibold text-slate-800">{b.value}{b.unit}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-slate-100 rounded-full h-2 relative">
                  <div
                    className={`h-2 rounded-full ${b.value >= b.benchmark ? "bg-emerald-500" : b.value >= b.benchmark * 0.6 ? "bg-amber-500" : "bg-red-400"}`}
                    style={{ width: `${Math.min(100, (b.value / (b.benchmark * 1.5)) * 100)}%` }}
                  />
                  <div
                    className="absolute top-0 h-2 w-0.5 bg-slate-400"
                    style={{ left: `${(b.benchmark / (b.benchmark * 1.5)) * 100}%` }}
                    title={`Target: ${b.benchmark}${b.unit}`}
                  />
                </div>
                <span className="text-xs text-slate-400 w-16 text-right">target {b.benchmark}{b.unit}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-xl border border-dashed border-indigo-200 bg-indigo-50/30 p-5">
          <div className="flex items-center gap-2 mb-2">
            <Package className="h-4 w-4 text-indigo-400" />
            <span className="text-sm font-semibold text-indigo-700">Phase 20 Preview — Cross-Facility Benchmarking</span>
          </div>
          <p className="text-xs text-slate-500">
            Anonymized peer benchmarking across the LumenAI network — compare your contamination rates, baseline coverage, and inspection velocity against similar-sized facilities. Requires ≥5 network participants. Facility identities are never disclosed.
          </p>
        </div>
        <div className="rounded-xl border border-dashed border-violet-200 bg-violet-50/30 p-5">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="h-4 w-4 text-violet-400" />
            <span className="text-sm font-semibold text-violet-700">Phase 23 Preview — Network Intelligence</span>
          </div>
          <p className="text-xs text-slate-500">
            Anonymized cross-network quality signals — scope type risk patterns, recall early warning, manufacturer defect trends. k-anonymity ≥10 enforced before any signal is published. Human review required on all correlation outputs.
          </p>
        </div>
      </div>
      </>
      )}

      <p className="text-xs text-slate-400 text-center">
        Network Dashboard shows health data only for facilities within your enterprise tenant. Facility identities are not shared across enterprise accounts. All AI findings require qualified human review. LumenAI makes no claim of FDA clearance or regulatory approval.
      </p>
    </div>
  );
}
