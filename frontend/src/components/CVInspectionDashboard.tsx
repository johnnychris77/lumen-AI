/**
 * R8: CV Inspection Dashboard tile.
 *
 * Displays:
 * - KPI summary cards (total analyses, recognition rate, blood detections,
 *   baseline match %, avg cleanliness score)
 * - Finding category breakdown bar
 * - Active learning review queue size
 * - Provider cost + latency telemetry
 * - Recent inference history list
 */
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Droplets,
  Eye,
  Layers,
  Microscope,
  RefreshCw,
  ShieldCheck,
  TrendingDown,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { useAuth, API_BASE } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

type CVKPISummary = {
  total_analyses: number;
  recognized_count: number;
  recognition_rate_pct: number;
  blood_detections: number;
  bone_detections: number;
  tissue_detections: number;
  corrosion_detections: number;
  crack_detections: number;
  insulation_defect_detections: number;
  residue_detections: number;
  baseline_comparisons_run: number;
  baseline_pass_count: number;
  baseline_fail_count: number;
  avg_confidence: number;
  avg_baseline_match_pct: number;
  avg_processing_ms: number;
  total_provider_cost_usd: number;
  review_queue_size: number;
};

type ProviderMetrics = {
  total_inferences: number;
  avg_processing_ms: number;
  p95_processing_ms: number;
  total_cost_usd: number;
  avg_cost_per_inference_usd: number;
  provider_breakdown: Record<string, { count: number; total_cost_usd: number }>;
};

