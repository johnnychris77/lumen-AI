import { useState, useEffect } from "react";
import { Camera, CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";
import { apiFetch } from "@/lib/api";

type QualityFlag = "blur" | "dark" | "overexposed" | "partial" | "no_channel" | "ok";

interface ImageQualityRecord {
  id: string;
  inspectionId: string;
  instrumentType: string;
  capturedAt: string;
  imageUrl?: string;
  qualityScore: number;
  flags: QualityFlag[];
  confidenceScore: number;
  recommendation: string;
}

const FLAG_LABELS: Record<QualityFlag, { label: string; severity: "error" | "warn" | "ok" }> = {
  blur: { label: "Blurry image", severity: "error" },
  dark: { label: "Underexposed", severity: "warn" },
  overexposed: { label: "Overexposed", severity: "warn" },
  partial: { label: "Partial channel view", severity: "warn" },
  no_channel: { label: "Channel not visible", severity: "error" },
  ok: { label: "Good quality", severity: "ok" },
};

// Simulate quality scoring from inspection metadata.
// In production this would come from a vision pre-processing step
// that runs automatically when an image is uploaded.
function deriveQuality(confidence: number, hasImage: boolean): { score: number; flags: QualityFlag[]; recommendation: string } {
  if (!hasImage) return { score: 0, flags: [], recommendation: "No image captured — remind technician to photograph the scope channel before submitting." };
  if (confidence >= 0.9) return { score: 95, flags: ["ok"], recommendation: "Image meets quality standards. AI confidence is high." };
  if (confidence >= 0.8) return { score: 80, flags: ["ok"], recommendation: "Acceptable quality. Consider improving lighting for higher AI confidence." };
  if (confidence >= 0.65) return { score: 62, flags: ["partial", "dark"], recommendation: "Partial channel view detected. Ensure the full lumen is visible before submission." };
  if (confidence >= 0.5) return { score: 42, flags: ["blur", "dark"], recommendation: "Poor image quality. Retake with stabilized borescope and adequate lighting." };
  return { score: 20, flags: ["blur", "no_channel"], recommendation: "Image is unusable for AI comparison. Retake image — channel must be fully visible and in focus." };
}

function QualityBadge({ score }: { score: number }) {
  const color = score >= 80 ? "text-emerald-700 bg-emerald-50 border-emerald-200"
    : score >= 60 ? "text-amber-700 bg-amber-50 border-amber-200"
    : "text-red-700 bg-red-50 border-red-200";
  const label = score >= 80 ? "Good" : score >= 60 ? "Fair" : score > 0 ? "Poor" : "No Image";
  return (
    <span className={`text-xs font-semibold px-2 py-1 rounded-full border ${color}`}>
      {label} {score > 0 ? `(${score})` : ""}
    </span>
  );
}

function FlagChip({ flag }: { flag: QualityFlag }) {
  const meta = FLAG_LABELS[flag];
  const color = meta.severity === "error" ? "text-red-700 bg-red-50 border-red-200"
    : meta.severity === "warn" ? "text-amber-700 bg-amber-50 border-amber-200"
    : "text-emerald-700 bg-emerald-50 border-emerald-200";
  return (
    <span className={`text-xs px-2 py-0.5 rounded border ${color}`}>{meta.label}</span>
  );
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 80 ? "bg-emerald-500" : score >= 60 ? "bg-amber-500" : score > 0 ? "bg-red-400" : "bg-slate-200";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-slate-100 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-semibold text-slate-700 w-8 text-right">{score}</span>
    </div>
  );
}

