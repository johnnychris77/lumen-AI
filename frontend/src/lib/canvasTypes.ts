// Project Canvas — shared types for the Image Ingestion, Annotation &
// Ground-Truth Workspace. Mirrors the backend response shapes exactly
// (app.routes.dataset_registry / dataset_ingestion / annotation_database /
// reviewer_queues / dataset_eligibility / review_workspace / dataset_release)
// rather than inventing a parallel client-side schema.

export const OBSERVATION_TAXONOMY: { value: string; label: string }[] = [
  { value: "probable_blood_like_residue", label: "Probable blood-like residue" },
  { value: "probable_tissue_or_organic_residue", label: "Probable tissue or organic residue" },
  { value: "probable_bone_fragment", label: "Probable bone fragment" },
  { value: "probable_retained_debris", label: "Probable retained debris" },
  { value: "probable_corrosion_like_degradation", label: "Probable corrosion-like degradation" },
  { value: "probable_lint_or_fiber", label: "Probable lint or fiber" },
  { value: "probable_plastic_or_insulation_fragment", label: "Probable plastic or insulation fragment" },
  { value: "probable_unknown_foreign_material", label: "Probable unknown foreign material" },
  { value: "no_observable_abnormality", label: "No observable abnormality" },
  { value: "insufficient_image_quality", label: "Insufficient image quality" },
];

export const IMAGE_TYPES: { value: string; label: string }[] = [
  { value: "baseline_reference", label: "Baseline reference" },
  { value: "after_use", label: "After use" },
  { value: "after_cleaning", label: "After cleaning" },
  { value: "after_recleaning", label: "After re-cleaning" },
  { value: "post_repair", label: "Post repair" },
  { value: "unknown_context", label: "Unknown context" },
  { value: "research_reference", label: "Research reference" },
];

export const IMAGE_QUALITY_LEVELS = ["Excellent", "Good", "Marginal", "Poor", "Reject"] as const;

export const REGION_TYPES: { value: string; label: string }[] = [
  { value: "whole_image_classification", label: "Whole-image classification" },
  { value: "bounding_box", label: "Bounding box" },
  { value: "polygon", label: "Polygon" },
  { value: "point", label: "Point" },
  { value: "segmentation_mask", label: "Segmentation mask" },
];

export interface DatasetEntry {
  id: number;
  lcid: string;
  digital_twin_id?: string;
  baseline_id?: number | null;
  dataset_version_id: number;
  dataset_version_label?: string;
  retained_image_id: number;
  instrument_family: string;
  instrument_model: string;
  manufacturer: string;
  instrument_id?: string;
  catalog_number?: string;
  anatomy_zone: string;
  inspection_region?: string;
  image_type?: string;
  image_quality: string;
  review_status: string;
  usage_rights: string;
  phi_verification: string;
  training_eligibility?: boolean;
  reviewer_notes?: string;
  facility?: string;
  operator?: string;
  current_label?: string;
}

export interface AnnotationRecord {
  id: number;
  ann_id: string;
  retained_image_id: number;
  inspection_id: number | null;
  instrument_family: string;
  instrument_model: string;
  manufacturer: string;
  digital_twin_id: string;
  baseline_id: number | null;
  reviewer: string;
  dataset_version_id: number | null;
  ground_truth_version: number;
  model_version: string;
  primary_observation: string;
  secondary_observation: string;
  appearance_attributes: string[];
  severity: string;
  location: string;
  confidence: number | null;
  reviewer_confidence: number | null;
  comments: string;
  recommendation: string;
  supervisor_required: boolean;
  unknown_flag: boolean;
  image_quality: string;
  region_type: string;
  region_coordinates: number[];
  review_status: string;
  ground_truth_status: "DRAFT" | "ACTIVE";
  current_version: number;
  baseline_type: string;
  baseline_version: string;
  baseline_similarity: number | null;
  baseline_deviation: number | null;
}

export interface AnnotationReview {
  id: number;
  annotation_id: number;
  primary_reviewer: string;
  primary_label: string;
  secondary_reviewer: string;
  secondary_label: string;
  agreement: boolean | null;
  disagreement_reason: string;
  adjudicator: string;
  resolution: string;
  resolved_at: string | null;
}

export interface QueueItem {
  id: number;
  ann_id?: string;
  lcid?: string;
  reviewer?: string;
  primary_reviewer?: string;
  secondary_reviewer?: string;
  agreement?: boolean | null;
  primary_observation?: string;
  ground_truth_status?: string;
  missing_fields?: string[];
  eligibility_reason?: string;
  disagreement_reason?: string;
  instrument_family?: string;
  manufacturer?: string;
  image_type?: string;
  review_status?: string;
  image_quality?: string;
  usage_rights?: string;
}

export interface ReviewerQueues {
  counts: Record<string, number>;
  queues: Record<string, QueueItem[]>;
}

export interface EligibilityEntry {
  id: number;
  lcid: string;
  eligibility: string;
  reason: string;
  review_status: string;
  image_quality: string;
  usage_rights: string;
  phi_verification: string;
  training_eligibility: boolean;
  split_assignment: string;
}

export interface EligibilityReport {
  entries_checked: number;
  counts: Record<string, number>;
  entries: EligibilityEntry[];
}

export const ELIGIBILITY_LABELS: Record<string, string> = {
  not_reviewed: "Not reviewed",
  review_in_progress: "Review in progress",
  ground_truth_approved: "Ground Truth approved",
  excluded_from_training: "Excluded from training",
  eligible_for_training: "Eligible for training",
  eligible_for_validation: "Eligible for validation",
  eligible_for_testing: "Eligible for testing",
  research_only: "Research only",
  rights_restricted: "Rights restricted",
  archived: "Archived",
};
