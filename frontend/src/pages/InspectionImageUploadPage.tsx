import { useState } from "react";
import {
  ImageIcon,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { ImageAcquisition, imageAcquisitionSource } from "@/components/ui/image-acquisition";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

type FindingCategory =
  | "blood"
  | "bone"
  | "tissue"
  | "debris"
  | "corrosion"
  | "crack"
  | "insulation_damage"
  | "other"
  | "none";

type RiskLevel = "low" | "medium" | "high" | "critical";
type CaptureDevice = "borescope_pro_3000" | "rigid_borescope_4mm" | "usb_macro" | "mobile_camera" | "other";
type CaptureAngle = "distal_tip_0" | "distal_tip_45" | "lateral_full" | "jaw_interior" | "channel_lumen" | "shaft_mid" | "other";
type ImageQualityRating = "high" | "medium" | "low";

interface FormState {
  instrument_name: string;
  manufacturer: string;
  model_number: string;
  identifier: string;
  identifier_type: "keydot" | "qr" | "barcode" | "manual" | "";
  finding_category: FindingCategory;
  risk_level: RiskLevel;
  notes: string;
  capture_device: CaptureDevice | "";
  capture_angle: CaptureAngle | "";
  image_quality_rating: ImageQualityRating | "";
}

const INITIAL: FormState = {
  instrument_name: "",
  manufacturer: "",
  model_number: "",
  identifier: "",
  identifier_type: "",
  finding_category: "none",
  risk_level: "low",
  notes: "",
  capture_device: "",
  capture_angle: "",
  image_quality_rating: "",
};

const FINDING_OPTIONS: Array<{ value: FindingCategory; label: string }> = [
  { value: "none", label: "No Finding (Pass)" },
  { value: "blood", label: "Blood" },
  { value: "bone", label: "Bone" },
  { value: "tissue", label: "Tissue" },
  { value: "debris", label: "Debris / Bioburden" },
  { value: "corrosion", label: "Corrosion" },
  { value: "crack", label: "Crack / Fracture" },
  { value: "insulation_damage", label: "Insulation Damage" },
  { value: "other", label: "Other" },
];

const RISK_OPTIONS: Array<{ value: RiskLevel; label: string; color: string }> = [
  { value: "low", label: "Low", color: "text-emerald-700 bg-emerald-50 border-emerald-200" },
  { value: "medium", label: "Medium", color: "text-amber-700 bg-amber-50 border-amber-200" },
  { value: "high", label: "High", color: "text-orange-700 bg-orange-50 border-orange-200" },
  { value: "critical", label: "Critical", color: "text-red-700 bg-red-50 border-red-200" },
];

// ─── Select / Field helpers ────────────────────────────────────────────────────

function Field({ label, required, children, hint }: { label: string; required?: boolean; children: React.ReactNode; hint?: string }) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-slate-700">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
      {hint && <p className="text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

function TextInput({ value, onChange, placeholder, mono }: { value: string; onChange: (v: string) => void; placeholder?: string; mono?: boolean }) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 ${mono ? "font-mono" : ""}`}
    />
  );
}

function Select({ value, onChange, options, placeholder = "Select…" }: { value: string; onChange: (v: string) => void; options: Array<{ value: string; label: string }>; placeholder?: string }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <option value="">{placeholder}</option>
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InspectionImageUploadPage() {
  const { headers } = useAuth();
  const [form, setForm] = useState<FormState>(INITIAL);
  const [inspectionImages, setInspectionImages] = useState<File[]>([]);
  const [borescopeImages, setBorescopeImages] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);

  function set(key: keyof FormState, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
    setResult(null);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.instrument_name.trim()) {
      setResult({ type: "error", message: "Instrument name is required." });
      return;
    }
    const allImages = [...inspectionImages, ...borescopeImages];
    if (allImages.length === 0) {
      setResult({ type: "error", message: "Upload at least one image before submitting." });
      return;
    }

    setSubmitting(true);
    try {
      const hdrs = headers();

      // Step 1: create inspection record
      const inspectionRes = await apiFetch(`/api/inspections`, { raw: true,
        method: "POST",
        headers: { ...hdrs, "Content-Type": "application/json" },
        body: JSON.stringify({
          instrument_name: form.instrument_name,
          manufacturer: form.manufacturer || undefined,
          model_number: form.model_number || undefined,
          identifier: form.identifier || undefined,
          identifier_type: form.identifier_type || undefined,
          finding_category: form.finding_category !== "none" ? form.finding_category : undefined,
          risk_level: form.risk_level,
          notes: form.notes || undefined,
          image_metadata: {
            capture_device: form.capture_device || undefined,
            capture_angle: form.capture_angle || undefined,
            image_quality_rating: form.image_quality_rating || undefined,
            uploaded_by: localStorage.getItem("actor") || "unknown",
            upload_timestamp: new Date().toISOString(),
            inspection_image_count: inspectionImages.length,
            borescope_image_count: borescopeImages.length,
          },
        }),
      });

      let inspectionId = "";
      if (inspectionRes.ok) {
        const d = await inspectionRes.json().catch(() => ({}));
        inspectionId = String(d?.id || d?.inspection_id || "");
      }

      // Step 2: upload images — borescope captures and uploaded files share
      // this one governed endpoint; annotate the source(s) for audit provenance.
      const fd = new FormData();
      allImages.forEach((f) => fd.append("images", f));
      const sources = new Set(allImages.map(imageAcquisitionSource));
      const imageSource = sources.size > 1 ? "mixed" : [...sources][0] ?? "file_upload";
      const uploadRes = await apiFetch(`/api/inspections/upload-images?image_source=${encodeURIComponent(imageSource)}`, { raw: true,
        method: "POST",
        headers: { Authorization: hdrs["Authorization"] },
        body: fd,
      });

      const uploadData = uploadRes.ok ? await uploadRes.json().catch(() => ({})) : {};
      const uploadedCount = uploadData?.uploaded ?? allImages.length;

      setResult({
        type: "success",
        message: `Inspection submitted.${inspectionId ? ` ID: ${inspectionId}.` : ""} ${uploadedCount} image(s) uploaded for CV analysis.`,
      });
      setForm(INITIAL);
      setInspectionImages([]);
      setBorescopeImages([]);
    } catch (e) {
      setResult({ type: "error", message: e instanceof Error ? e.message : "Submission failed." });
    } finally {
      setSubmitting(false);
    }
  }

  const selectedRisk = RISK_OPTIONS.find((r) => r.value === form.risk_level);

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Inspection Image Upload</h2>
        <p className="text-sm text-slate-500 mt-1">
          Submit inspection images for AI analysis. Images are hashed and processed by the CV pipeline.
        </p>
      </div>

      {/* Capture guidelines */}
      <details className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm">
        <summary className="cursor-pointer font-medium text-blue-800 select-none">
          📷 Image Capture Guidelines
        </summary>
        <ul className="mt-3 space-y-1.5 text-blue-900 text-xs list-none">
          <li><strong>Format:</strong> JPEG or PNG</li>
          <li><strong>Resolution:</strong> Minimum 1920×1080 (1080p); 4K preferred for borescope images</li>
          <li><strong>File size:</strong> Maximum 20 MB per image</li>
          <li><strong>Lighting:</strong> White LED illumination; avoid flash flare at lumen entry point</li>
          <li><strong>Borescope:</strong> Capture lumen entry, mid-channel, and distal tip — 3 images minimum</li>
          <li><strong>Naming:</strong> <code className="bg-blue-100 px-1 rounded">{"{facility}_{instrument_id}_{YYYYMMDD}_{seq}.jpg"}</code></li>
          <li className="text-red-800 font-medium">⚠ PHI: Do not photograph patient labels, wristbands, or any identifiers in frame.</li>
        </ul>
      </details>

      {result && (
        <div className={`flex items-start gap-3 rounded-lg p-4 border ${result.type === "success" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-800"}`}>
          {result.type === "success" ? <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" /> : <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />}
          <p className="text-sm">{result.message}</p>
        </div>
      )}

      <form onSubmit={submit} className="space-y-6">
        {/* Instrument */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Instrument</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Instrument Name" required>
              <TextInput value={form.instrument_name} onChange={(v) => set("instrument_name", v)} placeholder="e.g. Laparoscopic Grasper" />
            </Field>
            <Field label="Manufacturer">
              <TextInput value={form.manufacturer} onChange={(v) => set("manufacturer", v)} placeholder="e.g. Storz" />
            </Field>
            <Field label="Model Number">
              <TextInput value={form.model_number} onChange={(v) => set("model_number", v)} placeholder="e.g. 26173KA" mono />
            </Field>
            <Field label="Identifier" hint="Barcode, QR, KeyDot, or serial">
              <div className="flex gap-2">
                <select
                  value={form.identifier_type}
                  onChange={(e) => set("identifier_type", e.target.value)}
                  className="rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Type</option>
                  <option value="keydot">KeyDot</option>
                  <option value="qr">QR / UDI</option>
                  <option value="barcode">Barcode</option>
                  <option value="manual">Manual</option>
                </select>
                <TextInput value={form.identifier} onChange={(v) => set("identifier", v)} placeholder="Identifier value" mono />
              </div>
            </Field>
          </CardContent>
        </Card>

        {/* Images */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Images</CardTitle>
            <CardDescription>Upload inspection and borescope images. All images are SHA-256 hashed for audit integrity.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <ImageAcquisition
              id="inspection_images"
              label="Add Inspection Image"
              files={inspectionImages}
              onChange={setInspectionImages}
            />
            <ImageAcquisition
              id="borescope_images"
              label="Add Borescope Image"
              files={borescopeImages}
              onChange={setBorescopeImages}
            />

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Field label="Capture Device">
                <Select
                  value={form.capture_device}
                  onChange={(v) => set("capture_device", v)}
                  options={[
                    { value: "borescope_pro_3000", label: "Borescope Pro 3000" },
                    { value: "rigid_borescope_4mm", label: "Rigid Borescope 4 mm" },
                    { value: "usb_macro", label: "USB Macro Camera" },
                    { value: "mobile_camera", label: "Mobile Camera" },
                    { value: "other", label: "Other" },
                  ]}
                />
              </Field>
              <Field label="Capture Angle">
                <Select
                  value={form.capture_angle}
                  onChange={(v) => set("capture_angle", v)}
                  options={[
                    { value: "distal_tip_0", label: "Distal tip, 0°" },
                    { value: "distal_tip_45", label: "Distal tip, 45°" },
                    { value: "lateral_full", label: "Lateral — full instrument" },
                    { value: "jaw_interior", label: "Jaw interior" },
                    { value: "channel_lumen", label: "Channel / lumen" },
                    { value: "shaft_mid", label: "Shaft mid-point" },
                    { value: "other", label: "Other" },
                  ]}
                />
              </Field>
              <Field label="Image Quality">
                <Select
                  value={form.image_quality_rating}
                  onChange={(v) => set("image_quality_rating", v)}
                  options={[
                    { value: "high", label: "High — sharp, well-lit" },
                    { value: "medium", label: "Medium — acceptable" },
                    { value: "low", label: "Low — poor / blurry" },
                  ]}
                />
              </Field>
            </div>
          </CardContent>
        </Card>

        {/* Finding */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Finding Classification</CardTitle>
            <CardDescription>
              Classify any findings observed. AI output will be generated by the CV pipeline;
              this is the technician's initial classification.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field label="Finding Category">
              <div className="flex flex-wrap gap-2">
                {FINDING_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => set("finding_category", opt.value)}
                    className={cn(
                      "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
                      form.finding_category === opt.value
                        ? "bg-blue-600 border-blue-600 text-white"
                        : "border-slate-200 text-slate-600 hover:border-blue-300 hover:text-blue-600"
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="Risk Level">
              <div className="flex gap-2">
                {RISK_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => set("risk_level", opt.value)}
                    className={cn(
                      "flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                      form.risk_level === opt.value
                        ? opt.color
                        : "border-slate-200 text-slate-500 hover:bg-slate-50"
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              {selectedRisk && form.risk_level !== "low" && (
                <p className="text-xs text-slate-500 mt-1">
                  {form.risk_level === "critical"
                    ? "Critical risk — instrument should be removed from service pending review."
                    : form.risk_level === "high"
                    ? "High risk — quality review recommended before next use."
                    : "Medium risk — document and monitor."}
                </p>
              )}
            </Field>

            <Field label="Inspection Notes">
              <textarea
                value={form.notes}
                onChange={(e) => set("notes", e.target.value)}
                rows={3}
                placeholder="Describe findings, location, severity, and any recommended actions…"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </Field>
          </CardContent>
        </Card>

        {/* Submit */}
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={submitting || (inspectionImages.length === 0 && borescopeImages.length === 0)}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? <Spinner className="h-4 w-4" /> : <ImageIcon className="h-4 w-4" />}
            Submit Inspection
          </button>
          <button
            type="button"
            onClick={() => { setForm(INITIAL); setInspectionImages([]); setBorescopeImages([]); setResult(null); }}
            className="rounded-lg border border-slate-200 px-5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            Reset
          </button>
        </div>
      </form>
    </div>
  );
}
