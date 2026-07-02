import { useState } from "react";
import { useAuth, API_BASE } from "@/lib/auth";

// Must match the inspection instrument types so a baseline lines up with the
// instrument an inspection is run against.
const INSTRUMENT_TYPES = [
  { value: "rigid_scope", label: "Rigid Scope / Endoscope" },
  { value: "flexible_endoscope", label: "Flexible Endoscope" },
  { value: "drill_bit", label: "Drill Bit / Reamer / Burr" },
  { value: "kerrison_rongeur", label: "Kerrison / Rongeur" },
  { value: "laparoscopic_grasper", label: "Laparoscopic Grasper" },
  { value: "scissors", label: "Scissors" },
  { value: "forceps", label: "Forceps" },
  { value: "needle_holder", label: "Needle Holder" },
  { value: "retractor", label: "Retractor" },
  { value: "trocar", label: "Trocar" },
  { value: "electrosurgical", label: "Electrosurgical" },
  { value: "suction_irrigation", label: "Suction / Irrigation" },
  { value: "clip_applier", label: "Clip Applier" },
  { value: "stapler", label: "Stapler" },
  { value: "other", label: "Other (type a new instrument type)" },
];

// Normalize a free-text instrument type to the slug convention the rest of the
// app uses (lowercase, underscores) so a custom baseline lines up with the
// instrument type an inspection is run against.
function slugifyType(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/tiff"];

export default function CreateManufacturerBaseline({ onCreated }: { onCreated?: () => void }) {
  const { headers, role, logout } = useAuth();
  const [instrumentType, setInstrumentType] = useState("");
  const [customType, setCustomType] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [model, setModel] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const canCreate = role === "admin" || role === "spd_manager";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBanner(null);
    if (!instrumentType || !manufacturer.trim() || !image) {
      setBanner({ type: "error", message: "Instrument type, manufacturer, and a baseline image are required." });
      return;
    }
    // Resolve the effective instrument type: a custom entry when "Other" is chosen.
    const effectiveType = instrumentType === "other" ? slugifyType(customType) : instrumentType;
    if (instrumentType === "other" && !effectiveType) {
      setBanner({ type: "error", message: "Enter the instrument type name for “Other”." });
      return;
    }

    setSubmitting(true);
    try {
      const hdrs = headers();

      // 1. Upload the baseline image (records SHA-256)
      const fd = new FormData();
      fd.append("images", image);
      const imgRes = await fetch(`${API_BASE}/api/baselines/upload-images`, {
        method: "POST",
        headers: { Authorization: hdrs["Authorization"] },
        body: fd,
      });
      if (imgRes.status === 401) {
        logout();
        return;
      }
      if (!imgRes.ok) {
        const e1 = await imgRes.json().catch(() => ({}));
        setBanner({ type: "error", message: e1?.detail || `Image upload failed (${imgRes.status}).` });
        return;
      }
      const imgData = await imgRes.json();
      const sha = imgData?.images?.[0]?.sha256;

      // 2. Create the approved manufacturer baseline keyed to the instrument type
      const res = await fetch(`${API_BASE}/api/baselines/manufacturer`, {
        method: "POST",
        headers: hdrs,
        body: JSON.stringify({
          instrument_type: effectiveType,
          manufacturer_name: manufacturer.trim(),
          model_name: model.trim(),
          image_sha256: sha,
        }),
      });
      if (res.status === 401) {
        logout();
        return;
      }
      if (res.status === 403) {
        setBanner({ type: "error", message: "You need admin or SPD-manager access to create a baseline." });
        return;
      }
      if (!res.ok) {
        const e2 = await res.json().catch(() => ({}));
        const msg = Array.isArray(e2?.detail)
          ? e2.detail.map((d: { msg: string }) => d.msg).join("; ")
          : e2?.detail || `Failed to create baseline (${res.status}).`;
        setBanner({ type: "error", message: msg });
        return;
      }
      const data = await res.json();
      setBanner({
        type: "success",
        message: `Approved manufacturer baseline #${data.id} created for ${data.instrument_type.replace(/_/g, " ")}. Inspections of this instrument type will now be scored against it.`,
      });
      setInstrumentType("");
      setCustomType("");
      setManufacturer("");
      setModel("");
      setImage(null);
      onCreated?.();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">Add Manufacturer Baseline</h3>
        <p className="text-xs text-slate-500">
          Enter the instrument, upload its reference image, and it becomes the approved baseline the AI scores against.
        </p>
      </div>

      {!canCreate && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">
          Your role ({role}) cannot create baselines. Admin or SPD-manager access is required.
        </div>
      )}

      {banner && (
        <div className={`rounded-lg px-3 py-2 text-sm ${banner.type === "success" ? "bg-emerald-50 border border-emerald-200 text-emerald-800" : "bg-red-50 border border-red-200 text-red-700"}`}>
          {banner.message}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Instrument Type *</label>
            <select
              value={instrumentType}
              onChange={(e) => setInstrumentType(e.target.value)}
              disabled={!canCreate}
              className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Select instrument type…</option>
              {INSTRUMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            {instrumentType === "other" && (
              <div className="mt-2">
                <input
                  value={customType}
                  onChange={(e) => setCustomType(e.target.value)}
                  disabled={!canCreate}
                  placeholder="Type the instrument type, e.g. Cystoscope"
                  className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
                {customType.trim() && (
                  <p className="mt-1 text-xs text-slate-500">
                    Will be saved as <code className="rounded bg-slate-100 px-1">{slugifyType(customType)}</code>.
                    Use this same type when running inspections so they score against this baseline.
                  </p>
                )}
              </div>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Manufacturer *</label>
            <input
              value={manufacturer}
              onChange={(e) => setManufacturer(e.target.value)}
              disabled={!canCreate}
              placeholder="e.g. Karl Storz"
              className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Model / Catalog (optional)</label>
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={!canCreate}
            placeholder="e.g. 26173 AA"
            className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Baseline Image *</label>
          <input
            type="file"
            accept={ALLOWED_TYPES.join(",")}
            disabled={!canCreate}
            onChange={(e) => setImage(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:text-blue-700"
          />
          {image && <p className="mt-1 text-xs text-slate-500">{image.name}</p>}
        </div>

        <button
          type="submit"
          disabled={submitting || !canCreate}
          className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? "Creating baseline…" : "Create Approved Baseline"}
        </button>
      </form>
    </div>
  );
}
