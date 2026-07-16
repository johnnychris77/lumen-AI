import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, GitCompareArrows } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { apiFetch, ApiError } from "@/lib/api";
import type { QueueItem, ReviewerQueues } from "@/lib/canvasTypes";

// Project Canvas — Section 11: Agreement and Disagreement. Reads the
// `disagreement` bucket from the shared reviewer-queues endpoint (Section
// 20) — the same data the Adjudication workspace resolves.
export default function DisagreementQueuePage() {
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ReviewerQueues>("/api/reviewer-queues")
      .then((r) => setQueue(r.queues.disagreement))
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Failed to load the disagreement queue."));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <GitCompareArrows className="h-6 w-6 text-amber-600" />
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Disagreements</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Annotations where the primary and secondary reviewers did not agree. Ground Truth
            promotion is blocked until a clinical adjudicator resolves each one.
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
          <Spinner className="h-5 w-5" /> <span className="text-sm">Loading disagreement queue…</span>
        </div>
      )}

      {queue && queue.length === 0 && (
        <p className="text-sm text-slate-500 text-center py-12">No open disagreements.</p>
      )}

      {queue && queue.length > 0 && (
        <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
          {queue.map((item) => (
            <div key={item.id} className="flex items-center justify-between gap-4 px-4 py-3">
              <div>
                <p className="font-mono text-sm text-slate-700">{item.ann_id}</p>
                <p className="text-xs text-slate-500">
                  {item.primary_reviewer} vs {item.secondary_reviewer}
                  {item.disagreement_reason ? ` — ${item.disagreement_reason}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant="warning">Disagreement</Badge>
                <Link to="/review/adjudication" className="text-sm text-blue-600 hover:underline">Adjudicate</Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
