# Healthmark Borescope — Compatibility Test Plan

**Purpose:** verify that the embedded LumenAI image-acquisition layer works with
the available **Healthmark borescope** as a standard browser camera source.

> This is **compatibility testing with the available Healthmark borescope**. It
> is **not** a Healthmark certification, an official vendor integration, or any
> regulatory clearance. LumenAI makes no such claim. The borescope is used here
> only as a UVC-class camera input through standard web APIs.

## Preconditions

- A laptop/tablet running a current Chromium/Edge/Firefox/Safari build.
- The Healthmark borescope connected (directly, or via a UVC video grabber).
- A LumenAI account with **operator** or **spd_manager** access.
- A **non-clinical test instrument** and a clearly-labeled **test** record. Do
  not use patient/clinical instruments or place PHI in frame.

## Test steps

| # | Step | Expected |
|---|------|----------|
| 1 | **Device connection** — connect the borescope, reload the app. | OS/browser exposes it as a video input. |
| 2 | **Browser detection** — open New Inspection → Add Image → Capture from Borescope. | Live preview starts, or a clear permission prompt appears. |
| 3 | **Camera selection** — if multiple inputs, open the "Camera source" selector. | Healthmark device is selectable by label; switching works. |
| 4 | **Live preview** | Smooth live feed in the preview pane. |
| 5 | **Capture** — click "Capture frame". | A still frame appears in the captured pane. |
| 6 | **Preview** | Captured frame is clear and correctly oriented. |
| 7 | **Attach to inspection** — "Attach image", complete and submit. | Image attaches to the inspection; analysis runs; result shows. |
| 8 | **Attach to baseline** — repeat via a baseline image upload. | Image attaches to the baseline record (status stays pre-approval). |
| 9 | **Re-capture** — capture, then "Recapture", capture again. | Previous frame is discarded; new frame shown. |
| 10 | **Disconnect / reconnect** — unplug mid-session, retry. | Clear "no compatible camera source" message; "Retry camera" recovers after reconnect. |
| 11 | **Multiple-camera handling** — attach a second camera. | Both listed; correct device used after selection. |
| 12 | **Permission denied** — block camera permission, retry. | "Camera access is required…" message; no raw JS error; upload still available. |
| 13 | **Browser restart** — restart the browser, repeat capture. | Permission re-prompt; capture works. |
| 14 | **Application restart** — reload app mid-workflow. | No crash; user can re-acquire. |
| 15 | **Repeated capture** — capture ~10 frames in succession. | Stable; no leaked streams (camera light turns off when the panel closes/cancels). |
| 16 | **Image quality** — note sharpness, lighting, focus at typical distance. | Record observations. |
| 17 | **Latency** — note preview-to-capture responsiveness. | Record observations. |
| 18 | **Failures** — capture with feed not ready. | Graceful message, no crash. |
| 19 | **Screenshots** — capture each key screen. | Attach to the run log below. |
| 20 | **Final result** — summarize PASS/PARTIAL/FAIL with notes. | Record decision. |

## Home-lab / pilot scenario

```
Laptop → Healthmark Borescope → Test Instrument → New Inspection
  → Add Image → Capture from Borescope → Attach → Submit → Analyze → Review
```

Use the **Borescope Diagnostics & Device Test** page (Administration → Borescope
Diagnostics) to verify the device end-to-end on a labeled test instrument before
running the embedded workflow. This path uses the same governed evidence rules —
it is not a shortcut around them.

## Run log (fill in during testing)

| Field | Value |
|-------|-------|
| Date / tester | |
| Device / grabber | |
| Browser / OS | |
| Steps passed | |
| Issues observed | |
| Image quality notes | |
| Latency notes | |
| Screenshots attached | |
| **Final result** | |

## Known limitations

- Live browser camera capture depends on the OS exposing the borescope as a
  UVC device and on the browser's `getUserMedia` support; some embedded mobile
  webviews do not support it — file upload remains available there.
- No device-specific SDK is used; only standard web camera APIs.
