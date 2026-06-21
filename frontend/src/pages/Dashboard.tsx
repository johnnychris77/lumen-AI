import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PilotDashboardCards } from "@/components/PilotDashboardCards";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Droplets,
  Package,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  XCircle,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { useAuth, API_BASE } from "@/lib/auth";

type Summary = {
  total_inspections?: number;
  completed?: number;
  queued?: number;
  failed?: number;
};

type Inspection = {
  id: number;
  status?: string;
  vendor_name?: string;
  instrument_type?: string;
  detected_issue?: string;
  risk_score?: number;
};

type KpiSummary = {
  total_findings: number;
  high_risk_instruments: number;
  finding_categories: Record<string, number>;
  baselines: {
    total: number;
    approved: number;
    pending: number;
    vendor_submissions: number;
    approval_rate: number;
  };
};

type ModuleStatus = {
  key: string;
  label: string;
  endpoint: string;
  status: "checking" | "online" | "protected" | "offline";
  httpStatus?: number;
};

const MODULES: ModuleStatus[] = [
  { key: "vendor", label: "Vendor Governance", endpoint: "/api/analytics/vendors", status: "checking" },
  { key: "capa", label: "CAPA Workflow", endpoint: "/api/capa", status: "checking" },
  { key: "audit", label: "Audit Command Center", endpoint: "/api/enterprise/audit/events?limit=1", status: "checking" },
  { key: "evidence", label: "Compliance Evidence", endpoint: "/api/enterprise/audit/evidence-bundle/verification-summary", status: "checking" },
];

const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  blood:             { label: "Blood",             color: "text-red-700 bg-red-50 border-red-200" },
  bone:              { label: "Bone",              color: "text-orange-700 bg-orange-50 border-orange-200" },
  tissue:            { label: "Tissue",            color: "text-pink-700 bg-pink-50 border-pink-200" },
  debris:            { label: "Debris / Bioburden",color: "text-amber-700 bg-amber-50 border-amber-200" },
  corrosion:         { label: "Corrosion",         color: "text-yellow-700 bg-yellow-50 border-yellow-200" },
  crack:             { label: "Crack / Fracture",  color: "text-slate-700 bg-slate-50 border-slate-200" },
  insulation_damage: { label: "Insulation Damage", color: "text-purple-700 bg-purple-50 border-purple-200" },
  baseline_match:    { label: "Baseline Match",    color: "text-blue-700 bg-blue-50 border-blue-200" },
  barcode_qr_keydot: { label: "Barcode / QR / KeyDot", color: "text-teal-700 bg-teal-50 border-teal-200" },
  other:             { label: "Other",             color: "text-slate-600 bg-slate-50 border-slate-200" },
};

function statusVariant(s: ModuleStatus["status"]): "success" | "warning" | "destructive" | "secondary" {
  return s === "online" ? "success" : s === "protected" ? "warning" : s === "offline" ? "destructive" : "secondary";
}

