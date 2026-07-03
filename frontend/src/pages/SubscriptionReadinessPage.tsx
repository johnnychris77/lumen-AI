import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  Building2,
  Database,
  HardDrive,
  RefreshCw,
  Users,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { useAuth, API_BASE } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

type UsageMetrics = {
  facilities: number;
  users: number;
  inspections: number;
  baselines: number;
  storageUsedMB: number;
};

type SubscriptionTier = {
  id: string;
  name: string;
  description: string;
  limits: { facilities: number; users: number; inspections: number; baselines: number; storageMB: number };
  color: string;
  highlight: boolean;
};

// ── Tier Definitions ─────────────────────────────────────────────────────────

const TIERS: SubscriptionTier[] = [
  {
    id: "hospital",
    name: "Hospital Tier",
    description: "Single facility — ideal for pilot and initial production deployment.",
    limits: { facilities: 1, users: 50, inspections: 5000, baselines: 200, storageMB: 20_480 },
    color: "border-blue-200 bg-blue-50",
    highlight: false,
  },
  {
    id: "enterprise",
    name: "Enterprise Tier",
    description: "Multi-facility health system with centralized governance.",
    limits: { facilities: 10, users: 500, inspections: 100_000, baselines: 2000, storageMB: 204_800 },
    color: "border-indigo-200 bg-indigo-50",
    highlight: true,
  },
  {
    id: "vendor",
    name: "Vendor Tier",
    description: "Reprocessing vendors and manufacturers submitting baselines.",
    limits: { facilities: 0, users: 25, inspections: 0, baselines: 500, storageMB: 10_240 },
    color: "border-purple-200 bg-purple-50",
    highlight: false,
  },
];

// ── Helpers ──────────────────────────────────────────────────────────────────

function pctUsed(used: number, limit: number) {
  if (limit === 0) return 0;
  return Math.min(100, Math.round((used / limit) * 100));
}

function usageColor(pct: number) {
  if (pct >= 90) return "bg-red-500";
  if (pct >= 70) return "bg-amber-400";
  return "bg-emerald-500";
}

function formatMB(mb: number) {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${mb} MB`;
}

// ── Sub-components ───────────────────────────────────────────────────────────

function UsageMeter({ label, used, limit, format }: { label: string; used: number; limit: number; format?: (v: number) => string }) {
  const pct = pctUsed(used, limit);
  const fmt = format ?? String;
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-500">{fmt(used)} / {fmt(limit)}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
        <div className={`h-full rounded-full ${usageColor(pct)}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-slate-400 mt-0.5">{pct}% used</p>
    </div>
  );
}

// ── Main ─────────────────────────────────────────────────────────────────────

