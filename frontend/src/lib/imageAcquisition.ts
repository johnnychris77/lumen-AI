/**
 * Vendor-neutral image-acquisition core.
 *
 * LumenAI integrates with the *image source*, never with a borescope
 * manufacturer's workflow. Any compatible device — a Healthmark borescope, a
 * third-party USB borescope, an industrial inspection camera, an HDMI/USB
 * capture card, or a plain webcam — flows through the same abstraction and
 * produces the same standard `ImageAcquisitionResult`. There is deliberately no
 * hard-coded manufacturer name, USB VID/PID, or device label anywhere in this
 * module, and no capability is *required* for basic capture.
 *
 * Everything here is pure and DOM-free (the browser `MediaDevices` object is
 * injected, never read from a global), so the discovery/selection/preference/
 * capability logic is unit-testable with a fake device set — see
 * `frontend/tests/imageAcquisition.test.mts`. The DOM-bound wrapper lives in
 * `borescopeAdapter.ts`.
 */

// ─── Standard result object ─────────────────────────────────────────────────

/** Generic source category. Never a vendor-specific value. */
export type SourceType = "borescope" | "camera" | "file_upload" | "external_capture";

export type CaptureMethod = "media_devices" | "file_upload" | "adapter_sdk";

/**
 * Best-effort *generic* device category, derived only from generic descriptor
 * words in the OS-provided label (see `classifyVideoInputLabel`). A display
 * hint only — never authoritative, never required, never manufacturer-specific.
 */
export type DeviceType =
  | "integrated_camera"
  | "usb_camera"
  | "borescope"
  | "capture_device"
  | "virtual_camera"
  | "unknown";

/** Optional, only populated when a source actually provides it. */
export interface AcquisitionDeviceMetadata {
  manufacturer?: string;
  model?: string;
  deviceLabel?: string;
  driver?: string;
}

/** The one object every acquisition source ultimately produces. */
export interface ImageAcquisitionResult {
  image: File;
  sourceType: SourceType;
  captureTimestamp: string; // ISO-8601
  deviceType?: DeviceType;
  deviceLabel?: string;
  captureMethod: CaptureMethod;
  metadata?: AcquisitionDeviceMetadata;
}

// ─── Injectable browser surface (so logic is testable without a DOM) ─────────

export interface MediaDeviceLike {
  deviceId: string;
  kind: string;
  label: string;
}

export interface MediaDevicesLike {
  enumerateDevices(): Promise<MediaDeviceLike[]>;
  getUserMedia(constraints: unknown): Promise<unknown>;
}

export interface VideoInput {
  deviceId: string;
  label: string;
  deviceType: DeviceType;
}

// ─── Device preference (remembered across captures) ──────────────────────────

export const PREFERENCE_STORAGE_KEY = "lumenai.imageAcquisition.preferredVideoInput";

export interface AcquisitionDevicePreference {
  /** Transient across browser sessions/replug — matched first when present. */
  deviceId?: string;
  /** Stable-ish human label — the fallback match when deviceId has changed. */
  label?: string;
}

// ─── Camera error taxonomy (UI maps kind → message) ──────────────────────────

export type CamErrorKind = "permission" | "not_found" | "in_use" | "unsupported" | "generic";

