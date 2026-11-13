# Stage 6A — Scientific Evidence Review & Measurement Availability

Status: **framework + measurement matrix; no real measurements exist yet.** Reuses the
Stage 5C scientific-evidence contract and its four strictly-separated layers.

## 1. The four separated layers (unchanged)

1. **AI-detected anomaly** — a research-only, uncalibrated spatial signal.
2. **Human visual interpretation** — a reviewer's opinion; not confirmation.
3. **Laboratory-confirmed material identity** — independently verified.
4. **Clinical instrument disposition** — **never produced in research.**

An anomaly score never crosses these boundaries. In particular, the following are
**forbidden inferences** from an anomaly score or RGB appearance and are enforced in
code (`infer_identity_from_rgb` raises; observations carry no disposition):

- biological identity (blood vs tissue vs bone),
- pit depth or corrosion/oxidation **age**,
- **cleanliness** or **sterility** status.

## 2. Measurement availability matrix

For each evidence category, which measurements *define* the ground truth, and which
remain **unverified** until the laboratory program (Stage 5D ground-truth protocol)
runs. "Available" = the contract + validator already require and capture it; it still
depends on a real laboratory partner producing the measurement.

| Category | Defining reference measurement(s) | In-contract (required) | Remains unverified until lab runs |
|---|---|---|---|
| **Corrosion-like** | Material characterization (EDS/XRD/SEM-EDS) + affected-area + units + uncertainty | ✅ required by `validate_evidence` | Actual material ID; corrosion mechanism/age (age is **never** inferred) |
| **Localized pitting** | Optical/SEM microscopy or profilometry + pit geometry | ✅ required | True pit depth/volume; pit vs scratch discrimination |
| **Blood-like residue** | Protein/hemoglobin assay or documented soil-identity confirmation | ✅ required | Biological identity (blood vs other protein); species |
| **Bone/tissue-like** | Histology / composition analysis / FTIR / independently-verified particle ID | ✅ required | Tissue type; biological origin |
| **Confounders** (reflections, scratches, detergent films, mineral deposits, benign discoloration) | Independent review / reference standard | ✅ required | Confirmation the surface is benign; separability from true anomalies |

## 3. What the AI layer may and may not assert

- **May:** "an anomalous region was localized here, with score X (uncalibrated)."
- **May not:** "this is corrosion/blood/tissue/pitting", "this instrument is
  unclean/unsterile", "this pit is N µm deep", or any clinical disposition.

A confirmed material identity is recorded **only** from verified laboratory evidence
linked by an authenticated, authorized reviewer whose identity matches the verifier and
whose image/specimen match the anomaly (Stage 5D `link_observation` +
`ReviewerAuthorization`).

## 4. Outstanding (BLOCKED until the laboratory program runs)

1. A qualified laboratory partner and methods for each category's reference measurement.
2. Independently-reviewed labels + adjudication (Stage 5D ground-truth protocol).
3. Governed storage of lab evidence linked to retained images, with reviewer attribution.

Until then, every category's "laboratory-confirmed identity" layer is **empty**, and the
benchmark may report only AI-anomaly behavior — never confirmed material identity.
