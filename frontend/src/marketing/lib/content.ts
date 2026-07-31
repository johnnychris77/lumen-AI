import { mlink } from "./base";
/**
 * Single source of marketing copy for the public LumenAI site.
 *
 * Content discipline (see docs/marketing/PRODUCT_CLAIMS_REVIEW.md):
 *  - `maturity` on capabilities/specialists mirrors the repository's
 *    PRODUCT_CAPABILITY_MATRIX and AI_SPECIALIST_CATALOG — it is not
 *    aspirational.
 *  - No infection-rate, regulatory-compliance, FDA/HIPAA, diagnostic-accuracy,
 *    or cost-saving claims appear here.
 *  - AI is always described as decision support with human review.
 */

export type Maturity = "supported" | "demonstrated" | "concept";

export const MATURITY_LABEL: Record<Maturity, string> = {
  supported: "In product",
  demonstrated: "Demonstrated with simulated data",
  concept: "Concept stage",
};

export interface Capability {
  title: string;
  body: string;
  maturity: Maturity;
}

export const CAPABILITIES: Capability[] = [
  {
    title: "Borescope Image Review",
    body: "Capture and review internal-channel borescope images inside a structured inspection record instead of a loose image folder.",
    maturity: "supported",
  },
  {
    title: "Structured Inspection Records",
    body: "Every inspection carries instrument, tray, location, technician, and timestamp metadata so a finding is never an orphaned image.",
    maturity: "supported",
  },
  {
    title: "Baseline-Aware Comparison",
    body: "When an approved baseline exists for an instrument, the current inspection is presented alongside it to support a like-for-like review.",
    maturity: "supported",
  },
  {
    title: "Evidence Integrity",
    body: "Inspection evidence, review status, and rationale are recorded with a tamper-evident, hash-chained audit trail.",
    maturity: "supported",
  },
  {
    title: "Risk & Review Routing",
    body: "Uncertain or higher-risk findings are routed to a qualified human reviewer; the platform never finalizes a clinical judgment on its own.",
    maturity: "supported",
  },
  {
    title: "Instrument History & Digital Twin",
    body: "Findings accumulate against a per-instrument record so condition can be viewed over time rather than one inspection at a time.",
    maturity: "supported",
  },
  {
    title: "Audit Logging",
    body: "User actions, review decisions, and evidence events are appended to an immutable, hash-chained log for audit readiness.",
    maturity: "supported",
  },
  {
    title: "Role-Based Access & Multi-Tenant Governance",
    body: "Access is scoped by role and by tenant so organizations only see their own data, enforced at the API layer.",
    maturity: "supported",
  },
  {
    title: "Quality & Exportable Reports",
    body: "Generate inspection, trend, and audit-evidence reports for quality review and export.",
    maturity: "supported",
  },
  {
    title: "AI-Assisted Finding Suggestions",
    body: "The platform can surface suggested finding categories to focus a reviewer's attention. In the current build this is a non-validated assistive layer, always subject to human confirmation.",
    maturity: "concept",
  },
  {
    title: "Vendor & Instrument Trend Intelligence",
    body: "Aggregate findings by instrument type and vendor to reveal patterns a single inspection cannot show.",
    maturity: "demonstrated",
  },
  {
    title: "Knowledge-Graph Relationships",
    body: "Relate instruments, findings, baselines, and reviews so context travels with the evidence.",
    maturity: "demonstrated",
  },
];

/** The 10 named specialists, described from the repository's specialist catalog. */
export interface Specialist {
  name: string;
  role: string;
  purpose: string;
  inputs: string;
  outputs: string;
  allowed: string;
  notAllowed: string;
  humanReview: string;
  /** Honest status note where the catalog flags a gap. */
  note?: string;
}

