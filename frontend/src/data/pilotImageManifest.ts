/**
 * Pilot Image Manifest — LumenAI Phase 5
 *
 * Single source of truth for all demo/pilot lumened instrument images.
 *
 * HOW TO ADD REAL IMAGES:
 *   1. Copy your .jpg/.png/.webp file into:
 *        frontend/public/demo-images/lumened-instruments/
 *      using the naming convention:
 *        {facility}_{instrument}_{model}_{identifier}_{imageType}_{findingCategory}_{YYYYMMDD}.jpg
 *   2. Set `imageSrc` to the filename (no leading slash — Vite serves from /public at root).
 *   3. Set `available: true`.
 *   4. The UI will display the real image; `placeholderSrc` is only used as fallback.
 *
 * PHI GUIDANCE:
 *   - Do NOT include patient names, MRNs, DOBs, or procedure dates in any field.
 *   - captureDate should reflect the IMAGE capture date, not a patient event date.
 *   - notes must describe instrument condition only — no patient context.
 *   - facility field must match an anonymised site code or consented facility name.
 *
 * See docs/pilot/pilot-image-ingestion-guide.md for full instructions.
 */

// ─── Types ────────────────────────────────────────────────────────────────────

export type ImageType = "baseline" | "inspection" | "borescope" | "finding";

export type FindingCategory =
  | "blood"
  | "bone"
  | "tissue"
  | "debris"
  | "corrosion"
  | "crack"
  | "insulation_damage"
  | "other"
  | "none";

export type RiskLevel = "low" | "medium" | "high" | "critical";
export type BaselineStatus = "approved" | "pending_review" | "rejected" | "draft";
export type ImageQuality = "high" | "medium" | "low";
export type IdentifierType = "keydot" | "qr" | "barcode" | "manual";

export interface PilotImage {
  /** Unique manifest ID — never changes once assigned */
  id: string;

  // ── Image source ─────────────────────────────────────────────────────────
  /** Filename in frontend/public/demo-images/lumened-instruments/. Set when image is loaded. */
  imageSrc: string;
  /** Fallback SVG shown when imageSrc is missing or fails to load */
  placeholderSrc: string;
  /** Set to true once the real image file exists at imageSrc */
  available: boolean;

  // ── Instrument identity ──────────────────────────────────────────────────
  facility: string;
  instrumentName: string;
  manufacturer: string;
  model: string;
  /** Full identifier value, e.g. "keydot-127" */
  identifier: string;
  identifierType: IdentifierType;

  // ── Image classification ─────────────────────────────────────────────────
  imageType: ImageType;
  findingCategory: FindingCategory;
  baselineStatus: BaselineStatus;
  riskLevel: RiskLevel;
  imageQuality: ImageQuality;

  // ── Capture metadata ─────────────────────────────────────────────────────
  captureDate: string;
  captureDevice: string;
  captureAngle: string;
  uploadedBy: string;

  // ── Content ──────────────────────────────────────────────────────────────
  notes: string;
  knownNormalCharacteristics?: string;
  knownAbnormalCharacteristics?: string;
  /** File name of the matching baseline image (for inspection/finding entries) */
  pairedBaselineFile?: string;
}

// ─── Placeholder paths (served from /public) ─────────────────────────────────

const PH = {
  baseline:   "demo-images/lumened-instruments/_placeholder-baseline.svg",
  inspection: "demo-images/lumened-instruments/_placeholder-inspection.svg",
  borescope:  "demo-images/lumened-instruments/_placeholder-borescope.svg",
  finding:    "demo-images/lumened-instruments/_placeholder-finding.svg",
} as const satisfies Record<ImageType, string>;

// ─── Manifest ─────────────────────────────────────────────────────────────────

export const MANIFEST_VERSION = "1.0.0";

