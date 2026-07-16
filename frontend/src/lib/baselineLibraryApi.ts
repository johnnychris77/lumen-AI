/**
 * Client for the Project Atlas Sprint 1 Baseline Image Library API
 * (`app.routes.baseline_image_library`). Kept in its own module rather than
 * folded into `canvasTypes`/`api.ts` because this is a distinct governed
 * entity (the reverse link from a `BaselineLibraryEntry` to an
 * LCID-registered image), not an extension of the dataset registry types.
 */
import { apiFetch } from "@/lib/api";

export const BASELINE_SOURCE_TYPES = [
  "manufacturer_reference",
  "organization_known_good",
  "new_instrument_reference",
  "post_repair_reference",
  "digital_twin_initial_reference",
  "governed_consensus_reference",
  "research_reference",
] as const;

export const SOURCE_TYPES_REQUIRING_PROVENANCE = new Set(["manufacturer_reference"]);

export const BASELINE_IMAGE_TYPES = [
  "manufacturer_baseline",
  "organization_baseline",
  "digital_twin_baseline",
  "anatomy_zone_reference",
  "post_repair_reference",
  "candidate_baseline",
] as const;

export const BASELINE_IMAGE_STATES = [
  "DRAFT",
  "PENDING_REVIEW",
  "APPROVED",
  "ACTIVE",
  "SUSPENDED",
  "SUPERSEDED",
  "REJECTED",
  "ARCHIVED",
] as const;

export interface BaselineImageLink {
  id: number;
  tenant_id: string;
  facility_id: string;
  baseline_library_entry_id: number;
  lcid_image_id: number;
  instrument_family: string;
  manufacturer: string;
  model_name: string;
  catalog_number: string;
  anatomy_zone: string;
  inspection_view: string;
  orientation: string;
  image_type: string;
  source_type: string;
  source_organization: string;
  source_reference: string;
  baseline_version: string;
  effective_date: string | null;
  lifecycle_status: string;
  approved_by: string;
  approved_at: string | null;
  usage_rights_status: string;
  image_quality_status: string;
  annotation_ref: string;
  digital_twin_id: string;
  image_sha256: string;
  retained_image_id: number | null;
  superseded_at: string | null;
  supersedes_link_id: number | null;
  created_by: string;
  superseded_by: string;
  limitations: string;
  created_at: string | null;
}

export interface BaselineImageReview {
  id: number;
  baseline_image_link_id: number;
  reviewer: string;
  reviewer_role: string;
  decision: string;
  rationale: string;
  limitations: string;
  source_verification: string;
  anatomy_compatibility_confirmed: boolean;
  image_quality_assessment: string;
  review_date: string | null;
  next_review_date: string | null;
}

export interface BaselineSet {
  id: number;
  tenant_id: string;
  manufacturer: string;
  model_name: string;
  instrument_family: string;
  anatomy_zone: string;
  view_protocol: string;
  orientation_protocol: string;
  version: string;
  lifecycle_status: string;
  active: boolean;
  limitations: string;
  effective_date: string | null;
  supersedes_set_id: number | null;
  baseline_image_link_ids: number[];
}

