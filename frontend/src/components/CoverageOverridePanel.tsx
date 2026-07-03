import { useState } from "react";
import { useAuth } from "@/lib/auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

/**
 * v1.2 §7 — Supervisor Override for insufficient coverage. Role-gated at the
 * call site (admin/spd_manager); the backend also enforces it. A reason
 * (min 10 chars) is required, matching the baseline-override pattern.
 */
export default function CoverageOverridePanel({
  inspectionId,
  onApplied,
}: {
  inspectionId: number;
  onApplied?: () => void;
}) {
  const { headers } = useAuth();
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit() {
    if (reason.trim().length < 10) {
      setMsg({ ok: false, text: "Reason must be at least 10 characters." });
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/inspections/${inspectionId}/coverage-override`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ reason: reason.trim() }),
      });
      if (res.status === 403) { setMsg({ ok: false, text: "Supervisor access (admin/SPD manager) required." }); return; }
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        setMsg({ ok: false, text: b?.detail || `Override failed (${res.status}).` });
        return;
      }
      setMsg({ ok: true, text: "Coverage override applied — inspection can proceed to a final decision." });
      onApplied?.();
    } catch {
      setMsg({ ok: false, text: "Unable to reach the server." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-red-300 bg-red-50 p-4 space-y-2">
      <p className="text-sm font-semibold text-red-900">Coverage Override Required</p>
      <p className="text-xs text-red-700">
        Org policy requires full anatomy-zone coverage before a final AI decision. A supervisor or admin can
        proceed anyway with a documented reason.
      </p>
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Reason for proceeding despite incomplete coverage (min 10 characters)…"
        rows={2}
        className="w-full rounded-lg border border-red-300 px-3 py-2 text-sm"
      />
      <div className="flex items-center gap-3">
        <button
          onClick={submit}
          disabled={busy}
          className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
        >
          {busy ? "Applying…" : "Apply Coverage Override"}
        </button>
        {msg && <span className={`text-sm ${msg.ok ? "text-emerald-700" : "text-red-700"}`}>{msg.text}</span>}
      </div>
    </div>
  );
}
