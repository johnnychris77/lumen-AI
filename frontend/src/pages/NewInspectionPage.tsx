import { ChangeEvent, FormEvent, useCallback, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth, API_BASE } from "@/lib/auth";
import { FormSection } from "@/components/ui/FormSection";
import { RequiredLabel, FieldError } from "@/components/ui/RequiredField";
import { StatusBanner } from "@/components/ui/StatusBanner";

// ─── types ─────────────────────────────────────────────────────────────────── v2

type FindingCategory =
  | "blood" | "bone" | "tissue" | "debris"
  | "corrosion" | "crack" | "insulation_damage" | "other";

type FormFields = {
  facility_name: string;
  department: string;
  technician_name: string;
  inspection_date: string;
  tray_name: string;
  tray_id: string;
  instrument_name: string;
  instrument_type: string;
  manufacturer: string;
  model_number: string;
  serial_number: string;
  barcode: string;
  qr_code: string;
  udi: string;
  keydot_id: string;
  finding_categories: FindingCategory[];
  notes: string;
};

type FieldErrors = Partial<Record<keyof FormFields | "images", string>>;

type AIPrediction = {
  id: string;
  risk_score: number;
  score_status: string;
  baseline_status: string;
  baseline_source: string | null;
  supervisor_review_required: boolean;
  detected_issue: string;
  confidence: number;
  instrument_type: string;
};

// ─── constants ────────────────────────────────────────────────────────────────

const INSTRUMENT_TYPES = [
  { value: "scope", label: "Scope (Lumened)" },
  { value: "flexible_ureteroscope", label: "Flexible Ureteroscope" },
  { value: "bronchoscope", label: "Bronchoscope" },
  { value: "colonoscope", label: "Colonoscope" },
  { value: "cystoscope", label: "Cystoscope" },
  { value: "hysteroscope", label: "Hysteroscope" },
  { value: "laparoscope", label: "Laparoscope" },
  { value: "arthroscope", label: "Arthroscope" },
  { value: "nephroscope", label: "Nephroscope" },
  { value: "scissors", label: "Scissors" },
  { value: "forceps", label: "Forceps" },
  { value: "clamp", label: "Clamp" },
  { value: "needle_holder", label: "Needle Holder" },
  { value: "retractor", label: "Retractor" },
  { value: "scalpel_handle", label: "Scalpel Handle" },
  { value: "drill", label: "Drill" },
  { value: "other", label: "Other" },
];

const FINDING_CATEGORIES: { value: FindingCategory; label: string; tooltip: string }[] = [
  { value: "blood", label: "Blood", tooltip: "Visible blood residue in lumen or on instrument surface" },
  { value: "bone", label: "Bone", tooltip: "Calcified tissue or bone fragment visible in channel" },
  { value: "tissue", label: "Tissue", tooltip: "Soft tissue or protein residue visible in lumen" },
  { value: "debris", label: "Debris / Bioburden", tooltip: "Non-specific particulate, organic matter, or buildup" },
  { value: "corrosion", label: "Corrosion", tooltip: "Rust, pitting, or surface degradation of metal" },
  { value: "crack", label: "Crack / Fracture", tooltip: "Visible structural break, fracture, or delamination" },
  { value: "insulation_damage", label: "Insulation Damage", tooltip: "Damage to electrical insulation on monopolar/bipolar instruments" },
  { value: "other", label: "Other", tooltip: "Any finding not covered by categories above" },
];

const OVERRIDE_SOURCES = [
  { value: "vendor", label: "Vendor Baseline" },
  { value: "hospital", label: "Hospital Baseline" },
  { value: "manufacturer", label: "Alternate Manufacturer" },
  { value: "manual_review", label: "Manual Review" },
  { value: "none", label: "No Baseline — Manual Assessment Only" },
];

const MAX_FILE_BYTES = 10 * 1024 * 1024;

