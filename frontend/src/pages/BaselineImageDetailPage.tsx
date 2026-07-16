import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronRight, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { AuthenticatedImage } from "@/components/ui/authenticated-image";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import {
  baselineLibraryApi,
  formatLifecycleLabel,
  type AuditEvent,
  type BaselineImageLink,
} from "@/lib/baselineLibraryApi";

const REVIEW_ROLES = new Set(["admin", "spd_manager", "clinical_reviewer"]);
const CREATE_ROLES = new Set(["admin", "spd_manager", "clinical_reviewer", "operator"]);

function statusVariant(status: string): "success" | "warning" | "destructive" | "secondary" | "outline" {
  if (status === "ACTIVE") return "success";
  if (status === "PENDING_REVIEW" || status === "SUSPENDED") return "warning";
  if (status === "REJECTED") return "destructive";
  if (status === "SUPERSEDED" || status === "ARCHIVED") return "secondary";
  return "outline";
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3 text-sm py-1">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-900 font-medium text-right">{value ?? "—"}</span>
    </div>
  );
}

export default function BaselineImageDetailPage() {
  const { baselineId } = useParams<{ baselineId: string }>();
  const { role } = useAuth();
  const [link, setLink] = useState<BaselineImageLink | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [actionBusy, setActionBusy] = useState("");

  const [rationale, setRationale] = useState("");
  const [reviewLimitations, setReviewLimitations] = useState("");
  const [sourceVerification, setSourceVerification] = useState("");
  const [anatomyConfirmed, setAnatomyConfirmed] = useState(false);
  const [qualityAssessment, setQualityAssessment] = useState("");

  const load = useCallback(async () => {
    if (!baselineId) return;
    setError("");
    try {
      const row = await baselineLibraryApi.getImage(Number(baselineId));
      setLink(row);
      const history = await baselineLibraryApi.auditHistory(Number(baselineId));
      setEvents(history.events);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load this baseline image.");
    }
  }, [baselineId]);

  useEffect(() => {
    load();
  }, [load]);

  async function runAction(name: string, fn: () => Promise<unknown>) {
    setActionBusy(name);
    setActionError("");
    try {
      await fn();
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : `Failed to ${name}.`);
    } finally {
      setActionBusy("");
    }
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center" role="alert">
        <ShieldAlert className="h-8 w-8 text-red-400" />
        <p className="text-sm text-slate-600">{error}</p>
        <Link to="/baselines/library" className="text-sm text-blue-600 hover:underline">Back to Baseline Library</Link>
      </div>
    );
  }

  if (!link) {
    return (
      <div className="flex items-center justify-center gap-3 py-20 text-slate-500">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading baseline image…</span>
      </div>
    );
  }

  const latestReviewEvent = events.find((e) => e.action_type === "baseline_image_approved" || e.action_type === "baseline_image_rejectd" || e.action_type === "baseline_image_rejected");

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/baselines/library" className="hover:text-slate-600">Baseline Library</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-600 font-medium">Baseline image #{link.id}</span>
      </nav>

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">
            Baseline image #{link.id} <Badge variant={statusVariant(link.lifecycle_status)} className="ml-2 align-middle">{formatLifecycleLabel(link.lifecycle_status)}</Badge>
          </h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {link.manufacturer || "Unknown manufacturer"} {link.model_name} · {link.anatomy_zone || "no anatomy zone"} ·{" "}
            {link.inspection_view || "no view"} · version {link.baseline_version}
          </p>
        </div>
      </div>

      {actionError && <Alert variant="destructive"><AlertDescription>{actionError}</AlertDescription></Alert>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle className="text-base">Baseline Image</CardTitle></CardHeader>
          <CardContent>
            {link.retained_image_id ? (
              <div className="w-full h-72 overflow-hidden rounded-lg border border-slate-200 bg-slate-950 flex items-center justify-center">
                <AuthenticatedImage
                  retainedImageId={link.retained_image_id}
                  alt={`Baseline image ${link.id}`}
                  className="max-h-72 max-w-full object-contain"
                />
              </div>
            ) : (
              <div className="w-full h-72 rounded-lg border border-dashed border-slate-300 flex items-center justify-center text-sm text-slate-400">
                No retained image bytes reference — this baseline image cannot be displayed or compared.
              </div>
            )}
            <p className="text-xs text-slate-400 mt-2 font-mono break-all">SHA-256: {link.image_sha256 || "not recorded"}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Provenance &amp; Governance</CardTitle></CardHeader>
          <CardContent>
            <Row label="LCID image ID" value={link.lcid_image_id} />
            <Row label="Baseline entry" value={`#${link.baseline_library_entry_id}`} />
            <Row label="Image type" value={link.image_type.replace(/_/g, " ")} />
            <Row label="Source type" value={link.source_type.replace(/_/g, " ")} />
            <Row label="Source organization" value={link.source_organization} />
            <Row label="Source reference" value={link.source_reference} />
            <Row label="Orientation" value={link.orientation} />
            <Row label="Approved by" value={link.approved_by} />
            <Row label="Approved at" value={link.approved_at ? new Date(link.approved_at).toLocaleString() : "—"} />
            <Row label="Usage rights" value={link.usage_rights_status} />
            <Row label="Image quality" value={link.image_quality_status} />
            <Row label="Digital Twin" value={link.digital_twin_id || "Untracked"} />
            {link.supersedes_link_id && (
              <Row label="Supersedes" value={<Link className="text-blue-600 hover:underline" to={`/baselines/library/${link.supersedes_link_id}`}>#{link.supersedes_link_id}</Link>} />
            )}
            {link.superseded_by && <Row label="Superseded by" value={link.superseded_by} />}
            {link.limitations && (
              <div className="mt-2 pt-2 border-t border-slate-100">
                <p className="text-xs font-medium text-slate-500 mb-1">Limitations</p>
                <p className="text-sm text-slate-700">{link.limitations}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Latest Review</CardTitle></CardHeader>
          <CardContent>
            {!latestReviewEvent && <p className="text-sm text-slate-400">No review decision recorded yet.</p>}
            {latestReviewEvent && (
              <>
                <Row label="Decision" value={latestReviewEvent.action_type === "baseline_image_approved" ? "Approved" : "Rejected"} />
                <Row label="Reviewer" value={latestReviewEvent.actor_email} />
                <Row label="Reviewer role" value={latestReviewEvent.actor_role} />
                <Row label="Date" value={new Date(latestReviewEvent.created_at).toLocaleString()} />
                {latestReviewEvent.details && (
                  <>
                    <Row label="Rationale" value={String(latestReviewEvent.details.rationale ?? "—")} />
                    <Row label="Limitations" value={String(latestReviewEvent.details.limitations ?? "—")} />
                  </>
                )}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Audit History</CardTitle></CardHeader>
          <CardContent>
            {events.length === 0 && <p className="text-sm text-slate-400">No audit events recorded yet.</p>}
            <ol className="space-y-2">
              {events.map((e, i) => (
                <li key={i} className="flex items-center justify-between gap-2 text-xs border-t border-slate-100 pt-2 first:border-0 first:pt-0">
                  <span className="text-slate-700 font-medium">{e.action_type.replace(/_/g, " ")}</span>
                  <span className="text-slate-500">{e.actor_email || "system"}</span>
                  <span className="text-slate-400">{new Date(e.created_at).toLocaleString()}</span>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>

      {/* Lifecycle actions */}
      <Card>
        <CardHeader><CardTitle className="text-base">Lifecycle Actions</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {link.lifecycle_status === "DRAFT" && CREATE_ROLES.has(role) && (
            <Button disabled={actionBusy !== ""} onClick={() => runAction("submit for review", () => baselineLibraryApi.submitForReview(link.id))}>
              {actionBusy === "submit for review" ? "Submitting…" : "Submit for review"}
            </Button>
          )}

          {link.lifecycle_status === "PENDING_REVIEW" && REVIEW_ROLES.has(role) && (
            <div className="space-y-3 max-w-xl">
              <label className="block">
                <span className="text-xs font-medium text-slate-600 mb-1 block">Rationale (required)</span>
                <textarea value={rationale} onChange={(e) => setRationale(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 min-h-20" />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-slate-600 mb-1 block">Limitations</span>
                <textarea value={reviewLimitations} onChange={(e) => setReviewLimitations(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 min-h-16" />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-slate-600 mb-1 block">Source verification notes</span>
                <textarea value={sourceVerification} onChange={(e) => setSourceVerification(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 min-h-16" />
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={anatomyConfirmed} onChange={(e) => setAnatomyConfirmed(e.target.checked)} />
                Anatomy zone / view compatibility confirmed
              </label>
              <label className="block">
                <span className="text-xs font-medium text-slate-600 mb-1 block">Image quality assessment</span>
                <select value={qualityAssessment} onChange={(e) => setQualityAssessment(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900">
                  <option value="">Not assessed</option>
                  <option value="excellent">Excellent</option>
                  <option value="acceptable">Acceptable</option>
                  <option value="poor">Poor</option>
                  <option value="reject">Reject</option>
                </select>
              </label>
              <div className="flex gap-3">
                <Button
                  disabled={actionBusy !== "" || !rationale.trim()}
                  onClick={() =>
                    runAction("approve", () =>
                      baselineLibraryApi.review(link.id, {
                        decision: "approve", rationale, limitations: reviewLimitations,
                        source_verification: sourceVerification, anatomy_compatibility_confirmed: anatomyConfirmed,
                        image_quality_assessment: qualityAssessment,
                      })
                    )
                  }
                >
                  {actionBusy === "approve" ? "Approving…" : "Approve"}
                </Button>
                <Button
                  variant="destructive"
                  disabled={actionBusy !== "" || !rationale.trim()}
                  onClick={() =>
                    runAction("reject", () =>
                      baselineLibraryApi.review(link.id, {
                        decision: "reject", rationale, limitations: reviewLimitations,
                        source_verification: sourceVerification, anatomy_compatibility_confirmed: anatomyConfirmed,
                        image_quality_assessment: qualityAssessment,
                      })
                    )
                  }
                >
                  {actionBusy === "reject" ? "Rejecting…" : "Reject"}
                </Button>
              </div>
            </div>
          )}

          {link.lifecycle_status === "APPROVED" && REVIEW_ROLES.has(role) && (
            <Button disabled={actionBusy !== ""} onClick={() => runAction("activate", () => baselineLibraryApi.activate(link.id))}>
              {actionBusy === "activate" ? "Activating…" : "Activate"}
            </Button>
          )}

          {link.lifecycle_status === "ACTIVE" && REVIEW_ROLES.has(role) && (
            <Button
              variant="outline"
              disabled={actionBusy !== ""}
              onClick={() => runAction("suspend", () => baselineLibraryApi.suspend(link.id, "Suspended from Baseline Library workspace."))}
            >
              {actionBusy === "suspend" ? "Suspending…" : "Suspend"}
            </Button>
          )}

          {link.lifecycle_status === "SUSPENDED" && REVIEW_ROLES.has(role) && (
            <Button disabled={actionBusy !== ""} onClick={() => runAction("activate", () => baselineLibraryApi.activate(link.id))}>
              {actionBusy === "activate" ? "Reactivating…" : "Reactivate"}
            </Button>
          )}

          {!["ARCHIVED", "SUPERSEDED"].includes(link.lifecycle_status) && REVIEW_ROLES.has(role) && (
            <Button variant="outline" disabled={actionBusy !== ""} onClick={() => runAction("archive", () => baselineLibraryApi.archive(link.id))}>
              {actionBusy === "archive" ? "Archiving…" : "Archive"}
            </Button>
          )}

          {!REVIEW_ROLES.has(role) && link.lifecycle_status !== "DRAFT" && (
            <p className="text-xs text-slate-400">Your role ({role || "viewer"}) can view this baseline image but not change its lifecycle state.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