type InferenceRecord = {
  inference_id: string;
  instrument_name: string;
  instrument_recognized: boolean;
  overall_cleanliness_score: number;
  finding_count: number;
  baseline_compared: boolean;
  baseline_match_pct: number;
  baseline_verdict: string;
  review_required: boolean;
  provider: string;
  processing_ms: number;
  created_at: string | null;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function scoreColor(score: number) {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  if (score >= 40) return "text-orange-600";
  return "text-red-600";
}

function verdictBadge(verdict: string) {
  const map: Record<string, string> = {
    pass: "bg-green-100 text-green-800",
    review_required: "bg-yellow-100 text-yellow-800",
    fail: "bg-red-100 text-red-800",
  };
  return map[verdict] ?? "bg-gray-100 text-gray-700";
}

// ── Main component ────────────────────────────────────────────────────────────

export function CVInspectionDashboard({ tenantId = "demo-tenant" }: { tenantId?: string }) {
  const { token } = useAuth();
  const [kpi, setKpi] = useState<CVKPISummary | null>(null);
  const [metrics, setMetrics] = useState<ProviderMetrics | null>(null);
  const [history, setHistory] = useState<InferenceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const headers = {
    Authorization: `Bearer ${token || localStorage.getItem("token") || ""}`,
    "X-LumenAI-Role": "operator",
    "Content-Type": "application/json",
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const base = API_BASE || import.meta.env.VITE_API_BASE_URL || "";
      const [kpiRes, metricsRes, historyRes] = await Promise.all([
        apiFetch(`/api/enterprise/cv/kpi-summary?tenant_id=${tenantId}`, { raw: true, headers }),
        apiFetch(`/api/enterprise/cv/provider/metrics?tenant_id=${tenantId}`, { raw: true, headers }),
        apiFetch(`/api/enterprise/cv/history?tenant_id=${tenantId}&limit=10`, { raw: true, headers }),
      ]);
      if (kpiRes.ok) setKpi(await kpiRes.json());
      if (metricsRes.ok) setMetrics(await metricsRes.json());
      if (historyRes.ok) setHistory(await historyRes.json());
    } catch (e) {
      setError("Failed to load CV data");
    } finally {
      setLoading(false);
    }
  }, [tenantId, token]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Spinner size="lg" />
        <span className="ml-3 text-gray-500">Loading CV inspection data…</span>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!kpi) return null;

  // provider_breakdown's keys are the literal CV_PROVIDER values that
  // actually produced these records (backend/app/routes/cv.py's
  // provider_metrics()). "mock" means CVRegistry fell back to
  // MockCVProvider -- random.Random(hash(image_url))-seeded findings, not
  // real pixel analysis -- which is the default whenever no onnx/openai/
  // roboflow provider is configured. Surface that plainly instead of
  // presenting these counts as if they came from real image inference.
  const usesMockProvider = Boolean(metrics?.provider_breakdown && "mock" in metrics.provider_breakdown);

  const findingBreakdown = [
    { label: "Blood", count: kpi.blood_detections, color: "bg-red-500" },
    { label: "Bone", count: kpi.bone_detections, color: "bg-orange-400" },
    { label: "Tissue", count: kpi.tissue_detections, color: "bg-yellow-400" },
    { label: "Residue", count: kpi.residue_detections, color: "bg-amber-500" },
    { label: "Corrosion", count: kpi.corrosion_detections, color: "bg-blue-400" },
    { label: "Cracks", count: kpi.crack_detections, color: "bg-purple-500" },
    { label: "Insulation", count: kpi.insulation_defect_detections, color: "bg-pink-500" },
  ];
  const totalFindings = findingBreakdown.reduce((s, f) => s + f.count, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Microscope className="h-6 w-6 text-blue-600" />
          <h2 className="text-xl font-semibold text-gray-900">CV Inspection Intelligence</h2>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 rounded-md border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      {usesMockProvider && (
        <Alert variant="warning">
          <AlertDescription>
            <strong>Demo data:</strong> these counts come from the mock CV provider (deterministic pseudo-random findings, not real image analysis) — no onnx/vision provider is configured for this deployment. See <code>CV_PROVIDER</code> in provider settings to connect a real model.
          </AlertDescription>
        </Alert>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <KpiCard
          icon={<Activity className="h-5 w-5 text-blue-500" />}
          label="Total Analyses"
          value={kpi.total_analyses.toString()}
        />
        <KpiCard
          icon={<ShieldCheck className="h-5 w-5 text-green-500" />}
          label="Recognition Rate"
          value={`${kpi.recognition_rate_pct}%`}
          sub={`${kpi.recognized_count} / ${kpi.total_analyses}`}
        />
        <KpiCard
          icon={<Droplets className="h-5 w-5 text-red-500" />}
          label="Blood Detections"
          value={kpi.blood_detections.toString()}
          urgent={kpi.blood_detections > 0}
        />
        <KpiCard
          icon={<CheckCircle2 className="h-5 w-5 text-teal-500" />}
          label="Baseline Pass Rate"
          value={
            kpi.baseline_comparisons_run > 0
              ? `${Math.round((kpi.baseline_pass_count / kpi.baseline_comparisons_run) * 100)}%`
              : "—"
          }
          sub={`${kpi.baseline_pass_count} pass / ${kpi.baseline_fail_count} fail`}
        />
        {kpi.review_queue_size > 0 && (
          <KpiCard
            icon={<Eye className="h-5 w-5 text-amber-500" />}
            label="Review Queue"
            value={kpi.review_queue_size.toString()}
            sub="Awaiting annotation"
            urgent
          />
        )}
        {kpi.review_queue_size === 0 && (
          <KpiCard
            icon={<Zap className="h-5 w-5 text-purple-500" />}
            label="Avg Latency"
            value={`${kpi.avg_processing_ms} ms`}
          />
        )}
      </div>

      {/* Finding category breakdown */}
      {totalFindings > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <Layers className="h-4 w-4" /> Finding Category Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {findingBreakdown.filter(f => f.count > 0).map(f => (
                <div key={f.label} className="flex items-center gap-3">
                  <span className="w-20 text-xs text-gray-600 text-right">{f.label}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div
                      className={`${f.color} h-2 rounded-full transition-all`}
                      style={{ width: `${Math.min(100, (f.count / totalFindings) * 100)}%` }}
                    />
                  </div>
                  <span className="w-6 text-xs text-gray-500 text-right">{f.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Provider telemetry (R12) */}
      {metrics && metrics.total_inferences > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <TrendingDown className="h-4 w-4" /> Provider Telemetry
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-sm">
              <div>
                <p className="text-gray-500">Avg Latency</p>
                <p className="font-semibold">{metrics.avg_processing_ms} ms</p>
              </div>
              <div>
                <p className="text-gray-500">p95 Latency</p>
                <p className="font-semibold">{metrics.p95_processing_ms} ms</p>
              </div>
              <div>
                <p className="text-gray-500">Total Cost</p>
                <p className="font-semibold">${metrics.total_cost_usd.toFixed(4)}</p>
              </div>
              <div>
                <p className="text-gray-500">Cost / Inference</p>
                <p className="font-semibold">${metrics.avg_cost_per_inference_usd.toFixed(6)}</p>
              </div>
            </div>
            {Object.keys(metrics.provider_breakdown).length > 0 && (
              <div className="mt-3 flex gap-2 flex-wrap">
                {Object.entries(metrics.provider_breakdown).map(([provider, info]) => (
                  <span
                    key={provider}
                    className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700"
                  >
                    {provider}: {info.count} inferences
                  </span>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Recent inference history */}
      {history.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <Clock className="h-4 w-4" /> Recent Inferences
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y divide-gray-100">
              {history.map(rec => (
                <div key={rec.inference_id} className="flex items-center justify-between py-2.5 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-gray-800">
                      {rec.instrument_name || "Unknown Instrument"}
                    </p>
                    <p className="text-xs text-gray-400">
                      {rec.inference_id} · {rec.processing_ms} ms
                    </p>
                  </div>
                  <div className="ml-3 flex items-center gap-2">
                    <span className={`font-semibold ${scoreColor(rec.overall_cleanliness_score)}`}>
                      {rec.overall_cleanliness_score}
                    </span>
                    {rec.finding_count > 0 && (
                      <Badge variant="secondary" className="text-xs">
                        {rec.finding_count} finding{rec.finding_count > 1 ? "s" : ""}
                      </Badge>
                    )}
                    {rec.baseline_compared && (
                      <Badge className={`text-xs ${verdictBadge(rec.baseline_verdict)}`}>
                        BL {rec.baseline_verdict}
                      </Badge>
                    )}
                    {rec.review_required && (
                      <AlertTriangle className="h-4 w-4 text-amber-500" title="Needs annotation" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function KpiCard({
  icon,
  label,
  value,
  sub,
  urgent = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  urgent?: boolean;
}) {
  return (
    <Card className={urgent ? "border-amber-300 bg-amber-50" : ""}>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between">
          {icon}
        </div>
        <p className={`mt-2 text-2xl font-bold ${urgent ? "text-amber-700" : "text-gray-900"}`}>
          {value}
        </p>
        <p className="text-xs text-gray-500 mt-0.5">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  );
}