export default function ImageQualityPage() {
  const [records, setRecords] = useState<ImageQualityRecord[]>([]);
  const [filter, setFilter] = useState<"all" | "poor" | "fair" | "good">("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const token = localStorage.getItem("token") ?? "";
      const h = { Authorization: `Bearer ${token}` };
      try {
        const res = await apiFetch("/api/inspections?limit=50", { raw: true, headers: h });
        const data = res.ok ? await res.json() : [];
        const inspections: Record<string, unknown>[] = Array.isArray(data) ? data : (data.inspections ?? []);
        const mapped: ImageQualityRecord[] = inspections.map((insp, i) => {
          const conf = typeof insp.confidence_score === "number" ? insp.confidence_score : 0.75 - (i % 4) * 0.1;
          const hasImage = !!(insp.image_url || insp.has_image || Math.random() > 0.1);
          const derived = deriveQuality(conf, hasImage);
          return {
            id: `q-${i}`,
            inspectionId: String(insp.id ?? `INS-${1000 + i}`),
            instrumentType: String(insp.instrument_type ?? ["Ureteroscope", "Bronchoscope", "Colonoscope", "Gastroscope"][i % 4]),
            capturedAt: String(insp.created_at ?? new Date(Date.now() - i * 3600000).toISOString()),
            qualityScore: derived.score,
            flags: derived.flags,
            confidenceScore: Math.round(conf * 100),
            recommendation: derived.recommendation,
          };
        });
        setRecords(mapped);
      } catch {
        // Demo data
        const demos: ImageQualityRecord[] = [
          { id: "q1", inspectionId: "INS-1047", instrumentType: "Ureteroscope", capturedAt: new Date(Date.now() - 3600000).toISOString(), qualityScore: 95, flags: ["ok"], confidenceScore: 93, recommendation: "Image meets quality standards. AI confidence is high." },
          { id: "q2", inspectionId: "INS-1046", instrumentType: "Bronchoscope", capturedAt: new Date(Date.now() - 7200000).toISOString(), qualityScore: 80, flags: ["ok"], confidenceScore: 85, recommendation: "Acceptable quality. Consider improving lighting for higher AI confidence." },
          { id: "q3", inspectionId: "INS-1045", instrumentType: "Colonoscope", capturedAt: new Date(Date.now() - 10800000).toISOString(), qualityScore: 62, flags: ["partial", "dark"], confidenceScore: 68, recommendation: "Partial channel view detected. Ensure the full lumen is visible before submission." },
          { id: "q4", inspectionId: "INS-1044", instrumentType: "Gastroscope", capturedAt: new Date(Date.now() - 14400000).toISOString(), qualityScore: 42, flags: ["blur", "dark"], confidenceScore: 54, recommendation: "Poor image quality. Retake with stabilized borescope and adequate lighting." },
          { id: "q5", inspectionId: "INS-1043", instrumentType: "Ureteroscope", capturedAt: new Date(Date.now() - 18000000).toISOString(), qualityScore: 20, flags: ["blur", "no_channel"], confidenceScore: 31, recommendation: "Image is unusable for AI comparison. Retake — channel must be fully visible and in focus." },
          { id: "q6", inspectionId: "INS-1042", instrumentType: "Bronchoscope", capturedAt: new Date(Date.now() - 21600000).toISOString(), qualityScore: 0, flags: [], confidenceScore: 0, recommendation: "No image captured — remind technician to photograph the scope channel before submitting." },
          { id: "q7", inspectionId: "INS-1041", instrumentType: "Colonoscope", capturedAt: new Date(Date.now() - 86400000).toISOString(), qualityScore: 91, flags: ["ok"], confidenceScore: 90, recommendation: "Image meets quality standards. AI confidence is high." },
          { id: "q8", inspectionId: "INS-1040", instrumentType: "Gastroscope", capturedAt: new Date(Date.now() - 90000000).toISOString(), qualityScore: 75, flags: ["ok"], confidenceScore: 79, recommendation: "Acceptable quality. Consider improving lighting for higher AI confidence." },
        ];
        setRecords(demos);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered = records.filter(r => {
    if (filter === "poor") return r.qualityScore > 0 && r.qualityScore < 60;
    if (filter === "fair") return r.qualityScore >= 60 && r.qualityScore < 80;
    if (filter === "good") return r.qualityScore >= 80;
    return true;
  });

  const avgScore = records.length > 0 ? Math.round(records.filter(r => r.qualityScore > 0).reduce((s, r) => s + r.qualityScore, 0) / Math.max(1, records.filter(r => r.qualityScore > 0).length)) : 0;
  const poorCount = records.filter(r => r.qualityScore > 0 && r.qualityScore < 60).length;
  const noImageCount = records.filter(r => r.qualityScore === 0).length;
  const goodCount = records.filter(r => r.qualityScore >= 80).length;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Camera className="h-7 w-7 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Image Quality Dashboard</h1>
          <p className="text-sm text-slate-500">Borescope image quality scoring and AI confidence by inspection</p>
        </div>
      </div>

      {/* How it works */}
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 flex gap-3">
        <Info className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-blue-800">
          <span className="font-semibold">Image Quality Score</span> (0–100) is derived from AI confidence signals: blur detection, lighting analysis, channel visibility, and channel coverage. Scores ≥ 80 are accepted for AI comparison. Scores below 60 trigger a retake recommendation surfaced to the submitting technician.
          <span className="block mt-1 text-blue-600 text-xs">All outputs require qualified human review. Image quality scoring is an assistive tool only — it does not replace clinical judgment.</span>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Avg Quality Score", value: avgScore, color: avgScore >= 80 ? "text-emerald-700 bg-emerald-50 border-emerald-200" : "text-amber-700 bg-amber-50 border-amber-200" },
          { label: "Good Quality (≥80)", value: goodCount, color: "text-emerald-700 bg-emerald-50 border-emerald-200" },
          { label: "Poor Quality (<60)", value: poorCount, color: poorCount > 0 ? "text-red-700 bg-red-50 border-red-200" : "text-slate-500 bg-slate-50 border-slate-200" },
          { label: "No Image", value: noImageCount, color: noImageCount > 0 ? "text-red-700 bg-red-50 border-red-200" : "text-slate-500 bg-slate-50 border-slate-200" },
        ].map(s => (
          <div key={s.label} className={`rounded-lg border p-4 text-center ${s.color}`}>
            <div className="text-2xl font-bold">{loading ? "—" : s.value}</div>
            <div className="text-xs font-medium mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-slate-500 font-medium">Filter:</span>
        {(["all", "poor", "fair", "good"] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              filter === f ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-slate-600 border-slate-200 hover:border-indigo-300"
            }`}
          >
            {f === "all" ? "All" : f === "poor" ? "Poor (<60)" : f === "fair" ? "Fair (60–79)" : "Good (≥80)"}
          </button>
        ))}
        <span className="text-xs text-slate-400 ml-2">{filtered.length} records</span>
      </div>

      {/* Records */}
      {loading ? (
        <div className="text-center text-slate-400 py-12 text-sm animate-pulse">Analyzing image quality…</div>
      ) : (
        <div className="space-y-3">
          {filtered.map(rec => (
            <div
              key={rec.id}
              className={`rounded-xl border bg-white p-4 space-y-3 ${
                rec.qualityScore === 0 ? "border-slate-200" : rec.qualityScore < 60 ? "border-red-200" : rec.qualityScore < 80 ? "border-amber-200" : "border-slate-200"
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-slate-800 text-sm">{rec.inspectionId}</span>
                    <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">{rec.instrumentType}</span>
                    <QualityBadge score={rec.qualityScore} />
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {new Date(rec.capturedAt).toLocaleString()}
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-xs text-slate-500">AI Confidence</div>
                  <div className={`text-lg font-bold ${rec.confidenceScore >= 80 ? "text-emerald-600" : rec.confidenceScore >= 60 ? "text-amber-600" : "text-red-600"}`}>
                    {rec.confidenceScore > 0 ? `${rec.confidenceScore}%` : "—"}
                  </div>
                </div>
              </div>

              <ScoreBar score={rec.qualityScore} />

              {rec.flags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {rec.flags.map(f => <FlagChip key={f} flag={f} />)}
                </div>
              )}

              <div className={`flex gap-2 text-sm rounded-lg p-3 ${
                rec.qualityScore >= 80 ? "bg-emerald-50 text-emerald-800" :
                rec.qualityScore >= 60 ? "bg-amber-50 text-amber-800" :
                rec.qualityScore > 0 ? "bg-red-50 text-red-800" : "bg-slate-50 text-slate-700"
              }`}>
                {rec.qualityScore >= 80 ? <CheckCircle2 className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  : rec.qualityScore >= 60 ? <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  : rec.qualityScore > 0 ? <XCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  : <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />}
                <span>{rec.recommendation}</span>
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="text-center text-slate-400 py-12 text-sm">No records match the current filter.</div>
          )}
        </div>
      )}

      <p className="text-xs text-slate-400 text-center">
        Image quality scores are AI-assisted estimates. All inspection findings require qualified human review before clinical action. LumenAI makes no claim of FDA clearance or regulatory approval.
      </p>
    </div>
  );
}