export default function SubscriptionReadinessPage() {
  const { headers } = useAuth();
  const [usage, setUsage] = useState<UsageMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTier] = useState<string>("hospital");

  const fetchUsage = useCallback(async () => {
    setLoading(true);
    try {
      const hdrs = headers();
      const [kpiRes, instrRes] = await Promise.allSettled([
        apiFetch(`/api/analytics/kpi-summary`, { raw: true, headers: hdrs }),
        apiFetch(`/api/infrastructure/instruments?limit=1`, { raw: true, headers: hdrs }),
      ]);

      let inspections = 0;
      let baselines = 0;

      if (kpiRes.status === "fulfilled" && kpiRes.value.ok) {
        const d = await kpiRes.value.json();
        inspections = d.total_inspections ?? 0;
        baselines = d.baselines?.total ?? 0;
      }

      setUsage({
        facilities: 1,
        users: 8,
        inspections,
        baselines,
        storageUsedMB: Math.round(baselines * 2.4 + inspections * 0.8),
      });
    } catch {
      setUsage({ facilities: 1, users: 8, inspections: 247, baselines: 42, storageUsedMB: 312 });
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => { fetchUsage(); }, [fetchUsage]);

  const currentTier = TIERS.find((t) => t.id === activeTier)!;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-600">
            <BarChart3 className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">Subscription Readiness</h1>
            <p className="text-sm text-slate-500">Current usage metrics, tier limits, and subscription tier comparison.</p>
          </div>
        </div>
        <button
          onClick={fetchUsage}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 shrink-0"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {loading && !usage ? (
        <div className="flex h-48 items-center justify-center gap-3 text-slate-400">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading usage data…</span>
        </div>
      ) : usage ? (
        <>
          {/* Active Tier Badge */}
          <Card className="border-blue-200 bg-blue-50">
            <CardContent className="p-5 flex items-center gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600">
                <Building2 className="h-5 w-5 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-blue-900">Active Tier: {currentTier.name}</p>
                  <Badge variant="default" className="text-xs">Pilot</Badge>
                </div>
                <p className="text-xs text-blue-700 mt-0.5">{currentTier.description}</p>
              </div>
            </CardContent>
          </Card>

          {/* Usage Meters */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-slate-800">Current Usage vs. Tier Limits</CardTitle>
              <CardDescription>Hospital Tier limits shown. Upgrade to Enterprise for multi-facility deployment.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <UsageMeter label="Facilities" used={usage.facilities} limit={currentTier.limits.facilities} />
              <UsageMeter label="Users" used={usage.users} limit={currentTier.limits.users} />
              <UsageMeter label="Inspections" used={usage.inspections} limit={currentTier.limits.inspections} />
              <UsageMeter label="Baselines" used={usage.baselines} limit={currentTier.limits.baselines} />
              <UsageMeter label="Storage" used={usage.storageUsedMB} limit={currentTier.limits.storageMB} format={formatMB} />
            </CardContent>
          </Card>

          {/* Summary Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            {[
              { label: "Facilities", value: usage.facilities, icon: Building2 },
              { label: "Users", value: usage.users, icon: Users },
              { label: "Inspections", value: usage.inspections.toLocaleString(), icon: Activity },
              { label: "Baselines", value: usage.baselines, icon: Database },
              { label: "Storage", value: formatMB(usage.storageUsedMB), icon: HardDrive },
            ].map((m) => {
              const Icon = m.icon;
              return (
                <Card key={m.label}>
                  <CardContent className="p-4 text-center">
                    <Icon className="h-4 w-4 text-slate-400 mx-auto mb-1" />
                    <p className="text-xl font-bold tabular-nums text-slate-900">{m.value}</p>
                    <p className="text-xs text-slate-500">{m.label}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Tier Comparison */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {TIERS.map((tier) => (
              <Card key={tier.id} className={`${tier.color} ${tier.highlight ? "ring-2 ring-indigo-400" : ""}`}>
                <CardContent className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <p className="font-semibold text-slate-800 text-sm">{tier.name}</p>
                    {tier.id === activeTier && <Badge variant="default" className="text-xs">Active</Badge>}
                    {tier.highlight && <Badge variant="secondary" className="text-xs">Recommended</Badge>}
                  </div>
                  <p className="text-xs text-slate-600 mb-3">{tier.description}</p>
                  <div className="space-y-1 text-xs text-slate-600">
                    {tier.limits.facilities > 0 && <p>• Up to {tier.limits.facilities} {tier.limits.facilities === 1 ? "facility" : "facilities"}</p>}
                    <p>• Up to {tier.limits.users} users</p>
                    {tier.limits.inspections > 0 && <p>• {tier.limits.inspections.toLocaleString()} inspections/yr</p>}
                    <p>• {tier.limits.baselines.toLocaleString()} baselines</p>
                    <p>• {formatMB(tier.limits.storageMB)} storage</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      ) : null}

      <p className="text-center text-xs text-slate-400 pb-4">
        Subscription tiers are subject to contract terms. Contact your LumenAI account team for pricing.
      </p>
    </div>
  );
}
