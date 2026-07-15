import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { apiFetch, ApiError } from "@/lib/api";
import type { AnnotationRecord, QueueItem, ReviewerQueues } from "@/lib/canvasTypes";

// Project Canvas — Section 13: Ground Truth Workspace. Every bucket here
// maps to a real, already-governed state — no "excluded"/"insufficient
// evidence" bucket is fabricated where the schema doesn't track one.
export default function GroundTruthWorkspacePage() {
  const [eligible, setEligible] = useState<QueueItem[] | null>(null);
  const [awaitingAdjudication, setAwaitingAdjudication] = useState<QueueItem[] | null>(null);
  const [active, setActive] = useState<AnnotationRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [promoting, setPromoting] = useState<number | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; message: string } | null>(null);

  function load() {
    apiFetch<ReviewerQueues>("/api/reviewer-queues")
      .then((r) => {
        setEligible(r.queues.ground_truth_eligible);
        setAwaitingAdjudication(r.queues.adjudication_due);
      })
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Failed to load Ground Truth queues."));

    apiFetch<{ count: number; annotations: AnnotationRecord[] }>("/api/annotations?ground_truth_status=ACTIVE")
      .then((r) => setActive(r.annotations))
      .catch(() => setActive([]));
  }

  useEffect(load, []);

  async function promote(id: number) {
    setPromoting(id);
    setMessage(null);
    try {
      await apiFetch(`/api/annotations/${id}/promote-ground-truth`, { method: "POST" });
      setMessage({ type: "success", message: `Annotation #${id} promoted to Ground Truth.` });
      load();
    } catch (e) {
      setMessage({ type: "error", message: e instanceof ApiError ? e.message : "Promotion failed." });
    } finally {
      setPromoting(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ShieldCheck className="h-6 w-6 text-emerald-600" />
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Ground Truth Workspace</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Promotion always requires independent reviewer agreement or completed clinical
            adjudication — never a UI shortcut.
          </p>
        </div>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" /><p>{error}</p>
        </div>
      )}
      {message && (
        <div role="alert" className={`flex items-start gap-3 rounded-lg border p-4 text-sm ${message.type === "success" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-800"}`}>
          {message.type === "success" ? <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" /> : <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />}
          <p>{message.message}</p>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Eligible for Promotion</CardTitle>
          <CardDescription>Independent agreement reached, or adjudication resolved.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {!eligible && <div className="p-4"><Spinner className="h-5 w-5" /></div>}
          {eligible && eligible.length === 0 && <p className="text-sm text-slate-400 p-4">Nothing is currently eligible.</p>}
          {eligible && eligible.length > 0 && (
            <ul className="divide-y divide-slate-100">
              {eligible.map((item) => (
                <li key={item.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                  <div>
                    <p className="font-mono text-sm text-slate-700">{item.ann_id}</p>
                    <p className="text-xs text-slate-500">{item.eligibility_reason}</p>
                  </div>
                  <Button size="sm" disabled={promoting === item.id} onClick={() => promote(item.id)}>
                    {promoting === item.id && <Spinner className="h-4 w-4" />}
                    Promote
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Awaiting Adjudication</CardTitle>
          <CardDescription>Disagreements blocking promotion until resolved.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {!awaitingAdjudication && <div className="p-4"><Spinner className="h-5 w-5" /></div>}
          {awaitingAdjudication && awaitingAdjudication.length === 0 && <p className="text-sm text-slate-400 p-4">Nothing awaiting adjudication.</p>}
          {awaitingAdjudication && awaitingAdjudication.length > 0 && (
            <ul className="divide-y divide-slate-100">
              {awaitingAdjudication.map((item) => (
                <li key={item.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                  <p className="font-mono text-sm text-slate-700">{item.ann_id}</p>
                  <Link to="/review/adjudication" className="text-sm text-blue-600 hover:underline">Adjudicate</Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Active Ground Truth</CardTitle>
          <CardDescription>Currently ACTIVE and usable in a governed dataset release.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {!active && <div className="p-4"><Spinner className="h-5 w-5" /></div>}
          {active && active.length === 0 && <p className="text-sm text-slate-400 p-4">No active Ground Truth annotations yet.</p>}
          {active && active.length > 0 && (
            <ul className="divide-y divide-slate-100">
              {active.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                  <div>
                    <Link to={`/annotations/${a.id}`} className="font-mono text-sm text-blue-600 hover:underline">{a.ann_id}</Link>
                    <span className="text-xs text-slate-500 ml-2">{a.primary_observation}</span>
                  </div>
                  <Badge variant="success">v{a.ground_truth_version}</Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