export const SPECIALISTS: Specialist[] = [
  {
    name: "Vision",
    role: "Image inference (infrastructure)",
    purpose: "Runs computer-vision inference over inspection images to suggest finding signals.",
    inputs: "Inspection image bytes.",
    outputs: "Suggested categories and confidence scores attached to an inspection.",
    allowed: "Surface assistive image signals for a reviewer.",
    notAllowed: "Decide disposition, replace the technician, or act without review.",
    humanReview: "Every suggestion is advisory and confirmed by a qualified human.",
    note: "In the current build this is infrastructure, not a validated model — findings run through a documented placeholder scorer pending a trained, validated model.",
  },
  {
    name: "Anatomy",
    role: "Zone taxonomy (infrastructure)",
    purpose: "Provides a standardized internal-channel / zone vocabulary so findings are described consistently.",
    inputs: "Instrument type and inspection zone references.",
    outputs: "A resolved, standardized zone for each finding.",
    allowed: "Normalize how instrument regions are named across inspections.",
    notAllowed: "Assess condition or make a review decision.",
    humanReview: "Supports human interpretation; makes no judgments itself.",
    note: "Cross-cutting infrastructure shared across the platform rather than a standalone decision agent.",
  },
  {
    name: "Veritas",
    role: "Evidence integrity",
    purpose: "The platform's evidence-integrity and baseline-governance layer.",
    inputs: "Baseline resolutions, retained images, model registry references.",
    outputs: "Evidence provenance, baseline lineage, readiness assessments, evidence-conflict records.",
    allowed: "Assure the integrity and lineage of inspection evidence.",
    notAllowed: "Overwrite another specialist's conclusion or make a clinical call.",
    humanReview: "Strengthens the record a human reviewer relies on.",
  },
  {
    name: "Aegis",
    role: "Process-variation signal (a Vulcan sub-capability)",
    purpose: "Highlights technician/vendor concentration patterns behind a recurring finding.",
    inputs: "Technician and vendor concentration across inspections.",
    outputs: "A minimal process-variation signal recorded alongside reliability data.",
    allowed: "Flag a possible process pattern for review.",
    notAllowed: "Attribute cause or discipline anyone; it names an association, never a conclusion.",
    humanReview: "A prompt for quality review, not a verdict.",
    note: "Deliberately scoped as a Vulcan sub-capability today, not an independent specialist.",
  },
  {
    name: "Vulcan",
    role: "Instrument reliability",
    purpose: "Instrument reliability, failure analysis, and repair intelligence.",
    inputs: "Finding history, repair requests, instrument knowledge, digital-twin state.",
    outputs: "Reliability and repair-effectiveness assessments.",
    allowed: "Assess instrument reliability trends and repair signals.",
    notAllowed: "Make clinical dispositions or override human review.",
    humanReview: "Informs maintenance and quality decisions made by people.",
  },
  {
    name: "Sage",
    role: "Education & competency",
    purpose: "Sterile-processing education, competency, and workforce intelligence.",
    inputs: "Competency events, supervisor reviews, coverage/confidence signals.",
    outputs: "Knowledge-gap detection, learning plans, microlearning, competency assessments.",
    allowed: "Suggest targeted education and competency support.",
    notAllowed: "Evaluate a person punitively or gate clinical decisions.",
    humanReview: "Supports supervisors and educators, who make the calls.",
  },
  {
    name: "Sentinel-X",
    role: "Composite risk intelligence",
    purpose: "Composite risk intelligence and proactive quality-review alerting.",
    inputs: "Reliability, process-variation, evidence-readiness, and gap signals.",
    outputs: "Risk assessments and quality-review alerts with supervisor override.",
    allowed: "Raise a prioritized quality-review alert.",
    notAllowed: "Assert patient outcomes or finalize risk decisions.",
    humanReview: "Every alert carries a supervisor override path.",
  },
  {
    name: "Maestro",
    role: "Operational synthesis (decision support)",
    purpose: "Executive-layer synthesis that reads specialist outputs to rank operational priorities.",
    inputs: "Read-only outputs from the other specialists.",
    outputs: "Prioritized items, recommendations, daily briefs, decision journal.",
    allowed: "Rank and summarize what deserves attention.",
    notAllowed: "Execute changes or make clinical decisions.",
    humanReview: "Presents priorities to leaders; humans decide and act.",
  },
  {
    name: "Council",
    role: "Decision support",
    purpose: "Convenes cross-specialist perspectives into transparent, dissent-preserving recommendations.",
    inputs: "Read-only assessments from multiple specialists.",
    outputs: "Cases, specialist assessments, dissent records, decision options, and the human decision record.",
    allowed: "Present options and preserve disagreement for a human decision.",
    notAllowed: "Decide autonomously; it explicitly records the human decision separately.",
    humanReview: "The decision itself is always made and recorded by a person.",
  },
  {
    name: "Oracle",
    role: "Discovery (human-gated)",
    purpose: "Proposes research hypotheses and trend observations for human review.",
    inputs: "Health snapshots, twin history, progression and finding timelines.",
    outputs: "Hypotheses, trend observations, and knowledge suggestions — all gated.",
    allowed: "Propose questions and patterns worth investigating.",
    notAllowed: "Promote a hypothesis to knowledge without human approval.",
    humanReview: "Promotion writes a governance-approval record requiring sign-off.",
  },
];

export interface WorkflowStepInfo {
  n: number;
  title: string;
  detail: string;
  kind: "capture" | "analyze" | "compare" | "review" | "govern" | "report";
}

export const WORKFLOW_STEPS: WorkflowStepInfo[] = [
  { n: 1, title: "Identify the instrument", detail: "Select or scan the instrument so evidence attaches to the right record.", kind: "capture" },
  { n: 2, title: "Capture the lumen image", detail: "Record the internal-channel borescope image.", kind: "capture" },
  { n: 3, title: "Attach metadata", detail: "Instrument, tray, location, technician, and inspection context.", kind: "capture" },
  { n: 4, title: "Validate evidence quality", detail: "Confirm the image and evidence are usable before analysis.", kind: "capture" },
  { n: 5, title: "Analyze visible findings", detail: "Assistive analysis surfaces suggested finding categories.", kind: "analyze" },
  { n: 6, title: "Compare with baseline", detail: "When an approved baseline exists, review side-by-side.", kind: "compare" },
  { n: 7, title: "Provisional or final ranking", detail: "A ranking is produced according to review status.", kind: "analyze" },
  { n: 8, title: "Route for human review", detail: "Uncertain or higher-risk findings go to a qualified reviewer.", kind: "review" },
  { n: 9, title: "Record evidence & rationale", detail: "Evidence, decisions, actions, and timestamps are written to the audit trail.", kind: "govern" },
  { n: 10, title: "Reports & insights", detail: "Produce reports, trends, and audit evidence.", kind: "report" },
];

