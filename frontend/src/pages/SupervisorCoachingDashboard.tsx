import { useState, useEffect, useCallback } from "react";
import { ClipboardCheck } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface QueueItem {
  inspection_id: number;
  instrument_type: string;
  technician: string | null;
  risk_level: string | null;
  recommended_action: string | null;
  coaching_reviewed: boolean;
}

interface Effectiveness {
  total_reviews: number;
  approved_unchanged: number;
  edited: number;
  with_educational_comment: number;
  approved_unchanged_pct: number | null;
}

export default function SupervisorCoachingDashboard() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [effectiveness, setEffectiveness] = useState<Effectiveness | null>(null);
  const [loading, setLoading] = useState(true);
  const [comment, setComment] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [q, e] = await Promise.all([
        apiFetch<{ queue: QueueItem[] }>("/api/mentor/coaching-queue"),
        apiFetch<Effectiveness>("/api/mentor/coaching-effectiveness"),
      ]);
      setQueue(q.queue);
      setEffectiveness(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function review(inspectionId: number, approved: boolean) {
    setBusy(inspectionId);
    try {
      await apiFetch(`/api/inspections/${inspectionId}/coaching-review`, {
        method: "POST",
        body: { approved, educational_comment: comment[inspectionId] ?? "" },
      });
      await load();
    } finally {
      setBusy(null);
    }
  }

  if (loading) {
    return <div className="p-6 text-sm text-slate-500">Loading coaching dashboard…</div>;
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-4">
      <div className="flex items-center gap-2">
        <ClipboardCheck className="h-6 w-6 text-indigo-600" />
        <h1 className="text-xl font-bold text-slate-900">Supervisor Coaching Dashboard</h1>
      </div>
      <p className="text-sm text-slate-500">
        Review the AI Mentor's coaching on recent inspections — approve it, or add an educational
        comment for the technician.
      </p>

      {effectiveness && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 rounded-lg border border-slate-200 bg-white p-4">
          <div><div className="text-xs text-slate-500">Total reviews</div><div className="text-xl font-bold text-slate-900">{effectiveness.total_reviews}</div></div>
          <div><div className="text-xs text-slate-500">Approved unchanged</div><div className="text-xl font-bold text-emerald-700">{effectiveness.approved_unchanged}</div></div>
          <div><div className="text-xs text-slate-500">Edited</div><div className="text-xl font-bold text-amber-700">{effectiveness.edited}</div></div>
          <div><div className="text-xs text-slate-500">With comment</div><div className="text-xl font-bold text-slate-900">{effectiveness.with_educational_comment}</div></div>
        </div>
      )}

      <div className="space-y-2">
        {queue.map((item) => (
          <div key={item.inspection_id} className="rounded-lg border border-slate-200 bg-white p-4 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-sm">
                <span className="font-semibold capitalize text-slate-800">{item.instrument_type}</span>
                <span className="text-slate-400"> · #{item.inspection_id}</span>
                {item.technician && <span className="text-slate-500"> · {item.technician}</span>}
              </div>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${item.coaching_reviewed ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                {item.coaching_reviewed ? "Reviewed" : "Awaiting review"}
              </span>
            </div>
            <p className="text-sm text-slate-600">{item.recommended_action ?? "—"}</p>
            <input
              type="text"
              placeholder="Add an educational comment for the technician…"
              value={comment[item.inspection_id] ?? ""}
              onChange={(e) => setComment((c) => ({ ...c, [item.inspection_id]: e.target.value }))}
              className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
            />
            <div className="flex gap-2">
              <button
                onClick={() => review(item.inspection_id, true)}
                disabled={busy === item.inspection_id}
                className="rounded bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
              >
                Approve
              </button>
              <button
                onClick={() => review(item.inspection_id, false)}
                disabled={busy === item.inspection_id}
                className="rounded bg-slate-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
              >
                Flag for edit
              </button>
            </div>
          </div>
        ))}
        {queue.length === 0 && <p className="text-sm text-slate-400">No inspections in the coaching queue.</p>}
      </div>
    </div>
  );
}
