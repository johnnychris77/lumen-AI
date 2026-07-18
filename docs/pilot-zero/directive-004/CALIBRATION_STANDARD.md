# LPZ-DIR-004 — Calibration Standard

**Purpose:** define the calibration procedures and acceptance tolerances that
make Pilot Zero captures **repeatable and comparable**. Calibration is verified
before every acquisition session and after any equipment change. A session may
**not** proceed if any calibration check fails (fail-closed).

> Tolerances below are stated as engineering defaults to be **confirmed during
> Operational Qualification** against the selected borescope and display. They
> are the framework; the qualified numbers are recorded in the OQ record.

## Calibration references (physical targets)

| Reference | Used for |
|---|---|
| Resolution target (e.g., line-pair / slanted-edge chart) | Resolution verification |
| Neutral gray / white card | White balance & exposure |
| Color reference card (known patches) | Color fidelity |
| Scale reference (ruler / dot grid of known pitch) | Scale/measurement reference |
| Fixed geometry jig | Repeatability of standoff/angle |

All references are controlled items with an ID and a condition check; a damaged
or soiled reference invalidates the calibration.

## 1. Focus verification

* **Procedure:** image the resolution target at the fixed working distance; the
  target's finest specified feature set must be resolvable and sharp.
* **Acceptance (default, confirm in OQ):** the target's specified resolution
  element is clearly resolved; no visible defocus blur at the center and across
  the working field.
* **Fail action:** adjust/lock focus and re-test; if it cannot hold focus,
  quarantine the device and raise an incident.

## 2. Lighting verification

* **Procedure:** image the neutral gray/white card; measure mean luminance and
  uniformity across the frame.
* **Acceptance (default):** mean exposure within the documented target band;
  corner-to-center luminance falloff within the documented uniformity tolerance;
  no clipping (blown highlights) on the card.
* **Fail action:** adjust illumination intensity/geometry; re-test.

## 3. White-balance verification

* **Procedure:** with white balance locked, image the neutral card; measure the
  R/G/B channel balance.
* **Acceptance (default):** neutral card reads neutral within the documented
  per-channel tolerance; no per-frame WB drift across a short burst.
* **Fail action:** re-lock/reset white balance; if drift persists, quarantine.

## 4. Color reference check

* **Procedure:** image the color reference card; record measured patch values.
* **Acceptance (default):** measured patch values within the documented delta of
  the reference values.
* **Purpose:** provides a per-session color anchor so datasets are color-stable.

## 5. Scale reference

* **Procedure:** image the scale reference at the fixed geometry; record the
  pixels-per-unit.
* **Acceptance (default):** measured scale within tolerance of the previously
  qualified value at the same geometry.
* **Note:** this is an **engineering** scale reference, not a clinical
  measurement claim.

## 6. Resolution verification

* **Procedure:** quantify resolving power from the resolution target
  (e.g., MTF/slanted-edge or line-pair count).
* **Acceptance (default):** meets or exceeds the resolution floor established in
  OQ for the selected device.

## 7. Repeatability testing

* **Procedure:** capture the same reference under the fixed geometry N times
  (e.g., 10), across the session start and end.
* **Acceptance (default):** variation in exposure, white balance, scale, and
  resolution across the repeats stays within the documented repeatability
  tolerances.
* **Purpose:** proves the capture chain is stable enough to produce comparable
  images — the core requirement for future dataset use.

## Acceptance tolerance table (template — fill during OQ)

| Check | Metric | Target/Tolerance (set in OQ) | Pass? |
|---|---|---|---|
| Focus | Resolvable feature set | | |
| Lighting | Mean exposure / uniformity | | |
| White balance | Per-channel neutrality / drift | | |
| Color | Patch delta | | |
| Scale | Pixels-per-unit deviation | | |
| Resolution | MTF / line-pairs | | |
| Repeatability | Cross-repeat variation | | |

## Records

* Each session's calibration results are logged with operator, timestamp,
  device/probe ID, and reference IDs.
* Calibration records are archived as evidence (Zone 10). Images captured under
  a failed or missing calibration are **not eligible** for any dataset.
