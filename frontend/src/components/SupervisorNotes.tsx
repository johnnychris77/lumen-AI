import { useState } from "react";
import { useAuth, API_BASE } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

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
  const [zoneCorrect, setZoneCorrect] = useState<boolean | null>(null);
  const [correctedZone, setCorrectedZone] = useState("");
  const [familyCorrect, setFamilyCorrect] = useState<boolean | null>(null);
  const [correctedFamily, setCorrectedFamily] = useState("");
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
      const res = await apiFetch(`/api/inspections/${inspectionId}/supervisor-review`, { raw: true,
        method: "POST",
        headers: headers(),
        body: JSON.stringify({
          agreement,
          rationale: rationale.trim(),
          override_action: override.trim(),
          zone_correct: zoneCorrect,
          corrected_zone: correctedZone.trim(),
          instrument_family_correct: familyCorrect,
          corrected_instrument_family: correctedFamily.trim(),
        }),
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
      {/* Anatomy-family feedback → labeled training data */}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <span className="text-slate-500">AI instrument family correct?</span>
        <button onClick={() => setFamilyCorrect(true)} className={`rounded-full px-2 py-0.5 border ${familyCorrect === true ? "bg-emerald-600 text-white border-emerald-600" : "border-slate-300 text-slate-600"}`}>Yes</button>
        <button onClick={() => setFamilyCorrect(false)} className={`rounded-full px-2 py-0.5 border ${familyCorrect === false ? "bg-red-600 text-white border-red-600" : "border-slate-300 text-slate-600"}`}>No</button>
        {familyCorrect === false && (
          <input
            value={correctedFamily}
            onChange={(e) => setCorrectedFamily(e.target.value)}
            placeholder="Corrected family (e.g. flexible endoscope, drill bit)"
            className="flex-1 min-w-[10rem] rounded-lg border border-slate-300 px-2 py-1"
          />
        )}
      </div>
      {/* Zone-aware feedback → labeled training data */}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <span className="text-slate-500">AI zone correct?</span>
        <button onClick={() => setZoneCorrect(true)} className={`rounded-full px-2 py-0.5 border ${zoneCorrect === true ? "bg-emerald-600 text-white border-emerald-600" : "border-slate-300 text-slate-600"}`}>Yes</button>
        <button onClick={() => setZoneCorrect(false)} className={`rounded-full px-2 py-0.5 border ${zoneCorrect === false ? "bg-red-600 text-white border-red-600" : "border-slate-300 text-slate-600"}`}>No</button>
        {zoneCorrect === false && (
          <input
            value={correctedZone}
            onChange={(e) => setCorrectedZone(e.target.value)}
            placeholder="Corrected zone (e.g. hinge, box lock)"
            className="flex-1 min-w-[10rem] rounded-lg border border-slate-300 px-2 py-1"
          />
        )}
      </div>
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
