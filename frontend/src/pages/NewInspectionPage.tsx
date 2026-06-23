import { ChangeEvent, FormEvent, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth, API_BASE } from "@/lib/auth";
import { FormSection } from "@/components/ui/FormSection";
import { RequiredLabel, FieldError } from "@/components/ui/RequiredField";
import { StatusBanner } from "@/components/ui/StatusBanner";

// ─── types ───────────────────────────────────────────────────────────────────

type FindingCategory =
  | "blood"
  | "bone"
  | "tissue"
  | "debris"
  | "corrosion"
  | "crack"
  | "insulation_damage"
  | "other";

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
  keydot_id: string;
  finding_categories: FindingCategory[];
  risk_level: string;
  notes: string;
  baseline_status: string;
  baseline_source: string;
};

type FieldErrors = Partial<Record<keyof FormFields, string>>;

// ─── constants ────────────────────────────────────────────────────────────────

const INSTRUMENT_TYPES = [
  { value: "scissors", label: "Scissors" },
  { value: "forceps", label: "Forceps" },
  { value: "clamp", label: "Clamp" },
  { value: "needle_holder", label: "Needle Holder" },
  { value: "retractor", label: "Retractor" },
  { value: "scalpel_handle", label: "Scalpel Handle" },
  { value: "scope", label: "Scope" },
  { value: "drill", label: "Drill" },
  { value: "other", label: "Other" },
];

const FINDING_CATEGORIES: { value: FindingCategory; label: string }[] = [
  { value: "blood", label: "Blood" },
  { value: "bone", label: "Bone" },
  { value: "tissue", label: "Tissue" },
  { value: "debris", label: "Debris" },
  { value: "corrosion", label: "Corrosion" },
  { value: "crack", label: "Crack" },
  { value: "insulation_damage", label: "Insulation Damage" },
  { value: "other", label: "Other" },
];

const RISK_LEVELS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

const BASELINE_STATUSES = [
  { value: "matched", label: "Matched" },
  { value: "no_baseline", label: "No Baseline" },
  { value: "deviation", label: "Deviation" },
  { value: "unknown", label: "Unknown" },
];

const MAX_FILE_BYTES = 10 * 1024 * 1024;

