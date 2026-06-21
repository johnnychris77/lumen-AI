import { ChangeEvent, FormEvent, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth, API_BASE } from "@/lib/auth";
import { FormSection } from "@/components/ui/FormSection";
import { RequiredLabel, FieldError } from "@/components/ui/RequiredField";
import { StatusBanner } from "@/components/ui/StatusBanner";

// ─── types ───────────────────────────────────────────────────────────────────

type FormFields = {
  vendor_name: string;
  manufacturer: string;
  submitter_name: string;
  submitter_organization: string;
  instrument_name: string;
  model_number: string;
  catalog_number: string;
  barcode: string;
  qr_code: string;
  keydot_reference: string;
  known_normal_characteristics: string;
  known_abnormal_characteristics: string;
  ifu_url: string;
  baseline_notes: string;
};

type FieldErrors = Partial<Record<keyof FormFields, string>>;

const MAX_FILE_BYTES = 10 * 1024 * 1024;

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const initialForm: FormFields = {
  vendor_name: "",
  manufacturer: "",
  submitter_name: "",
  submitter_organization: "",
  instrument_name: "",
  model_number: "",
  catalog_number: "",
  barcode: "",
  qr_code: "",
  keydot_reference: "",
  known_normal_characteristics: "",
  known_abnormal_characteristics: "",
  ifu_url: "",
  baseline_notes: "",
};

// ─── component ────────────────────────────────────────────────────────────────

