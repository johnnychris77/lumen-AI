import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/auth";

/**
 * Shared borescope station — KIOSK mode.
 *
 * Runs on a small tablet/mini-PC at a shared, standalone borescope station with
 * a UVC video grabber on the scope's video-out. Authenticated as a registered
 * capture DEVICE (device key), not a personal login, so it is always ready.
 *
 * Flow (scan-first, hands-light, auto-reset for the next tech):
 *   scan instrument barcode → capture the live frame → analyze against the
 *   baseline → show a big glanceable PASS / SUPERVISOR REVIEW / REPROCESS
 *   verdict → auto-reset. Optional tech badge/PIN attributes the capture.
 *
 * Full-screen and outside the app shell — no sidebar, no per-capture login.
 */
const DEVICE_KEY_STORAGE = "lumenai_station_device_key";
const STATION_TYPE_STORAGE = "lumenai_station_instrument_type";

type Verdict = "PASS" | "MONITOR" | "SUPERVISOR REVIEW" | "REPROCESS" | "UNKNOWN";

function verdictFrom(risk: string | null | undefined, action: string | undefined): Verdict {
  const a = (action || "").toLowerCase();
  if (a.includes("reprocess") || a.includes("remove from service")) return "REPROCESS";
  if (a.includes("supervisor review")) return "SUPERVISOR REVIEW";
  if (a.startsWith("monitor")) return "MONITOR";
  if (risk === "low" || a.startsWith("pass")) return "PASS";
  if (risk === "critical" || risk === "high") return "SUPERVISOR REVIEW";
  if (risk === "medium") return "MONITOR";
  return "UNKNOWN";
}

const VERDICT_STYLE: Record<Verdict, string> = {
  PASS: "bg-emerald-600",
  MONITOR: "bg-amber-500",
  "SUPERVISOR REVIEW": "bg-orange-600",
  REPROCESS: "bg-red-600",
  UNKNOWN: "bg-slate-600",
};