export const PILOT_IMAGES: PilotImage[] = [
  // ── Laparoscopic Grasper — Storz 26173KA / keydot-127 ──────────────────
  {
    id: "pi-001",
    imageSrc: "demo-images/lumened-instruments/bonsecours_laparoscopic-grasper_model-26173ka_keydot-127_baseline_none_20260115.jpg",
    placeholderSrc: PH.baseline,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Laparoscopic Grasper",
    manufacturer: "Storz",
    model: "26173KA",
    identifier: "keydot-127",
    identifierType: "keydot",
    imageType: "baseline",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-01-15",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "Distal tip, 0°",
    uploadedBy: "spd-tech-01",
    notes: "Clean. No visible tissue residue. Jaws close flush.",
    knownNormalCharacteristics: "Jaws close flush with no gap. Tungsten carbide surface intact. No discolouration.",
    knownAbnormalCharacteristics: "Tissue at jaw hinge. Corrosion at box joint. Jaw misalignment.",
  },
  {
    id: "pi-002",
    imageSrc: "demo-images/lumened-instruments/bonsecours_laparoscopic-grasper_model-26173ka_keydot-127_finding_tissue_20260310.jpg",
    placeholderSrc: PH.finding,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Laparoscopic Grasper",
    manufacturer: "Storz",
    model: "26173KA",
    identifier: "keydot-127",
    identifierType: "keydot",
    imageType: "finding",
    findingCategory: "tissue",
    baselineStatus: "approved",
    riskLevel: "high",
    imageQuality: "high",
    captureDate: "2026-03-10",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "Distal tip, 0°",
    uploadedBy: "spd-tech-01",
    notes: "Tissue fragment visible at jaw hinge. Requires re-cleaning. Investigation candidate.",
    pairedBaselineFile: "bonsecours_laparoscopic-grasper_model-26173ka_keydot-127_baseline_none_20260115.jpg",
  },
  {
    id: "pi-003",
    imageSrc: "demo-images/lumened-instruments/bonsecours_laparoscopic-grasper_model-26173ka_keydot-127_inspection_none_20260402.jpg",
    placeholderSrc: PH.inspection,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Laparoscopic Grasper",
    manufacturer: "Storz",
    model: "26173KA",
    identifier: "keydot-127",
    identifierType: "keydot",
    imageType: "inspection",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-04-02",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "Lateral — full instrument",
    uploadedBy: "spd-tech-02",
    notes: "Post-cleaning inspection. No residue detected. Passes baseline comparison.",
    pairedBaselineFile: "bonsecours_laparoscopic-grasper_model-26173ka_keydot-127_baseline_none_20260115.jpg",
  },

  // ── Needle Driver — Olympus MAJ-1262 / barcode-A04421 ──────────────────
  {
    id: "pi-004",
    imageSrc: "demo-images/lumened-instruments/mercy-health_needle-driver_model-maj1262_barcode-a04421_baseline_none_20260120.jpg",
    placeholderSrc: PH.baseline,
    available: false,
    facility: "Mercy Health",
    instrumentName: "Needle Driver",
    manufacturer: "Olympus",
    model: "MAJ-1262",
    identifier: "barcode-A04421",
    identifierType: "barcode",
    imageType: "baseline",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-01-20",
    captureDevice: "USB Macro Camera",
    captureAngle: "Lateral — full instrument",
    uploadedBy: "spd-tech-03",
    notes: "Reference baseline. Tungsten carbide inserts intact. Jaws meet cleanly.",
    knownNormalCharacteristics: "TC inserts intact. Jaw gap <0.2 mm when closed. Ratchet engages all positions.",
    knownAbnormalCharacteristics: "TC insert chipping. Jaw misalignment. Ratchet skip.",
  },
  {
    id: "pi-005",
    imageSrc: "demo-images/lumened-instruments/mercy-health_needle-driver_model-maj1262_barcode-a04421_finding_corrosion_20260402.jpg",
    placeholderSrc: PH.finding,
    available: false,
    facility: "Mercy Health",
    instrumentName: "Needle Driver",
    manufacturer: "Olympus",
    model: "MAJ-1262",
    identifier: "barcode-A04421",
    identifierType: "barcode",
    imageType: "finding",
    findingCategory: "corrosion",
    baselineStatus: "approved",
    riskLevel: "medium",
    imageQuality: "medium",
    captureDate: "2026-04-02",
    captureDevice: "USB Macro Camera",
    captureAngle: "Jaw box",
    uploadedBy: "spd-tech-03",
    notes: "Early-stage corrosion at box joint. Quality review recommended. Not yet critical.",
    pairedBaselineFile: "mercy-health_needle-driver_model-maj1262_barcode-a04421_baseline_none_20260120.jpg",
  },

  // ── Hemostatic Forceps — Aesculap BH741R / qr-4892-B ──────────────────
  {
    id: "pi-006",
    imageSrc: "demo-images/lumened-instruments/bonsecours_hemostatic-forceps_model-bh741r_qr-4892b_baseline_none_20260122.jpg",
    placeholderSrc: PH.baseline,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Hemostatic Forceps",
    manufacturer: "Aesculap",
    model: "BH741R",
    identifier: "qr-4892-B",
    identifierType: "qr",
    imageType: "baseline",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-01-22",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "Ratchet mechanism",
    uploadedBy: "spd-tech-01",
    notes: "Ratchet engages cleanly through all positions. No residue.",
    knownNormalCharacteristics: "Ratchet clicks positively. Jaw serrations sharp and clean.",
    knownAbnormalCharacteristics: "Blood in ratchet channel. Jaw serration wear.",
  },
  {
    id: "pi-007",
    imageSrc: "demo-images/lumened-instruments/bonsecours_hemostatic-forceps_model-bh741r_qr-4892b_finding_blood_20260514.jpg",
    placeholderSrc: PH.finding,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Hemostatic Forceps",
    manufacturer: "Aesculap",
    model: "BH741R",
    identifier: "qr-4892-B",
    identifierType: "qr",
    imageType: "finding",
    findingCategory: "blood",
    baselineStatus: "approved",
    riskLevel: "critical",
    imageQuality: "high",
    captureDate: "2026-05-14",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "Ratchet interior",
    uploadedBy: "spd-tech-02",
    notes: "Blood residue in ratchet channel. Immediate re-cleaning required. Near-miss signal.",
    pairedBaselineFile: "bonsecours_hemostatic-forceps_model-bh741r_qr-4892b_baseline_none_20260122.jpg",
  },

  // ── Bone Rongeur — Codman 10-0006 / keydot-088 ─────────────────────────
  {
    id: "pi-008",
    imageSrc: "demo-images/lumened-instruments/bonsecours_bone-rongeur_model-10-0006_keydot-088_finding_bone_20260428.jpg",
    placeholderSrc: PH.finding,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Bone Rongeur",
    manufacturer: "Codman",
    model: "10-0006",
    identifier: "keydot-088",
    identifierType: "keydot",
    imageType: "finding",
    findingCategory: "bone",
    baselineStatus: "approved",
    riskLevel: "high",
    imageQuality: "medium",
    captureDate: "2026-04-28",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "Cup jaw interior",
    uploadedBy: "spd-tech-04",
    notes: "Bone fragment in cup recess. Investigation candidate. Human review required.",
  },
  {
    id: "pi-009",
    imageSrc: "demo-images/lumened-instruments/bonsecours_bone-rongeur_model-10-0006_keydot-088_baseline_none_20260110.jpg",
    placeholderSrc: PH.baseline,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Bone Rongeur",
    manufacturer: "Codman",
    model: "10-0006",
    identifier: "keydot-088",
    identifierType: "keydot",
    imageType: "baseline",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-01-10",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "Cup jaw interior",
    uploadedBy: "spd-tech-04",
    notes: "Reference baseline. Cup jaw clean and sharp.",
    knownNormalCharacteristics: "Cup jaw edges sharp. Interior smooth. Spring tension consistent.",
    knownAbnormalCharacteristics: "Bone debris in cup. Jaw edge chipping.",
  },

  // ── Bipolar Forceps — Erbe / keydot-219 ────────────────────────────────
  {
    id: "pi-010",
    imageSrc: "demo-images/lumened-instruments/mercy-health_bipolar-forceps_model-vio300d_keydot-219_inspection_insulation-damage_20260501.jpg",
    placeholderSrc: PH.inspection,
    available: false,
    facility: "Mercy Health",
    instrumentName: "Bipolar Forceps",
    manufacturer: "Erbe",
    model: "VIO 300D",
    identifier: "keydot-219",
    identifierType: "keydot",
    imageType: "inspection",
    findingCategory: "insulation_damage",
    baselineStatus: "pending_review",
    riskLevel: "high",
    imageQuality: "high",
    captureDate: "2026-05-01",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "Shaft insulation, mid-point",
    uploadedBy: "spd-tech-02",
    notes: "Possible insulation thinning at 120 mm. Electrical safety check required before next use.",
  },

  // ── Retractor — Thompson M-3760 / manual-R9921 ─────────────────────────
  {
    id: "pi-011",
    imageSrc: "demo-images/lumened-instruments/mercy-health_retractor_model-m3760_manual-r9921_borescope_debris_20260508.jpg",
    placeholderSrc: PH.borescope,
    available: false,
    facility: "Mercy Health",
    instrumentName: "Retractor",
    manufacturer: "Thompson",
    model: "M-3760",
    identifier: "manual-R9921",
    identifierType: "manual",
    imageType: "borescope",
    findingCategory: "debris",
    baselineStatus: "approved",
    riskLevel: "medium",
    imageQuality: "medium",
    captureDate: "2026-05-08",
    captureDevice: "Rigid Borescope 4 mm",
    captureAngle: "Inner channel",
    uploadedBy: "spd-tech-03",
    notes: "Debris / bioburden accumulation in inner channel. Re-cleaning indicated.",
  },

  // ── Scissors Metzenbaum — Jarit 110-218 / keydot-341 ──────────────────
  {
    id: "pi-012",
    imageSrc: "demo-images/lumened-instruments/bonsecours_scissors-metzenbaum_model-110218_keydot-341_finding_crack_20260512.jpg",
    placeholderSrc: PH.finding,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Scissors — Metzenbaum",
    manufacturer: "Jarit",
    model: "110-218",
    identifier: "keydot-341",
    identifierType: "keydot",
    imageType: "finding",
    findingCategory: "crack",
    baselineStatus: "approved",
    riskLevel: "critical",
    imageQuality: "high",
    captureDate: "2026-05-12",
    captureDevice: "USB Macro Camera",
    captureAngle: "Blade edge",
    uploadedBy: "spd-tech-01",
    notes: "Hairline crack at blade pivot. Remove from service immediately.",
  },
  {
    id: "pi-013",
    imageSrc: "demo-images/lumened-instruments/bonsecours_scissors-metzenbaum_model-110218_keydot-341_baseline_none_20260118.jpg",
    placeholderSrc: PH.baseline,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Scissors — Metzenbaum",
    manufacturer: "Jarit",
    model: "110-218",
    identifier: "keydot-341",
    identifierType: "keydot",
    imageType: "baseline",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-01-18",
    captureDevice: "USB Macro Camera",
    captureAngle: "Blade edge",
    uploadedBy: "spd-tech-01",
    notes: "Reference baseline. Blade edges sharp, no cracks or chips.",
    knownNormalCharacteristics: "Blade edges sharp, continuous. Pivot smooth. Micro serrations intact.",
    knownAbnormalCharacteristics: "Blade crack. Edge chipping. Pivot wear.",
  },

  // ── Suction Irrigator — Medtronic REF-0090 / qr-7731-C ────────────────
  {
    id: "pi-014",
    imageSrc: "demo-images/lumened-instruments/bonsecours_suction-irrigator_model-ref0090_qr-7731c_baseline_none_20260518.jpg",
    placeholderSrc: PH.baseline,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Suction Irrigator",
    manufacturer: "Medtronic",
    model: "REF-0090",
    identifier: "qr-7731-C",
    identifierType: "qr",
    imageType: "baseline",
    findingCategory: "none",
    baselineStatus: "draft",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-05-18",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "Lumen, distal",
    uploadedBy: "spd-tech-05",
    notes: "Draft baseline pending SPD manager approval. Lumen clear on capture.",
    knownNormalCharacteristics: "Lumen fully patent. No occlusion or discolouration. Valve seal intact.",
    knownAbnormalCharacteristics: "Debris in lumen. Valve seal failure.",
  },
  {
    id: "pi-015",
    imageSrc: "demo-images/lumened-instruments/bonsecours_suction-irrigator_model-ref0090_qr-7731c_borescope_none_20260602.jpg",
    placeholderSrc: PH.borescope,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Suction Irrigator",
    manufacturer: "Medtronic",
    model: "REF-0090",
    identifier: "qr-7731-C",
    identifierType: "qr",
    imageType: "borescope",
    findingCategory: "none",
    baselineStatus: "draft",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-06-02",
    captureDevice: "Rigid Borescope 4 mm",
    captureAngle: "Lumen, distal — 0°",
    uploadedBy: "spd-tech-05",
    notes: "Clear lumen. No occlusion, debris, or discolouration detected.",
  },

  // ── Trocar 12 mm — Applied Medical G35012 / keydot-455 ────────────────
  {
    id: "pi-016",
    imageSrc: "demo-images/lumened-instruments/mercy-health_trocar-12mm_model-g35012_keydot-455_inspection_none_20260520.jpg",
    placeholderSrc: PH.inspection,
    available: false,
    facility: "Mercy Health",
    instrumentName: "Trocar — 12 mm",
    manufacturer: "Applied Medical",
    model: "G35012",
    identifier: "keydot-455",
    identifierType: "keydot",
    imageType: "inspection",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-05-20",
    captureDevice: "Rigid Borescope 4 mm",
    captureAngle: "Valve channel",
    uploadedBy: "spd-tech-02",
    notes: "Routine inspection. Valve seals intact. No findings detected.",
  },

  // ── Clip Applier — Ethicon ECS25W / keydot-512 ────────────────────────
  {
    id: "pi-017",
    imageSrc: "demo-images/lumened-instruments/mercy-health_clip-applier_model-ecs25w_keydot-512_baseline_none_20260201.jpg",
    placeholderSrc: PH.baseline,
    available: false,
    facility: "Mercy Health",
    instrumentName: "Clip Applier",
    manufacturer: "Ethicon",
    model: "ECS25W",
    identifier: "keydot-512",
    identifierType: "keydot",
    imageType: "baseline",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-02-01",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "Jaw mechanism, 0°",
    uploadedBy: "spd-tech-03",
    notes: "Clean baseline. Clip feed mechanism functional. Jaw alignment correct.",
    knownNormalCharacteristics: "Clip channel clear. Jaw closes evenly. No staining.",
    knownAbnormalCharacteristics: "Tissue in clip channel. Jaw misalignment. Feed jam.",
  },
  {
    id: "pi-018",
    imageSrc: "demo-images/lumened-instruments/mercy-health_clip-applier_model-ecs25w_keydot-512_finding_tissue_20260528.jpg",
    placeholderSrc: PH.finding,
    available: false,
    facility: "Mercy Health",
    instrumentName: "Clip Applier",
    manufacturer: "Ethicon",
    model: "ECS25W",
    identifier: "keydot-512",
    identifierType: "keydot",
    imageType: "finding",
    findingCategory: "tissue",
    baselineStatus: "approved",
    riskLevel: "high",
    imageQuality: "high",
    captureDate: "2026-05-28",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "Clip channel interior",
    uploadedBy: "spd-tech-03",
    notes: "Tissue fragment in clip channel. Re-cleaning required before next use.",
    pairedBaselineFile: "mercy-health_clip-applier_model-ecs25w_keydot-512_baseline_none_20260201.jpg",
  },

  // ── Electrosurgical Hook — ConMed 7-900-1 / barcode-B0091 ──────────────
  {
    id: "pi-019",
    imageSrc: "demo-images/lumened-instruments/bonsecours_electrosurgical-hook_model-7-900-1_barcode-b0091_baseline_none_20260215.jpg",
    placeholderSrc: PH.baseline,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Electrosurgical Hook",
    manufacturer: "ConMed",
    model: "7-900-1",
    identifier: "barcode-B0091",
    identifierType: "barcode",
    imageType: "baseline",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-02-15",
    captureDevice: "USB Macro Camera",
    captureAngle: "Hook tip, 45°",
    uploadedBy: "spd-tech-04",
    notes: "Baseline. Hook tip clean. Insulation intact along full shaft length.",
    knownNormalCharacteristics: "Insulation continuous, no thinning. Hook tip free of char.",
    knownAbnormalCharacteristics: "Insulation breach. Char at tip. Shaft discolouration.",
  },
  {
    id: "pi-020",
    imageSrc: "demo-images/lumened-instruments/bonsecours_electrosurgical-hook_model-7-900-1_barcode-b0091_finding_insulation-damage_20260610.jpg",
    placeholderSrc: PH.finding,
    available: false,
    facility: "Bon Secours",
    instrumentName: "Electrosurgical Hook",
    manufacturer: "ConMed",
    model: "7-900-1",
    identifier: "barcode-B0091",
    identifierType: "barcode",
    imageType: "finding",
    findingCategory: "insulation_damage",
    baselineStatus: "approved",
    riskLevel: "critical",
    imageQuality: "high",
    captureDate: "2026-06-10",
    captureDevice: "USB Macro Camera",
    captureAngle: "Shaft, 80 mm from tip",
    uploadedBy: "spd-tech-04",
    notes: "Insulation breach confirmed at 80 mm. Remove from service. Electrical hazard.",
    pairedBaselineFile: "bonsecours_electrosurgical-hook_model-7-900-1_barcode-b0091_baseline_none_20260215.jpg",
  },
];

