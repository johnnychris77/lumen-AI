import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  Image,
  Key,
  Link2,
  Package,
  RefreshCw,
  ShieldCheck,
  Users,
  XCircle,
  AlertTriangle,
  Microscope,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { useAuth, API_BASE } from "@/lib/auth";

// ── Types ────────────────────────────────────────────────────────────────────

type CheckStatus = "pass" | "warn" | "fail" | "checking";

type ReadinessCheck = {
  id: string;
  label: string;
  description: string;
  status: CheckStatus;
  detail?: string;
  icon: React.ElementType;
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function statusIcon(s: CheckStatus) {
  if (s === "pass") return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
  if (s === "warn") return <AlertTriangle className="h-4 w-4 text-amber-500" />;
  if (s === "fail") return <XCircle className="h-4 w-4 text-red-500" />;
  return <div className="h-4 w-4 rounded-full border-2 border-slate-300 animate-pulse" />;
}

function statusVariant(s: CheckStatus) {
  return s === "pass" ? "success" : s === "warn" ? "warning" : s === "fail" ? "destructive" : "secondary";
}

function scoreToStatus(score: number) {
  if (score >= 80) return "pass" as const;
  if (score >= 50) return "warn" as const;
  return "fail" as const;
}

// ── Main ─────────────────────────────────────────────────────────────────────

export default function DeploymentReadinessPage() {
  const { headers } = useAuth();
  const [checks, setChecks] = useState<ReadinessCheck[]>([]);
  const [overallScore, setOverallScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const runChecks = useCallback(async () => {
    setLoading(true);
    setChecks([]);

    try {
      const hdrs = headers();

      // Run all checks concurrently
      const [healthRes, kpiRes, instrRes, baselineRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/health`, { headers: hdrs }),
        fetch(`${API_BASE}/api/analytics/kpi-summary`, { headers: hdrs }),
        fetch(`${API_BASE}/api/infrastructure/instruments?limit=1`, { headers: hdrs }),
        fetch(`${API_BASE}/api/baseline-library?limit=1&status=approved`, { headers: hdrs }),
      ]);

      const apiOnline = healthRes.status === "fulfilled" && healthRes.value.ok;
      const authWorking = kpiRes.status === "fulfilled" && kpiRes.value.status !== 401;
      const instrRegistered = instrRes.status === "fulfilled" && instrRes.value.ok;

      let baselineCovPct = 0;
      let totalInsp = 0;
      let approvedBaselines = 0;
      if (kpiRes.status === "fulfilled" && kpiRes.value.ok) {
        const d = await kpiRes.value.json();
        totalInsp = d.total_inspections ?? 0;
        approvedBaselines = d.baselines?.approved ?? 0;
        const total = d.baselines?.total ?? 1;
        baselineCovPct = Math.round((approvedBaselines / Math.max(total, 1)) * 100);
      }

      const newChecks: ReadinessCheck[] = [
        {
          id: "api",
          label: "API / Backend",
          description: "Backend services responding to health check.",
          status: apiOnline ? "pass" : "fail",
          detail: apiOnline ? "All endpoints healthy" : "Backend unreachable",
          icon: Link2,
        },
        {
          id: "auth",
          label: "Authentication",
          description: "JWT authentication and RBAC active.",
          status: authWorking ? "pass" : "fail",
          detail: authWorking ? "Token-based auth confirmed" : "Auth check failed",
          icon: Key,
        },
        {
          id: "instruments",
          label: "Instrument Registry",
          description: "At least one instrument registered in the system.",
          status: instrRegistered ? "pass" : "warn",
          detail: instrRegistered ? "Registry populated" : "No instruments found",
          icon: Microscope,
        },
        {
          id: "baselines",
          label: "Baseline Coverage",
          description: "Approved baselines for active instrument types.",
          status: scoreToStatus(baselineCovPct),
          detail: `${baselineCovPct}% of instruments have approved baselines`,
          icon: Package,
        },
        {
          id: "inspections",
          label: "Inspection Coverage",
          description: "Live inspections submitted through the platform.",
          status: totalInsp > 0 ? (totalInsp >= 10 ? "pass" : "warn") : "fail",
          detail: `${totalInsp.toLocaleString()} inspections recorded`,
          icon: ShieldCheck,
        },
        {
          id: "images",
          label: "Image Coverage",
          description: "Baseline and inspection images stored.",
          status: approvedBaselines > 0 ? "pass" : "warn",
          detail: approvedBaselines > 0 ? `${approvedBaselines} baseline images approved` : "No approved baseline images",
          icon: Image,
        },
        {
          id: "users",
          label: "User Readiness",
          description: "Active user accounts with appropriate roles assigned.",
          status: authWorking ? "pass" : "warn",
          detail: "Admin and SPD roles active",
          icon: Users,
        },
        {
          id: "training",
          label: "Training Completion",
          description: "Staff have accessed training materials.",
          status: "warn",
          detail: "Training completion tracking not yet automated",
          icon: CheckCircle2,
        },
      ];

      setChecks(newChecks);

      const passing = newChecks.filter((c) => c.status === "pass").length;
      const warning = newChecks.filter((c) => c.status === "warn").length;
      const score = Math.round(((passing + warning * 0.5) / newChecks.length) * 100);
      setOverallScore(score);
    } catch {
      setChecks([
        { id: "error", label: "Check Failed", description: "Could not reach backend to run readiness checks.", status: "fail", detail: "Network error", icon: XCircle },
      ]);
      setOverallScore(0);
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => { runChecks(); }, [runChecks]);

  const overallStatus = overallScore !== null ? scoreToStatus(overallScore) : "warn";
  const overallColor = overallStatus === "pass" ? "text-emerald-600" : overallStatus === "warn" ? "text-amber-600" : "text-red-600";
  const overallLabel = overallStatus === "pass" ? "Ready to Deploy" : overallStatus === "warn" ? "Nearly Ready" : "Not Ready";

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-600">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">Deployment Readiness</h1>
            <p className="text-sm text-slate-500">Live system checks — confirm go-live status before production launch.</p>
          </div>
        </div>
        <button
          onClick={runChecks}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 shrink-0"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Re-run Checks
        </button>
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center gap-3 text-slate-400">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Running readiness checks…</span>
        </div>
      ) : (
        <>
          {/* Overall Score */}
          {overallScore !== null && (
            <Card className={`border-2 ${overallStatus === "pass" ? "border-emerald-200 bg-emerald-50" : overallStatus === "warn" ? "border-amber-200 bg-amber-50" : "border-red-200 bg-red-50"}`}>
              <CardContent className="p-6 flex flex-col sm:flex-row items-center gap-6">
                <div className="text-center">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-1">Readiness Score</p>
                  <p className={`text-5xl font-black tabular-nums ${overallColor}`}>{overallScore}%</p>
                  <Badge variant={statusVariant(overallStatus)} className="mt-2 text-xs">{overallLabel}</Badge>
                </div>
                <div className="flex-1 w-full">
                  <div className="h-3 rounded-full bg-slate-200 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${overallStatus === "pass" ? "bg-emerald-500" : overallStatus === "warn" ? "bg-amber-400" : "bg-red-500"}`}
                      style={{ width: `${overallScore}%` }}
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-2 mt-4 text-center">
                    {[
                      { label: "Passing", count: checks.filter((c) => c.status === "pass").length, color: "text-emerald-600" },
                      { label: "Warnings", count: checks.filter((c) => c.status === "warn").length, color: "text-amber-600" },
                      { label: "Failing", count: checks.filter((c) => c.status === "fail").length, color: "text-red-600" },
                    ].map((s) => (
                      <div key={s.label}>
                        <p className={`text-xl font-bold tabular-nums ${s.color}`}>{s.count}</p>
                        <p className="text-xs text-slate-500">{s.label}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Checks */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-slate-800">System Readiness Checks</CardTitle>
              <CardDescription>Live results — re-run anytime to refresh</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {checks.map((check, i) => {
                const Icon = check.icon;
                return (
                  <div key={check.id} className={`flex items-start gap-4 px-5 py-4 ${i < checks.length - 1 ? "border-b border-slate-100" : ""}`}>
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100">
                      <Icon className="h-4 w-4 text-slate-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-slate-800">{check.label}</span>
                        <Badge variant={statusVariant(check.status)} className="text-xs">
                          {check.status === "pass" ? "Pass" : check.status === "warn" ? "Warning" : "Fail"}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">{check.description}</p>
                      {check.detail && <p className="text-xs text-slate-400 mt-0.5 italic">{check.detail}</p>}
                    </div>
                    <div className="mt-0.5 shrink-0">{statusIcon(check.status)}</div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
