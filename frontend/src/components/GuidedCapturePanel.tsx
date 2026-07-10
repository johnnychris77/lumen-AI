import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

interface GuidedCaptureData {
  instrument_family: string;
  instrument_category: string;
  required_zones: string[];
  optional_zones: string[];
  captured_zones: string[];
  missing_zones: string[];
  high_risk_zones: string[];
  current_zone: string | null;
  risk_level: string | null;
  expected_findings: string[];
  recommended_camera_angle: string | null;
  lighting_tips: string | null;
  focus_tips: string | null;
  example_placeholder_guidance: string;
  all_required_captured: boolean;
  coverage_score: number | null;
  coverage_status: string;
  missing_high_risk_zones: string[];
  missing_image_guidance: string[];
  ready_for_ai_analysis: boolean;
  gate_status: "ready" | "draft" | "blocked_pending_override";
  require_full_coverage: boolean;
}

const STATUS_STYLE: Record<string, string> = {
  complete: "bg-emerald-100 text-emerald-800",
  acceptable: "bg-amber-100 text-amber-800",
  incomplete: "bg-orange-100 text-orange-800",
  insufficient: "bg-red-100 text-red-800",
  not_assessed: "bg-slate-100 text-slate-500",
};

const RISK_STYLE: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-slate-100 text-slate-600",
};

function ZoneChips({ zones, tone }: { zones: string[]; tone: "slate" | "emerald" | "red" | "amber" }) {
  const cls = {
    slate: "bg-slate-100 text-slate-700",
    emerald: "bg-emerald-50 text-emerald-700",
    red: "bg-red-50 text-red-700",
    amber: "bg-amber-50 text-amber-800",
  }[tone];
  if (zones.length === 0) return <span className="text-xs text-slate-400">none</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {zones.map((z) => (
        <span key={z} className={`rounded-full px-2 py-0.5 text-xs capitalize ${cls}`}>{z}</span>
      ))}
    </div>
  );
}

export default function GuidedCapturePanel({
  instrumentType,
  capturedZones,
}: {
  instrumentType: string;
  capturedZones: string[];
}) {
  const { headers } = useAuth();
  const [data, setData] = useState<GuidedCaptureData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!instrumentType.trim()) {
      setData(null);
      return;
    }
    const params = new URLSearchParams({ captured_zones: capturedZones.join(",") });
    let cancelled = false;
    fetch(`${API_BASE}/api/guided-capture/${encodeURIComponent(instrumentType)}?${params}`, { headers: headers() })
      .then((r) => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); })
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(String(e)); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instrumentType, capturedZones.join(",")]);

  if (!instrumentType.trim()) return null;
  if (error) return <p className="text-sm text-red-600">Guided capture unavailable: {error}</p>;
  if (!data) return <p className="text-sm text-slate-400">Loading guided capture guidance…</p>;

  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Guided Capture — <span className="capitalize">{data.instrument_family.replace(/_/g, " ")}</span>
        </p>
        <span className={`rounded-full px-2 py-0.5 text-xs font-bold capitalize ${STATUS_STYLE[data.coverage_status] ?? "bg-slate-100"}`}>
          {data.coverage_status.replace(/_/g, " ")}
        </span>
      </div>

      {/* Coverage score */}
      {data.coverage_score != null && (
        <div className="flex items-center gap-3">
          <div className="text-2xl font-bold text-slate-900">{data.coverage_score}%</div>
          <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
            <div
              className={`h-full ${data.coverage_score >= 80 ? "bg-emerald-500" : data.coverage_score >= 50 ? "bg-amber-500" : "bg-red-500"}`}
              style={{ width: `${data.coverage_score}%` }}
            />
          </div>
        </div>
      )}

      {/* Current zone to capture */}
      {data.current_zone ? (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 space-y-1">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-blue-900">
              Next: capture <span className="capitalize">{data.current_zone}</span>
            </p>
            {data.risk_level && (
              <span className={`rounded-full px-2 py-0.5 text-xs font-bold capitalize ${RISK_STYLE[data.risk_level] ?? "bg-slate-100"}`}>
                {data.risk_level} risk
              </span>
            )}
          </div>
          <p className="text-sm text-blue-800">{data.example_placeholder_guidance}</p>
          <div className="mt-1 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs text-blue-700">
            <div><span className="font-medium">Angle:</span> {data.recommended_camera_angle}</div>
            <div><span className="font-medium">Lighting:</span> {data.lighting_tips}</div>
            <div><span className="font-medium">Focus:</span> {data.focus_tips}</div>
          </div>
          {data.expected_findings?.length > 0 && (
            <div className="mt-1">
              <span className="text-xs font-medium text-blue-900">Expected findings at this zone: </span>
              <span className="text-xs text-blue-700 capitalize">{data.expected_findings.join(", ")}</span>
            </div>
          )}
        </div>
      ) : (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
          All required zones captured.
        </div>
      )}

      {/* Capture checklist */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-xs text-slate-500 mb-0.5">Required zones</div>
          <ZoneChips zones={data.required_zones} tone="slate" />
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-0.5">Optional zones</div>
          <ZoneChips zones={data.optional_zones} tone="slate" />
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-0.5">Captured</div>
          <ZoneChips zones={data.captured_zones} tone="emerald" />
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-0.5">Missing (required)</div>
          <ZoneChips zones={data.missing_zones} tone="red" />
        </div>
        <div className="sm:col-span-2">
          <div className="text-xs text-slate-500 mb-0.5">High-risk zones</div>
          <ZoneChips zones={data.high_risk_zones} tone="amber" />
        </div>
      </div>

      {/* AI Analysis Gate */}
      {!data.ready_for_ai_analysis && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          <p className="font-semibold">Coverage insufficient for a final AI decision.</p>
          <p className="text-xs mt-0.5">
            Org policy requires full coverage before a final decision. A supervisor/admin override with a reason
            will be required after submission, or save this inspection as a draft.
          </p>
        </div>
      )}
      {data.ready_for_ai_analysis && data.missing_high_risk_zones.length > 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
          Missing high-risk zones: <span className="capitalize">{data.missing_high_risk_zones.join(", ")}</span>. Upload
          additional images before finalizing when possible.
        </div>
      )}
    </div>
  );
}
