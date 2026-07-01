import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, API_BASE } from "@/lib/auth";

/**
 * Direct borescope capture — live UVC/webcam preview → capture frame → analyze.
 *
 * Runs entirely in the browser on hospital-managed hardware (tablet/PC with a
 * UVC video grabber attached to the borescope). No native install, no USB
 * drive: the captured frame is uploaded straight into the inspection pipeline.
 */
type CaptureResult = {
  inspection_score: number | null;
  risk_level: string | null;
  recommended_action?: string;
  overall_cleaning_assessment?: string;
  baseline_source?: string | null;
};

const RISK_STYLE: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-800",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

export default function CapturePage() {
  const { headers, role } = useAuth();
  const navigate = useNavigate();
  const canRun = role === "operator" || role === "spd_manager" || role === "admin";

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState<string>("");
  const [camError, setCamError] = useState<string>("");
  const [captured, setCaptured] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>("");

  const [instrumentType, setInstrumentType] = useState("");
  const [facility, setFacility] = useState("");
  const [barcode, setBarcode] = useState("");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CaptureResult | null>(null);

  const startStream = useCallback(async (id?: string) => {
    setCamError("");
    try {
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
      const stream = await navigator.mediaDevices.getUserMedia({
        video: id ? { deviceId: { exact: id } } : true,
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      // Device labels are only populated after permission is granted.
      const all = await navigator.mediaDevices.enumerateDevices();
      setDevices(all.filter((d) => d.kind === "videoinput"));
    } catch (e) {
      setCamError(
        e instanceof Error && e.name === "NotAllowedError"
          ? "Camera access was blocked. Allow camera access to use the borescope feed."
          : "No camera/borescope feed found. Connect a UVC video grabber and reload.",
      );
    }
  }, []);

  useEffect(() => {
    if (canRun) startStream();
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    };
  }, [canRun, startStream]);

  function switchDevice(id: string) {
    setDeviceId(id);
    startStream(id);
  }

  function capture() {
    const video = videoRef.current;
    if (!video || !video.videoWidth) {
      setError("The video feed is not ready yet.");
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      setCaptured(blob);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(URL.createObjectURL(blob));
      setResult(null);
      setError("");
    }, "image/jpeg", 0.92);
  }

  async function analyze() {
    if (!captured) return;
    if (!instrumentType.trim()) {
      setError("Enter the instrument type before analyzing.");
      return;
    }
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const hdrs = headers();
      // 1. Upload the captured frame (also decodes identifiers).
      const fd = new FormData();
      fd.append("images", captured, "capture.jpg");
      const up = await fetch(
        `${API_BASE}/api/inspections/upload-images?instrument_type=${encodeURIComponent(instrumentType)}`,
        { method: "POST", headers: { Authorization: hdrs["Authorization"] }, body: fd },
      );
      if (up.status === 401) { navigate("/login", { replace: true }); return; }
      if (!up.ok) {
        const b = await up.json().catch(() => ({}));
        setError(b?.detail || `Upload failed (${up.status}).`);
        return;
      }
      const upData = await up.json();
      const img = upData?.images?.[0] || {};
      const sha = img.sha256;
      const decodedBarcode = img.barcode_value || "";
      const decodedUdi = img.qr_udi_value || "";

      // 2. Create the inspection (AI scores it against the baseline).
      const res = await fetch(`${API_BASE}/api/inspections`, {
        method: "POST",
        headers: hdrs,
        body: JSON.stringify({
          instrument_type: instrumentType,
          site_name: facility || "capture",
          facility_name: facility || undefined,
          has_image: true,
          image_sha256: sha,
          file_name: "capture.jpg",
          instrument_barcode: barcode || decodedBarcode || undefined,
          instrument_udi: decodedUdi || undefined,
          identifier_source: !barcode && (decodedBarcode || decodedUdi) ? "pyzbar" : "declared",
        }),
      });
      if (res.status === 401) { navigate("/login", { replace: true }); return; }
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        setError(b?.detail || `Analysis failed (${res.status}).`);
        return;
      }
      const data = await res.json();
      const a = data.analysis || {};
      setResult({
        inspection_score: a.inspection_score ?? (data.inspection_score ?? null),
        risk_level: a.risk_level ?? data.risk_level ?? null,
        recommended_action: a.recommended_action,
        overall_cleaning_assessment: a.overall_cleaning_assessment,
        baseline_source: a.baseline_source,
      });
    } catch {
      setError("Unable to reach the server. Check the connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  if (!canRun) {
    return (
      <div className="p-6">
        <h2 className="text-xl font-semibold text-slate-900">Borescope Capture</h2>
        <p className="mt-2 text-sm text-amber-700">
          Viewer access is read-only. Ask an admin for Operator or SPD Manager access to capture inspections.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5 p-1">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Borescope Capture</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Live capture from a connected borescope (UVC video grabber). Capture a frame and analyze it directly —
          no phone photos, no USB drive.
        </p>
      </div>

      {/* Camera / device selector */}
      {devices.length > 1 && (
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Capture source</label>
          <select
            value={deviceId}
            onChange={(e) => switchDevice(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Default camera</option>
            {devices.map((d) => (
              <option key={d.deviceId} value={d.deviceId}>{d.label || "Camera"}</option>
            ))}
          </select>
        </div>
      )}

      {camError ? (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
          {camError}
          <button onClick={() => startStream(deviceId)} className="ml-2 underline">Retry</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="rounded-lg border border-slate-200 bg-black overflow-hidden">
            <video ref={videoRef} autoPlay playsInline muted className="w-full aspect-video object-contain" />
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 overflow-hidden flex items-center justify-center">
            {previewUrl ? (
              <img src={previewUrl} alt="Captured frame" className="w-full aspect-video object-contain" />
            ) : (
              <span className="text-sm text-slate-400">Captured frame will appear here</span>
            )}
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          onClick={capture}
          disabled={!!camError}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Capture frame
        </button>
      </div>

      {/* Instrument context */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Instrument type *</label>
          <input value={instrumentType} onChange={(e) => setInstrumentType(e.target.value)}
            placeholder="e.g. rigid scope" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Facility</label>
          <input value={facility} onChange={(e) => setFacility(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Barcode / UDI (optional)</label>
          <input value={barcode} onChange={(e) => setBarcode(e.target.value)}
            placeholder="auto-decoded if blank" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        </div>
      </div>

      <button
        onClick={analyze}
        disabled={!captured || busy}
        className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
      >
        {busy ? "Analyzing…" : "Analyze captured frame"}
      </button>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {result && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700 mb-2">Analysis Complete</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div>
              <div className="text-xs text-slate-500">Inspection Score</div>
              <div className="text-2xl font-bold text-slate-900">{result.inspection_score ?? "—"}<span className="text-sm text-slate-400"> / 100</span></div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Risk Level</div>
              <span className={`mt-1 inline-flex items-center rounded-full px-2.5 py-1 text-sm font-bold capitalize ${RISK_STYLE[result.risk_level ?? ""] ?? "bg-slate-200 text-slate-700"}`}>
                {result.risk_level ?? "—"}
              </span>
            </div>
            <div>
              <div className="text-xs text-slate-500">Cleaning</div>
              <div className="text-sm font-medium text-slate-800">{result.overall_cleaning_assessment ?? "—"}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Baseline</div>
              <div className="text-sm font-medium text-slate-800 capitalize">{result.baseline_source ?? "—"}</div>
            </div>
          </div>
          {result.recommended_action && (
            <p className="mt-3 text-sm font-medium text-slate-900">{result.recommended_action}</p>
          )}
          <button onClick={() => navigate("/intake-history")} className="mt-3 text-sm text-blue-600 underline">
            View in Inspection History
          </button>
        </div>
      )}
    </div>
  );
}
