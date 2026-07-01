import { useState } from "react";
import { useAuth, API_BASE } from "@/lib/auth";

/**
 * Supervisor Review Notes — human-in-the-loop AI agreement capture.
 * Role-gated at the call site (admin/spd_manager); the backend also enforces it.
 * A comment is required for partial agreement, disagreement, or override.
 */
const AGREEMENT_OPTIONS = [
  { value: "agree", label: "Agree with AI" },
  { value: "partially_agree", label: "Partially agree" },
  { value: "disagree", label: "Disagree with AI" },
];

export default function SupervisorNotes({
  inspectionId,
  onSubmitted,
}: {
  inspectionId?: number;
  onSubmitted?: () => void;
}) {
  const { headers } = useAuth();
  const [agreement, setAgreement] = useState("agree");
  const [rationale, setRationale] = useState("");
  const [override, setOverride] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const commentRequired = agreement !== "agree" || !!override.trim();

  async function submit() {
    if (!inspectionId) return;
    if (commentRequired && !rationale.trim()) {
      setMsg({ ok: false, text: "A comment is required for partial agreement, disagreement, or override." });
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/inspections/${inspectionId}/supervisor-review`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ agreement, rationale: rationale.trim(), override_action: override.trim() }),
      });
      if (res.status === 403) { setMsg({ ok: false, text: "Supervisor access (admin/SPD manager) required." }); return; }
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        setMsg({ ok: false, text: b?.detail || `Submit failed (${res.status}).` });
        return;
      }
      setMsg({ ok: true, text: "Supervisor review recorded." });
      setRationale("");
      setOverride("");
      onSubmitted?.();
    } catch {
      setMsg({ ok: false, text: "Unable to reach the server." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Supervisor Review Notes</p>
      <div className="flex flex-wrap gap-2 mb-2">
        {AGREEMENT_OPTIONS.map((o) => (
          <button
            key={o.value}
            onClick={() => setAgreement(o.value)}
            className={`rounded-full px-3 py-1 text-xs font-medium border ${
              agreement === o.value ? "bg-blue-600 text-white border-blue-600" : "border-slate-300 text-slate-600"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
      <textarea
        value={rationale}
        onChange={(e) => setRationale(e.target.value)}
        placeholder={commentRequired ? "Rationale (required)" : "Rationale (optional)"}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        rows={2}
      />
      <input
        value={override}
        onChange={(e) => setOverride(e.target.value)}
        placeholder="Override action (optional, e.g. reprocess / remove)"
        className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
      />
      <div className="mt-2 flex items-center gap-3">
        <button onClick={submit} disabled={busy} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
          {busy ? "Saving…" : "Submit review"}
        </button>
        {msg && <span className={`text-sm ${msg.ok ? "text-emerald-700" : "text-red-700"}`}>{msg.text}</span>}
      </div>
      <p className="mt-2 text-xs text-slate-400">
        Feedback is stored as labeled training data. Operators/viewers cannot submit.
      </p>
    </div>
  );
}
