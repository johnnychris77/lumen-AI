import { useCallback, useEffect, useId, useRef, useState } from "react";
import { Camera, RefreshCw, X, Check, AlertTriangle, Video } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * BorescopeCapturePanel — reusable *live* image-acquisition source.
 *
 * This is the borescope treated as a **camera/image source**, not a workflow.
 * It runs entirely in the browser via the standard MediaDevices/getUserMedia
 * web APIs, so any UVC-class device (the Healthmark borescope, a USB video
 * grabber, a laptop webcam, an external camera) appears as a selectable video
 * input. It does NOT talk to the backend and it does NOT own any record — it
 * only hands captured frames (as JPEG `File`s) back to the active workflow via
 * `onAttach`, so the workflow's existing, governed upload pipeline stays the
 * single source of truth.
 *
 * Device edge cases handled with plain-language messages (never raw JS errors):
 * permission denied, no device found, device disconnected/unreadable
 * (already in use), over-constrained selection, and browsers without camera
 * support.
 */

export type BorescopeEvent =
  | "borescope_capture_started"
  | "borescope_capture_completed"
  | "camera_permission_denied"
  | "camera_unavailable";

// Frames captured live carry this filename prefix so downstream code and
// metadata can distinguish a borescope capture from an uploaded file without a
// separate side-channel. Keep in sync with `imageAcquisitionSource`.
export const BORESCOPE_FILENAME_PREFIX = "borescope-capture";

interface BorescopeCapturePanelProps {
  /** Called with the confirmed captured frame(s). Parent owns the upload. */
  onAttach: (files: File[]) => void;
  /** Optional — dismiss the live panel without attaching. */
  onCancel?: () => void;
  /** Read-only / disabled state (e.g. viewer role). */
  disabled?: boolean;
  /** Optional telemetry hook. Never receives image data or PHI. */
  onEvent?: (name: BorescopeEvent, detail?: string) => void;
  className?: string;
}

type CamErrorKind = "" | "permission" | "not_found" | "in_use" | "unsupported" | "generic";

const CAM_ERROR_MESSAGE: Record<Exclude<CamErrorKind, "">, string> = {
  permission: "Camera access is required to capture from the borescope. Allow camera access in your browser, then retry.",
  not_found: "No compatible camera source was detected. Connect the borescope (or a UVC video grabber) and retry — or upload an existing image instead.",
  in_use: "The camera source is already in use by another application. Close the other app, then retry.",
  unsupported: "This browser or device does not support live camera capture. Upload an existing image instead.",
  generic: "The camera could not be started. Retry, or upload an existing image instead.",
};

function classifyCamError(e: unknown): CamErrorKind {
  if (!(e instanceof Error)) return "generic";
  switch (e.name) {
    case "NotAllowedError":
    case "SecurityError":
      return "permission";
    case "NotFoundError":
    case "OverconstrainedError":
    case "DevicesNotFoundError":
      return "not_found";
    case "NotReadableError":
    case "TrackStartError":
      return "in_use";
    default:
      return "generic";
  }
}