// ─── Derived helpers ──────────────────────────────────────────────────────────

/** Return images matching a given identifier (for Instrument Passport view) */
export function getImagesByIdentifier(identifier: string): PilotImage[] {
  return PILOT_IMAGES.filter((img) => img.identifier === identifier);
}

/** Return images matching a given instrument name (case-insensitive) */
export function getImagesByInstrument(name: string): PilotImage[] {
  const q = name.toLowerCase();
  return PILOT_IMAGES.filter((img) => img.instrumentName.toLowerCase().includes(q));
}

/** Summary counts derived from the manifest */
export function getManifestSummary() {
  const total = PILOT_IMAGES.length;
  const available = PILOT_IMAGES.filter((i) => i.available).length;
  const byType = {
    baseline: PILOT_IMAGES.filter((i) => i.imageType === "baseline").length,
    inspection: PILOT_IMAGES.filter((i) => i.imageType === "inspection").length,
    borescope: PILOT_IMAGES.filter((i) => i.imageType === "borescope").length,
    finding: PILOT_IMAGES.filter((i) => i.imageType === "finding").length,
  };
  const byStatus = {
    approved: PILOT_IMAGES.filter((i) => i.baselineStatus === "approved").length,
    pending: PILOT_IMAGES.filter((i) => i.baselineStatus === "pending_review").length,
    draft: PILOT_IMAGES.filter((i) => i.baselineStatus === "draft").length,
  };
  const criticalFindings = PILOT_IMAGES.filter(
    (i) => i.riskLevel === "critical" && i.imageType === "finding"
  ).length;
  return { total, available, byType, byStatus, criticalFindings };
}

/** Unique instrument identifiers in the manifest (for Registry / Passport selectors) */
export const MANIFEST_IDENTIFIERS = [
  ...new Set(PILOT_IMAGES.map((i) => i.identifier)),
];

/** Unique instrument names in the manifest */
export const MANIFEST_INSTRUMENTS = [
  ...new Set(PILOT_IMAGES.map((i) => i.instrumentName)),
];
