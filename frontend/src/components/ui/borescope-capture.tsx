import { useCallback, useEffect, useId, useRef, useState } from "react";
import { Camera, RefreshCw, X, Check, AlertTriangle, Video, Lightbulb, ZoomIn } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  type CamErrorKind,
  type OptionalControlSupport,
  type VideoInput,
  type ImageAcquisitionResult,
  BORESCOPE_FILENAME_PREFIX,
  captureFilename,
  buildAcquisitionResult,
  resolvePreferredDevice,
} from "@/lib/imageAcquisition";
import { MediaDevicesAdapter, loadDevicePreference, saveDevicePreference } from "@/lib/borescopeAdapter";

/**
 * BorescopeCapturePanel — reusable, **vendor-neutral** live image source.
 *
 * The borescope is treated as a camera/image source, not a workflow. This panel
 * discovers video inputs through the standard MediaDevices web APIs (via the
 * default `MediaDevicesAdapter`), so any device that presents as a camera — a
 * Healthmark borescope, any third-party USB borescope, an industrial inspection
 * camera, or an HDMI/USB capture card — appears automatically as a selectable
 * source with **no** manufacturer-specific code. It never assumes the first
 * camera is the borescope; the technician picks the source (and their choice is
 * remembered). It emits captured frames both as JPEG `File`s (`onAttach`) and as
 * the standard `ImageAcquisitionResult` (`onResult`); the active workflow owns
 * the upload.
 *
 * Device edge cases are surfaced in plain language, never a raw JS error:
 * permission denied, no device, device in use, over-constrained, unsupported
 * browser. Optional controls (torch/zoom) appear only when the device reports
 * them — basic capture always works without them.
 */

export type BorescopeEvent =
  | "borescope_capture_started"
  | "borescope_capture_completed"
  | "camera_permission_denied"
  | "camera_unavailable";

// Re-exported for consumers that classify a File by source (see ImageAcquisition).
export { BORESCOPE_FILENAME_PREFIX };

const CAM_ERROR_MESSAGE: Record<CamErrorKind, string> = {
  permission: "Camera access is required to capture from the borescope. Allow camera access in your browser, then retry.",
  not_found: "No compatible camera source was detected. Connect the borescope (or a USB/HDMI capture source) and retry — or upload an existing image instead.",
  in_use: "The camera source is already in use by another application. Close the other app, then retry.",
  unsupported: "This browser or device does not support live camera capture. Upload an existing image instead.",
  generic: "The camera could not be started. Retry, or upload an existing image instead.",
};

interface BorescopeCapturePanelProps {
  /** Confirmed captured frame(s) as Files. Parent owns the upload. */
  onAttach: (files: File[]) => void;
  /** Confirmed capture as the standard vendor-neutral result object. */
  onResult?: (result: ImageAcquisitionResult) => void;
  /** Dismiss the live panel without attaching. */
  onCancel?: () => void;
  /** Read-only / disabled (e.g. viewer role). */
  disabled?: boolean;
  /** Optional telemetry hook. Never receives image data or PHI. */
  onEvent?: (name: BorescopeEvent, detail?: string) => void;
  className?: string;
}

