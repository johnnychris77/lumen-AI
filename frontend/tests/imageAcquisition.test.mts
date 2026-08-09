/**
 * Vendor-neutral image-acquisition — automated tests.
 *
 * Runs on Node's built-in test runner with type-stripping (no test-framework
 * dependency, no audit surface):
 *
 *   node --test --experimental-strip-types tests/imageAcquisition.test.mts
 *
 * The device discovery/selection/preference/capability logic is pure and takes
 * an injected MediaDevices-like object, so the 13 required device scenarios are
 * exercised with a fake device set — no real camera, no DOM. Everything here is
 * generic camera/video behavior; nothing is keyed to a manufacturer.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  classifyVideoInputLabel,
  deviceTypeToSourceType,
  supportedOptionalControls,
  resolvePreferredDevice,
  listVideoInputs,
  requestVideoAccess,
  buildAcquisitionResult,
  captureFilename,
  fileSourceType,
  BORESCOPE_FILENAME_PREFIX,
  type MediaDevicesLike,
  type MediaDeviceLike,
} from "../src/lib/imageAcquisition.ts";

// ── fakes ────────────────────────────────────────────────────────────────────

function videoInput(deviceId: string, label: string): MediaDeviceLike {
  return { deviceId, kind: "videoinput", label };
}

/** A configurable fake MediaDevices. `devices` is read live so it can mutate. */
function fakeMediaDevices(opts: {
  devices?: () => MediaDeviceLike[];
  getUserMediaError?: string; // Error.name to throw
}): MediaDevicesLike {
  return {
    async enumerateDevices() {
      return opts.devices ? opts.devices() : [];
    },
    async getUserMedia() {
      if (opts.getUserMediaError) {
        const e = new Error(opts.getUserMediaError);
        e.name = opts.getUserMediaError;
        throw e;
      }
      return { id: "fake-stream" };
    },
  };
}

// ── Scenario 1: laptop webcam only ───────────────────────────────────────────
test("scenario 1 — single webcam enumerates as one input", async () => {
  const md = fakeMediaDevices({ devices: () => [videoInput("cam1", "Integrated Webcam")] });
  const inputs = await listVideoInputs(md);
  assert.equal(inputs.length, 1);
  assert.equal(inputs[0].deviceType, "integrated_camera");
});

// ── Scenario 2: webcam + borescope ───────────────────────────────────────────
test("scenario 2 — webcam + borescope: both listed, borescope classified generically", async () => {
  const md = fakeMediaDevices({
    devices: () => [videoInput("cam1", "Integrated Webcam"), videoInput("scope1", "USB Borescope")],
  });
  const inputs = await listVideoInputs(md);
  assert.equal(inputs.length, 2);
  assert.equal(inputs.find((d) => d.deviceId === "scope1")?.deviceType, "borescope");
});

// ── Scenario 3: multiple external cameras ────────────────────────────────────
test("scenario 3 — multiple external cameras all enumerate", async () => {
  const md = fakeMediaDevices({
    devices: () => [
      videoInput("a", "USB Camera"),
      videoInput("b", "HDMI Capture Device"),
      videoInput("c", "USB Borescope"),
    ],
  });
  const inputs = await listVideoInputs(md);
  assert.equal(inputs.length, 3);
  assert.equal(inputs.find((d) => d.deviceId === "b")?.deviceType, "capture_device");
});

// ── Scenario 4: borescope disconnected ───────────────────────────────────────
test("scenario 4 — a disconnected borescope is absent from enumeration", async () => {
  const md = fakeMediaDevices({ devices: () => [videoInput("cam1", "Integrated Webcam")] });
  const inputs = await listVideoInputs(md);
  assert.ok(!inputs.some((d) => d.deviceType === "borescope"));
});

// ── Scenario 5: device connected after page load ─────────────────────────────
test("scenario 5 — device appearing after load shows up on re-enumeration", async () => {
  let list = [videoInput("cam1", "Integrated Webcam")];
  const md = fakeMediaDevices({ devices: () => list });
  assert.equal((await listVideoInputs(md)).length, 1);
  list = [...list, videoInput("scope1", "USB Borescope")]; // plugged in
  const after = await listVideoInputs(md);
  assert.equal(after.length, 2);
});

// ── Scenario 6: permission denied ────────────────────────────────────────────
test("scenario 6 — permission denied maps to a clear 'permission' error, never throws", async () => {
  const md = fakeMediaDevices({ getUserMediaError: "NotAllowedError" });
  const res = await requestVideoAccess(md);
  assert.deepEqual(res, { ok: false, error: "permission" });
});

// ── Scenario 7: permission granted ───────────────────────────────────────────
test("scenario 7 — permission granted returns an ok stream result", async () => {
  const md = fakeMediaDevices({});
  const res = await requestVideoAccess(md);
  assert.equal(res.ok, true);
});

// ── Scenario 8: device removed during preview ────────────────────────────────
test("scenario 8 — device removed mid-preview surfaces 'in_use'/'not_found', not a raw error", async () => {
  const removed = fakeMediaDevices({ getUserMediaError: "NotReadableError" });
  assert.deepEqual(await requestVideoAccess(removed), { ok: false, error: "in_use" });
  const gone = fakeMediaDevices({ getUserMediaError: "NotFoundError" });
  assert.deepEqual(await requestVideoAccess(gone, "scope1"), { ok: false, error: "not_found" });
});