export function BorescopeCapturePanel({
  onAttach,
  onCancel,
  disabled,
  onEvent,
  className,
}: BorescopeCapturePanelProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState<string>("");
  const [camError, setCamError] = useState<CamErrorKind>("");
  const [ready, setReady] = useState(false);
  const [captured, setCaptured] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const statusId = useId();

  const stopStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  const startStream = useCallback(
    async (id?: string) => {
      setCamError("");
      setReady(false);
      // Browsers without the MediaDevices API (older/embedded webviews) — fail
      // clearly rather than throwing an uncaught TypeError.
      if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
        setCamError("unsupported");
        onEvent?.("camera_unavailable", "mediaDevices_unavailable");
        return;
      }
      try {
        stopStream();
        const stream = await navigator.mediaDevices.getUserMedia({
          video: id ? { deviceId: { exact: id } } : true,
          audio: false,
        });
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
        setReady(true);
        onEvent?.("borescope_capture_started");
        // Device labels only populate after permission is granted.
        const all = await navigator.mediaDevices.enumerateDevices();
        setDevices(all.filter((d) => d.kind === "videoinput"));
      } catch (e) {
        const kind = classifyCamError(e);
        setCamError(kind);
        onEvent?.(kind === "permission" ? "camera_permission_denied" : "camera_unavailable", (e as Error)?.name);
      }
    },
    [onEvent, stopStream],
  );

  useEffect(() => {
    if (!disabled) startStream();
    return () => {
      stopStream();
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function switchDevice(id: string) {
    setDeviceId(id);
    startStream(id);
  }

  function capture() {
    const video = videoRef.current;
    if (!video || !video.videoWidth) {
      setCamError("generic");
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        setCaptured(blob);
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        setPreviewUrl(URL.createObjectURL(blob));
      },
      "image/jpeg",
      0.92,
    );
  }

  function recapture() {
    setCaptured(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl("");
  }

  function attach() {
    if (!captured) return;
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const file = new File([captured], `${BORESCOPE_FILENAME_PREFIX}-${stamp}.jpg`, {
      type: "image/jpeg",
      lastModified: Date.now(),
    });
    onEvent?.("borescope_capture_completed");
    onAttach([file]);
    recapture();
  }

  function cancel() {
    stopStream();
    recapture();
    onCancel?.();
  }

  return (
    <div
      className={cn("rounded-lg border border-slate-200 bg-white p-3 space-y-3", className)}
      role="group"
      aria-label="Borescope live capture"
    >
      {/* Device selector — only when more than one video input is available. */}
      {devices.length > 1 && !camError && (
        <div>
          <label htmlFor={`${statusId}-device`} className="block text-xs font-medium text-slate-500 mb-1">
            Camera source
          </label>
          <select
            id={`${statusId}-device`}
            value={deviceId}
            onChange={(e) => switchDevice(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Default camera</option>
            {devices.map((d, i) => (
              <option key={d.deviceId || i} value={d.deviceId}>
                {d.label || `Camera ${i + 1}`}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Live status region for assistive tech. */}
      <p id={statusId} className="sr-only" aria-live="polite">
        {camError
          ? CAM_ERROR_MESSAGE[camError]
          : captured
            ? "Frame captured. Review it, then attach or recapture."
            : ready
              ? "Live borescope preview is running. Ready to capture."
              : "Starting camera…"}
      </p>

      {camError ? (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900" role="alert">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" aria-hidden="true" />
            <p>{CAM_ERROR_MESSAGE[camError]}</p>
          </div>
          {camError !== "unsupported" && (
            <button
              type="button"
              onClick={() => startStream(deviceId)}
              className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-amber-400 bg-white px-3 py-1.5 text-xs font-semibold text-amber-800 hover:bg-amber-100"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> Retry camera
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Live preview */}
          <div className="rounded-lg border border-slate-200 bg-black overflow-hidden">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              aria-label="Live borescope preview"
              className="w-full aspect-video object-contain"
            />
          </div>
          {/* Captured frame */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 overflow-hidden flex items-center justify-center min-h-[8rem]">
            {previewUrl ? (
              <img src={previewUrl} alt="Captured borescope frame" className="w-full aspect-video object-contain" />
            ) : (
              <span className="flex items-center gap-1.5 text-sm text-slate-400">
                <Video className="h-4 w-4" aria-hidden="true" /> Captured frame will appear here
              </span>
            )}
          </div>
        </div>
      )}

      {/* Controls — large touch targets, reachable on mobile. */}
      {!camError && (
        <div className="flex flex-wrap gap-2">
          {!captured ? (
            <button
              type="button"
              onClick={capture}
              disabled={!ready || disabled}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Camera className="h-4 w-4" aria-hidden="true" /> Capture frame
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={attach}
                disabled={disabled}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                <Check className="h-4 w-4" aria-hidden="true" /> Attach image
              </button>
              <button
                type="button"
                onClick={recapture}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <RefreshCw className="h-4 w-4" aria-hidden="true" /> Recapture
              </button>
            </>
          )}
          {onCancel && (
            <button
              type="button"
              onClick={cancel}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
            >
              <X className="h-4 w-4" aria-hidden="true" /> Cancel
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default BorescopeCapturePanel;
