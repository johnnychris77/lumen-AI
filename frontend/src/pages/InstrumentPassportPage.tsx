import { useCallback, useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ClipboardList,
  CreditCard,
  Droplets,
  ExternalLink,
  FlaskConical,
  History,
  Image,
  Layers,
  LineChart,
  Microscope,
  Minus,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { useAuth, API_BASE } from "@/lib/auth";

// ── Types ────────────────────────────────────────────────────────────────────

type Instrument = {
  id: number;
  internal_id?: string;
  barcode?: string;
  udi?: string;
  keydot_id?: string;
  instrument_type?: string;
  manufacturer?: string;
  model?: string;
  status?: string;
};

type Inspection = {
  id: number;
  detected_issue?: string;
  risk_score?: number;
  status?: string;
  created_at?: string;
  confidence?: number;
  instrument_barcode?: string;
  instrument_udi?: string;
  instrument_name?: string;
};

type Baseline = {
  id: number;
  instrument_category?: string;
  status?: string;
  created_at?: string;
  manufacturer?: string;
  image_url?: string;
};

// Phase 14.8 — deterministic predictive intelligence from the backend
// /api/instruments/{identifier}/timeline endpoint.
type Prediction = {
  risk_trend: "improving" | "stable" | "worsening" | "insufficient_data";
  latest_risk_score: number | null;
  estimated_remaining_life: string | null;
  replacement_planning: string;
  note: string;
};
type TimelineResponse = {
  identifier: string;
  inspection_count: number;
  prediction: Prediction;
};

// ── Helpers ──────────────────────────────────────────────────────────────────

const FINDING_META: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  blood:             { label: "Blood",             icon: Droplets,    color: "text-red-600 bg-red-50 border-red-200" },
  bone:              { label: "Bone",              icon: Microscope,  color: "text-orange-600 bg-orange-50 border-orange-200" },
  tissue:            { label: "Tissue",            icon: FlaskConical, color: "text-pink-600 bg-pink-50 border-pink-200" },
  debris:            { label: "Debris",            icon: Layers,      color: "text-amber-600 bg-amber-50 border-amber-200" },
  corrosion:         { label: "Corrosion",         icon: AlertTriangle, color: "text-yellow-600 bg-yellow-50 border-yellow-200" },
  crack:             { label: "Crack / Fracture",  icon: Zap,         color: "text-slate-700 bg-slate-100 border-slate-200" },
  insulation_damage: { label: "Insulation Damage", icon: ShieldAlert, color: "text-purple-600 bg-purple-50 border-purple-200" },
  none:              { label: "Clean",             icon: CheckCircle2, color: "text-emerald-600 bg-emerald-50 border-emerald-200" },
};

function riskVariant(score: number): "destructive" | "warning" | "secondary" | "success" {
  if (score >= 80) return "destructive";
  if (score >= 60) return "warning";
  if (score >= 40) return "secondary";
  return "success";
}

function riskLabel(score: number) {
  if (score >= 80) return "Critical";
  if (score >= 60) return "High";
  if (score >= 40) return "Medium";
  return "Low";
}

const TREND_META: Record<Prediction["risk_trend"], { label: string; icon: React.ElementType; color: string }> = {
  worsening:         { label: "Worsening",         icon: TrendingUp,   color: "text-red-600 bg-red-50 border-red-200" },
  stable:            { label: "Stable",            icon: Minus,        color: "text-slate-600 bg-slate-50 border-slate-200" },
  improving:         { label: "Improving",         icon: TrendingDown, color: "text-emerald-600 bg-emerald-50 border-emerald-200" },
  insufficient_data: { label: "Insufficient data", icon: Minus,        color: "text-slate-400 bg-slate-50 border-slate-200" },
};

