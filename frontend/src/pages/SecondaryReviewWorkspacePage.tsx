import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, EyeOff } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { AuthenticatedImage } from "@/components/ui/authenticated-image";
import { apiFetch, ApiError } from "@/lib/api";
import { OBSERVATION_TAXONOMY } from "@/lib/canvasTypes";
import type { QueueItem, ReviewerQueues } from "@/lib/canvasTypes";

interface BlindView {
  annotation_id: number;
  retained_image_id: number;
  instrument_family: string;
  manufacturer: string;
  image_quality: string;
  annotation_instructions: string;
  eligible_to_submit_secondary: boolean;
  blocked_reason: string;
}

// Project Canvas — Section 10: Blind Secondary Review Workspace. The
// backend's `/review/secondary/blind-view` response never contains the
// primary reviewer's label/confidence/comments/agreement — reviewer
// independence is enforced server-side, not by this component hiding a field.
export default function SecondaryReviewWorkspacePage() {
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [view, setView] = useState<BlindView | null>(null);
  const [label, setLabel] = useState("");
  const [confidence, setConfidence] = useState("");
  const [comments, setComments] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setQueue(null);
    apiFetch<ReviewerQueues>("/api/reviewer-queues")
      .then((r) => setQueue(r.queues.secondary_review_due))
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Failed to load the secondary review queue."));
  }

  useEffect(load, []);

  function selectItem(id: number) {
    setSelected(id); setLabel(""); setConfidence(""); setComments(""); setResult(null); setView(null);
    apiFetch<BlindView>(`/api/annotations/${id}/review/secondary/blind-view`)
      .then(setView)
      .catch((e: unknown) => setResult({ type: "error", message: e instanceof ApiError ? e.message : "Failed to load blind review context." }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) return;
    if (!label) {
      setResult({ type: "error", message: "Select an observation category before submitting." });
      return;
    }
    setSubmitting(true);
    try {
      await apiFetch(`/api/annotations/${selected}/review/secondary`, {
        method: "POST",
        body: { label, confidence: confidence ? Number(confidence) : null, comments },
      });
      setResult({ type: "success", message: "Secondary review submitted." });
      setLabel(""); setConfidence(""); setComments("");
      load();
    } catch (err) {
      setResult({ type: "error", message: err instanceof ApiError ? err.message : "Submission failed." });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <EyeOff className="h-6 w-6 text-blue-600" />
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Secondary (Blind) Review Workspace</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            You will never see the primary reviewer's classification, confidence, or comments
            before submitting your own independent assessment.
          </p>
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

      {queue && queue.length === 0 && !selected && (
        <p className="text-sm text-slate-500 text-center py-12">No annotations are awaiting secondary review.</p>
      )}

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
            <CardHeader><CardTitle className="text-base">{selected ? "Blind Review" : "Select an annotation"}</CardTitle></CardHeader>
            <CardContent>
              {!selected && <p className="text-sm text-slate-400">Choose an item from the queue to begin.</p>}
              {selected && !view && <Spinner className="h-5 w-5" />}
              {selected && view && !view.eligible_to_submit_secondary && (
                <div role="alert" className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" /><p>{view.blocked_reason}</p>
                </div>
              )}
              {selected && view && view.eligible_to_submit_secondary && (
                <div className="space-y-4">
                  <AuthenticatedImage retainedImageId={view.retained_image_id} alt="Image under review" className="w-full h-56 object-contain rounded-lg border border-slate-200 bg-slate-950" />
                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-500">
                    <span>Instrument: {view.instrument_family || "—"}</span>
                    <span>Manufacturer: {view.manufacturer || "—"}</span>
                    <span>Image quality: {view.image_quality || "—"}</span>
                  </div>
                  {view.annotation_instructions && (
                    <p className="text-xs text-slate-500 italic">Instructions: {view.annotation_instructions}</p>
                  )}

                  {result && (
                    <div role="alert" className={`flex items-start gap-2 rounded-lg border p-2.5 text-sm ${result.type === "success" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-800"}`}>
                      {result.type === "success" ? <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" /> : <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />}
                      <p>{result.message}</p>
                    </div>
                  )}
                  {result?.type !== "success" && (
                    <form onSubmit={submit} className="space-y-4">
                      <div>
                        <Label>Your independent observation classification *</Label>
                        <Select value={label} onChange={(e) => setLabel(e.target.value)} required>
                          <option value="">Select…</option>
                          {OBSERVATION_TAXONOMY.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </Select>
                      </div>
                      <div>
                        <Label>Reviewer confidence (0–1)</Label>
                        <Input type="number" min={0} max={1} step={0.05} value={confidence} onChange={(e) => setConfidence(e.target.value)} />
                      </div>
                      <div>
                        <Label>Comments</Label>
                        <Textarea value={comments} onChange={(e) => setComments(e.target.value)} rows={3} />
                      </div>
                      <Button type="submit" disabled={submitting}>
                        {submitting && <Spinner className="h-4 w-4" />}
                        Submit Secondary Review
                      </Button>
                    </form>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