// ── Scenario 9: preferred device unavailable (+ label fallback) ──────────────
test("scenario 9 — preferred-device resolution: id, label fallback, then none", () => {
  const devices = [
    { deviceId: "cam1", label: "Integrated Webcam" },
    { deviceId: "scope-new", label: "USB Borescope" },
  ];
  // exact id
  assert.deepEqual(resolvePreferredDevice(devices, { deviceId: "scope-new" }), {
    deviceId: "scope-new",
    matchedBy: "id",
  });
  // id changed after replug → fall back to label
  assert.deepEqual(resolvePreferredDevice(devices, { deviceId: "scope-old", label: "USB Borescope" }), {
    deviceId: "scope-new",
    matchedBy: "label",
  });
  // preferred device truly gone → none (caller shows selector, never guesses)
  assert.deepEqual(resolvePreferredDevice(devices, { deviceId: "x", label: "Document Camera" }), {
    deviceId: null,
    matchedBy: "none",
  });
});

// ── Scenario 10 & 11: file-upload fallback / unsupported browser ─────────────
test("scenario 10/11 — no MediaDevices: enumeration empty, access 'unsupported' (upload remains)", async () => {
  assert.deepEqual(await listVideoInputs(undefined), []);
  assert.deepEqual(await requestVideoAccess(undefined), { ok: false, error: "unsupported" });
});

// ── Scenario 12: capture failure ─────────────────────────────────────────────
test("scenario 12 — an unclassified capture failure degrades to 'generic'", async () => {
  const md = fakeMediaDevices({ getUserMediaError: "WeirdUnknownError" });
  assert.deepEqual(await requestVideoAccess(md), { ok: false, error: "generic" });
});

// ── Scenario 13: multiple consecutive captures ───────────────────────────────
test("scenario 13 — consecutive captures mint distinct, source-tagged filenames", () => {
  const f1 = captureFilename("2026-08-09T10:00:00.000Z");
  const f2 = captureFilename("2026-08-09T10:00:01.000Z");
  const f3 = captureFilename("2026-08-09T10:00:01.000Z", 2);
  assert.notEqual(f1, f2);
  assert.notEqual(f2, f3);
  for (const f of [f1, f2, f3]) assert.ok(f.startsWith(BORESCOPE_FILENAME_PREFIX));
});

// ── Vendor neutrality of classification ──────────────────────────────────────
test("classification uses only generic descriptors — a bare brand name is not a borescope", () => {
  assert.equal(classifyVideoInputLabel("Acme HD 4K Camera"), "unknown");
  assert.equal(classifyVideoInputLabel("USB Video Device"), "usb_camera");
  assert.equal(classifyVideoInputLabel("Some Vendor Borescope XL"), "borescope");
  assert.equal(classifyVideoInputLabel("OBS Virtual Camera"), "virtual_camera");
  assert.equal(classifyVideoInputLabel(""), "unknown");
});

test("device type maps to a generic source type (never vendor-specific)", () => {
  assert.equal(deviceTypeToSourceType("borescope"), "borescope");
  assert.equal(deviceTypeToSourceType("capture_device"), "external_capture");
  assert.equal(deviceTypeToSourceType("integrated_camera"), "camera");
  assert.equal(deviceTypeToSourceType(undefined), "camera");
});

// ── Capability-driven optional controls ──────────────────────────────────────
test("optional controls are only reported when actually supported", () => {
  assert.deepEqual(supportedOptionalControls(null), { torch: false, zoom: false, focus: false });
  assert.deepEqual(supportedOptionalControls({}), { torch: false, zoom: false, focus: false });
  assert.deepEqual(
    supportedOptionalControls({ torch: true, zoom: { min: 1, max: 4 }, focusMode: ["manual"] }),
    { torch: true, zoom: true, focus: true },
  );
  // A zoom object with no real range is not a usable control.
  assert.equal(supportedOptionalControls({ zoom: { min: 1, max: 1 } }).zoom, false);
});

// ── Standard result object ───────────────────────────────────────────────────
test("buildAcquisitionResult derives source type and omits empty metadata", () => {
  const image = { name: captureFilename("2026-08-09T10:00:00.000Z") } as unknown as File;
  const r = buildAcquisitionResult({ image, captureMethod: "media_devices", deviceType: "borescope", deviceLabel: "USB Borescope" });
  assert.equal(r.sourceType, "borescope");
  assert.equal(r.captureMethod, "media_devices");
  assert.equal(r.deviceLabel, "USB Borescope");
  assert.equal(r.metadata, undefined); // no vendor metadata provided → omitted
  assert.ok(typeof r.captureTimestamp === "string" && r.captureTimestamp.length > 0);
});

test("buildAcquisitionResult keeps provided vendor metadata (optional)", () => {
  const image = { name: "existing-photo.jpg" } as unknown as File;
  const r = buildAcquisitionResult({
    image,
    captureMethod: "file_upload",
    metadata: { manufacturer: "Example Co", model: "IX-1" },
  });
  assert.equal(r.sourceType, "file_upload");
  assert.deepEqual(r.metadata, { manufacturer: "Example Co", model: "IX-1" });
});

test("fileSourceType recovers source from the File name alone", () => {
  assert.equal(fileSourceType({ name: captureFilename("2026-08-09T10:00:00.000Z") }), "borescope");
  assert.equal(fileSourceType({ name: "IMG_0421.jpg" }), "file_upload");
});
