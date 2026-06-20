import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Package,
  ShieldCheck,
  TrendingUp,
  XCircle,
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
  created_at?: string;
  file_name?: string;
  status?: string;
  vendor_name?: string;
  instrument_type?: string;
  detected_issue?: string;
  risk_score?: number;
};

type BaselineKPIs = {
  total: number;
  approved: number;
  pending: number;
  vendor: number;
  rate: number;
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

function statusVariant(s: ModuleStatus["status"]) {
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
        <div className="text-2xl font-bold text-slate-900">{value === "" || value === null || value === undefined ? "—" : value}</div>
        {detail && <p className="text-xs text-slate-500 mt-1">{detail}</p>}
        {trend === "up" && <div className="flex items-center gap-1 mt-1 text-xs text-emerald-600"><TrendingUp className="h-3 w-3" />Trending up</div>}
      </CardContent>
    </Card>
  );
}

function statusRow(status?: string) {
  const s = (status || "").toLowerCase();
  if (s === "completed" || s === "done") return "text-emerald-700 bg-emerald-50";
  if (s === "failed" || s === "error") return "text-red-700 bg-red-50";
  if (s === "queued" || s === "pending") return "text-amber-700 bg-amber-50";
  return "text-slate-700";
}

export default function Dashboard() {
  const { headers } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recent, setRecent] = useState<Inspection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [baselineKPIs, setBaselineKPIs] = useState<BaselineKPIs | null>(null);
  const [modules, setModules] = useState<ModuleStatus[]>(MODULES);

  const hdrs = useMemo(() => headers(), [headers]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const [summaryRes, historyRes, baselineRes] = await Promise.allSettled([
          fetch(`${API_BASE}/api/history/summary`, { headers: hdrs }),
          fetch(`${API_BASE}/api/history?limit=10`, { headers: hdrs }),
          fetch(`${API_BASE}/api/enterprise/vendor-baseline-subscription/baselines`, { headers: hdrs }),
        ]);
        if (cancelled) return;

        if (summaryRes.status === "fulfilled" && summaryRes.value.ok)
          setSummary(await summaryRes.value.json());

        if (historyRes.status === "fulfilled" && historyRes.value.ok) {
          const d = await historyRes.value.json();
          setRecent(Array.isArray(d) ? d : d.items || []);
        }

        if (baselineRes.status === "fulfilled" && baselineRes.value.ok) {
          const d = await baselineRes.value.json();
          const bs: { baseline_status?: string; approval_status?: string; baseline_source?: string }[] =
            Array.isArray(d) ? d : d.records || [];
          const approved = bs.filter((b) =>
            ["approved", "active", "vendor_approved"].includes((b.baseline_status || "").toLowerCase())
          ).length;
          const pending = bs.filter((b) => (b.approval_status || "").toLowerCase().includes("pending")).length;
          const vendor = bs.filter((b) => b.baseline_source === "vendor").length;
          setBaselineKPIs({
            total: bs.length,
            approved,
            pending,
            vendor,
            rate: bs.length > 0 ? Math.round((approved / bs.length) * 100) : 0,
          });
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [hdrs]);

  useEffect(() => {
    let cancelled = false;
    Promise.all(
      MODULES.map(async (m) => {
        try {
          const r = await fetch(`${API_BASE}${m.endpoint}`, { headers: hdrs });
          return { ...m, status: r.ok ? "online" : [401, 403, 422].includes(r.status) ? "protected" : "offline", httpStatus: r.status } as ModuleStatus;
        } catch {
          return { ...m, status: "offline" as const };
        }
      })
    ).then((r) => { if (!cancelled) setModules(r); });
    return () => { cancelled = true; };
  }, [hdrs]);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Operational Overview</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Live inspection intelligence, quality metrics, and compliance status
        </p>
      </div>

      {error && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Inspection KPIs */}
      <section>
        <h3 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Inspections</h3>
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Spinner /> Loading inspection data…
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard label="Total" value={summary?.total_inspections ?? "—"} icon={Activity} detail="All records" />
            <KPICard label="Completed" value={summary?.completed ?? "—"} icon={CheckCircle2} detail="Workflow complete" trend="up" />
            <KPICard label="Queued" value={summary?.queued ?? "—"} icon={Clock} detail="Awaiting action" />
            <KPICard label="Failed" value={summary?.failed ?? "—"} icon={XCircle} detail="Needs review" />
          </div>
        )}
      </section>

      {/* Baseline KPIs */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Inspection Intelligence — Baselines</h3>
          <div className="flex gap-2">
            <Link to="/vendor-intake" className="text-xs text-blue-600 hover:underline">Vendor Intake</Link>
            <Link to="/baseline-review" className="text-xs text-blue-600 hover:underline">Review Queue</Link>
            <Link to="/vendor-baseline-portal" className="text-xs text-blue-600 hover:underline">Baseline Portal</Link>
          </div>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <KPICard label="Total Baselines" value={baselineKPIs?.total ?? "—"} icon={Package} />
          <KPICard label="Approved" value={baselineKPIs?.approved ?? "—"} icon={CheckCircle2} />
          <KPICard label="Pending Review" value={baselineKPIs?.pending ?? "—"} icon={Clock} />
          <KPICard label="Vendor Submissions" value={baselineKPIs?.vendor ?? "—"} icon={ShieldCheck} />
          <KPICard label="Approval Rate" value={baselineKPIs ? `${baselineKPIs.rate}%` : "—"} icon={TrendingUp} trend={baselineKPIs && baselineKPIs.rate >= 50 ? "up" : "neutral"} />
        </div>
      </section>

      {/* Recent activity table */}
      <section>
        <h3 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Recent Inspection Activity</h3>
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center gap-2 p-6 text-sm text-slate-500"><Spinner />Loading…</div>
            ) : recent.length === 0 ? (
              <div className="p-6 text-center text-sm text-slate-500">
                No recent inspection records. Submit an inspection via{" "}
                <Link to="/vendor-intake" className="text-blue-600 hover:underline">Vendor Intake</Link>.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100">
                      {["ID", "Vendor", "Instrument", "Issue", "Risk", "Status"].map((h) => (
                        <th key={h} className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map((row) => (
                      <tr key={row.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 text-slate-500 font-mono text-xs">{row.id}</td>
                        <td className="px-4 py-3 font-medium text-slate-800">{row.vendor_name || "—"}</td>
                        <td className="px-4 py-3 text-slate-600">{row.instrument_type || "—"}</td>
                        <td className="px-4 py-3 text-slate-600 max-w-[200px] truncate">{row.detected_issue || "—"}</td>
                        <td className="px-4 py-3">
                          {row.risk_score != null ? (
                            <span className={`font-semibold ${Number(row.risk_score) >= 0.8 ? "text-red-600" : Number(row.risk_score) >= 0.5 ? "text-amber-600" : "text-emerald-600"}`}>
                              {Number(row.risk_score).toFixed(2)}
                            </span>
                          ) : "—"}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusRow(row.status)}`}>
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
        <h3 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Module Health</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {modules.map((m) => (
            <Card key={m.key} className="p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-slate-800">{m.label}</span>
                <Badge variant={statusVariant(m.status)} className="capitalize">{m.status}</Badge>
              </div>
              <p className="text-xs text-slate-400 font-mono">{m.httpStatus ? `HTTP ${m.httpStatus}` : "pending"}</p>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
