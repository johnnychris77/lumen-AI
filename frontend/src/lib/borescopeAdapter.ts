/**
 * Default device adapter — Tier 1/2/4.
 *
 * `MediaDevicesAdapter` services every device that presents to the OS/browser
 * as a standard video input: built-in webcams, USB borescopes (any vendor),
 * industrial USB inspection cameras, and HDMI/USB capture cards. It is the one
 * adapter needed today; a future Tier-3 device requiring a proprietary SDK is
 * added by implementing `BorescopeAdapter` (see imageAcquisition.ts) without
 * touching any inspection/baseline/evidence workflow.
 *
 * The pure discovery/selection/capability logic lives in imageAcquisition.ts;
 * this file only binds it to the real browser globals (`navigator.mediaDevices`,
 * `localStorage`) and manages the active `MediaStream`.
 */
import {
  type BorescopeAdapter,
  type MediaDevicesLike,
  type VideoInput,
  type VideoAccessResult,
  type OptionalControlSupport,
  type AcquisitionDeviceMetadata,
  type AcquisitionDevicePreference,
  PREFERENCE_STORAGE_KEY,
  listVideoInputs,
  requestVideoAccess,
  supportedOptionalControls,
} from "./imageAcquisition";

export class MediaDevicesAdapter implements BorescopeAdapter {
  readonly id = "media-devices";
  private md: MediaDevicesLike | undefined;
  private stream: MediaStream | null = null;

  constructor(md?: MediaDevicesLike) {
    this.md =
      md ??
      (typeof navigator !== "undefined" && navigator.mediaDevices
        ? (navigator.mediaDevices as unknown as MediaDevicesLike)
        : undefined);
  }

  async detect(): Promise<boolean> {
    return !!this.md?.getUserMedia;
  }

  async listDevices(): Promise<VideoInput[]> {
    return listVideoInputs(this.md);
  }

  async connect(deviceId?: string): Promise<VideoAccessResult> {
    const res = await requestVideoAccess(this.md, deviceId);
    if (res.ok) this.stream = res.stream as MediaStream;
    return res;
  }

  disconnect(): void {
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
  }

  /** The live stream, for binding to a <video> element. */
  get activeStream(): MediaStream | null {
    return this.stream;
  }

  getCapabilities(): OptionalControlSupport | null {
    const track = this.stream?.getVideoTracks?.()[0];
    if (!track || typeof track.getCapabilities !== "function") return null;
    try {
      return supportedOptionalControls(track.getCapabilities() as unknown as Parameters<typeof supportedOptionalControls>[0]);
    } catch {
      return null;
    }
  }

  getDeviceMetadata(): AcquisitionDeviceMetadata {
    // Standard web APIs expose only a device *label*, never manufacturer / model
    // / driver — so metadata stays minimal and optional. A future SDK adapter
    // may supply richer fields without any workflow change.
    const track = this.stream?.getVideoTracks?.()[0];
    const label = track?.label || undefined;
    const meta: AcquisitionDeviceMetadata = {};
    if (label) meta.deviceLabel = label;
    return meta;
  }

  /** Apply an optional, capability-gated control (torch/zoom/focus). Non-fatal. */
  async applyControl(constraint: Record<string, unknown>): Promise<void> {
    const track = this.stream?.getVideoTracks?.()[0];
    if (track && typeof track.applyConstraints === "function") {
      try {
        await track.applyConstraints({ advanced: [constraint] } as MediaTrackConstraints);
      } catch {
        /* non-fatal — the control simply has no effect on this device */
      }
    }
  }
}

// ─── Device-preference persistence (localStorage) ────────────────────────────

export function loadDevicePreference(): AcquisitionDevicePreference | null {
  try {
    if (typeof localStorage === "undefined") return null;
    const raw = localStorage.getItem(PREFERENCE_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AcquisitionDevicePreference;
    if (parsed && (parsed.deviceId || parsed.label)) return parsed;
    return null;
  } catch {
    return null;
  }
}

export function saveDevicePreference(pref: AcquisitionDevicePreference): void {
  try {
    if (typeof localStorage === "undefined") return;
    if (!pref.deviceId && !pref.label) return;
    localStorage.setItem(PREFERENCE_STORAGE_KEY, JSON.stringify(pref));
  } catch {
    /* preference memory is best-effort — never break capture over storage */
  }
}

export function clearDevicePreference(): void {
  try {
    if (typeof localStorage === "undefined") return;
    localStorage.removeItem(PREFERENCE_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
