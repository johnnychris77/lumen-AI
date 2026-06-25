import { useState } from "react";
import { CheckCircle2, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { BaselineImageUpload } from "@/components/ui/baseline-image-upload";
import { Spinner } from "@/components/ui/spinner";
import { useAuth, API_BASE } from "@/lib/auth";

// ─── Types ────────────────────────────────────────────────────────────────────

type CaptureDevice = "borescope_pro_3000" | "rigid_borescope_4mm" | "usb_macro" | "mobile_camera" | "other";
type CaptureAngle = "distal_tip_0" | "distal_tip_45" | "lateral_full" | "jaw_interior" | "channel_lumen" | "shaft_mid" | "other";
type ImageQualityRating = "high" | "medium" | "low";

interface FormState {
  instrument_name: string;
  manufacturer: string;
  model_number: string;
  barcode: string;
  qr_code: string;
  keydot_id: string;
  udi: string;
  baseline_image_url: string;
  known_normal_characteristics: string;
  known_abnormal_characteristics: string;
  baseline_notes: string;
  capture_device: CaptureDevice | "";
  capture_angle: CaptureAngle | "";
  image_quality_rating: ImageQualityRating | "";
}

const INITIAL: FormState = {
  instrument_name: "",
  manufacturer: "",
  model_number: "",
  barcode: "",
  qr_code: "",
  keydot_id: "",
  udi: "",
  baseline_image_url: "",
  known_normal_characteristics: "",
  known_abnormal_characteristics: "",
  baseline_notes: "",
  capture_device: "",
  capture_angle: "",
  image_quality_rating: "",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function Field({
  label,
  required,
  children,
  hint,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-slate-700">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
      {hint && <p className="text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

function TextInput({
  value,
  onChange,
  placeholder,
  mono,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  mono?: boolean;
}) {
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

function Textarea({
  value,
  onChange,
  placeholder,
  rows = 3,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
    />
  );
}

function Select({
  value,
  onChange,
  options,
  placeholder = "Select…",
}: {
  value: string;
  onChange: (v: string) => void;
  options: Array<{ value: string; label: string }>;
  placeholder?: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function BaselineImageUploadPage() {
  const { headers } = useAuth();
  const [form, setForm] = useState<FormState>(INITIAL);
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
    if (!form.baseline_image_url) {
      setResult({ type: "error", message: "Upload a baseline image before submitting." });
      return;
    }

    setSubmitting(true);
    try {
      const hdrs = headers();
      const res = await fetch(
        `${API_BASE}/api/enterprise/vendor-baseline-subscription/baselines`,
        {
          method: "POST",
          headers: { ...hdrs, "Content-Type": "application/json" },
          body: JSON.stringify({
            instrument_name: form.instrument_name,
            manufacturer: form.manufacturer,
            model_number: form.model_number,
            barcode: form.barcode || undefined,
            qr_code: form.qr_code || undefined,
            keydot_id: form.keydot_id || undefined,
            udi: form.udi || undefined,
            baseline_image_url: form.baseline_image_url,
            known_normal_characteristics: form.known_normal_characteristics || undefined,
            known_abnormal_characteristics: form.known_abnormal_characteristics || undefined,
            notes: form.baseline_notes || undefined,
            image_metadata: {
              capture_device: form.capture_device || undefined,
              capture_angle: form.capture_angle || undefined,
              image_quality_rating: form.image_quality_rating || undefined,
              uploaded_by: localStorage.getItem("actor") || "unknown",
              upload_timestamp: new Date().toISOString(),
            },
          }),
        }
      );

      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d?.detail || `Submission failed (${res.status})`);
      }

      setResult({ type: "success", message: "Baseline submitted successfully and is pending review." });
      setForm(INITIAL);
    } catch (e) {
      setResult({ type: "error", message: e instanceof Error ? e.message : "Submission failed." });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Baseline Image Upload</h2>
        <p className="text-sm text-slate-500 mt-1">
          Submit a reference baseline image for a surgical instrument. Baselines go through SPD manager review before they become active.
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
          <li><strong>Lighting:</strong> White LED illumination; avoid flash flare at lumen entry</li>
          <li><strong>Required angles:</strong> (1) lumen entry, (2) distal tip, (3) insertion tube shaft</li>
          <li><strong>Naming:</strong> <code className="bg-blue-100 px-1 rounded">{"{facility}_{instrument_id}_{YYYYMMDD}_{seq}.jpg"}</code></li>
          <li className="text-red-800 font-medium">⚠ PHI: Do not photograph patient labels, wristbands, or medical records in frame.</li>
        </ul>
      </details>

      {result && (
        <div
          className={`flex items-start gap-3 rounded-lg p-4 border ${
            result.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-red-50 border-red-200 text-red-800"
          }`}
        >
          {result.type === "success" ? (
            <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
          ) : (
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          )}
          <p className="text-sm">{result.message}</p>
        </div>
      )}

      <form onSubmit={submit} className="space-y-6">
        {/* Instrument Identification */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Instrument Identification</CardTitle>
            <CardDescription>Select or describe the instrument this baseline belongs to.</CardDescription>
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
            <Field label="Barcode" hint="Scan or enter manually">
              <TextInput value={form.barcode} onChange={(v) => set("barcode", v)} placeholder="e.g. A04421" mono />
            </Field>
            <Field label="QR / UDI" hint="Full UDI string if available">
              <TextInput value={form.qr_code} onChange={(v) => set("qr_code", v)} placeholder="e.g. (01)00888912345601" mono />
            </Field>
            <Field label="KeyDot ID" hint="KeyDot micro-dot identifier">
              <TextInput value={form.keydot_id} onChange={(v) => set("keydot_id", v)} placeholder="e.g. keydot-127" mono />
            </Field>
          </CardContent>
        </Card>

        {/* Baseline Image */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Baseline Image</CardTitle>
            <CardDescription>Upload a high-quality reference image of the instrument in known-good condition.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <BaselineImageUpload
              value={form.baseline_image_url}
              onChange={(url) => set("baseline_image_url", url)}
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
                    { value: "low", label: "Low — poor lighting / blur" },
                  ]}
                />
              </Field>
            </div>
          </CardContent>
        </Card>

        {/* Baseline Characteristics */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Baseline Characteristics</CardTitle>
            <CardDescription>Document what a normal instrument looks like versus known defect patterns.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field label="Known Normal Characteristics" hint="Describe expected appearance in clean, functioning condition">
              <Textarea
                value={form.known_normal_characteristics}
                onChange={(v) => set("known_normal_characteristics", v)}
                placeholder="e.g. Jaws close flush. No discolouration. Tungsten carbide inserts intact. Smooth jaw action."
                rows={3}
              />
            </Field>
            <Field label="Known Abnormal Characteristics" hint="Describe defect patterns previously observed on this instrument type">
              <Textarea
                value={form.known_abnormal_characteristics}
                onChange={(v) => set("known_abnormal_characteristics", v)}
                placeholder="e.g. Tissue residue at jaw hinge. Corrosion at box joint. Insulation thinning on shaft."
                rows={3}
              />
            </Field>
            <Field label="Baseline Notes">
              <Textarea
                value={form.baseline_notes}
                onChange={(v) => set("baseline_notes", v)}
                placeholder="Any additional notes for the reviewer…"
                rows={2}
              />
            </Field>
          </CardContent>
        </Card>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={submitting || !form.baseline_image_url}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting && <Spinner className="h-4 w-4" />}
            Submit for Review
          </button>
          <button
            type="button"
            onClick={() => { setForm(INITIAL); setResult(null); }}
            className="rounded-lg border border-slate-200 px-5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            Reset
          </button>
        </div>
      </form>
    </div>
  );
}