export interface UseCase {
  title: string;
  body: string;
  audience: string;
}

export const USE_CASES: UseCase[] = [
  { title: "Routine lumen inspection", body: "Standardize daily internal-channel inspection into structured, reviewable evidence.", audience: "SPD technicians & leaders" },
  { title: "Escalation of suspicious findings", body: "Route an uncertain or higher-risk finding to a qualified reviewer with full context.", audience: "SPD & Infection Prevention" },
  { title: "Comparison with a known-good baseline", body: "Review a current image beside an approved baseline for a like-for-like check.", audience: "SPD & Quality" },
  { title: "Instrument condition monitoring", body: "Watch condition trends per instrument instead of judging one inspection in isolation.", audience: "SPD & Biomed" },
  { title: "Damaged or missing instrument investigation", body: "Assemble the evidence trail around an instrument for a structured investigation.", audience: "Risk & Quality" },
  { title: "Vendor quality review", body: "Aggregate findings by vendor and instrument type to inform vendor conversations.", audience: "Supply chain & Quality" },
  { title: "Audit preparation", body: "Produce audit-ready evidence with timestamps, rationale, and review status.", audience: "Quality & Accreditation" },
  { title: "Training & competency review", body: "Use real inspection examples to support competency and education.", audience: "SPD educators" },
  { title: "Quality-improvement analysis", body: "Turn accumulated findings into improvement themes and priorities.", audience: "Quality & Patient Safety" },
  { title: "Multi-site trend review", body: "Compare trends across sites within a tenant, with data kept isolated per tenant.", audience: "Executives" },
];

export interface VideoScene {
  n: number;
  name: string;
  narration: string;
  onScreen: string;
  animation: string;
  seconds: number;
}

/** 10-scene, ~110s explainer concept. Full script/storyboard in docs/marketing. */
export const VIDEO_SCENES: VideoScene[] = [
  { n: 1, name: "The hidden problem", narration: "Some of the most important surfaces on a surgical instrument are also the hardest to see.", onScreen: "See what traditional inspection cannot.", animation: "Camera moves from the exterior of an instrument into its internal channel.", seconds: 12 },
  { n: 2, name: "Inspection limits", narration: "Borescope evidence can be hard to standardize, compare, review, and trace over time.", onScreen: "Scattered images. Spreadsheets. Paper logs.", animation: "Disconnected images and rows drift apart.", seconds: 12 },
  { n: 3, name: "Introduce LumenAI", narration: "LumenAI turns internal instrument inspection into structured, reviewable evidence.", onScreen: "LumenAI — inspection, evidence, decision support.", animation: "Interface assembles from the scattered pieces.", seconds: 12 },
  { n: 4, name: "Capture", narration: "Identify the instrument, capture the lumen image, and attach the context that makes it evidence.", onScreen: "Identify · Capture · Attach metadata.", animation: "Instrument selected, image framed, metadata fields fill in.", seconds: 12 },
  { n: 5, name: "Analyze", narration: "Assistive analysis highlights areas for a reviewer — it never decides alone.", onScreen: "Assistive analysis. Human confirmed.", animation: "Subtle highlights appear on the image; a 'review required' tag stays visible.", seconds: 12 },
  { n: 6, name: "Compare", narration: "When an approved baseline exists, the current inspection sits right beside it.", onScreen: "Current vs. approved baseline.", animation: "Two panels slide together for a side-by-side.", seconds: 11 },
  { n: 7, name: "Review", narration: "Uncertain or higher-risk findings route to a qualified reviewer.", onScreen: "Routed to human review.", animation: "A card moves into a reviewer queue.", seconds: 11 },
  { n: 8, name: "Govern", narration: "Every decision is recorded with rationale, timestamps, permissions, and an audit trail.", onScreen: "Evidence. Rationale. Audit trail.", animation: "A hash-chained timeline of events builds up.", seconds: 12 },
  { n: 9, name: "Learn", narration: "Findings become trends across instruments, vendors, sites, and time.", onScreen: "From findings to intelligence.", animation: "Points aggregate into clean trend lines.", seconds: 10 },
  { n: 10, name: "Close", narration: "Better visibility. Better evidence. Better decisions.", onScreen: "LumenAI — Better visibility. Better evidence. Better decisions.", animation: "Wordmark resolves on a calm gradient.", seconds: 6 },
];

export const NAV_LINKS = [
  { to: mlink("/problem"), label: "The Problem" },
  { to: mlink("/workflow"), label: "How It Works" },
  { to: mlink("/platform"), label: "Platform" },
  { to: mlink("/architecture"), label: "AI Architecture" },
  { to: mlink("/security"), label: "Security" },
  { to: mlink("/use-cases"), label: "Use Cases" },
  { to: mlink("/video"), label: "Video" },
  { to: mlink("/about"), label: "About" },
];