function formatDate(s?: string) {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

function FindingBadge({ issue }: { issue?: string }) {
  const meta = FINDING_META[issue ?? ""] ?? { label: issue ?? "—", icon: AlertTriangle, color: "text-slate-500 bg-slate-50 border-slate-200" };
  const Icon = meta.icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${meta.color}`}>
      <Icon className="h-3 w-3" />
      {meta.label}
    </span>
  );
}

function SectionTitle({ icon: Icon, title }: { icon: React.ElementType; title: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon className="h-4 w-4 text-slate-500" />
      <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
    </div>
  );
}

function Row({ label, value, mono, capitalize: cap }: { label: string; value: React.ReactNode; mono?: boolean; capitalize?: boolean }) {
  return (
    <div className="flex justify-between gap-2 text-sm">
      <span className="text-slate-500 shrink-0">{label}</span>
      <span className={`text-slate-800 text-right min-w-0 truncate ${mono ? "font-mono text-xs" : ""} ${cap ? "capitalize" : ""}`}>
        {value}
      </span>
    </div>
  );
}

// ── Empty State ──────────────────────────────────────────────────────────────

function EmptyPassport() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[420px] text-center px-4">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 mb-5">
        <CreditCard className="h-7 w-7 text-indigo-500" />
      </div>
      <h2 className="text-lg font-semibold text-slate-900 mb-2">Instrument Passport V2</h2>
      <p className="text-sm text-slate-500 max-w-md mb-6">
        View a full lifecycle passport — identity, images, findings history, risk intelligence,
        and CAPA timeline — for any registered instrument. Select one from the Registry or
        pass <code className="bg-slate-100 rounded px-1">?instrument=ID</code> in the URL.
      </p>
      <Link
        to="/infrastructure?tab=passport"
        className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
      >
        Open Instrument Registry
        <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

export default function InstrumentPassportPage() {
  const [searchParams] = useSearchParams();
  const instrumentParam = searchParams.get("instrument");
  const { headers } = useAuth();

  const [instrument, setInstrument] = useState<Instrument | null>(null);
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [baselines, setBaselines] = useState<Baseline[]>([]);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPassport = useCallback(async (identifier: string) => {
    setLoading(true);
    setError(null);
    try {
      const hdrs = headers();
      const [instrRes, inspRes, baselineRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/infrastructure/instruments?limit=200`, { headers: hdrs }),
        fetch(`${API_BASE}/api/inspections?limit=50`, { headers: hdrs }),
        fetch(`${API_BASE}/api/baseline-library?limit=50`, { headers: hdrs }),
      ]);

      let found: Instrument | null = null;
      if (instrRes.status === "fulfilled" && instrRes.value.ok) {
        const raw = await instrRes.value.json();
        const list: Instrument[] = Array.isArray(raw) ? raw : raw.items ?? [];
        found = list.find(
          (i) =>
            i.internal_id === identifier ||
            i.barcode === identifier ||
            i.udi === identifier ||
            String(i.id) === identifier
        ) ?? null;
      }
      setInstrument(found);

      if (inspRes.status === "fulfilled" && inspRes.value.ok) {
        const raw = await inspRes.value.json();
        const all: Inspection[] = Array.isArray(raw) ? raw : raw.items ?? [];
        setInspections(
          found
            ? all.filter(
                (ins) =>
                  ins.instrument_barcode === found!.barcode ||
                  ins.instrument_udi === found!.udi ||
                  ins.instrument_name === found!.internal_id
              )
            : all.slice(0, 10)
        );
      }

      if (baselineRes.status === "fulfilled" && baselineRes.value.ok) {
        const raw = await baselineRes.value.json();
        const all: Baseline[] = Array.isArray(raw) ? raw : raw.items ?? [];
        setBaselines(
          found?.instrument_type
            ? all.filter((b) => b.instrument_category === found!.instrument_type)
            : all.slice(0, 4)
        );
      }

      // Phase 14.8 — deterministic predictive intelligence. The endpoint keys off
      // the instrument's barcode/UDI; fall back to the raw URL param.
      const trendKey = found?.barcode || found?.udi || identifier;
      setPrediction(null);
      try {
        const predRes = await fetch(
          `${API_BASE}/api/instruments/${encodeURIComponent(trendKey)}/timeline`,
          { headers: hdrs }
        );
        if (predRes.ok) {
          const data: TimelineResponse = await predRes.json();
          setPrediction(data.prediction ?? null);
        }
      } catch {
        /* non-fatal — prediction card simply hides */
      }
    } catch {
      setError("Failed to load passport data.");
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => {
    if (instrumentParam) fetchPassport(instrumentParam);
  }, [instrumentParam, fetchPassport]);

  if (!instrumentParam) return <EmptyPassport />;

  const latestScore = inspections[0]?.risk_score ?? 0;
  const prevScore = inspections[1]?.risk_score ?? 0;
  const trend = latestScore > prevScore ? "up" : latestScore < prevScore ? "down" : "neutral";

  const findingCounts: Record<string, number> = {};
  inspections.forEach((ins) => {
    if (ins.detected_issue && ins.detected_issue !== "none") {
      findingCounts[ins.detected_issue] = (findingCounts[ins.detected_issue] ?? 0) + 1;
    }
  });

  const approvedBaseline = baselines.find((b) => b.status === "approved");

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-600">
            <CreditCard className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900">Instrument Passport</h1>
              <Badge variant="secondary">V2</Badge>
            </div>
            <p className="text-sm text-slate-500">
              Lifecycle intelligence for{" "}
              <span className="font-medium text-slate-700">{instrumentParam}</span>
            </p>
          </div>
        </div>
        <button
          onClick={() => fetchPassport(instrumentParam)}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 shrink-0"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center gap-3 text-slate-400">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading passport…</span>
        </div>
      ) : error ? (
        <Card>
          <CardContent className="p-8 text-center">
            <AlertTriangle className="h-8 w-8 text-amber-400 mx-auto mb-3" />
            <p className="text-sm text-slate-600">{error}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left — Identity + Risk */}
          <div className="space-y-5">
            <Card>
              <CardHeader className="pb-2">
                <SectionTitle icon={CreditCard} title="Identity" />
              </CardHeader>
              <CardContent className="space-y-3 pt-0">
                {instrument ? (
                  <>
                    <Row label="Internal ID" value={instrument.internal_id ?? "—"} mono />
                    <Row label="Type" value={(instrument.instrument_type ?? "—").replace(/_/g, " ")} capitalize />
                    <Row label="Manufacturer" value={instrument.manufacturer ?? "—"} />
                    <Row label="Model" value={instrument.model ?? "—"} />
                    <Row label="Barcode" value={instrument.barcode ?? "—"} mono />
                    <Row label="UDI" value={instrument.udi ?? "—"} mono />
                    <Row label="KeyDot" value={instrument.keydot_id ?? "—"} mono />
                    <Row
                      label="Status"
                      value={
                        <Badge variant={instrument.status === "active" ? "success" : "secondary"} className="text-xs capitalize">
                          {instrument.status ?? "active"}
                        </Badge>
                      }
                    />
                  </>
                ) : (
                  <p className="text-xs text-slate-400 text-center py-3">
                    Instrument not found.{" "}
                    <Link to="/infrastructure" className="text-blue-600 hover:underline">Open Registry</Link>
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <SectionTitle icon={BarChart3} title="Risk Intelligence" />
              </CardHeader>
              <CardContent className="pt-0 space-y-4">
                <div className="text-center py-2">
                  <p className="text-xs text-slate-500 mb-1">Current Risk Score</p>
                  <div className="flex items-center justify-center gap-2">
                    <span className={`text-4xl font-black tabular-nums ${latestScore >= 80 ? "text-red-600" : latestScore >= 60 ? "text-amber-600" : "text-emerald-600"}`}>
                      {latestScore}
                    </span>
                    <span className="text-slate-400">/ 100</span>
                  </div>
                  <div className="mt-2">
                    <Badge variant={riskVariant(latestScore)} className="text-xs">{riskLabel(latestScore)}</Badge>
                  </div>
                </div>
                {inspections.length > 1 && (
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 justify-center">
                    {trend === "up" ? <TrendingUp className="h-3.5 w-3.5 text-red-500" /> : trend === "down" ? <TrendingDown className="h-3.5 w-3.5 text-emerald-500" /> : null}
                    {trend === "up" ? `↑ from ${prevScore}` : trend === "down" ? `↓ from ${prevScore}` : "No change"}
                  </div>
                )}
                <div className="text-xs text-slate-500 space-y-1 pt-1 border-t border-slate-100">
                  <p className="font-medium text-slate-600">Recommended Actions</p>
                  {latestScore >= 80 && <p>• Quarantine pending clinical review</p>}
                  {latestScore >= 60 && latestScore < 80 && <p>• Schedule detailed inspection within 24h</p>}
                  {latestScore > 0 && latestScore < 60 && <p>• Continue standard inspection cycle</p>}
                  {latestScore === 0 && <p>• No inspections on record — submit baseline</p>}
                  {!approvedBaseline && <p>• Submit approved baseline to improve accuracy</p>}
                </div>
                <p className="text-xs text-slate-400 border-t border-slate-100 pt-2">
                  AI-assisted scores. Human review required before clinical action.
                </p>
              </CardContent>
            </Card>

            {prediction && (
              <Card>
                <CardHeader className="pb-2">
                  <SectionTitle icon={LineChart} title="Predictive Intelligence" />
                </CardHeader>
                <CardContent className="pt-0 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-500">Risk trend</span>
                    {(() => {
                      const meta = TREND_META[prediction.risk_trend];
                      const Icon = meta.icon;
                      return (
                        <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${meta.color}`}>
                          <Icon className="h-3 w-3" />
                          {meta.label}
                        </span>
                      );
                    })()}
                  </div>

                  {prediction.latest_risk_score != null && (
                    <Row label="Latest risk score" value={`${prediction.latest_risk_score} / 100`} />
                  )}

                  <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2">
                    <p className="text-xs font-medium text-slate-600 mb-0.5">Estimated remaining life</p>
                    <p className="text-xs text-slate-500">
                      {prediction.estimated_remaining_life ?? "No clear worsening trend — no projection offered."}
                    </p>
                  </div>

                  <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2">
                    <p className="text-xs font-medium text-slate-600 mb-0.5">Replacement planning</p>
                    <p className="text-xs text-slate-500">{prediction.replacement_planning}</p>
                  </div>

                  <p className="text-xs text-slate-400 border-t border-slate-100 pt-2 italic">
                    {prediction.note}
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right — Images, Findings, Timeline, Baselines */}
          <div className="lg:col-span-2 space-y-5">
            <Card>
              <CardHeader className="pb-2">
                <SectionTitle icon={Image} title="Images" />
              </CardHeader>
              <CardContent className="pt-0">
                <div className="grid grid-cols-3 gap-3">
                  {["Baseline Image", "Inspection Image", "Borescope Image"].map((label) => (
                    <div key={label} className="aspect-video rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 flex flex-col items-center justify-center gap-1">
                      <Image className="h-5 w-5 text-slate-300" />
                      <span className="text-xs text-slate-400 text-center px-1">{label}</span>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2 mt-3">
                  <Link to="/baseline-image-upload" className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                    Upload Baseline <ExternalLink className="h-3 w-3" />
                  </Link>
                  <span className="text-slate-300">·</span>
                  <Link to="/inspection-image-upload" className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                    Upload Inspection <ExternalLink className="h-3 w-3" />
                  </Link>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <SectionTitle icon={ShieldAlert} title="Findings Summary" />
              </CardHeader>
              <CardContent className="pt-0">
                {Object.keys(findingCounts).length === 0 ? (
                  <div className="flex items-center gap-2 py-3">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    <span className="text-sm text-slate-500">No contamination findings on record.</span>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(findingCounts).map(([issue, count]) => {
                      const meta = FINDING_META[issue] ?? { label: issue, color: "text-slate-500 bg-slate-50 border-slate-200", icon: AlertTriangle };
                      const Icon = meta.icon;
                      return (
                        <span key={issue} className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${meta.color}`}>
                          <Icon className="h-3 w-3" />
                          {meta.label} <span className="font-bold">×{count}</span>
                        </span>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <SectionTitle icon={History} title="Inspection Timeline" />
                  <Link to="/intake-history" className="text-xs text-blue-600 hover:underline flex items-center gap-1 mb-4">
                    View all <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                {inspections.length === 0 ? (
                  <div className="flex flex-col items-center py-6 text-center gap-2">
                    <History className="h-6 w-6 text-slate-300" />
                    <p className="text-xs text-slate-400">No inspections on record.</p>
                    <Link to="/inspection/new" className="text-xs text-blue-600 hover:underline">Submit first inspection →</Link>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {inspections.slice(0, 8).map((ins) => (
                      <div key={ins.id} className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white border border-slate-200">
                          {(ins.risk_score ?? 0) >= 80
                            ? <ShieldAlert className="h-3.5 w-3.5 text-red-500" />
                            : <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <FindingBadge issue={ins.detected_issue} />
                            {(ins.risk_score ?? 0) > 0 && (
                              <Badge variant={riskVariant(ins.risk_score!)} className="text-xs">{ins.risk_score}</Badge>
                            )}
                          </div>
                          <p className="text-xs text-slate-400 mt-0.5">{formatDate(ins.created_at)}</p>
                        </div>
                        <Badge variant={ins.status === "closed" ? "success" : ins.status === "flagged" ? "destructive" : "secondary"} className="text-xs capitalize shrink-0">
                          {ins.status ?? "pending"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <SectionTitle icon={ClipboardList} title="Baseline History" />
              </CardHeader>
              <CardContent className="pt-0">
                {baselines.length === 0 ? (
                  <div className="flex items-center gap-2 py-3">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    <span className="text-sm text-slate-500">No baselines for this instrument type.</span>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {baselines.slice(0, 4).map((bl) => (
                      <div key={bl.id} className="flex items-center gap-3 text-sm">
                        <Badge variant={bl.status === "approved" ? "success" : bl.status === "rejected" ? "destructive" : "secondary"} className="text-xs capitalize shrink-0">
                          {bl.status ?? "pending"}
                        </Badge>
                        <span className="text-slate-600 capitalize">{(bl.instrument_category ?? "—").replace(/_/g, " ")}</span>
                        <span className="text-xs text-slate-400 ml-auto shrink-0">{formatDate(bl.created_at)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      <p className="text-center text-xs text-slate-400 pb-4">
        All AI outputs require qualified human review before clinical action.
        LumenAI makes no claim of FDA clearance or regulatory approval.
      </p>
    </div>
  );
}