export default function StationPage() {
  const [deviceKey, setDeviceKey] = useState<string>(() => localStorage.getItem(DEVICE_KEY_STORAGE) || "");
  const [keyInput, setKeyInput] = useState("");
  const [instrumentType, setInstrumentType] = useState<string>(() => localStorage.getItem(STATION_TYPE_STORAGE) || "");
  const [techId, setTechId] = useState("");

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const scanRef = useRef<HTMLInputElement | null>(null);
  const [camError, setCamError] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [result, setResult] = useState<{ verdict: Verdict; score: number | null; risk: string | null; action?: string; cleaning?: string } | null>(null);

  // ── Camera ────────────────────────────────────────────────────────────────
  const startStream = useCallback(async () => {
    setCamError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
    } catch {
      setCamError("No borescope feed found. Connect the UVC video grabber and reload.");
    }
  }, []);

  useEffect(() => {
    if (deviceKey) startStream();
    return () => { if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop()); };
  }, [deviceKey, startStream]);

  // Keep the scan field focused so a barcode gun always lands there.
  const focusScan = useCallback(() => { scanRef.current?.focus(); }, []);
  useEffect(() => {
    if (!deviceKey) return;
    focusScan();
    const iv = window.setInterval(focusScan, 1500);
    return () => window.clearInterval(iv);
  }, [deviceKey, focusScan, result, busy]);

  function captureBlob(): Promise<Blob | null> {
    return new Promise((resolve) => {
      const video = videoRef.current;
      if (!video || !video.videoWidth) return resolve(null);
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return resolve(null);
      ctx.drawImage(video, 0, 0);
      canvas.toBlob((b) => resolve(b), "image/jpeg", 0.92);
    });
  }

  async function handleScan(barcode: string) {
    const code = barcode.trim();
    if (!code || busy) return;
    if (!instrumentType.trim()) {
      setStatus("Set the instrument type for this station first (Station setup).");
      return;
    }
    setBusy(true);
    setResult(null);
    setStatus("Capturing…");
    try {
      const blob = await captureBlob();
      if (!blob) { setStatus("Video feed not ready — try again."); return; }
      setStatus("Analyzing…");
      const fd = new FormData();
      fd.append("image", blob, "capture.jpg");
      fd.append("instrument_type", instrumentType.trim());
      fd.append("instrument_barcode", code);
      if (techId.trim()) fd.append("captured_by", techId.trim());
      const res = await fetch(`${API_BASE}/api/capture/ingest`, {
        method: "POST",
        headers: { "X-Device-Key": deviceKey },
        body: fd,
      });
      if (res.status === 401) {
        setStatus("This station's device key is invalid or revoked. Re-enter it in Station setup.");
        localStorage.removeItem(DEVICE_KEY_STORAGE);
        setDeviceKey("");
        return;
      }
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        setStatus(b?.detail || `Analysis failed (${res.status}).`);
        return;
      }
      const data = await res.json();
      const a = data.analysis || {};
      const verdict = verdictFrom(a.risk_level, a.recommended_action);
      setResult({
        verdict,
        score: a.inspection_score ?? null,
        risk: a.risk_level ?? null,
        action: a.recommended_action,
        cleaning: a.overall_cleaning_assessment,
      });
      setStatus("");
      // Auto-reset for the next tech.
      window.setTimeout(() => { setResult(null); setStatus(""); focusScan(); }, 9000);
    } catch {
      setStatus("Unable to reach the server. Check the connection.");
    } finally {
      setBusy(false);
    }
  }

  // ── Setup screen (no device key yet) ────────────────────────────────────────
  if (!deviceKey) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white p-8">
        <div className="w-full max-w-md space-y-4">
          <h1 className="text-2xl font-bold">Borescope Station Setup</h1>
          <p className="text-sm text-slate-300">
            Enter this station's device key (issued once by an admin under Capture Devices).
            It is stored on this device only.
          </p>
          <input
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder="Device key"
            className="w-full rounded-lg px-3 py-2 text-slate-900"
          />
          <input
            value={instrumentType}
            onChange={(e) => setInstrumentType(e.target.value)}
            placeholder="Default instrument type (e.g. rigid scope)"
            className="w-full rounded-lg px-3 py-2 text-slate-900"
          />
          <button
            onClick={() => {
              if (!keyInput.trim()) return;
              localStorage.setItem(DEVICE_KEY_STORAGE, keyInput.trim());
              localStorage.setItem(STATION_TYPE_STORAGE, instrumentType.trim());
              setDeviceKey(keyInput.trim());
            }}
            className="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold hover:bg-blue-700"
          >
            Start station
          </button>
        </div>
      </div>
    );
  }

  // ── Kiosk ───────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col">
      <div className="flex items-center justify-between px-6 py-3 border-b border-slate-700">
        <div className="font-bold text-lg">LumenAI · Borescope Station</div>
        <div className="text-xs text-slate-400">
          {instrumentType || "no type set"} ·{" "}
          <button
            className="underline"
            onClick={() => {
              const t = window.prompt("Station instrument type", instrumentType) ?? instrumentType;
              setInstrumentType(t);
              localStorage.setItem(STATION_TYPE_STORAGE, t.trim());
            }}
          >
            change
          </button>
          {" · "}
          <button className="underline" onClick={() => { localStorage.removeItem(DEVICE_KEY_STORAGE); setDeviceKey(""); }}>
            setup
          </button>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 p-4">
        {/* Live feed */}
        <div className="rounded-xl border border-slate-700 bg-black overflow-hidden flex items-center justify-center">
          {camError ? (
            <div className="p-6 text-center text-amber-300">
              {camError}
              <button onClick={startStream} className="ml-2 underline">Retry</button>
            </div>
          ) : (
            <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-contain" />
          )}
        </div>

        {/* Verdict / prompt */}
        <div className="rounded-xl border border-slate-700 bg-slate-800 flex flex-col items-center justify-center p-6 text-center">
          {result ? (
            <>
              <div className={`w-full rounded-xl py-8 text-4xl font-extrabold tracking-wide ${VERDICT_STYLE[result.verdict]}`}>
                {result.verdict}
              </div>
              <div className="mt-6 grid grid-cols-3 gap-6 w-full">
                <div><div className="text-xs text-slate-400">Score</div><div className="text-3xl font-bold">{result.score ?? "—"}</div></div>
                <div><div className="text-xs text-slate-400">Risk</div><div className="text-2xl font-bold capitalize">{result.risk ?? "—"}</div></div>
                <div><div className="text-xs text-slate-400">Cleaning</div><div className="text-sm font-medium">{result.cleaning ?? "—"}</div></div>
              </div>
              {result.action && <p className="mt-5 text-base text-slate-200">{result.action}</p>}
              <button onClick={() => { setResult(null); focusScan(); }} className="mt-6 text-sm text-blue-300 underline">
                Next instrument
              </button>
            </>
          ) : (
            <>
              <div className="text-2xl font-semibold text-slate-200">
                {busy ? (status || "Working…") : "Scan the instrument barcode to inspect"}
              </div>
              <p className="mt-2 text-sm text-slate-400">{status && !busy ? status : "Position the lumen in the borescope, then scan."}</p>
            </>
          )}

          {/* Hidden-ish scan field: a barcode gun types here + Enter. */}
          <input
            ref={scanRef}
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const v = (e.target as HTMLInputElement).value;
                (e.target as HTMLInputElement).value = "";
                handleScan(v);
              }
            }}
            placeholder="Barcode"
            className="mt-8 w-2/3 rounded-lg px-3 py-2 text-slate-900 text-center"
          />
          <input
            value={techId}
            onChange={(e) => setTechId(e.target.value)}
            placeholder="Tech badge / ID (optional)"
            className="mt-3 w-1/2 rounded-lg px-3 py-1.5 text-slate-900 text-center text-sm"
          />
        </div>
      </div>
    </div>
  );
}
