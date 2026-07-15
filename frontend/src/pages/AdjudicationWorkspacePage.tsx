import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Scale } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";
import type { AnnotationRecord, AnnotationReview, QueueItem, ReviewerQueues } from "@/lib/canvasTypes";

const ADJUDICATOR_ROLES = ["admin", "clinical_reviewer"];

// Project Canvas — Section 12: Adjudication Workspace. Compares both
// independent reviews (available to this workspace only because the role
// gate on `/annotations/{id}/review` restricts it to adjudicator roles —
// Section 10's blindness guarantee for plain reviewers is unaffected).
export default function AdjudicationWorkspacePage() {
  const { role } = useAuth();
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [annotation, setAnnotation] = useState<AnnotationRecord | null>(null);
  const [review, setReview] = useState<AnnotationReview | null>(null);
  const [resolution, setResolution] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setQueue(null);
    apiFetch<ReviewerQueues>("/api/reviewer-queues")
      .then((r) => setQueue(r.queues.adjudication_due))
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Failed to load the adjudication queue."));
  }

  useEffect(load, []);

  function selectItem(id: number) {
    setSelected(id); setResolution(""); setReason(""); setResult(null);
    apiFetch<AnnotationRecord>(`/api/annotations/${id}`).then(setAnnotation).catch(() => setAnnotation(null));
    apiFetch<AnnotationReview>(`/api/annotations/${id}/review`).then(setReview).catch(() => setReview(null));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) return;
    if (!resolution.trim() || !reason.trim()) {
      setResult({ type: "error", message: "Both a resolution and a rationale are required." });
      return;
    }
    setSubmitting(true);
    try {
      await apiFetch(`/api/annotations/${selected}/review/adjudicate`, {
        method: "POST",
        body: { resolution, reason },
      });
      setResult({ type: "success", message: "Adjudication recorded." });
      setResolution(""); setReason("");
      load();
    } catch (err) {
      setResult({ type: "error", message: err instanceof ApiError ? err.message : "Adjudication failed." });
    } finally {
      setSubmitting(false);
    }
  }

  if (!ADJUDICATOR_ROLES.includes(role)) {
    return (
      <div role="alert" className="mx-auto mt-16 max-w-md rounded-lg border border-slate-200 bg-white p-8 text-center">
        <h2 className="text-lg font-semibold text-slate-900">Not authorized</h2>
        <p className="mt-2 text-sm text-slate-600">
          Adjudication is restricted to Clinical Reviewer and Administrator roles.
        </p>
        <Link to="/" className="mt-4 inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Scale className="h-6 w-6 text-purple-600" />
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Adjudication Workspace</h2>
          <p className="text-sm text-slate-500 mt-0.5">Compare both independent reviews and record a clinical resolution.</p>
        </div>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" /><p>{error}</p>
        </div>
      )}

      {!queue && !error && (
        <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
          <Spinner className="h-5 w-5" /> <span className="text-sm">Loading queue…</span>
        </div>
      )}

      {queue && queue.length === 0 && !selected && <p className="text-sm text-slate-500 text-center py-12">No disagreements await adjudication.</p>}

      {queue && (queue.length > 0 || selected) && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-1">
            <CardHeader><CardTitle className="text-base">Queue ({queue.length})</CardTitle></CardHeader>
            <CardContent className="p-0">
              {queue.length === 0 && <p className="text-xs text-slate-400 px-4 py-3">Queue is now empty.</p>}
              <ul>
                {queue.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => selectItem(item.id)}
                      className={`w-full text-left px-4 py-2.5 border-t border-slate-100 text-sm hover:bg-slate-50 ${selected === item.id ? "bg-blue-50" : ""}`}
                    >
                      <span className="font-mono text-xs text-slate-500 block">{item.ann_id}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader><CardTitle className="text-base">{selected ? "Compare Reviews" : "Select a disagreement"}</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {selected && (!annotation || !review) && <Spinner className="h-5 w-5" />}
              {selected && annotation && review && (
                <>
                  <Link to={`/dataset/images/${annotation.retained_image_id}`} className="text-xs text-blue-600 hover:underline">
                    View source image and baseline context
                  </Link>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="rounded-lg border border-slate-200 p-3">
                      <p className="text-xs font-medium text-slate-500 mb-1">Primary — {review.primary_reviewer}</p>
                      <p className="text-sm text-slate-800">{review.primary_label || "—"}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-3">
                      <p className="text-xs font-medium text-slate-500 mb-1">Secondary — {review.secondary_reviewer}</p>
                      <p className="text-sm text-slate-800">{review.secondary_label || "—"}</p>
                    </div>
                  </div>
                  {review.disagreement_reason && (
                    <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-2">
                      {review.disagreement_reason}
                    </p>
                  )}

                  {result && (
                    <div role="alert" className={`flex items-start gap-2 rounded-lg border p-2.5 text-sm ${result.type === "success" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-800"}`}>
                      {result.type === "success" ? <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" /> : <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />}
                      <p>{result.message}</p>
                    </div>
                  )}
                  {result?.type !== "success" && (
                    <form onSubmit={submit} className="space-y-4 pt-2 border-t border-slate-100">
                      <div>
                        <Label>Adjudicated resolution *</Label>
                        <Input value={resolution} onChange={(e) => setResolution(e.target.value)} placeholder="Final classification / decision" required />
                      </div>
                      <div>
                        <Label>Rationale *</Label>
                        <Textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} required placeholder="Required — document the clinical reasoning for this resolution." />
                      </div>
                      <Button type="submit" disabled={submitting}>
                        {submitting && <Spinner className="h-4 w-4" />}
                        Record Adjudication
                      </Button>
                    </form>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