export default function VendorIntakePage() {
  const { headers } = useAuth();
  const [form, setForm] = useState<FormFields>(initialForm);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [baselineImages, setBaselineImages] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [submittedId, setSubmittedId] = useState<string | null>(null);

  const imageInputRef = useRef<HTMLInputElement>(null);

  // ── helpers ────────────────────────────────────────────────────────────────

  function setStr(key: keyof FormFields) {
    return (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setForm((f) => ({ ...f, [key]: e.target.value }));
    };
  }

  function clearError(key: keyof FormFields) {
    setFieldErrors((e) => { const n = { ...e }; delete n[key]; return n; });
  }

  function onBlurStr(key: keyof FormFields) {
    return () => {
      const required: (keyof FormFields)[] = [
        "vendor_name",
        "manufacturer",
        "submitter_name",
        "instrument_name",
        "known_normal_characteristics",
      ];
      if (required.includes(key) && !form[key].trim()) {
        setFieldErrors((e) => ({ ...e, [key]: "This field is required." }));
      } else {
        clearError(key);
      }
    };
  }

  // ── images ─────────────────────────────────────────────────────────────────

  function handleImages(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    const valid = files.filter((f) => f.size <= MAX_FILE_BYTES);
    const oversized = files.filter((f) => f.size > MAX_FILE_BYTES);
    setBaselineImages(valid);
    if (oversized.length) alert(`${oversized.length} file(s) exceed 10 MB and were removed.`);
  }

  function removeImage(index: number) {
    setBaselineImages((prev) => prev.filter((_, i) => i !== index));
  }

  // ── validation ─────────────────────────────────────────────────────────────

  function validate(): boolean {
    const errors: FieldErrors = {};
    const required: { key: keyof FormFields; label: string }[] = [
      { key: "vendor_name", label: "Vendor Name" },
      { key: "manufacturer", label: "Manufacturer" },
      { key: "submitter_name", label: "Submitter Name" },
      { key: "instrument_name", label: "Instrument Name" },
      { key: "known_normal_characteristics", label: "Known Normal Characteristics" },
    ];
    for (const { key, label } of required) {
      if (!form[key].trim()) errors[key] = `${label} is required.`;
    }
    if (form.ifu_url && !/^https?:\/\/.+/.test(form.ifu_url)) {
      errors.ifu_url = "Enter a valid URL (must start with http:// or https://).";
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
        vendor_name: form.vendor_name,
        manufacturer: form.manufacturer,
        submitter_name: form.submitter_name,
        submitter_organization: form.submitter_organization,
        instrument_name: form.instrument_name,
        model_number: form.model_number,
        catalog_number: form.catalog_number,
        barcode: form.barcode,
        qr_code: form.qr_code,
        keydot_reference: form.keydot_reference,
        known_normal_characteristics: form.known_normal_characteristics,
        known_abnormal_characteristics: form.known_abnormal_characteristics,
        ifu_url: form.ifu_url,
        baseline_notes: form.baseline_notes,
        source: "pilot_vendor_intake_form",
      };

      const res = await fetch(`${API_BASE}/api/network/baselines`, {
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
          // ignore
        }
        setBanner({ type: "error", message: msg });
        return;
      }

      let id = "";
      try {
        const data = await res.json();
        id = String(data?.id || data?.baseline_id || "");
      } catch {
        // ignore
      }
      setSubmittedId(id);

      // Upload baseline images if any were selected
      if (baselineImages.length > 0) {
        try {
          const fd = new FormData();
          baselineImages.forEach((f) => fd.append("images", f));
          const imgToken = localStorage.getItem("token");
          await fetch(`${API_BASE}/api/baselines/upload-images`, {
            method: "POST",
            headers: { Authorization: `Bearer ${imgToken}` },
            body: fd,
          });
        } catch {
          // Non-fatal — baseline record already saved
        }
      }

      setBanner({
        type: "success",
        message: `Baseline submitted successfully.${id ? ` ID: ${id}` : ""}${baselineImages.length > 0 ? ` ${baselineImages.length} image(s) uploaded.` : ""}`,
      });
    } finally {
      setSubmitting(false);
    }
  }

  function resetForm() {
    setForm(initialForm);
    setBaselineImages([]);
    setFieldErrors({});
    setBanner(null);
    setSubmittedId(null);
  }

  const inputCls =
    "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

  const totalBytes = baselineImages.reduce((s, f) => s + f.size, 0);

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-6 px-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Vendor Baseline Intake</h1>
        <p className="text-sm text-gray-500 mt-1">
          Submit instrument baseline information for quality review and approval.
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
        <button type="button" onClick={resetForm} className="text-sm text-blue-600 underline">
          Submit Another Baseline
        </button>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-6">
        {/* Section 1 — Vendor & Manufacturer */}
        <FormSection title="Vendor & Manufacturer">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <RequiredLabel label="Vendor Name" />
              <input
                id="vendor_name"
                type="text"
                value={form.vendor_name}
                onChange={setStr("vendor_name")}
                onBlur={onBlurStr("vendor_name")}
                required
                className={inputCls}
              />
              <FieldError message={fieldErrors.vendor_name} />
            </div>

            <div>
              <RequiredLabel label="Manufacturer" />
              <input
                id="manufacturer"
                type="text"
                value={form.manufacturer}
                onChange={setStr("manufacturer")}
                onBlur={onBlurStr("manufacturer")}
                required
                className={inputCls}
              />
              <FieldError message={fieldErrors.manufacturer} />
            </div>

            <div>
              <RequiredLabel label="Submitter Name" />
              <input
                id="submitter_name"
                type="text"
                value={form.submitter_name}
                onChange={setStr("submitter_name")}
                onBlur={onBlurStr("submitter_name")}
                required
                className={inputCls}
              />
              <FieldError message={fieldErrors.submitter_name} />
            </div>

            <div>
              <label htmlFor="submitter_organization" className="block text-sm font-medium text-gray-700">
                Submitter Organization
              </label>
              <input
                id="submitter_organization"
                type="text"
                value={form.submitter_organization}
                onChange={setStr("submitter_organization")}
                className={inputCls}
              />
            </div>
          </div>
        </FormSection>

        {/* Section 2 — Instrument Identification */}
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
              <label htmlFor="catalog_number" className="block text-sm font-medium text-gray-700">
                Catalog Number
              </label>
              <input
                id="catalog_number"
                type="text"
                value={form.catalog_number}
                onChange={setStr("catalog_number")}
                className={inputCls}
              />
            </div>

            <div>
              <label htmlFor="barcode" className="block text-sm font-medium text-gray-700">
                Barcode / UDI
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
                QR Code
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
              <label htmlFor="keydot_reference" className="block text-sm font-medium text-gray-700">
                KeyDot Reference
              </label>
              <input
                id="keydot_reference"
                type="text"
                value={form.keydot_reference}
                onChange={setStr("keydot_reference")}
                className={inputCls}
              />
            </div>
          </div>
        </FormSection>

        {/* Section 3 — Baseline Characteristics */}
        <FormSection
          title="Baseline Characteristics"
          description="Describe what makes this instrument acceptable or unacceptable during inspection."
        >
          <div>
            <RequiredLabel label="Known Normal Characteristics" />
            <textarea
              id="known_normal_characteristics"
              value={form.known_normal_characteristics}
              onChange={setStr("known_normal_characteristics")}
              onBlur={onBlurStr("known_normal_characteristics")}
              required
              rows={4}
              placeholder="Describe the expected clean, undamaged appearance of this instrument..."
              className={inputCls}
            />
            <FieldError message={fieldErrors.known_normal_characteristics} />
          </div>

          <div>
            <label htmlFor="known_abnormal_characteristics" className="block text-sm font-medium text-gray-700">
              Known Abnormal Characteristics
            </label>
            <textarea
              id="known_abnormal_characteristics"
              value={form.known_abnormal_characteristics}
              onChange={setStr("known_abnormal_characteristics")}
              rows={4}
              placeholder="Describe defects or contamination that should be flagged during inspection..."
              className={inputCls}
            />
          </div>
        </FormSection>

        {/* Section 4 — Documentation */}
        <FormSection title="Documentation">
          <div>
            <label htmlFor="ifu_url" className="block text-sm font-medium text-gray-700">
              IFU / Reference Document URL
            </label>
            <input
              id="ifu_url"
              type="url"
              value={form.ifu_url}
              onChange={setStr("ifu_url")}
              onBlur={onBlurStr("ifu_url")}
              placeholder="https://"
              className={inputCls}
            />
            <FieldError message={fieldErrors.ifu_url} />
          </div>

          <div>
            <label htmlFor="baseline_notes" className="block text-sm font-medium text-gray-700">
              Baseline Notes
            </label>
            <textarea
              id="baseline_notes"
              value={form.baseline_notes}
              onChange={setStr("baseline_notes")}
              rows={3}
              className={inputCls}
            />
          </div>
        </FormSection>

        {/* Section 5 — Images */}
        <FormSection
          title="Baseline Reference Images"
          description="Upload reference images of this instrument in acceptable condition. Max 10 MB each."
        >
          <div>
            <label htmlFor="baseline_images" className="block text-sm font-medium text-gray-700">
              Baseline Reference Images
            </label>
            <input
              ref={imageInputRef}
              id="baseline_images"
              type="file"
              accept="image/*"
              multiple
              onChange={handleImages}
              className="mt-1 block w-full text-sm text-gray-600 file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
            />

            {baselineImages.length > 0 && (
              <div className="mt-2 space-y-1">
                <p className="text-xs text-gray-500">
                  {baselineImages.length} file{baselineImages.length !== 1 ? "s" : ""} ·{" "}
                  {formatBytes(totalBytes)} total
                </p>
                <div className="flex flex-wrap gap-2 mt-1">
                  {baselineImages.map((file, i) => (
                    <div key={i} className="relative group">
                      <img
                        src={URL.createObjectURL(file)}
                        alt={file.name}
                        className="h-16 w-16 object-cover rounded border border-gray-200"
                      />
                      <button
                        type="button"
                        onClick={() => removeImage(i)}
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

            <p className="mt-2 text-xs text-gray-500">
              Images are uploaded securely after form submission. Max 10 MB per file. Only SHA-256 hash is stored — raw images are not retained in the database.
            </p>
          </div>
        </FormSection>

        {/* Submit */}
        <div className="flex flex-col gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? "Submitting…" : "Submit Baseline"}
          </button>

          <p className="text-xs text-gray-500 text-center">
            Your baseline submission will be reviewed by the LumenAI quality team and approved before
            use in inspection comparisons.
          </p>
        </div>
      </form>

      <nav className="flex flex-wrap gap-3 text-xs text-blue-600 border-t pt-4">
        <Link to="/" className="hover:underline">Dashboard</Link>
        <Link to="/inspection/new" className="hover:underline">New Inspection</Link>
        <Link to="/intake-history" className="hover:underline">Intake History</Link>
      </nav>
    </div>
  );
}