/** Classify a getUserMedia rejection into a stable, message-free kind. */
export function classifyCamError(err: unknown): CamErrorKind {
  const name = (err as { name?: string } | null | undefined)?.name;
  switch (name) {
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

// ─── Generic (vendor-neutral) device classification ──────────────────────────

/**
 * Map an OS-provided video-input label to a *generic* device category using
 * only industry-generic descriptor words — never a manufacturer or product
 * name. Used purely to show a friendlier label/icon and to order the list; it
 * never gates capture and a wrong guess is harmless (falls back to "unknown").
 */
export function classifyVideoInputLabel(label: string | undefined): DeviceType {
  const l = (label || "").toLowerCase();
  if (!l) return "unknown";
  if (/\b(borescope|endoscope|videoscope|inspection cam)/.test(l)) return "borescope";
  if (/\b(capture|hdmi|acquisition|grabber|av\s?to\s?usb)/.test(l)) return "capture_device";
  if (/\b(virtual|obs|screen|snap\b)/.test(l)) return "virtual_camera";
  if (/\b(integrated|built[-\s]?in|internal|front|rear)\b/.test(l)) return "integrated_camera";
  if (/\busb\b/.test(l)) return "usb_camera";
  return "unknown";
}

/** Generic device category → standard source type. */
export function deviceTypeToSourceType(dt: DeviceType | undefined): SourceType {
  switch (dt) {
    case "borescope":
      return "borescope";
    case "capture_device":
      return "external_capture";
    default:
      return "camera";
  }
}

// ─── Optional, capability-driven controls ────────────────────────────────────

/** A structural subset of MediaTrackCapabilities — only what we probe. */
export interface TrackCapabilitiesLike {
  torch?: boolean;
  zoom?: { min?: number; max?: number; step?: number } | number[];
  focusMode?: string[];
  focusDistance?: { min?: number; max?: number };
}

export interface OptionalControlSupport {
  torch: boolean;
  zoom: boolean;
  focus: boolean;
}

/**
 * Detect which optional controls a track actually supports. Controls are only
 * ever exposed when true here — we never assume a borescope has a torch, zoom,
 * or focus, and basic capture works with all of these false.
 */
export function supportedOptionalControls(caps: TrackCapabilitiesLike | null | undefined): OptionalControlSupport {
  if (!caps) return { torch: false, zoom: false, focus: false };
  const zoom = Array.isArray(caps.zoom)
    ? caps.zoom.length > 1
    : !!caps.zoom && typeof caps.zoom === "object" && caps.zoom.max !== undefined && caps.zoom.max !== caps.zoom.min;
  const focus = Array.isArray(caps.focusMode)
    ? caps.focusMode.some((m) => m === "manual" || m === "continuous")
    : caps.focusDistance !== undefined;
  return { torch: !!caps.torch, zoom, focus };
}

// ─── Preferred-device resolution ─────────────────────────────────────────────

export interface PreferredResolution {
  deviceId: string | null;
  matchedBy: "id" | "label" | "none";
}

/**
 * Resolve which enumerated input to pre-select from a stored preference: exact
 * deviceId first, then label (deviceId is regenerated across sessions/replug on
 * many browsers), else none — the caller then shows the selector rather than
 * guessing. We never silently assume the first camera is the borescope.
 */
export function resolvePreferredDevice(
  devices: Pick<VideoInput, "deviceId" | "label">[],
  pref: AcquisitionDevicePreference | null | undefined,
): PreferredResolution {
  if (!pref || devices.length === 0) return { deviceId: null, matchedBy: "none" };
  if (pref.deviceId) {
    const byId = devices.find((d) => d.deviceId === pref.deviceId);
    if (byId) return { deviceId: byId.deviceId, matchedBy: "id" };
  }
  if (pref.label) {
    const byLabel = devices.find((d) => d.label && d.label === pref.label);
    if (byLabel) return { deviceId: byLabel.deviceId, matchedBy: "label" };
  }
  return { deviceId: null, matchedBy: "none" };
}

// ─── Pure discovery over an injected MediaDevices surface ─────────────────────

/**
 * Enumerate video inputs through an injected `MediaDevices`-like object,
 * classifying each generically. Returns [] when the surface is unavailable
 * (older/embedded webviews) — the caller then offers file upload, which is
 * always available.
 */
export async function listVideoInputs(md: MediaDevicesLike | undefined | null): Promise<VideoInput[]> {
  if (!md?.enumerateDevices) return [];
  const all = await md.enumerateDevices();
  return all
    .filter((d) => d.kind === "videoinput")
    .map((d) => ({
      deviceId: d.deviceId,
      label: d.label,
      deviceType: classifyVideoInputLabel(d.label),
    }));
}

export type VideoAccessResult =
  | { ok: true; stream: unknown }
  | { ok: false; error: CamErrorKind };

/**
 * Request camera access through an injected surface. Returns a discriminated
 * result (never throws) so callers render a clear message instead of a raw JS
 * error, and reports `unsupported` when the browser lacks the API entirely.
 */
export async function requestVideoAccess(
  md: MediaDevicesLike | undefined | null,
  deviceId?: string,
): Promise<VideoAccessResult> {
  if (!md?.getUserMedia) return { ok: false, error: "unsupported" };
  try {
    const stream = await md.getUserMedia({
      video: deviceId ? { deviceId: { exact: deviceId } } : true,
      audio: false,
    });
    return { ok: true, stream };
  } catch (err) {
    return { ok: false, error: classifyCamError(err) };
  }
}

// ─── Result construction ─────────────────────────────────────────────────────

/** Frames captured live carry this prefix so source is recoverable from the File alone. */
export const BORESCOPE_FILENAME_PREFIX = "borescope-capture";

/** Mint a unique, source-tagged filename for a captured frame. */
export function captureFilename(timestampIso: string, seq = 0): string {
  const stamp = timestampIso.replace(/[:.]/g, "-");
  return `${BORESCOPE_FILENAME_PREFIX}-${stamp}${seq ? `-${seq}` : ""}.jpg`;
}

/** Recover the standard source type from a File (borescope prefix vs upload). */
export function fileSourceType(file: { name: string }): Extract<SourceType, "borescope" | "file_upload"> {
  return file.name.startsWith(BORESCOPE_FILENAME_PREFIX) ? "borescope" : "file_upload";
}

export interface BuildResultInput {
  image: File;
  captureMethod: CaptureMethod;
  deviceType?: DeviceType;
  deviceLabel?: string;
  metadata?: AcquisitionDeviceMetadata;
  /** Override the derived source type (rarely needed). */
  sourceType?: SourceType;
  timestampIso?: string;
}

/** Build the standard result object. Vendor metadata stays optional. */
export function buildAcquisitionResult(input: BuildResultInput): ImageAcquisitionResult {
  const sourceType =
    input.sourceType ??
    (input.captureMethod === "file_upload"
      ? "file_upload"
      : deviceTypeToSourceType(input.deviceType));
  const metadata =
    input.metadata && Object.values(input.metadata).some((v) => v != null && v !== "")
      ? input.metadata
      : undefined;
  return {
    image: input.image,
    sourceType,
    captureTimestamp: input.timestampIso ?? new Date().toISOString(),
    deviceType: input.deviceType,
    deviceLabel: input.deviceLabel || undefined,
    captureMethod: input.captureMethod,
    metadata,
  };
}

// ─── Adapter interface (Tier 3 — future SDK / bridge devices) ────────────────

/**
 * A device adapter isolates *how* frames are acquired from the workflow that
 * consumes them. The default `MediaDevicesAdapter` (see borescopeAdapter.ts)
 * covers every device that presents as a standard video input — Tier 1 (browser
 * cameras/borescopes), Tier 2's captured files (via upload), and Tier 4 capture
 * cards. A future Tier-3 device that needs a proprietary SDK/native bridge is
 * added by implementing this same interface — **no** change to the inspection,
 * baseline, or evidence workflow, and **no** manufacturer-specific branching in
 * the UI. Implement a proprietary adapter only if such an SDK is actually
 * available and required.
 */
export interface BorescopeAdapter {
  /** Stable, generic adapter id (e.g. "media-devices"), never a brand. */
  readonly id: string;
  /** True if this adapter can service the current environment. */
  detect(): Promise<boolean>;
  /** List selectable video inputs, generically classified. */
  listDevices(): Promise<VideoInput[]>;
  /** Begin a preview for a chosen device (or the default). */
  connect(deviceId?: string): Promise<VideoAccessResult>;
  /** Tear down any active stream. */
  disconnect(): void;
  /** Capability probe for the active stream (null if none / unknown). */
  getCapabilities(): OptionalControlSupport | null;
  /** Optional device metadata, only when the adapter can supply it. */
  getDeviceMetadata(deviceId?: string): AcquisitionDeviceMetadata;
}