function KPICard({
  label,
  value,
  detail,
  icon: Icon,
  trend,
}: {
  label: string;
  value: string | number;
  detail?: string;
  icon?: React.ElementType;
  trend?: "up" | "down" | "neutral";
}) {
  return (
    <Card>
      <CardHeader className="pb-2 flex-row items-center justify-between space-y-0">
        <CardDescription className="text-xs font-medium uppercase tracking-wide">{label}</CardDescription>
        {Icon && <Icon className="h-4 w-4 text-slate-400" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-slate-900">
          {value === "" || value === null || value === undefined ? "—" : value}
        </div>
        {detail && <p className="text-xs text-slate-500 mt-1">{detail}</p>}
        {trend === "up" && (
          <div className="flex items-center gap-1 mt-1 text-xs text-emerald-600">
            <TrendingUp className="h-3 w-3" /> Trending up
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CategoryKPICard({ catKey, count }: { catKey: string; count: number }) {
  const meta = CATEGORY_LABELS[catKey] ?? { label: catKey, color: "text-slate-600 bg-white border-slate-200" };
  const isHighAlert = ["blood", "bone", "tissue", "crack", "insulation_damage"].includes(catKey) && count > 0;
  return (
    <div className={`rounded-xl border p-4 flex flex-col gap-1 ${meta.color}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide opacity-75">{meta.label}</span>
        {isHighAlert && count > 0 && (
          <span className="text-xs font-bold px-1.5 py-0.5 rounded-full bg-red-600 text-white">!</span>
        )}
      </div>
      <div className="text-3xl font-bold">{count}</div>
      <div className="text-xs opacity-60">findings</div>
    </div>
  );
}

function statusRowClass(status?: string) {
  const s = (status || "").toLowerCase();
  if (s === "completed" || s === "done") return "text-emerald-700 bg-emerald-50";
  if (s === "failed" || s === "error") return "text-red-700 bg-red-50";
  if (s === "queued" || s === "pending") return "text-amber-700 bg-amber-50";
  return "text-slate-700";
}

const REFRESH_INTERVAL_MS = 30_000;

export default function Dashboard() {
  const { headers } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recent, setRecent] = useState<Inspection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [kpi, setKpi] = useState<KpiSummary | null>(null);
  const [modules, setModules] = useState<ModuleStatus[]>(MODULES);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [countdown, setCountdown] = useState(REFRESH_INTERVAL_MS / 1000);

  const hdrs = useMemo(() => headers(), [headers]);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError("");
    try {
      const [summaryRes, historyRes, kpiRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/history/summary`, { headers: hdrs }),
        fetch(`${API_BASE}/api/history?limit=10`, { headers: hdrs }),
        fetch(`${API_BASE}/api/enterprise/findings/kpi-summary`, { headers: hdrs }),
      ]);

      if (summaryRes.status === "fulfilled" && summaryRes.value.ok)
        setSummary(await summaryRes.value.json());

      if (historyRes.status === "fulfilled" && historyRes.value.ok) {
        const d = await historyRes.value.json();
        setRecent(Array.isArray(d) ? d : d.items || []);
      }

      if (kpiRes.status === "fulfilled" && kpiRes.value.ok)
        setKpi(await kpiRes.value.json());

      setLastUpdated(new Date());
      setCountdown(REFRESH_INTERVAL_MS / 1000);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (!silent) setLoading(false);
    }
  }, [hdrs]);

  // Initial load
  useEffect(() => { load(); }, [load]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(() => load(true), REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [load]);

  // Countdown ticker
  useEffect(() => {
    const tick = setInterval(() => setCountdown((c) => (c <= 1 ? REFRESH_INTERVAL_MS / 1000 : c - 1)), 1000);
    return () => clearInterval(tick);
  }, [lastUpdated]);

  useEffect(() => {
    let cancelled = false;
    Promise.all(
      MODULES.map(async (m) => {
        try {
          const r = await fetch(`${API_BASE}${m.endpoint}`, { headers: hdrs });
          return {
            ...m,
            status: r.ok ? "online" : [401, 403, 422].includes(r.status) ? "protected" : "offline",
            httpStatus: r.status,
          } as ModuleStatus;
        } catch {
          return { ...m, status: "offline" as const };
        }
      })
    ).then((r) => { if (!cancelled) setModules(r); });
    return () => { cancelled = true; };
  }, [hdrs]);

  const cats = kpi?.finding_categories ?? {};

  return (
    <div className="space-y-8">
      {/* Pilot quick actions and KPIs */}
      <PilotDashboardCards />

      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Inspection Intelligence Dashboard</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Live sterile processing metrics — findings, baselines, and compliance status for SPD managers and executives.
          </p>
        </div>
        <div className="shrink-0 flex flex-col items-end gap-1.5">
          <button
            onClick={() => load(false)}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition-colors"
          >
            {loading ? <Spinner className="h-3 w-3" /> : <RefreshCw className="h-3 w-3" />}
            Refresh
          </button>
          {lastUpdated && (
            <p className="text-xs text-slate-400">
              Updated {lastUpdated.toLocaleTimeString()} · next in {countdown}s
            </p>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Dashboard data partially unavailable: {error}. Some KPIs may show "—" until the backend responds.
          </AlertDescription>
        </Alert>
      )}

      {/* Inspection workflow KPIs */}
      <section>
        <h3 className="text-xs font-semibold text-slate-500 mb-3 uppercase tracking-wider">Inspection Workflow</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard label="Total Inspections" value={summary?.total_inspections ?? "—"} icon={Activity} detail="All captured records" />
          <KPICard label="Completed" value={summary?.completed ?? "—"} icon={CheckCircle2} detail="Workflow complete" trend="up" />
          <KPICard label="Queued" value={summary?.queued ?? "—"} icon={Clock} detail="Awaiting triage" />
          <KPICard label="Failed" value={summary?.failed ?? "—"} icon={XCircle} detail="Requires review" />
        </div>
      </section>

      {/* Enterprise finding KPIs */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Enterprise Findings</h3>
          <Link to="/findings" className="text-xs text-blue-600 hover:underline">View findings queue →</Link>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <KPICard label="Total Findings" value={kpi?.total_findings ?? "—"} icon={Activity} detail="Enterprise intake records" />
          <KPICard
            label="High-Risk Instruments"
            value={kpi?.high_risk_instruments ?? "—"}
            icon={AlertTriangle}
            detail="High or critical severity"
          />
          <KPICard label="Approved Baselines" value={kpi?.baselines.approved ?? "—"} icon={CheckCircle2} detail="Cleared for scoring use" trend="up" />
          <KPICard label="Baseline Approval Rate" value={kpi ? `${kpi.baselines.approval_rate}%` : "—"} icon={TrendingUp} detail="Approved / total baselines" />
        </div>

        {/* Category breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Finding Category Breakdown</CardTitle>
            <CardDescription>
              AI-detected finding types across all enterprise inspections. Red alert (!) indicates clinically significant residue types.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {Object.entries(CATEGORY_LABELS).map(([key]) => (
                <CategoryKPICard key={key} catKey={key} count={cats[key] ?? 0} />
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Baseline KPIs */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Vendor Baseline Lifecycle</h3>
          <div className="flex gap-3">
            <Link to="/baseline-review" className="text-xs text-blue-600 hover:underline">Review queue →</Link>
            <Link to="/vendor-baseline-portal" className="text-xs text-blue-600 hover:underline">Baseline portal →</Link>
          </div>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard label="Total Baselines" value={kpi?.baselines.total ?? "—"} icon={Package} detail="All baseline records" />
          <KPICard label="Pending Review" value={kpi?.baselines.pending ?? "—"} icon={Clock} detail="Awaiting hospital approval" />
          <KPICard label="Vendor Submissions" value={kpi?.baselines.vendor_submissions ?? "—"} icon={ShieldCheck} detail="Submitted by vendors" />
          <KPICard label="Approval Rate" value={kpi ? `${kpi.baselines.approval_rate}%` : "—"} icon={Zap} detail="Approved / total" />
        </div>
      </section>

      {/* Recent activity table */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Recent Inspection Activity</h3>
          <Link to="/intake-history" className="text-xs text-blue-600 hover:underline">Full history →</Link>
        </div>
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center gap-2 p-6 text-sm text-slate-500"><Spinner />Loading…</div>
            ) : recent.length === 0 ? (
              <div className="p-8 text-center">
                <Droplets className="mx-auto h-8 w-8 text-slate-300 mb-3" />
                <p className="text-sm font-medium text-slate-600">No inspection records yet</p>
                <p className="text-xs text-slate-400 mt-1">
                  Submit your first inspection via{" "}
                  <Link to="/vendor-intake" className="text-blue-600 hover:underline">Vendor Intake</Link>.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100">
                      {["ID", "Vendor", "Instrument", "Issue Detected", "Risk Score", "Status"].map((h) => (
                        <th key={h} className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map((row) => (
                      <tr key={row.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 text-slate-400 font-mono text-xs">{row.id}</td>
                        <td className="px-4 py-3 font-medium text-slate-800">{row.vendor_name || "—"}</td>
                        <td className="px-4 py-3 text-slate-600">{row.instrument_type || "—"}</td>
                        <td className="px-4 py-3 text-slate-600 max-w-[180px] truncate">{row.detected_issue || "—"}</td>
                        <td className="px-4 py-3">
                          {row.risk_score != null ? (
                            <span className={`font-semibold ${Number(row.risk_score) >= 0.8 ? "text-red-600" : Number(row.risk_score) >= 0.5 ? "text-amber-600" : "text-emerald-600"}`}>
                              {Number(row.risk_score).toFixed(2)}
                            </span>
                          ) : "—"}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusRowClass(row.status)}`}>
                            {row.status || "—"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* Module health */}
      <section>
        <h3 className="text-xs font-semibold text-slate-500 mb-3 uppercase tracking-wider">System Module Health</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {modules.map((m) => (
            <Card key={m.key} className="p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-slate-800">{m.label}</span>
                <Badge variant={statusVariant(m.status)} className="capitalize text-xs">{m.status}</Badge>
              </div>
              <p className="text-xs text-slate-400 font-mono">{m.httpStatus ? `HTTP ${m.httpStatus}` : "checking…"}</p>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