function nowDatetimeLocal() {
  const d = new Date();
  // format: YYYY-MM-DDTHH:mm
  return d.toISOString().slice(0, 16);
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
  keydot_id: "",
  finding_categories: [],
  risk_level: "",
  notes: "",
  baseline_status: "",
  baseline_source: "",
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
  const [submittedId, setSubmittedId] = useState<string | null>(null);

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

  function validateField(key: keyof FormFields, value: FormFields[typeof key]) {
    const required: (keyof FormFields)[] = [
      "facility_name",
      "technician_name",
      "inspection_date",
      "tray_name",
      "instrument_name",
      "instrument_type",
      "risk_level",
    ];
    if (required.includes(key) && !String(value).trim()) {
      setFieldErrors((e) => ({ ...e, [key]: "This field is required." }));
    } else {
      clearError(key);
    }
  }

  function onBlurStr(key: keyof FormFields) {
    return () => validateField(key, form[key]);
  }

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
    clearError("finding_categories");
  }

  function clearFindings() {
    setForm((f) => ({ ...f, finding_categories: [] }));
    clearError("finding_categories");
  }

  // ── image handling ─────────────────────────────────────────────────────────

  function handleImages(
    e: ChangeEvent<HTMLInputElement>,
    setter: React.Dispatch<React.SetStateAction<File[]>>
  ) {
    const files = Array.from(e.target.files || []);
    const valid = files.filter((f) => f.size <= MAX_FILE_BYTES);
    const oversized = files.filter((f) => f.size > MAX_FILE_BYTES);
    setter(valid);
    if (oversized.length) {
      alert(`${oversized.length} file(s) exceed 10 MB and were removed.`);
    }
  }

  function removeImage(
    index: number,
    setter: React.Dispatch<React.SetStateAction<File[]>>
  ) {
    setter((prev) => prev.filter((_, i) => i !== index));
  }

  // ── validation ─────────────────────────────────────────────────────────────

  function validate(): boolean {
    const errors: FieldErrors = {};
    const requiredStr: { key: keyof FormFields; label: string }[] = [
      { key: "facility_name", label: "Facility / Site" },
      { key: "technician_name", label: "Technician Name" },
      { key: "inspection_date", label: "Inspection Date & Time" },
      { key: "tray_name", label: "Tray Name" },
      { key: "instrument_name", label: "Instrument Name" },
      { key: "instrument_type", label: "Instrument Type" },
      { key: "risk_level", label: "Risk Level" },
    ];
    for (const { key, label } of requiredStr) {
      if (!String(form[key]).trim()) errors[key] = `${label} is required.`;
    }
    if (form.finding_categories.length === 0) {
      errors.finding_categories = "Select at least one finding category.";
    }
    setFieldErrors(errors);
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
      const payload = {
        facility_name: form.facility_name,
        department: form.department,
        technician_name: form.technician_name,
        inspection_date: form.inspection_date,
        tray_name: form.tray_name,
        tray_id: form.tray_id,
        instrument_name: form.instrument_name,
        instrument_type: form.instrument_type,
        manufacturer: form.manufacturer,
        model_number: form.model_number,
        serial_number: form.serial_number,
        barcode: form.barcode,
        qr_code: form.qr_code,
        keydot_id: form.keydot_id,
        finding_categories: form.finding_categories,
        risk_level: form.risk_level,
        notes: form.notes,
        baseline_status: form.baseline_status,
        baseline_source: form.baseline_source,
        source: "pilot_inspection_form",
      };

      const res = await fetch(`${API_BASE}/api/inspections`, {
        method: "POST",
        headers: hdrs,
        body: JSON.stringify(payload),
      });

      if (res.status === 401 || res.status === 403) {
        setBanner({ type: "error", message: `${res.status}` });
        return;
      }

      if (!res.ok) {
        let msg = `Submission failed (${res.status}).`;
        try {
          const data = await res.json();
          msg = data?.detail || data?.message || msg;
        } catch {
          // ignore parse error
        }
        setBanner({ type: "error", message: msg });
        return;
      }

      let id = "";
      try {
        const data = await res.json();
        id = String(data?.id || data?.inspection_id || "");
      } catch {
        // ignore
      }
      setSubmittedId(id);

      // Upload images if any were selected
      const allImages = [...inspectionImages, ...borescopeImages];
      if (allImages.length > 0) {
        try {
          const fd = new FormData();
          allImages.forEach((f) => fd.append("images", f));
          await fetch(`${API_BASE}/api/inspections/upload-images`, {
            method: "POST",
            headers: { Authorization: hdrs["Authorization"] },
            body: fd,
          });
        } catch {
          // Image upload failure is non-fatal — inspection record already saved
        }
      }

      setBanner({
        type: "success",
        message: `Inspection submitted successfully.${id ? ` ID: ${id}` : ""}${allImages.length > 0 ? ` ${allImages.length} image(s) uploaded.` : ""}`,
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
    setSubmittedId(null);
  }

  // ─────────────────────────────────────────────────────────────────────────

  const inputCls =
    "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-6 px-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">New Inspection</h1>
        <p className="text-sm text-gray-500 mt-1">
          Capture instrument findings for sterile processing quality review.
        </p>
      </div>

      {banner && (
        <StatusBanner
          type={banner.type}
          message={banner.message}
          onDismiss={() => setBanner(null)}
        />
      )}

      {submittedId !== null && banner?.type === "success" && (
        <button
          type="button"
          onClick={resetForm}
          className="text-sm text-blue-600 underline"
        >
          Submit Another Inspection
        </button>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-6">
        {/* Section 1 — Facility & Assignment */}
        <FormSection
          title="Facility & Assignment"
          description="Who is performing this inspection and where."
        >
          <div>
            <RequiredLabel label="Facility / Site" />
            <input
              id="facility_name"
              type="text"
              value={form.facility_name}
              onChange={setStr("facility_name")}
              onBlur={onBlurStr("facility_name")}
              required
              className={inputCls}
              placeholder="e.g. Memorial Regional"
            />
            <FieldError message={fieldErrors.facility_name} />
          </div>

          <div>
            <label htmlFor="department" className="block text-sm font-medium text-gray-700">
              Department / Unit
            </label>
            <input
              id="department"
              type="text"
              value={form.department}
              onChange={setStr("department")}
              className={inputCls}
              placeholder="e.g. Decontamination"
            />
          </div>

          <div>
            <RequiredLabel label="Technician Name" />
            <input
              id="technician_name"
              type="text"
              value={form.technician_name}
              onChange={setStr("technician_name")}
              onBlur={onBlurStr("technician_name")}
              required
              className={inputCls}
            />
            <FieldError message={fieldErrors.technician_name} />
          </div>

          <div>
            <RequiredLabel label="Inspection Date & Time" />
            <input
              id="inspection_date"
              type="datetime-local"
              value={form.inspection_date}
              onChange={setStr("inspection_date")}
              onBlur={onBlurStr("inspection_date")}
              required
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
              id="tray_name"
              type="text"
              value={form.tray_name}
              onChange={setStr("tray_name")}
              onBlur={onBlurStr("tray_name")}
              required
              className={inputCls}
            />
            <FieldError message={fieldErrors.tray_name} />
          </div>

          <div>
            <label htmlFor="tray_id" className="block text-sm font-medium text-gray-700">
              Tray ID / Tray Number
            </label>
            <input
              id="tray_id"
              type="text"
              value={form.tray_id}
              onChange={setStr("tray_id")}
              className={inputCls}
            />
          </div>
        </FormSection>

        {/* Section 3 — Instrument Identification */}
        <FormSection title="Instrument Identification">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <RequiredLabel label="Instrument Name" />
              <input
                id="instrument_name"
                type="text"
                value={form.instrument_name}
                onChange={setStr("instrument_name")}
                onBlur={onBlurStr("instrument_name")}
                required
                className={inputCls}
              />
              <FieldError message={fieldErrors.instrument_name} />
            </div>

            <div>
              <RequiredLabel label="Instrument Type" />
              <select
                id="instrument_type"
                value={form.instrument_type}
                onChange={setStr("instrument_type")}
                onBlur={onBlurStr("instrument_type")}
                required
                className={inputCls}
              >
                <option value="">Select type…</option>
                {INSTRUMENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
              <FieldError message={fieldErrors.instrument_type} />
            </div>

            <div>
              <label htmlFor="manufacturer" className="block text-sm font-medium text-gray-700">
                Manufacturer
              </label>
              <input
                id="manufacturer"
                type="text"
                value={form.manufacturer}
                onChange={setStr("manufacturer")}
                className={inputCls}
              />
            </div>

            <div>
              <label htmlFor="model_number" className="block text-sm font-medium text-gray-700">
                Model Number
              </label>
              <input
                id="model_number"
                type="text"
                value={form.model_number}
                onChange={setStr("model_number")}
                className={inputCls}
              />
            </div>

            <div>
              <label htmlFor="serial_number" className="block text-sm font-medium text-gray-700">
                Serial Number
              </label>
              <input
                id="serial_number"
                type="text"
                value={form.serial_number}
                onChange={setStr("serial_number")}
                className={inputCls}
              />
            </div>

            <div>
              <label htmlFor="barcode" className="block text-sm font-medium text-gray-700">
                Barcode
              </label>
              <input
                id="barcode"
                type="text"
                value={form.barcode}
                onChange={setStr("barcode")}
                className={inputCls}
              />
            </div>

            <div>
              <label htmlFor="qr_code" className="block text-sm font-medium text-gray-700">
                QR Code / UDI
              </label>
              <input
                id="qr_code"
                type="text"
                value={form.qr_code}
                onChange={setStr("qr_code")}
                className={inputCls}
              />
            </div>

            <div>
              <label htmlFor="keydot_id" className="block text-sm font-medium text-gray-700">
                KeyDot ID
              </label>
              <input
                id="keydot_id"
                type="text"
                value={form.keydot_id}
                onChange={setStr("keydot_id")}
                className={inputCls}
              />
            </div>
          </div>
        </FormSection>

        {/* Section 4 — Findings */}
        <FormSection title="Findings" description="Select all applicable finding categories.">
          <div>
            <RequiredLabel label="Finding Categories" />
            <div className="mt-2 grid grid-cols-2 sm:grid-cols-3 gap-2">
              {FINDING_CATEGORIES.map((cat) => (
                <label
                  key={cat.value}
                  className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={form.finding_categories.includes(cat.value)}
                    onChange={() => toggleCategory(cat.value)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  {cat.label}
                </label>
              ))}
              <label className="flex items-center gap-2 text-sm text-gray-500 cursor-pointer col-span-full">
                <input
                  type="checkbox"
                  checked={form.finding_categories.length === 0}
                  onChange={clearFindings}
                  className="rounded border-gray-300 text-gray-400 focus:ring-gray-400"
                />
                No findings
              </label>
            </div>
            <FieldError message={fieldErrors.finding_categories} />
          </div>

          <div>
            <RequiredLabel label="Risk Level" />
            <select
              id="risk_level"
              value={form.risk_level}
              onChange={setStr("risk_level")}
              onBlur={onBlurStr("risk_level")}
              required
              className={inputCls}
            >
              <option value="">Select risk level…</option>
              {RISK_LEVELS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
            <FieldError message={fieldErrors.risk_level} />
          </div>

          <div>
            <label htmlFor="notes" className="block text-sm font-medium text-gray-700">
              Inspection Notes
            </label>
            <textarea
              id="notes"
              value={form.notes}
              onChange={setStr("notes")}
              rows={4}
              className={inputCls}
              placeholder="Add shift context, tray details, or follow-up notes."
            />
          </div>
        </FormSection>

        {/* Section 5 — Baseline Reference */}
        <FormSection title="Baseline Reference">
          <div>
            <label htmlFor="baseline_status" className="block text-sm font-medium text-gray-700">
              Baseline Match Status
            </label>
            <select
              id="baseline_status"
              value={form.baseline_status}
              onChange={setStr("baseline_status")}
              className={inputCls}
            >
              <option value="">Select status…</option>
              {BASELINE_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="baseline_source" className="block text-sm font-medium text-gray-700">
              Baseline Source / Reference
            </label>
            <input
              id="baseline_source"
              type="text"
              value={form.baseline_source}
              onChange={setStr("baseline_source")}
              className={inputCls}
            />
          </div>
        </FormSection>

        {/* Section 6 — Images */}
        <FormSection
          title="Images"
          description="Max 10 MB per file. Images are stored locally and noted on the record."
        >
          <ImageFileInput
            id="inspection_images"
            label="Inspection Images"
            files={inspectionImages}
            inputRef={inspectionInputRef}
            onChange={(e) => handleImages(e, setInspectionImages)}
            onRemove={(i) => removeImage(i, setInspectionImages)}
          />

          <ImageFileInput
            id="borescope_images"
            label="Borescope Images"
            files={borescopeImages}
            inputRef={borescopeInputRef}
            onChange={(e) => handleImages(e, setBorescopeImages)}
            onRemove={(i) => removeImage(i, setBorescopeImages)}
          />

          <p className="text-xs text-gray-500 mt-1">
            Images are uploaded securely after form submission. Max 10 MB per file. Only SHA-256 hash is stored — raw images are not retained in the database.
          </p>
        </FormSection>

        {/* Submit */}
        <div className="flex flex-col gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? "Submitting…" : "Submit Inspection"}
          </button>

          <p className="text-xs text-gray-500 text-center">
            Your inspection will be reviewed by the quality team. High and critical findings trigger
            immediate review.
          </p>
        </div>
      </form>

      {/* Quick links */}
      <nav className="flex flex-wrap gap-3 text-xs text-blue-600 border-t pt-4">
        <Link to="/" className="hover:underline">Dashboard</Link>
        <Link to="/intake-history" className="hover:underline">Intake History</Link>
        <Link to="/vendor-intake" className="hover:underline">Vendor Intake</Link>
      </nav>
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
      <label htmlFor={id} className="block text-sm font-medium text-gray-700">
        {label}
      </label>
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept="image/*"
        multiple
        onChange={onChange}
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