export interface AuditEvent {
  action_type: string;
  actor_email: string;
  actor_role: string;
  status: string;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface LinkImageInput {
  facility_id?: string;
  baseline_library_entry_id: number;
  lcid_image_id: number;
  anatomy_zone: string;
  inspection_view: string;
  orientation?: string;
  image_type: string;
  source_type: string;
  source_organization?: string;
  source_reference?: string;
  baseline_version?: string;
}

export interface ReviewInput {
  decision: "approve" | "reject";
  rationale: string;
  limitations?: string;
  source_verification?: string;
  anatomy_compatibility_confirmed?: boolean;
  image_quality_assessment?: string;
  next_review_date?: string | null;
}

export interface CandidateContext {
  instrument_family?: string;
  manufacturer?: string;
  model_name?: string;
  anatomy_zone?: string;
  inspection_view?: string;
  orientation?: string;
  image_quality_status?: string;
  digital_twin_id?: string;
}

export interface ResolutionResult {
  baseline_image_link_id: number | null;
  baseline_set_id: number | null;
  resolution_scope: string;
  resolution_reason: string;
  version: string | null;
  limitations: string[];
}

export interface LegacyBaselineReport {
  total_baseline_entries: number;
  with_active_image: number[];
  missing_image_evidence: number[];
  missing_image_evidence_marker: string;
  missing_anatomy_zone: number[];
  missing_usage_rights: number[];
  needing_review: number[];
}

const BASE = "/api/baseline-library";

export const baselineLibraryApi = {
  listImages: (params?: { baseline_library_entry_id?: number; lifecycle_status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.baseline_library_entry_id != null) qs.set("baseline_library_entry_id", String(params.baseline_library_entry_id));
    if (params?.lifecycle_status) qs.set("lifecycle_status", params.lifecycle_status);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return apiFetch<{ count: number; images: BaselineImageLink[] }>(`${BASE}/images${suffix}`);
  },

  getImage: (linkId: number) => apiFetch<BaselineImageLink>(`${BASE}/images/${linkId}`),

  createImage: (body: LinkImageInput) =>
    apiFetch<BaselineImageLink>(`${BASE}/images`, { method: "POST", body }),

  submitForReview: (linkId: number) =>
    apiFetch<BaselineImageLink>(`${BASE}/images/${linkId}/submit-for-review`, { method: "POST" }),

  review: (linkId: number, body: ReviewInput) =>
    apiFetch<BaselineImageReview>(`${BASE}/images/${linkId}/review`, { method: "POST", body }),

  activate: (linkId: number) =>
    apiFetch<BaselineImageLink>(`${BASE}/images/${linkId}/activate`, { method: "POST" }),

  suspend: (linkId: number, reason: string) =>
    apiFetch<BaselineImageLink>(`${BASE}/images/${linkId}/suspend`, { method: "POST", body: { reason } }),

  archive: (linkId: number) =>
    apiFetch<BaselineImageLink>(`${BASE}/images/${linkId}/archive`, { method: "POST" }),

  supersede: (linkId: number, newLinkId: number) =>
    apiFetch<{ superseded: BaselineImageLink; active: BaselineImageLink }>(
      `${BASE}/images/${linkId}/supersede`, { method: "POST", body: { new_link_id: newLinkId } },
    ),

  auditHistory: (linkId: number) =>
    apiFetch<{ count: number; events: AuditEvent[] }>(`${BASE}/images/${linkId}/audit-history`),

  compatibilityCheck: (candidate: CandidateContext, baselineImageLinkId?: number) => {
    const qs = baselineImageLinkId != null ? `?baseline_image_link_id=${baselineImageLinkId}` : "";
    return apiFetch<{ status: string }>(`${BASE}/compatibility-check${qs}`, { method: "POST", body: candidate });
  },

  resolve: (candidate: CandidateContext, requireExact = false) =>
    apiFetch<ResolutionResult>(`${BASE}/resolve?require_exact=${requireExact}`, { method: "POST", body: candidate }),

  createSet: (body: {
    manufacturer?: string; model_name?: string; instrument_family?: string; anatomy_zone?: string;
    view_protocol?: string; orientation_protocol?: string; version?: string; limitations?: string;
    baseline_image_link_ids?: number[];
  }) => apiFetch<BaselineSet>(`${BASE}/sets`, { method: "POST", body }),

  getSet: (setId: number) => apiFetch<BaselineSet>(`${BASE}/sets/${setId}`),

  legacyReport: () => apiFetch<LegacyBaselineReport>(`${BASE}/legacy-report`),
};

export function formatLifecycleLabel(status: string): string {
  return status
    .split("_")
    .map((p) => p.charAt(0) + p.slice(1).toLowerCase())
    .join(" ");
}
