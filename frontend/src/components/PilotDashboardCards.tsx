import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth, API_BASE } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

// ─── quick actions ────────────────────────────────────────────────────────────

const quickActions = [
  { label: "New Inspection", icon: "🔬", href: "/inspection/new", color: "blue" },
  { label: "Vendor Intake", icon: "📋", href: "/vendor-intake", color: "green" },
  { label: "Manufacturer Baselines", icon: "📦", href: "/manufacturer-baselines", color: "purple" },
  { label: "Baseline Review Queue", icon: "✅", href: "/baseline-review", color: "orange" },
  { label: "Intake History", icon: "📁", href: "/intake-history", color: "gray" },
];

const colorMap: Record<string, string> = {
  blue: "bg-blue-50 border-blue-200 hover:bg-blue-100 text-blue-800",
  green: "bg-green-50 border-green-200 hover:bg-green-100 text-green-800",
  purple: "bg-purple-50 border-purple-200 hover:bg-purple-100 text-purple-800",
  orange: "bg-orange-50 border-orange-200 hover:bg-orange-100 text-orange-800",
  gray: "bg-gray-50 border-gray-200 hover:bg-gray-100 text-gray-700",
};

// ─── KPI config ───────────────────────────────────────────────────────────────

type KpiConfig = {
  label: string;
  endpoint: string;
  countKey?: string;
};

const KPI_CONFIGS: KpiConfig[] = [
  { label: "Total Inspections", endpoint: "/api/history/summary", countKey: "total_inspections" },
  { label: "Baselines Submitted", endpoint: "/api/network/baselines", countKey: "baselines" },
  { label: "Pending Reviews", endpoint: "/api/network/baselines/stats", countKey: "pending" },
  { label: "Approved Baselines", endpoint: "/api/network/baselines/stats", countKey: "approved" },
  { label: "Blood Findings", endpoint: "/api/history/summary", countKey: "blood_findings" },
  { label: "Bone Findings", endpoint: "/api/history/summary", countKey: "bone_findings" },
  { label: "Tissue Findings", endpoint: "/api/history/summary", countKey: "tissue_findings" },
  { label: "Other Findings", endpoint: "/api/history/summary", countKey: "other_findings" },
];

type KpiValue = number | null; // null = loading, -1 = error

function extractCount(data: unknown, countKey?: string): number {
  if (typeof data === "number") return data;
  if (data && typeof data === "object") {
    const d = data as Record<string, unknown>;
    // Use explicit countKey first
    if (countKey && typeof d[countKey] === "number") return d[countKey] as number;
    // Array fields (baselines array from /api/network/baselines)
    if (countKey && Array.isArray(d[countKey])) return (d[countKey] as unknown[]).length;
    // Standard keys
    for (const key of ["total", "count", "total_count", "total_inspections", "total_baselines"]) {
      if (typeof d[key] === "number") return d[key] as number;
    }
    if (Array.isArray(d.items)) return (d as { total?: number }).total ?? (d.items as unknown[]).length;
    if (Array.isArray(data)) return (data as unknown[]).length;
  }
  return 0;
}

// /api/network/baselines and /api/network/baselines/stats both label their
// own fallback content with a data_source field ("mock"/"insufficient_data")
// when no real BaselineLibraryEntry rows exist yet -- surface that instead
// of letting a demo count render identically to a real one.
function extractDataSource(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;
  const d = data as Record<string, unknown>;
  const stats = d.stats && typeof d.stats === "object" ? (d.stats as Record<string, unknown>) : null;
  const source = (d.data_source ?? stats?.data_source) as unknown;
  return typeof source === "string" && source !== "real" ? source : null;
}

function KpiCard({ label, value, demoDataSource }: { label: string; value: KpiValue; demoDataSource?: string | null }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 flex flex-col gap-1 shadow-sm">
      <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</span>
      {value === null ? (
        <div className="h-7 w-12 rounded bg-gray-100 animate-pulse mt-1" />
      ) : value === -1 ? (
        <span className="text-2xl font-bold text-gray-400">—</span>
      ) : (
        <span className="text-2xl font-bold text-gray-900">{value}</span>
      )}
      {demoDataSource && (
        <span className="text-[10px] font-medium uppercase tracking-wide text-amber-600">Demonstration Data</span>
      )}
    </div>
  );
}

// ─── component ────────────────────────────────────────────────────────────────

export function PilotDashboardCards() {
  const { headers } = useAuth();
  const [kpis, setKpis] = useState<KpiValue[]>(KPI_CONFIGS.map(() => null));
  const [demoSources, setDemoSources] = useState<(string | null)[]>(KPI_CONFIGS.map(() => null));

  useEffect(() => {
    let cancelled = false;
    const hdrs = headers();

    KPI_CONFIGS.forEach(async (cfg, i) => {
      try {
        const res = await apiFetch(`${cfg.endpoint}`, { raw: true, headers: hdrs, signOutOn401: false });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const count = extractCount(data, cfg.countKey);
        const demoSource = extractDataSource(data);
        if (!cancelled) {
          setKpis((prev) => { const n = [...prev]; n[i] = count; return n; });
          setDemoSources((prev) => { const n = [...prev]; n[i] = demoSource; return n; });
        }
      } catch {
        if (!cancelled) setKpis((prev) => { const n = [...prev]; n[i] = -1; return n; });
      }
    });

    return () => { cancelled = true; };
  }, [headers]);

  return (
    <div className="space-y-6">
      {/* Quick actions */}
      <section>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Quick Actions
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {quickActions.map((action) => (
            <Link
              key={action.href}
              to={action.href}
              className={`flex flex-col items-center gap-2 rounded-xl border p-4 text-center transition-colors ${colorMap[action.color]}`}
            >
              <span className="text-2xl" role="img" aria-label={action.label}>
                {action.icon}
              </span>
              <span className="text-xs font-semibold leading-tight">{action.label}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* KPI cards */}
      <section>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Pilot KPIs
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {KPI_CONFIGS.map((cfg, i) => (
            <KpiCard key={cfg.label} label={cfg.label} value={kpis[i]} demoDataSource={demoSources[i]} />
          ))}
        </div>
      </section>
    </div>
  );
}
