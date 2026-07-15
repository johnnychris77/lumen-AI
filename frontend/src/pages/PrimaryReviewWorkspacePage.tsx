import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, ClipboardCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { apiFetch, ApiError } from "@/lib/api";
import { OBSERVATION_TAXONOMY } from "@/lib/canvasTypes";
import type { QueueItem, ReviewerQueues } from "@/lib/canvasTypes";

// Project Canvas — Section 9: Primary Review Workspace. Draws its queue
// straight from `/api/reviewer-queues` (Section 20) rather than a second,
// fabricated assignment list.
export default function PrimaryReviewWorkspacePage() {
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [label, setLabel] = useState("");
  const [confidence, setConfidence] = useState("");
  const [comments, setComments] = useState("");
  const [dirty, setDirty] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setQueue(null);
    apiFetch<ReviewerQueues>("/api/reviewer-queues")
      .then((r) => setQueue(r.queues.primary_review_due))
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Failed to load the primary review queue."));
  }

  useEffect(load, []);

  useEffect(() => {
    function handler(e: BeforeUnloadEvent) {
      if (dirty) { e.preventDefault(); e.returnValue = ""; }
    }
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  function selectItem(id: number) {
    if (dirty && !window.confirm("Discard your unsaved review notes for the current annotation?")) return;
    setSelected(id); setLabel(""); setConfidence(""); setComments(""); setDirty(false); setResult(null);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) return;
    if (!label) {
      setResult({ type: "error", message: "Select an observation category before submitting." });
      return;
    }
    setSubmitting(true);
    setResult(null);
    try {
      await apiFetch(`/api/annotations/${selected}/review/primary`, {
        method: "POST",
        body: { label, confidence: confidence ? Number(confidence) : null, comments },
      });
      setResult({ type: "success", message: "Primary review submitted." });
      setDirty(false);
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
        <ClipboardCheck className="h-6 w-6 text-blue-600" />
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Primary Review Workspace</h2>
          <p className="text-sm text-slate-500 mt-0.5">Annotations awaiting a first independent review.</p>
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
        <p className="text-sm text-slate-500 text-center py-12">No annotations are awaiting primary review.</p>
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
                      <span className="text-slate-700">{item.primary_observation || "unclassified"}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader><CardTitle className="text-base">{selected ? `Reviewing annotation #${selected}` : "Select an annotation"}</CardTitle></CardHeader>
            <CardContent>
              {!selected && <p className="text-sm text-slate-400">Choose an item from the queue to begin.</p>}
              {selected && (
                <>
                  <Link to={`/annotations/${selected}`} className="text-xs text-blue-600 hover:underline">View full annotation context</Link>
                  <form onSubmit={submit} className="space-y-4 mt-3" onChange={() => setDirty(true)}>
                    {result && (
                      <div role="alert" className={`flex items-start gap-2 rounded-lg border p-2.5 text-sm ${result.type === "success" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-800"}`}>
                        {result.type === "success" ? <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" /> : <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />}
                        <p>{result.message}</p>
                      </div>
                    )}
                    <div>
                      <Label>Observation classification *</Label>
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
                      Submit Primary Review
                    </Button>
                  </form>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
