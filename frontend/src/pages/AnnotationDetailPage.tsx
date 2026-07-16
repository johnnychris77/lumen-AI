import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, CheckCircle2, History } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";
import type { AnnotationRecord, AnnotationReview } from "@/lib/canvasTypes";
import { OBSERVATION_TAXONOMY } from "@/lib/canvasTypes";
import { AuditTimeline } from "@/components/canvas/AuditTimeline";

const CAN_SEE_REVIEW_ROLES = ["admin", "clinical_reviewer"];

interface VersionEntry {
  version_number: number;
  editor: string;
  reason: string;
  timestamp: string;
}

export default function AnnotationDetailPage() {
  const { annotationId } = useParams<{ annotationId: string }>();
  const { role } = useAuth();
  const [annotation, setAnnotation] = useState<AnnotationRecord | null>(null);
  const [review, setReview] = useState<AnnotationReview | null>(null);
  const [versions, setVersions] = useState<VersionEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [promoting, setPromoting] = useState(false);
  const [promoteMsg, setPromoteMsg] = useState<{ type: "success" | "error"; message: string } | null>(null);

  function load() {
    if (!annotationId) return;
    apiFetch<AnnotationRecord>(`/api/annotations/${annotationId}`)
      .then(setAnnotation)
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Failed to load annotation."));

    apiFetch<{ count: number; versions: VersionEntry[] }>(`/api/annotations/${annotationId}/versions`)
      .then((r) => setVersions(r.versions))
      .catch(() => {});

    if (CAN_SEE_REVIEW_ROLES.includes(role)) {
      apiFetch<AnnotationReview>(`/api/annotations/${annotationId}/review`)
        .then(setReview)
        .catch(() => setReview(null));
    }
  }

  useEffect(load, [annotationId, role]);

  async function promote() {
    if (!annotationId) return;
    setPromoting(true);
    setPromoteMsg(null);
    try {
      await apiFetch(`/api/annotations/${annotationId}/promote-ground-truth`, { method: "POST" });
      setPromoteMsg({ type: "success", message: "Promoted to Ground Truth." });
      load();
    } catch (e) {
      setPromoteMsg({ type: "error", message: e instanceof ApiError ? e.message : "Promotion failed." });
    } finally {
      setPromoting(false);
    }
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center" role="alert">
        <AlertTriangle className="h-8 w-8 text-red-400" />
        <p className="text-sm text-slate-600">{error}</p>
        <Link to="/annotations" className="text-sm text-blue-600 hover:underline">Back to annotations</Link>
      </div>
    );
  }

  if (!annotation) {
    return (
      <div className="flex items-center justify-center gap-3 py-20 text-slate-500">
        <Spinner className="h-5 w-5" /> <span className="text-sm">Loading annotation…</span>
      </div>
    );
  }

  const taxonomyLabel = OBSERVATION_TAXONOMY.find((o) => o.value === annotation.primary_observation)?.label
    ?? annotation.primary_observation;
  const eligibleToPromote = CAN_SEE_REVIEW_ROLES.includes(role) &&
    annotation.ground_truth_status !== "ACTIVE" &&
    review !== null &&
    (review.agreement === true || (review.resolved_at !== null && !!review.resolution));

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold text-slate-900 font-mono">{annotation.ann_id}</h2>
          <p className="text-sm text-slate-500 mt-0.5">{taxonomyLabel || "No observation classified yet"}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={annotation.ground_truth_status === "ACTIVE" ? "success" : "secondary"}>
            {annotation.ground_truth_status === "ACTIVE" ? "Ground Truth (Active)" : "Draft"}
          </Badge>
          <Link to={`/dataset/images/${annotation.retained_image_id}`} className="text-sm text-blue-600 hover:underline">
            View source image
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle className="text-base">Observation Detail</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-slate-500">Severity</span><span>{annotation.severity || "—"}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Location</span><span>{annotation.location || "—"}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Confidence</span><span>{annotation.confidence ?? "—"}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Region type</span><span>{annotation.region_type.replace(/_/g, " ")}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Version</span><span>{annotation.current_version}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Annotator</span><span>{annotation.reviewer || "—"}</span></div>
            {annotation.region_coordinates.length > 0 && (
              <div>
                <span className="text-slate-500 block mb-1">Region coordinates</span>
                <Textarea readOnly value={JSON.stringify(annotation.region_coordinates)} rows={2} className="font-mono text-xs" />
              </div>
            )}
            <div>
              <span className="text-slate-500 block mb-1">Comments</span>
              <p className="text-slate-700">{annotation.comments || "None recorded."}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Review &amp; Ground Truth</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            {!CAN_SEE_REVIEW_ROLES.includes(role) && (
              <p className="text-xs text-slate-500">
                Full independent-review detail is restricted to Clinical Reviewer / Administrator
                roles to preserve secondary-reviewer blindness. Use the{" "}
                <Link to="/review/primary" className="text-blue-600 hover:underline">Primary Review</Link> or{" "}
                <Link to="/review/secondary" className="text-blue-600 hover:underline">Secondary Review</Link> workspace
                to act on this annotation.
              </p>
            )}
            {CAN_SEE_REVIEW_ROLES.includes(role) && review && (
              <>
                <div className="flex justify-between"><span className="text-slate-500">Primary reviewer</span><span>{review.primary_reviewer || "Not yet submitted"}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Secondary reviewer</span><span>{review.secondary_reviewer || "Not yet submitted"}</span></div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Agreement</span>
                  <span>{review.agreement === null ? "Pending" : review.agreement ? "Agreed" : "Disagreement"}</span>
                </div>
                {review.resolved_at && (
                  <div className="flex justify-between"><span className="text-slate-500">Adjudicated by</span><span>{review.adjudicator}</span></div>
                )}
              </>
            )}
            {CAN_SEE_REVIEW_ROLES.includes(role) && !review && (
              <p className="text-xs text-slate-400">No review has been started for this annotation yet.</p>
            )}

            {promoteMsg && (
              <div role="alert" className={`flex items-start gap-2 rounded-lg border p-2 text-xs ${promoteMsg.type === "success" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-800"}`}>
                {promoteMsg.type === "success" ? <CheckCircle2 className="h-3.5 w-3.5 mt-0.5 shrink-0" /> : <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />}
                <p>{promoteMsg.message}</p>
              </div>
            )}
            {eligibleToPromote && (
              <Button size="sm" onClick={promote} disabled={promoting}>
                {promoting && <Spinner className="h-4 w-4" />}
                Promote to Ground Truth
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <History className="h-4 w-4 text-slate-400" />
          <CardTitle className="text-base">Version History (append-only)</CardTitle>
        </CardHeader>
        <CardContent>
          {versions.length === 0 ? (
            <p className="text-sm text-slate-400">Only the initial version exists.</p>
          ) : (
            <ol className="space-y-2">
              {versions.map((v) => (
                <li key={v.version_number} className="text-sm border-l-2 border-slate-200 pl-3">
                  <p className="font-medium text-slate-800">v{v.version_number} — {v.editor}</p>
                  <p className="text-slate-500 text-xs">{v.reason} · {new Date(v.timestamp).toLocaleString()}</p>
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>

      <AuditTimeline resourceType="annotation" resourceId={annotation.ann_id} />
    </div>
  );
}
