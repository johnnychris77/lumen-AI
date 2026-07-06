/**
 * v1.9 — Production Error Logging (Deliverable 7).
 *
 * A thin, fire-and-forget client for POST /api/pilot/error-log. Never
 * throws and never blocks the caller's own error handling — logging a
 * failure must never itself become a second failure the user has to deal
 * with. `detail` must be a short, developer-facing reason (an exception
 * message or HTTP status) — never image data, patient/procedure
 * identifiers, or any other PHI.
 */
import { apiFetch } from "@/lib/api";

export type PilotErrorType =
  | "upload_failure"
  | "ai_analysis_failure"
  | "baseline_lookup_failure"
  | "role_permission_failure"
  | "report_generation_failure";

export function logPilotError(errorType: PilotErrorType, detail: string, inspectionId?: number): void {
  apiFetch("/api/pilot-deployment/error-log", {
    method: "POST",
    body: { error_type: errorType, detail: String(detail).slice(0, 500), inspection_id: inspectionId },
  }).catch(() => {
    // Logging itself must never surface a second error to the user.
  });
}
