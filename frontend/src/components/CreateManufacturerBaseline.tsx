import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { ImageAcquisition } from "@/components/ui/image-acquisition";

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

export default function CreateManufacturerBaseline({ onCreated }: { onCreated?: () => void }) {
  const { headers, role, logout } = useAuth();
  const [instrumentType, setInstrumentType] = useState("");
  const [customType, setCustomType] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [model, setModel] = useState("");
  const [image, setImage] = useState<File | null>(null);
  // Governance evidence for a genuine manufacturer-reference image.
  const [sourceOrganization, setSourceOrganization] = useState("");
  const [sourceReference, setSourceReference] = useState("");
  const [rightsAttested, setRightsAttested] = useState(false);
  const [noPhiAttested, setNoPhiAttested] = useState(false);
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
    if (!sourceOrganization.trim() || !sourceReference.trim()) {
      setBanner({
        type: "error",
        message: "A manufacturer reference image needs a source organization and a source reference (document id, PO, or vendor-portal submission id).",
      });
      return;
    }
    if (!rightsAttested || !noPhiAttested) {
      setBanner({ type: "error", message: "Please attest usage rights and that the image contains no PHI." });
      return;
    }
    const effectiveType = instrumentType === "other" ? slugifyType(customType) : instrumentType;
    if (instrumentType === "other" && !effectiveType) {
      setBanner({ type: "error", message: "Enter the instrument type name for “Other”." });
      return;
    }

    setSubmitting(true);
    try {
      const hdrs = headers();

      // 1. Create the approved manufacturer baseline metadata record.
      const res = await apiFetch(`/api/baselines/manufacturer`, { raw: true,
        method: "POST",
        headers: hdrs,
        body: JSON.stringify({
          instrument_type: effectiveType,
          manufacturer_name: manufacturer.trim(),
          model_name: model.trim(),
        }),
      });
      if (res.status === 401) { logout(); return; }
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

      // 2. Register the GOVERNED reference image (retains bytes + LCID + link
      //    in PENDING_REVIEW). This replaces the old hash-only upload: the image
      //    only becomes usable for comparison after review + activation.
      const fd = new FormData();
      fd.append("image", image);
      fd.append("source_organization", sourceOrganization.trim());
      fd.append("source_reference", sourceReference.trim());
      fd.append("usage_rights_attested", "true");
      fd.append("no_phi_attested", "true");
      const imgRes = await apiFetch(`/api/baselines/${data.id}/reference-image`, { raw: true,
        method: "POST",
        headers: { Authorization: hdrs["Authorization"] },
        body: fd,
      });
      if (imgRes.status === 401) { logout(); return; }
      if (!imgRes.ok) {
        const e1 = await imgRes.json().catch(() => ({}));
        const msg = typeof e1?.detail === "string" ? e1.detail : `Reference image registration failed (${imgRes.status}).`;
        setBanner({
          type: "error",
          message: `Baseline #${data.id} metadata created, but the reference image was not registered: ${msg}`,
        });
        return;
      }
      const imgData = await imgRes.json();
      setBanner({
        type: "success",
        message:
          `Baseline #${data.id} created for ${data.instrument_type.replace(/_/g, " ")}. ` +
          `Reference image registered (status: ${imgData.lifecycle_status}). ` +
          `It becomes usable for inspection comparison only after a reviewer approves it and an authorized role activates it — ` +
          `it is not ACTIVE just because the metadata baseline was approved.`,
      });
      setInstrumentType(""); setCustomType(""); setManufacturer(""); setModel("");
      setImage(null); setSourceOrganization(""); setSourceReference("");
      setRightsAttested(false); setNoPhiAttested(false);
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
          Enter the instrument and upload its reference image. The image is retained and governed; it is
          used for a visual-similarity comparison only after it is reviewed and activated — not automatically.
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

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Source Organization *</label>
            <input
              value={sourceOrganization}
              onChange={(e) => setSourceOrganization(e.target.value)}
              disabled={!canCreate}
              placeholder="e.g. Karl Storz GmbH"
              className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Source Reference *</label>
            <input
              value={sourceReference}
              onChange={(e) => setSourceReference(e.target.value)}
              disabled={!canCreate}
              placeholder="Document id, PO, or vendor-portal submission id"
              className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Baseline Image *</label>
          <ImageAcquisition
            id="manufacturer_baseline_image"
            label="Add Baseline Image"
            multiple={false}
            disabled={!canCreate}
            files={image ? [image] : []}
            onChange={(files) => setImage(files[0] ?? null)}
          />
        </div>

        <div className="space-y-1.5 rounded-lg bg-slate-50 border border-slate-200 px-3 py-2">
          <label className="flex items-start gap-2 text-xs text-slate-700">
            <input type="checkbox" checked={rightsAttested} disabled={!canCreate}
              onChange={(e) => setRightsAttested(e.target.checked)} className="mt-0.5" />
            I attest the organization has the rights to store and use this reference image.
          </label>
          <label className="flex items-start gap-2 text-xs text-slate-700">
            <input type="checkbox" checked={noPhiAttested} disabled={!canCreate}
              onChange={(e) => setNoPhiAttested(e.target.checked)} className="mt-0.5" />
            I attest this is a manufacturer reference instrument image and contains no PHI.
          </label>
        </div>

        <button
          type="submit"
          disabled={submitting || !canCreate}
          className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? "Creating baseline…" : "Create Baseline + Register Reference Image"}
        </button>
        <p className="text-[11px] text-slate-500">
          The reference image is submitted for review. A reviewer must approve it and an authorized role must
          activate it before inspections compare against it.
        </p>
      </form>
    </div>
  );
}