function nowDatetimeLocal() {
  return new Date().toISOString().slice(0, 16);
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function riskColor(score: number) {
  if (score >= 80) return "bg-red-600 text-white";
  if (score >= 60) return "bg-orange-500 text-white";
  if (score >= 40) return "bg-amber-400 text-slate-900";
  return "bg-emerald-100 text-emerald-800";
}

const initialForm: FormFields = {
  facility_name: "",
  department: "",
  technician_name: "",
  inspection_date: nowDatetimeLocal(),
  tray_name: "",
  tray_id: "",
  instrument_name: "",
  instrument_type: "",
  manufacturer: "",
  model_number: "",
  serial_number: "",
  barcode: "",
  qr_code: "",
  udi: "",
  keydot_id: "",
  finding_categories: [],
  notes: "",
};

// ─── component ────────────────────────────────────────────────────────────────

export default function NewInspectionPage() {
  const { headers } = useAuth();
  const [form, setForm] = useState<FormFields>(initialForm);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [inspectionImages, setInspectionImages] = useState<File[]>([]);
  const [borescopeImages, setBorescopeImages] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [prediction, setPrediction] = useState<AIPrediction | null>(null);
  const [overrideSource, setOverrideSource] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [overriding, setOverriding] = useState(false);
  const [overrideBanner, setOverrideBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [barcodeScanned, setBarcodeScanned] = useState(false);
  const [noBaselineWarning, setNoBaselineWarning] = useState(false);

  const inspectionInputRef = useRef<HTMLInputElement>(null);
  const borescopeInputRef = useRef<HTMLInputElement>(null);

  // ── field helpers ──────────────────────────────────────────────────────────

  function set<K extends keyof FormFields>(key: K, value: FormFields[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function setStr(key: keyof FormFields) {
    return (e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      set(key, e.target.value as FormFields[typeof key]);
  }

  function clearError(key: keyof FormFields) {
    setFieldErrors((e) => { const n = { ...e }; delete n[key]; return n; });
  }

  function onBlurRequired(key: keyof FormFields, label: string) {
    return () => {
      if (!String(form[key]).trim()) {
        setFieldErrors((e) => ({ ...e, [key]: `${label} is required.` }));
      } else {
        clearError(key);
      }
    };
  }

  // ── baseline pre-check on instrument type change ───────────────────────────

  const checkBaseline = useCallback(async (instrumentType: string) => {
    if (!instrumentType) { setNoBaselineWarning(false); return; }
    try {
      const hdrs = headers();
      const r = await fetch(
        `${API_BASE}/api/baseline-library?instrument_category=${encodeURIComponent(instrumentType)}&status=approved&limit=1`,
        { headers: hdrs }
      );
      if (r.ok) {
        const d = await r.json();
        const items = Array.isArray(d) ? d : d.items ?? [];
        setNoBaselineWarning(items.length === 0);
      }
    } catch {
      // non-fatal
    }
  }, [headers]);

  // ── finding category checkboxes ────────────────────────────────────────────

  function toggleCategory(cat: FindingCategory) {
    setForm((f) => {
      const has = f.finding_categories.includes(cat);
      return {
        ...f,
        finding_categories: has
          ? f.finding_categories.filter((c) => c !== cat)
          : [...f.finding_categories, cat],
      };
    });
  }

  // ── image handling ─────────────────────────────────────────────────────────

  function handleImages(
    e: ChangeEvent<HTMLInputElement>,
    setter: React.Dispatch<React.SetStateAction<File[]>>
  ) {
    const files = Array.from(e.target.files || []);
    const valid = files.filter((f) => f.size <= MAX_FILE_BYTES);
    const oversized = files.filter((f) => f.size > MAX_FILE_BYTES);
    setter((prev) => [...prev, ...valid]);
    if (oversized.length) alert(`${oversized.length} file(s) exceed 10 MB and were skipped.`);
    // clear image error once files added
    if (valid.length > 0) setFieldErrors((e) => { const n = { ...e }; delete n.images; return n; });
  }

  function removeImage(index: number, setter: React.Dispatch<React.SetStateAction<File[]>>) {
    setter((prev) => prev.filter((_, i) => i !== index));
  }

  // ── validation ─────────────────────────────────────────────────────────────
  // Image is required. Findings and risk are always optional (AI determines them).

  function validate(): boolean {
    const errors: FieldErrors = {};

    const required: { key: keyof FormFields; label: string }[] = [
      { key: "facility_name", label: "Facility / Site" },
      { key: "technician_name", label: "Technician Name" },
      { key: "inspection_date", label: "Inspection Date & Time" },
      { key: "tray_name", label: "Tray Name" },
      { key: "instrument_name", label: "Instrument Name" },
      { key: "instrument_type", label: "Instrument Type" },
    ];
    for (const { key, label } of required) {
      if (!String(form[key]).trim()) errors[key] = `${label} is required.`;
    }

    const allImages = [...inspectionImages, ...borescopeImages];
    if (allImages.length === 0) {
      errors.images = "At least one inspection image is required for AI analysis.";
    }

    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      setTimeout(() => {
        const el = document.querySelector<HTMLElement>("[data-field-error]");
        el?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 50);
    }
    return Object.keys(errors).length === 0;
  }

  // ── submit ─────────────────────────────────────────────────────────────────

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBanner(null);
    if (!validate()) return;

    setSubmitting(true);
    try {
      const hdrs = headers();
      const allImages = [...inspectionImages, ...borescopeImages];

      // Step 1: Upload images first
      let imageSha256: string | undefined;
      try {
        const fd = new FormData();
        allImages.forEach((f) => fd.append("images", f));
        const imgRes = await fetch(`${API_BASE}/api/inspections/upload-images`, {
          method: "POST",
          headers: { Authorization: hdrs["Authorization"] },
          body: fd,
        });
        if (imgRes.ok) {
          const imgData = await imgRes.json();
          imageSha256 = imgData?.images?.[0]?.sha256;
        }
      } catch {
        // non-fatal — inspection can still be created
      }

      // Step 2: Submit inspection record (findings optional — AI will determine)
      const payload: Record<string, unknown> = {
        instrument_type: form.instrument_type,
        site_name: form.facility_name,
        vendor_name: form.manufacturer || "unknown",
        facility_name: form.facility_name,
        department: form.department || undefined,
        tray_id: form.tray_id || undefined,
        instrument_barcode: form.barcode || undefined,
        instrument_udi: form.udi || undefined,
        file_name: allImages[0]?.name || "inspection_image",
        has_image: true,
        image_sha256: imageSha256,
        // Risk level is AI-determined — never required from technician
        risk_level: "pending_ai_analysis",
        // Finding categories submitted as-is (empty [] is valid — AI will determine)
        finding_categories: form.finding_categories.length > 0
          ? form.finding_categories
          : ["pending_ai_analysis"],
        ...(form.finding_categories.length > 0 && {
          detected_issue: form.finding_categories[0],
          stain_detected: form.finding_categories.some(
            (c) => ["blood", "bone", "tissue", "debris"].includes(c)
          ),
          material_type: "stainless_steel",
        }),
      };

      const res = await fetch(`${API_BASE}/api/inspections`, {
        method: "POST",
        headers: hdrs,
        body: JSON.stringify(payload),
      });

      if (res.status === 401 || res.status === 403) {
        setBanner({ type: "error", message: "Access denied. Please log in again." });
        return;
      }
      if (!res.ok) {
        let msg = `Submission failed (${res.status}).`;
        try {
          const d = await res.json();
          if (Array.isArray(d?.detail)) {
            msg = d.detail.map((e: { msg: string }) => e.msg).join("; ");
          } else {
            msg = d?.detail || d?.message || msg;
          }
        } catch { /* ignore */ }
        setBanner({ type: "error", message: msg });
        return;
      }

      const data = await res.json();
      setPrediction({
        id: String(data.id),
        risk_score: data.risk_score ?? 0,
        score_status: data.score_status ?? "pending",
        baseline_status: data.baseline_status ?? "not_checked",
        baseline_source: data.baseline_source ?? null,
        supervisor_review_required: data.supervisor_review_required ?? false,
        detected_issue: data.detected_issue ?? "unknown",
        confidence: data.confidence ?? 0,
        instrument_type: data.instrument_type ?? form.instrument_type,
      });

      setBanner({
        type: "success",
        message: `Inspection #${data.id} submitted. ${allImages.length} image(s) uploaded. ${
          data.supervisor_review_required
            ? "⚠ Supervisor review required — no approved baseline found."
            : "✓ AI analysis complete."
        }`,
      });
    } finally {
      setSubmitting(false);
    }
  }

  function resetForm() {
    setForm({ ...initialForm, inspection_date: nowDatetimeLocal() });
    setInspectionImages([]);
    setBorescopeImages([]);
    setFieldErrors({});
    setBanner(null);
    setPrediction(null);
    setOverrideSource("");
    setOverrideReason("");
    setOverrideBanner(null);
    setNoBaselineWarning(false);
    setBarcodeScanned(false);
  }

  // ─────────────────────────────────────────────────────────────────────────

  const inputCls =
    "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-6 px-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">New Inspection</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload an image — AI will identify findings, check the manufacturer baseline, and generate a risk score automatically.
        </p>
      </div>

      {/* Field requirements summary */}
      <div className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
        <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-slate-100">
          <div className="px-4 py-3">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Required by technician</p>
            <ul className="text-xs text-slate-700 space-y-1">
              <li className="flex items-center gap-1.5"><span className="text-red-500">*</span> Facility / Site</li>
              <li className="flex items-center gap-1.5"><span className="text-red-500">*</span> Technician Name</li>
              <li className="flex items-center gap-1.5"><span className="text-red-500">*</span> Inspection Date &amp; Time</li>
              <li className="flex items-center gap-1.5"><span className="text-red-500">*</span> Tray Name</li>
              <li className="flex items-center gap-1.5"><span className="text-red-500">*</span> Instrument Name &amp; Type</li>
              <li className="flex items-center gap-1.5"><span className="text-red-500">*</span> At least 1 inspection image</li>
            </ul>
          </div>
          <div className="px-4 py-3 bg-slate-50">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Determined by AI — not required</p>
            <ul className="text-xs text-slate-500 space-y-1">
              <li className="flex items-center gap-1.5"><span className="text-emerald-500">✓</span> Finding Categories (AI predicts from image)</li>
              <li className="flex items-center gap-1.5"><span className="text-emerald-500">✓</span> Risk Level (AI scores after baseline check)</li>
              <li className="flex items-center gap-1.5"><span className="text-emerald-500">✓</span> Baseline Match Status (system checks automatically)</li>
              <li className="flex items-center gap-1.5"><span className="text-emerald-500">✓</span> Baseline Source (supervisor sets if no match)</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Workflow diagram */}
      <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-3 text-xs text-blue-800 space-y-1">
        <p className="font-semibold text-blue-900">Inspection Workflow</p>
        <div className="flex flex-wrap items-center gap-1.5 mt-1">
          {[
            "1. Identify Instrument",
            "→",
            "2. Upload Image",
            "→",
            "3. AI Baseline Check",
            "→",
            "4. AI Prediction (findings + risk)",
            "→",
            "5. Supervisor Review (if no baseline)",
          ].map((step, i) => (
            step === "→"
              ? <span key={i} className="text-blue-400">→</span>
              : <span key={i} className="bg-white border border-blue-200 rounded px-2 py-0.5">{step}</span>
          ))}
        </div>
      </div>

      {banner && (
        <StatusBanner
          type={banner.type}
          message={banner.message}
          onDismiss={() => setBanner(null)}
        />
      )}

      {/* AI Prediction Panel — shown after submission */}
      {prediction && (
        <AIPredictionPanel
          prediction={prediction}
          overrideSource={overrideSource}
          setOverrideSource={setOverrideSource}
          overrideReason={overrideReason}
          setOverrideReason={setOverrideReason}
          overriding={overriding}
          overrideBanner={overrideBanner}
          onOverride={async () => {
            setOverriding(true);
            try {
              const hdrs = headers();
              const r = await fetch(`${API_BASE}/api/inspections/${prediction.id}/baseline-override`, {
                method: "POST",
                headers: hdrs,
                body: JSON.stringify({ baseline_source: overrideSource, override_reason: overrideReason }),
              });
              if (r.ok) {
                const d = await r.json();
                setPrediction((p) => p ? {
                  ...p,
                  risk_score: d.risk_score ?? p.risk_score,
                  score_status: d.score_status ?? p.score_status,
                  baseline_status: d.baseline_status ?? p.baseline_status,
                  supervisor_review_required: false,
                  baseline_source: overrideSource,
                } : p);
                setOverrideBanner({ type: "success", message: `Override applied. Risk score: ${d.risk_score}/100.` });
              } else {
                const err = await r.json().catch(() => ({}));
                setOverrideBanner({ type: "error", message: Array.isArray(err?.detail) ? err.detail.map((e: { msg: string }) => e.msg).join("; ") : (err?.detail || `Override failed (${r.status})`) });
              }
            } catch {
              setOverrideBanner({ type: "error", message: "Network error during override." });
            } finally {
              setOverriding(false);
            }
          }}
          onReset={resetForm}
        />
      )}

      {!prediction && (
        <form onSubmit={handleSubmit} noValidate className="space-y-6">
          {/* Section 1 — Facility & Assignment */}
          <FormSection title="Facility & Assignment" description="Who is performing this inspection and where.">
            <div>
              <RequiredLabel label="Facility / Site" />
              <input
                id="facility_name" type="text" value={form.facility_name}
                onChange={setStr("facility_name")}
                onBlur={onBlurRequired("facility_name", "Facility / Site")}
                className={inputCls} placeholder="e.g. Memorial Regional"
              />
              <FieldError message={fieldErrors.facility_name} />
            </div>
            <div>
              <label htmlFor="department" className="block text-sm font-medium text-gray-700">Department / Unit</label>
              <input id="department" type="text" value={form.department} onChange={setStr("department")} className={inputCls} placeholder="e.g. Decontamination" />
            </div>
            <div>
              <RequiredLabel label="Technician Name" />
              <input
                id="technician_name" type="text" value={form.technician_name}
                onChange={setStr("technician_name")}
                onBlur={onBlurRequired("technician_name", "Technician Name")}
                className={inputCls}
              />
              <FieldError message={fieldErrors.technician_name} />
            </div>
            <div>
              <RequiredLabel label="Inspection Date & Time" />
              <input
                id="inspection_date" type="datetime-local" value={form.inspection_date}
                onChange={setStr("inspection_date")}
                onBlur={onBlurRequired("inspection_date", "Inspection Date & Time")}
                className={inputCls}
              />
              <FieldError message={fieldErrors.inspection_date} />
            </div>
          </FormSection>

          {/* Section 2 — Tray Information */}
          <FormSection title="Tray Information">
            <div>
              <RequiredLabel label="Tray Name" />
              <input
                id="tray_name" type="text" value={form.tray_name}
                onChange={setStr("tray_name")}
                onBlur={onBlurRequired("tray_name", "Tray Name")}
                className={inputCls}
              />
              <FieldError message={fieldErrors.tray_name} />
            </div>
            <div>
              <label htmlFor="tray_id" className="block text-sm font-medium text-gray-700">Tray ID / Tray Number</label>
              <input id="tray_id" type="text" value={form.tray_id} onChange={setStr("tray_id")} className={inputCls} />
            </div>
          </FormSection>

          {/* Section 3 — Instrument Identification */}
          <FormSection title="Instrument Identification">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <RequiredLabel label="Instrument Name" />
                <input
                  id="instrument_name" type="text" value={form.instrument_name}
                  onChange={setStr("instrument_name")}
                  onBlur={onBlurRequired("instrument_name", "Instrument Name")}
                  className={inputCls}
                />
                <FieldError message={fieldErrors.instrument_name} />
              </div>
              <div>
                <RequiredLabel label="Instrument Type" />
                <select
                  id="instrument_type" value={form.instrument_type}
                  onChange={(e) => { setStr("instrument_type")(e); checkBaseline(e.target.value); }}
                  onBlur={onBlurRequired("instrument_type", "Instrument Type")}
                  className={inputCls}
                >
                  <option value="">Select type…</option>
                  {INSTRUMENT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
                <FieldError message={fieldErrors.instrument_type} />
                {noBaselineWarning && (
                  <p className="mt-1 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                    ⚠ No approved manufacturer baseline found — inspection will require supervisor review.
                  </p>
                )}
              </div>
              <div>
                <label htmlFor="manufacturer" className="block text-sm font-medium text-gray-700">Manufacturer</label>
                <input id="manufacturer" type="text" value={form.manufacturer} onChange={setStr("manufacturer")} className={inputCls} />
              </div>
              <div>
                <label htmlFor="model_number" className="block text-sm font-medium text-gray-700">Model Number</label>
                <input id="model_number" type="text" value={form.model_number} onChange={setStr("model_number")} className={inputCls} />
              </div>
              <div>
                <label htmlFor="serial_number" className="block text-sm font-medium text-gray-700">Serial Number</label>
                <input id="serial_number" type="text" value={form.serial_number} onChange={setStr("serial_number")} className={inputCls} />
              </div>
              <div>
                <label htmlFor="barcode" className="block text-sm font-medium text-gray-700">
                  Barcode{barcodeScanned && <span className="ml-2 text-xs font-medium text-emerald-600">✓ Scanned</span>}
                </label>
                <input
                  id="barcode" type="text" value={form.barcode}
                  onChange={(e) => { setStr("barcode")(e); setBarcodeScanned(false); }}
                  onBlur={() => { if (form.barcode.trim()) setBarcodeScanned(true); }}
                  className={inputCls} placeholder="Scan or type barcode…"
                />
              </div>
              <div>
                <label htmlFor="qr_code" className="block text-sm font-medium text-gray-700">QR Code</label>
                <input id="qr_code" type="text" value={form.qr_code} onChange={setStr("qr_code")} className={inputCls} />
              </div>
              <div>
                <label htmlFor="udi" className="block text-sm font-medium text-gray-700">UDI</label>
                <input id="udi" type="text" value={form.udi} onChange={setStr("udi")} placeholder="(01)…" className={inputCls} />
              </div>
              <div>
                <label htmlFor="keydot_id" className="block text-sm font-medium text-gray-700">KeyDot ID</label>
                <input id="keydot_id" type="text" value={form.keydot_id} onChange={setStr("keydot_id")} className={inputCls} />
              </div>
            </div>
          </FormSection>

          {/* Section 4 — Images (REQUIRED — AI analysis runs on these) */}
          <FormSection
            title="Inspection Images"
            description="Required. Upload at least one image. AI will check the manufacturer baseline and generate findings and risk score automatically."
          >
            {/* Pre-upload status — always visible so technician knows what happens next */}
            <div className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-800">
              Upload an image first. LumenAI will compare against the approved manufacturer baseline and suggest findings / risk.
              Finding Categories and Risk Level are set by AI — <strong>technicians do not enter them</strong>.
            </div>

            {/* No-baseline early warning (shown when instrument type is selected but no baseline exists) */}
            {noBaselineWarning && (
              <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                <strong>No approved manufacturer baseline found.</strong>{" "}
                Supervisor review required before final scoring. Technicians do not set baseline status — this is system-controlled.
              </div>
            )}

            <div>
              <RequiredLabel label="Inspection Images" />
              <ImageFileInput
                id="inspection_images"
                label=""
                files={inspectionImages}
                inputRef={inspectionInputRef}
                onChange={(e) => handleImages(e, setInspectionImages)}
                onRemove={(i) => removeImage(i, setInspectionImages)}
              />
              <FieldError message={fieldErrors.images} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Borescope Images <span className="text-slate-400 font-normal">(optional)</span></label>
              <ImageFileInput
                id="borescope_images"
                label=""
                files={borescopeImages}
                inputRef={borescopeInputRef}
                onChange={(e) => handleImages(e, setBorescopeImages)}
                onRemove={(i) => removeImage(i, setBorescopeImages)}
              />
            </div>
            <p className="text-xs text-gray-500">Max 10 MB per file. Only SHA-256 hash is stored — raw images are not retained.</p>
          </FormSection>

          {/* Section 5 — Manual Observations (always optional) */}
          <FormSection
            title="Manual Observations"
            description="Optional. If you observed specific findings, you may note them here. AI prediction will run regardless."
          >
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Finding Categories (AI suggested after image upload)
              </label>
              <div className="mt-2 grid grid-cols-2 sm:grid-cols-3 gap-2">
                {FINDING_CATEGORIES.map((cat) => (
                  <label key={cat.value} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer" title={cat.tooltip}>
                    <input
                      type="checkbox"
                      checked={form.finding_categories.includes(cat.value)}
                      onChange={() => toggleCategory(cat.value)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span>{cat.label}</span>
                    <span className="text-gray-400 text-xs cursor-help" title={cat.tooltip}>?</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label htmlFor="notes" className="block text-sm font-medium text-gray-700">Inspection Notes <span className="text-slate-400 font-normal text-xs">(optional)</span></label>
              <textarea
                id="notes" value={form.notes} onChange={setStr("notes")} rows={3}
                className={inputCls} placeholder="Add shift context, tray details, or observations."
              />
            </div>
          </FormSection>

          {/* AI workflow clarification — shown just above submit */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600 space-y-1">
            <p className="font-semibold text-slate-700">What happens after you submit?</p>
            <ul className="list-disc list-inside space-y-0.5">
              <li><strong>Finding Categories and Risk Level are NOT required</strong> — AI predicts both from the image.</li>
              <li>Baseline Match Status is determined automatically — technicians do not set it.</li>
              <li>If no approved manufacturer baseline is found, the result is flagged for <strong>supervisor review</strong> before final scoring.</li>
            </ul>
          </div>

          {/* Submit */}
          <div className="flex flex-col gap-3">
            <button
              type="submit" disabled={submitting}
              className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? "Uploading image & running AI analysis…" : "Submit Inspection & Run AI Analysis"}
            </button>
            <p className="text-xs text-gray-500 text-center">
              AI findings require qualified human review before clinical action. All AI outputs include human_review_required: true.
            </p>
          </div>
        </form>
      )}

      {/* Quick links */}
      <nav className="flex flex-wrap gap-3 text-xs text-blue-600 border-t pt-4">
        <Link to="/" className="hover:underline">Dashboard</Link>
        <Link to="/intake-history" className="hover:underline">Intake History</Link>
        <Link to="/vendor-intake" className="hover:underline">Vendor Intake</Link>
      </nav>
    </div>
  );
}

// ─── AI Prediction Panel ──────────────────────────────────────────────────────

function AIPredictionPanel({
  prediction,
  overrideSource,
  setOverrideSource,
  overrideReason,
  setOverrideReason,
  overriding,
  overrideBanner,
  onOverride,
  onReset,
}: {
  prediction: AIPrediction;
  overrideSource: string;
  setOverrideSource: (v: string) => void;
  overrideReason: string;
  setOverrideReason: (v: string) => void;
  overriding: boolean;
  overrideBanner: { type: "success" | "error"; message: string } | null;
  onOverride: () => void;
  onReset: () => void;
}) {
  const isScored = prediction.score_status === "scored" || prediction.score_status === "scored_after_override";
  const isSupervisorRequired = prediction.supervisor_review_required;

  return (
    <div className="space-y-4">
      {/* AI Prediction Card */}
      <div className={`rounded-xl border-2 p-5 space-y-4 ${isSupervisorRequired ? "border-amber-400 bg-amber-50" : "border-emerald-300 bg-emerald-50"}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">AI Prediction — Inspection #{prediction.id}</p>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              {isSupervisorRequired ? "⚠ Supervisor Review Required" : "✓ AI Analysis Complete"}
            </h2>
          </div>
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${isSupervisorRequired ? "bg-amber-200 text-amber-900" : "bg-emerald-200 text-emerald-900"}`}>
            {prediction.score_status.replace(/_/g, " ")}
          </span>
        </div>

        {isSupervisorRequired && (
          <div className="rounded-lg border border-amber-400 bg-amber-50 px-4 py-3 text-sm text-amber-900 space-y-1">
            <p className="font-semibold">⚠ Manufacturer baseline not found — Supervisor review required before final scoring.</p>
            <p className="text-xs text-amber-700">
              No approved manufacturer baseline exists for this instrument type.
              Risk scoring is locked until a supervisor or admin applies a baseline override.
              Technicians cannot set baseline status — this is system-controlled.
            </p>
          </div>
        )}

        {/* Prediction grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <PredictionField label="Predicted Findings" value={
            prediction.detected_issue === "unknown" || prediction.detected_issue === ""
              ? "Pending AI analysis"
              : prediction.detected_issue.replace(/_/g, " ")
          } />
          <PredictionField label="Confidence" value={
            prediction.confidence > 0
              ? `${(prediction.confidence).toFixed(0)}%`
              : "Pending"
          } />
          <div className="flex flex-col">
            <span className="text-xs text-slate-500 font-medium">Predicted Risk</span>
            {isScored ? (
              <span className={`mt-1 inline-flex items-center rounded-full px-2.5 py-1 text-sm font-bold w-fit ${riskColor(prediction.risk_score)}`}>
                {prediction.risk_score} / 100
              </span>
            ) : (
              <span className="mt-1 text-sm text-slate-400 italic">Not scored — baseline required</span>
            )}
          </div>
          <PredictionField label="Baseline Source" value={
            prediction.baseline_source
              ? prediction.baseline_source.replace(/_/g, " ")
              : prediction.baseline_status.replace(/_/g, " ")
          } />
        </div>

        <p className="text-xs text-slate-500">
          Human review required. All AI findings represent potential associations only — qualified clinician review is mandatory before any clinical action.
        </p>
      </div>

      {/* Supervisor Override Panel */}
      {isSupervisorRequired && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3">
          <p className="text-sm font-semibold text-slate-800">Supervisor Baseline Override</p>
          <p className="text-xs text-slate-500">Supervisors and admins only. Select an alternate baseline source and provide an override justification to unlock final scoring.</p>

          {overrideBanner && (
            <div className={`rounded px-3 py-2 text-sm ${overrideBanner.type === "success" ? "bg-emerald-100 text-emerald-800" : "bg-red-50 text-red-700"}`}>
              {overrideBanner.message}
            </div>
          )}

          {overrideBanner?.type !== "success" && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Alternate Baseline Source</label>
                <select
                  value={overrideSource}
                  onChange={(e) => setOverrideSource(e.target.value)}
                  className="block w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                >
                  <option value="">Select baseline source…</option>
                  {OVERRIDE_SOURCES.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Override Justification <span className="text-red-500">*</span></label>
                <textarea
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  rows={2}
                  placeholder="Provide clinical justification for selecting this baseline source (min 10 characters)…"
                  className="block w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                />
                {overrideReason.length > 0 && overrideReason.length < 10 && (
                  <p className="text-xs text-red-600 mt-1">Justification must be at least 10 characters.</p>
                )}
              </div>
              <button
                type="button"
                disabled={overriding || !overrideSource || overrideReason.length < 10}
                onClick={onOverride}
                className="rounded bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {overriding ? "Applying override…" : "Apply Baseline Override & Unlock Score"}
              </button>
              <p className="text-xs text-slate-400">Override creates an audit event. Action is logged with your identity, role, timestamp, and justification.</p>
            </div>
          )}
        </div>
      )}

      <button
        type="button"
        onClick={onReset}
        className="text-sm text-blue-600 underline"
      >
        Submit Another Inspection
      </button>
    </div>
  );
}

function PredictionField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-slate-500 font-medium">{label}</span>
      <span className="mt-1 text-sm font-semibold text-slate-800 capitalize">{value}</span>
    </div>
  );
}

// ─── sub-component: image file input with previews ────────────────────────────

function ImageFileInput({
  id,
  label,
  files,
  inputRef,
  onChange,
  onRemove,
}: {
  id: string;
  label: string;
  files: File[];
  inputRef: React.RefObject<HTMLInputElement>;
  onChange: (e: ChangeEvent<HTMLInputElement>) => void;
  onRemove: (index: number) => void;
}) {
  const totalBytes = files.reduce((s, f) => s + f.size, 0);

  return (
    <div>
      {label && <label htmlFor={id} className="block text-sm font-medium text-gray-700">{label}</label>}
      <input
        ref={inputRef} id={id} type="file" accept="image/*" multiple onChange={onChange}
        className="mt-1 block w-full text-sm text-gray-600 file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
      />
      {files.length > 0 && (
        <div className="mt-2 space-y-1">
          <p className="text-xs text-gray-500">
            {files.length} file{files.length !== 1 ? "s" : ""} · {formatBytes(totalBytes)} total
          </p>
          <div className="flex flex-wrap gap-2 mt-1">
            {files.map((file, i) => (
              <div key={i} className="relative group">
                <img
                  src={URL.createObjectURL(file)}
                  alt={file.name}
                  className="h-16 w-16 object-cover rounded border border-gray-200"
                />
                <button
                  type="button"
                  onClick={() => onRemove(i)}
                  className="absolute -top-1.5 -right-1.5 hidden group-hover:flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-white text-xs leading-none"
                  aria-label={`Remove ${file.name}`}
                >
                  &times;
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