export function BorescopeCapturePanel({
  onAttach,
  onResult,
  onCancel,
  disabled,
  onEvent,
  className,
}: BorescopeCapturePanelProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const adapterRef = useRef<MediaDevicesAdapter | null>(null);
  const preferenceAppliedRef = useRef(false);
  const [devices, setDevices] = useState<VideoInput[]>([]);
  const [deviceId, setDeviceId] = useState<string>("");
  const [camError, setCamError] = useState<CamErrorKind | "">("");
  const [ready, setReady] = useState(false);
  const [controls, setControls] = useState<OptionalControlSupport | null>(null);
  const [torchOn, setTorchOn] = useState(false);
  const [zoom, setZoom] = useState<{ min: number; max: number; step: number; value: number } | null>(null);
  const [captured, setCaptured] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const statusId = useId();

  function getAdapter(): MediaDevicesAdapter {
    if (!adapterRef.current) adapterRef.current = new MediaDevicesAdapter();
    return adapterRef.current;
  }

  const bindStream = useCallback(() => {
    const stream = getAdapter().activeStream;
    if (videoRef.current && stream) videoRef.current.srcObject = stream;
  }, []);

  const probeControls = useCallback(() => {
    const adapter = getAdapter();
    setControls(adapter.getCapabilities());
    setTorchOn(false);
    // Zoom needs the numeric range, read from the live track when supported.
    const track = adapter.activeStream?.getVideoTracks?.()[0];
    const caps = track && typeof track.getCapabilities === "function" ? track.getCapabilities() : undefined;
    const z = (caps as { zoom?: { min?: number; max?: number; step?: number } } | undefined)?.zoom;
    if (z && typeof z.max === "number" && typeof z.min === "number" && z.max > z.min) {
      const settings = track?.getSettings?.() as { zoom?: number } | undefined;
      setZoom({ min: z.min, max: z.max, step: z.step || 0.1, value: settings?.zoom ?? z.min });
    } else {
      setZoom(null);
    }
  }, []);

  const start = useCallback(
    async (explicitId?: string) => {
      setCamError("");
      setReady(false);
      const adapter = getAdapter();
      if (!(await adapter.detect())) {
        setCamError("unsupported");
        onEvent?.("camera_unavailable", "mediaDevices_unavailable");
        return;
      }
      const res = await adapter.connect(explicitId);
      if (!res.ok) {
        setCamError(res.error);
        onEvent?.(res.error === "permission" ? "camera_permission_denied" : "camera_unavailable", res.error);
        return;
      }
      bindStream();
      setReady(true);
      onEvent?.("borescope_capture_started");
      const list = await adapter.listDevices();
      setDevices(list);
      probeControls();

      // Remembered-device preference — applied once, on the initial auto-start.
      // Never assume the first camera is the borescope: only switch when a
      // stored preference matches an available device.
      if (!explicitId && !preferenceAppliedRef.current) {
        preferenceAppliedRef.current = true;
        const resolved = resolvePreferredDevice(list, loadDevicePreference());
        const currentId = adapter.activeStream?.getVideoTracks?.()[0]?.getSettings?.().deviceId;
        if (resolved.deviceId && resolved.deviceId !== currentId) {
          setDeviceId(resolved.deviceId);
          await start(resolved.deviceId);
        }
      }
    },
    [bindStream, onEvent, probeControls],
  );

  useEffect(() => {
    if (!disabled) start();
    return () => {
      getAdapter().disconnect();
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function labelFor(id: string): string | undefined {
    return devices.find((d) => d.deviceId === id)?.label || undefined;
  }

  function switchDevice(id: string) {
    setDeviceId(id);
    // Remember the technician's chosen source for next time (id + label so it
    // still resolves after a replug regenerates the transient deviceId).
    saveDevicePreference({ deviceId: id, label: labelFor(id) });
    start(id);
  }

  function toggleTorch() {
    const next = !torchOn;
    setTorchOn(next);
    getAdapter().applyControl({ torch: next });
  }

  function changeZoom(value: number) {
    setZoom((z) => (z ? { ...z, value } : z));
    getAdapter().applyControl({ zoom: value });
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
    const iso = new Date().toISOString();
    const currentId =
      getAdapter().activeStream?.getVideoTracks?.()[0]?.getSettings?.().deviceId || deviceId;
    const label = labelFor(currentId);
    const deviceType = devices.find((d) => d.deviceId === currentId)?.deviceType;
    const file = new File([captured], captureFilename(iso), { type: "image/jpeg", lastModified: Date.now() });
    // Remember this source for subsequent captures.
    if (currentId) saveDevicePreference({ deviceId: currentId, label });
    onEvent?.("borescope_capture_completed");
    onResult?.(
      buildAcquisitionResult({
        image: file,
        captureMethod: "media_devices",
        deviceType,
        deviceLabel: label,
        metadata: getAdapter().getDeviceMetadata(),
      }),
    );
    onAttach([file]);
    recapture();
  }

  function cancel() {
    getAdapter().disconnect();
    recapture();
    onCancel?.();
  }

  return (
    <div
      className={cn("rounded-lg border border-slate-200 bg-white p-3 space-y-3", className)}
      role="group"
      aria-label="Borescope live capture"
    >
      {/* Camera-source selector — shown whenever more than one video input exists. */}
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
              onClick={() => start(deviceId || undefined)}
              className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-amber-400 bg-white px-3 py-1.5 text-xs font-semibold text-amber-800 hover:bg-amber-100"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> Retry camera
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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

      {/* Optional, capability-driven controls — only rendered when the device
          reports supporting them. Basic capture works without any of these. */}
      {!camError && !captured && controls && (controls.torch || (controls.zoom && zoom)) && (
        <div className="flex flex-wrap items-center gap-3">
          {controls.torch && (
            <button
              type="button"
              onClick={toggleTorch}
              aria-pressed={torchOn}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium",
                torchOn ? "border-amber-400 bg-amber-50 text-amber-800" : "border-slate-300 text-slate-700 hover:bg-slate-50",
              )}
            >
              <Lightbulb className="h-4 w-4" aria-hidden="true" /> Light {torchOn ? "on" : "off"}
            </button>
          )}
          {controls.zoom && zoom && (
            <label className="inline-flex items-center gap-2 text-sm text-slate-600">
              <ZoomIn className="h-4 w-4" aria-hidden="true" /> Zoom
              <input
                type="range"
                min={zoom.min}
                max={zoom.max}
                step={zoom.step}
                value={zoom.value}
                onChange={(e) => changeZoom(Number(e.target.value))}
                aria-label="Zoom"
              />
            </label>
          )}
        </div>
      )}

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
                <Check className="h-4 w-4" aria-hidden="true" /> Use image
              </button>
              <button
                type="button"
                onClick={recapture}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <RefreshCw className="h-4 w-4" aria-hidden="true" /> Retake
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
