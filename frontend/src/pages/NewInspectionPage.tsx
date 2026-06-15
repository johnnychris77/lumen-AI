import { FormEvent, useState } from "react";

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

const facilities = [
  "ORC",
  "St. Francis",
  "St. Mary’s",
  "Memorial Regional",
  "Southside",
  "Rappahannock General",
];

const departments = [
  "Decontamination",
  "Prep and Pack",
  "Sterilization",
  "Sterile Storage",
  "OR",
];

const findingTypes = [
  "Rust",
  "Blood",
  "Bone fragment",
  "Discoloration",
  "Lint",
  "Plastic/metal fragment",
  "Tissue",
  "Other",
];

const riskLevels = ["Low", "Medium", "High", "Critical"];
const captureMethods = ["Barcode", "QR Code", "KeyDot / 2D Dot", "Manual Entry"];
const instrumentCategories = [
  "Forceps",
  "Scissors",
  "Clamp",
  "Retractor",
  "Laparoscopic",
  "Orthopedic",
  "Spine",
  "Other",
];

const defaultBaselineStatus = {
  instrumentMatchStatus: "Not Checked",
  vendorBaselineStatus: "Not Checked",
  baselineSource: "None",
  baselineConfidence: "Unknown",
  rankingMode: "Pending baseline check",
  baselineReviewRequired: "Unknown",
};

const approvedBaselineStatus = {
  instrumentMatchStatus: "Matched",
  vendorBaselineStatus: "Approved Baseline Found",
  baselineSource: "Vendor Baseline",
  baselineConfidence: "High",
  rankingMode: "Baseline-confirmed ranking",
  baselineReviewRequired: "No",
};

const pendingBaselineStatus = {
  instrumentMatchStatus: "Partial Match",
  vendorBaselineStatus: "Pending Baseline Review",
  baselineSource: "Vendor Baseline",
  baselineConfidence: "Medium",
  rankingMode: "Provisional ranking",
  baselineReviewRequired: "Yes",
};

const noApprovedBaselineStatus = {
  instrumentMatchStatus: "Not Matched",
  vendorBaselineStatus: "No Approved Baseline",
  baselineSource: "None",
  baselineConfidence: "Unknown",
  rankingMode: "Manual review required",
  baselineReviewRequired: "Yes",
};

const approvedBaselineIdentity = {
  vendor: "Stryker",
  instrumentName: "Kerrison Rongeur",
  barcodeValue: "STRYKER-BARCODE-001",
  qrCodeValue: "STRYKER-QR-001",
  keydotValue: "DOT-STR-001",
  catalogNumber: "STR-KR-001",
  modelNumber: "KR-45",
};

const pendingBaselineIdentity = {
  vendor: "Aesculap",
  instrumentName: "Forceps",
  catalogNumber: "AES-FORCEPS-DEMO",
};

type BaselineStatus = typeof defaultBaselineStatus;

type FormState = {
  facility: string;
  department: string;
  trayName: string;
  captureMethod: string;
  barcodeValue: string;
  qrCodeValue: string;
  keydotValue: string;
  catalogNumber: string;
  modelNumber: string;
  manufacturer: string;
  instrumentName: string;
  instrumentCategory: string;
  vendor: string;
  findingType: string;
  riskLevel: string;
  notes: string;
};

type CapturedInspection = FormState & {
  photoName: string;
  baselineStatus: BaselineStatus;
};

const initialForm: FormState = {
  facility: "",
  department: "",
  trayName: "",
  captureMethod: "Barcode",
  barcodeValue: "",
  qrCodeValue: "",
  keydotValue: "",
  catalogNumber: "",
  modelNumber: "",
  manufacturer: "",
  instrumentName: "",
  instrumentCategory: "",
  vendor: "",
  findingType: "",
  riskLevel: "",
  notes: "",
};

function suggestedAction(riskLevel: string) {
  if (riskLevel === "Critical" || riskLevel === "High") {
    return "Route to findings review and prepare CAPA follow-up.";
  }
  if (riskLevel === "Medium") {
    return "Add to findings queue for same-shift review.";
  }
  return "Log the finding and monitor for repeat trend.";
}

function instrumentIdentitySummary(inspection: CapturedInspection) {
  if (inspection.barcodeValue.trim()) {
    return `Barcode ${inspection.barcodeValue}`;
  }
  if (inspection.qrCodeValue.trim()) {
    return `QR Code ${inspection.qrCodeValue}`;
  }
  if (inspection.keydotValue.trim()) {
    return `KeyDot / 2D Dot ${inspection.keydotValue}`;
  }

  return [
    inspection.vendor,
    inspection.manufacturer,
    inspection.instrumentName,
    inspection.catalogNumber,
    inspection.modelNumber,
    inspection.instrumentCategory,
  ]
    .filter((value) => value.trim())
    .join(" / ");
}

export default function NewInspectionPage() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [photo, setPhoto] = useState<File | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [baselineMessage, setBaselineMessage] = useState("");
  const [baselineStatus, setBaselineStatus] = useState(defaultBaselineStatus);
  const [captured, setCaptured] = useState<CapturedInspection | null>(null);

  function updateField(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function validate() {
    const hasScannedIdentity =
      Boolean(form.barcodeValue.trim()) ||
      Boolean(form.qrCodeValue.trim()) ||
      Boolean(form.keydotValue.trim());
    const hasManualIdentity =
      Boolean(form.catalogNumber.trim()) ||
      Boolean(form.modelNumber.trim()) ||
      Boolean(form.manufacturer.trim()) ||
      Boolean(form.vendor.trim()) ||
      Boolean(form.instrumentName.trim()) ||
      Boolean(form.instrumentCategory.trim());
    const missing = [
      ["Facility", form.facility],
      ["Department", form.department],
      ["Tray Name", form.trayName],
      ["Finding Type", form.findingType],
      ["Risk Level", form.riskLevel],
    ]
      .filter(([, value]) => !String(value).trim())
      .map(([label]) => `${label} is required.`);

    if (!hasScannedIdentity && !hasManualIdentity) {
      missing.push(
        "Add a barcode, QR code, KeyDot / 2D Dot value, or manual instrument details."
      );
    }

    setErrors(missing);
    return missing.length === 0;
  }

  function checkBaselineStatus() {
    const hasIdentityForBaselineCheck =
      Boolean(form.barcodeValue.trim()) ||
      Boolean(form.qrCodeValue.trim()) ||
      Boolean(form.keydotValue.trim()) ||
      Boolean(form.catalogNumber.trim()) ||
      Boolean(form.modelNumber.trim()) ||
      Boolean(form.vendor.trim()) ||
      Boolean(form.instrumentName.trim());

    if (!hasIdentityForBaselineCheck) {
      setBaselineStatus(defaultBaselineStatus);
      setBaselineMessage(
        "Enter a barcode, QR code, KeyDot / 2D Dot, catalog number, model number, vendor, or instrument name before checking baseline status."
      );
      return;
    }

    const approvedMatch = Object.entries(approvedBaselineIdentity).some(([field, approvedValue]) => {
      const value = form[field as keyof FormState];
      return (
        typeof value === "string" &&
        value.trim().length > 0 &&
        value.trim().toLowerCase() === approvedValue.toLowerCase()
      );
    });

    if (approvedMatch) {
      setBaselineStatus(approvedBaselineStatus);
      setBaselineMessage(
        "LumenAI can compare this inspection against an approved baseline before ranking."
      );
      return;
    }

    const pendingMatch = Object.entries(pendingBaselineIdentity).some(([field, pendingValue]) => {
      const value = form[field as keyof FormState];
      return (
        typeof value === "string" &&
        value.trim().length > 0 &&
        value.trim().toLowerCase() === pendingValue.toLowerCase()
      );
    });

    if (pendingMatch) {
      setBaselineStatus(pendingBaselineStatus);
      setBaselineMessage(
        "LumenAI will rank this finding provisionally until the baseline is approved."
      );
      return;
    }

    setBaselineStatus(noApprovedBaselineStatus);
    setBaselineMessage("Manual review is required before final ranking.");
  }

  async function submitInspection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setCaptured(null);

    if (!validate()) return;

    setSubmitting(true);

    const payload = {
      facility: form.facility,
      department: form.department,
      tray_name: form.trayName,
      capture_method: form.captureMethod,
      barcode_value: form.barcodeValue,
      qr_code_value: form.qrCodeValue,
      keydot_value: form.keydotValue,
      catalog_number: form.catalogNumber,
      model_number: form.modelNumber,
      manufacturer: form.manufacturer,
      instrument_name: form.instrumentName,
      instrument_category: form.instrumentCategory,
      vendor: form.vendor,
      instrument_match_status: baselineStatus.instrumentMatchStatus,
      baseline_status: baselineStatus.vendorBaselineStatus,
      baseline_source: baselineStatus.baselineSource,
      baseline_confidence: baselineStatus.baselineConfidence,
      ranking_mode: baselineStatus.rankingMode,
      baseline_review_required: baselineStatus.baselineReviewRequired,
      finding_type: form.findingType,
      risk_level: form.riskLevel,
      notes: form.notes,
      photo_name: photo?.name || "",
      source: "pilot_new_spd_inspection",
    };

    try {
      const res = await fetch(`${API_BASE}/inspections`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Inspection submission unavailable (${res.status})`);
      }

      setMessage("Inspection captured");
    } catch {
      setMessage("Inspection captured in pilot preview mode. Backend submission is unavailable.");
    } finally {
      setCaptured({ ...form, photoName: photo?.name || "", baselineStatus });
      setSubmitting(false);
    }
  }

  return (
    <main style={pageShell}>
      <section style={hero}>
        <nav style={topNav} aria-label="Inspection navigation">
          <a href="/operations" style={navLink}>Operations Dashboard</a>
          <a href="/findings" style={navLink}>Findings Queue</a>
          <a href="/capa" style={navLink}>CAPA Queue</a>
          <a href="/" style={navLink}>Public Landing</a>
        </nav>

        <p style={eyebrow}>Pilot capture</p>
        <h1 style={title}>New SPD Inspection</h1>
        <p style={subtitle}>
          Capture instrument, tray, and quality findings for sterile processing review.
        </p>
      </section>

      <section style={contentGrid}>
        <form onSubmit={submitInspection} style={formPanel}>
          {errors.length > 0 ? (
            <div style={errorBox}>
              {errors.map((error) => (
                <div key={error}>{error}</div>
              ))}
            </div>
          ) : null}

          <div style={fieldGrid}>
            <SelectField label="Facility" value={form.facility} options={facilities} onChange={(value) => updateField("facility", value)} required />
            <SelectField label="Department" value={form.department} options={departments} onChange={(value) => updateField("department", value)} required />
            <TextField label="Tray Name" value={form.trayName} onChange={(value) => updateField("trayName", value)} required />
          </div>

          <section style={identitySection} aria-labelledby="instrument-identification-title">
            <div style={sectionHeader}>
              <p style={sectionEyebrow}>Instrument Identification</p>
              <h2 id="instrument-identification-title" style={sectionTitle}>
                Identify the instrument
              </h2>
            </div>

            <div style={labelStyle}>
              <span>Capture Method</span>
              <div style={methodGrid}>
                {captureMethods.map((method) => (
                  <button
                    key={method}
                    type="button"
                    onClick={() => updateField("captureMethod", method)}
                    style={
                      form.captureMethod === method
                        ? { ...methodButton, ...methodButtonActive }
                        : methodButton
                    }
                    aria-pressed={form.captureMethod === method}
                  >
                    {method}
                  </button>
                ))}
              </div>
            </div>

            <div style={fieldGrid}>
              <TextField
                label="Barcode Value"
                value={form.barcodeValue}
                onChange={(value) => updateField("barcodeValue", value)}
                emphasized={form.captureMethod === "Barcode"}
              />
              <TextField
                label="QR Code Value"
                value={form.qrCodeValue}
                onChange={(value) => updateField("qrCodeValue", value)}
                emphasized={form.captureMethod === "QR Code"}
              />
              <TextField
                label="KeyDot / 2D Dot Value"
                value={form.keydotValue}
                onChange={(value) => updateField("keydotValue", value)}
                emphasized={form.captureMethod === "KeyDot / 2D Dot"}
              />
              <TextField
                label="Catalog Number"
                value={form.catalogNumber}
                onChange={(value) => updateField("catalogNumber", value)}
                emphasized={form.captureMethod === "Manual Entry"}
              />
              <TextField
                label="Model Number"
                value={form.modelNumber}
                onChange={(value) => updateField("modelNumber", value)}
                emphasized={form.captureMethod === "Manual Entry"}
              />
              <TextField
                label="Manufacturer"
                value={form.manufacturer}
                onChange={(value) => updateField("manufacturer", value)}
                emphasized={form.captureMethod === "Manual Entry"}
              />
              <TextField
                label="Vendor"
                value={form.vendor}
                onChange={(value) => updateField("vendor", value)}
                emphasized={form.captureMethod === "Manual Entry"}
              />
              <TextField
                label="Instrument Name"
                value={form.instrumentName}
                onChange={(value) => updateField("instrumentName", value)}
                emphasized={form.captureMethod === "Manual Entry"}
              />
              <SelectField
                label="Instrument Category"
                value={form.instrumentCategory}
                options={instrumentCategories}
                onChange={(value) => updateField("instrumentCategory", value)}
                emphasized={form.captureMethod === "Manual Entry"}
              />
            </div>
          </section>

          <section style={baselineSection} aria-labelledby="baseline-match-status-title">
            <div style={sectionHeader}>
              <p style={sectionEyebrow}>Baseline Match Status</p>
              <h2 id="baseline-match-status-title" style={sectionTitle}>
                Baseline check
              </h2>
            </div>

            <div style={baselineGrid}>
              <StatusRow label="Instrument Match Status" value={baselineStatus.instrumentMatchStatus} />
              <StatusRow label="Vendor Baseline Status" value={baselineStatus.vendorBaselineStatus} />
              <StatusRow label="Baseline Source" value={baselineStatus.baselineSource} />
              <StatusRow label="Baseline Confidence" value={baselineStatus.baselineConfidence} />
              <StatusRow label="Ranking Mode" value={baselineStatus.rankingMode} />
              <StatusRow label="Baseline Review Required" value={baselineStatus.baselineReviewRequired} />
            </div>

            <button
              type="button"
              onClick={checkBaselineStatus}
              style={baselineButton}
            >
              Check Baseline Status
            </button>

            {baselineMessage ? (
              <p style={baselineMessageStyle}>{baselineMessage}</p>
            ) : null}
          </section>

          <div style={fieldGrid}>
            <SelectField label="Finding Type" value={form.findingType} options={findingTypes} onChange={(value) => updateField("findingType", value)} required />
            <SelectField label="Risk Level" value={form.riskLevel} options={riskLevels} onChange={(value) => updateField("riskLevel", value)} required />
            <label style={labelStyle}>
              <span>Photo Upload</span>
              <input
                type="file"
                accept="image/*"
                onChange={(event) => setPhoto(event.target.files?.[0] || null)}
                style={fileInput}
              />
            </label>
          </div>

          <label style={labelStyle}>
            <span>Notes</span>
            <textarea
              value={form.notes}
              onChange={(event) => updateField("notes", event.target.value)}
              rows={5}
              placeholder="Add shift context, tray details, or follow-up notes."
              style={textareaStyle}
            />
          </label>

          <button type="submit" disabled={submitting} style={submitButton}>
            {submitting ? "Saving inspection..." : "Capture Inspection"}
          </button>
        </form>

        <aside style={sidePanel}>
          <h2 style={sideTitle}>Fast pilot capture</h2>
          <div style={stepList}>
            <div style={step}>1. Select facility and department.</div>
            <div style={step}>2. Scan a barcode, QR code, KeyDot / 2D Dot, or enter details.</div>
            <div style={step}>3. Classify finding and risk.</div>
            <div style={step}>4. Add photo or notes when useful.</div>
          </div>

          {message && captured ? (
            <div style={successBox}>
              <h2 style={successTitle}>Inspection captured</h2>
              <p style={successMessage}>{message}</p>
              <div style={summaryList}>
                <SummaryRow label="Facility" value={captured.facility} />
                <SummaryRow label="Capture method" value={captured.captureMethod} />
                <SummaryRow label="Instrument identity" value={instrumentIdentitySummary(captured)} />
                <SummaryRow label="Instrument" value={captured.instrumentName} />
                <SummaryRow label="Baseline status" value={captured.baselineStatus.vendorBaselineStatus} />
                <SummaryRow label="Ranking mode" value={captured.baselineStatus.rankingMode} />
                <SummaryRow label="Baseline review required" value={captured.baselineStatus.baselineReviewRequired} />
                <SummaryRow label="Finding type" value={captured.findingType} />
                <SummaryRow label="Risk level" value={captured.riskLevel} />
                <SummaryRow label="Suggested next action" value={suggestedAction(captured.riskLevel)} />
              </div>
            </div>
          ) : null}
        </aside>
      </section>
    </main>
  );
}

function TextField({
  label,
  value,
  onChange,
  required,
  emphasized,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  emphasized?: boolean;
}) {
  return (
    <label style={emphasized ? { ...labelStyle, ...emphasizedLabel } : labelStyle}>
      <span>{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        style={emphasized ? { ...inputStyle, ...emphasizedInput } : inputStyle}
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
  required,
  emphasized,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  required?: boolean;
  emphasized?: boolean;
}) {
  return (
    <label style={emphasized ? { ...labelStyle, ...emphasizedLabel } : labelStyle}>
      <span>{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        style={emphasized ? { ...inputStyle, ...emphasizedInput } : inputStyle}
      >
        <option value="">Select {label.toLowerCase()}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={summaryRow}>
      <span>{label}</span>
      <strong>{value || "Not provided"}</strong>
    </div>
  );
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={statusRow}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

const pageShell: React.CSSProperties = {
  minHeight: "100vh",
  padding: "28px",
  background: "linear-gradient(180deg, #07111f 0%, #0f172a 48%, #111827 100%)",
  color: "#e5e7eb",
  fontFamily: "Arial, sans-serif",
};

const hero: React.CSSProperties = {
  maxWidth: "1180px",
  margin: "0 auto 22px",
};

const topNav: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  flexWrap: "wrap",
  marginBottom: "22px",
};

const navLink: React.CSSProperties = {
  color: "#cbd5e1",
  textDecoration: "none",
  fontWeight: 800,
  padding: "10px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(148, 163, 184, 0.24)",
  background: "rgba(15, 23, 42, 0.72)",
};

const eyebrow: React.CSSProperties = {
  margin: "0 0 10px",
  color: "#67e8f9",
  fontWeight: 900,
  textTransform: "uppercase",
  fontSize: "13px",
};

const title: React.CSSProperties = {
  margin: 0,
  color: "#ffffff",
  fontSize: "42px",
  lineHeight: 1.08,
};

const subtitle: React.CSSProperties = {
  maxWidth: "780px",
  color: "#cbd5e1",
  fontSize: "17px",
  lineHeight: 1.6,
};

const contentGrid: React.CSSProperties = {
  maxWidth: "1180px",
  margin: "0 auto",
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 340px), 1fr))",
  gap: "18px",
};

const formPanel: React.CSSProperties = {
  border: "1px solid rgba(148, 163, 184, 0.22)",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.82)",
  padding: "20px",
};

const fieldGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 240px), 1fr))",
  gap: "16px",
};

const identitySection: React.CSSProperties = {
  margin: "18px 0",
  padding: "18px",
  borderRadius: "8px",
  border: "1px solid rgba(56, 189, 248, 0.28)",
  background: "rgba(8, 47, 73, 0.32)",
};

const sectionHeader: React.CSSProperties = {
  marginBottom: "14px",
};

const sectionEyebrow: React.CSSProperties = {
  margin: "0 0 6px",
  color: "#67e8f9",
  fontWeight: 900,
  textTransform: "uppercase",
  fontSize: "12px",
};

const sectionTitle: React.CSSProperties = {
  margin: 0,
  color: "#ffffff",
  fontSize: "22px",
};

const methodGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 170px), 1fr))",
  gap: "10px",
  marginBottom: "16px",
};

const methodButton: React.CSSProperties = {
  minHeight: "44px",
  borderRadius: "8px",
  border: "1px solid rgba(148, 163, 184, 0.3)",
  background: "rgba(15, 23, 42, 0.86)",
  color: "#dbeafe",
  fontWeight: 900,
  cursor: "pointer",
};

const methodButtonActive: React.CSSProperties = {
  borderColor: "#38bdf8",
  background: "rgba(14, 165, 233, 0.22)",
  color: "#ffffff",
  boxShadow: "0 0 0 2px rgba(56, 189, 248, 0.18)",
};

const baselineSection: React.CSSProperties = {
  margin: "18px 0",
  padding: "18px",
  borderRadius: "8px",
  border: "1px solid rgba(34, 197, 94, 0.28)",
  background: "rgba(6, 78, 59, 0.22)",
};

const baselineGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 210px), 1fr))",
  gap: "10px",
  marginBottom: "16px",
};

const statusRow: React.CSSProperties = {
  display: "grid",
  gap: "6px",
  padding: "12px",
  borderRadius: "8px",
  border: "1px solid rgba(148, 163, 184, 0.24)",
  background: "rgba(15, 23, 42, 0.78)",
  color: "#cbd5e1",
};

const baselineButton: React.CSSProperties = {
  minHeight: "46px",
  border: "none",
  borderRadius: "8px",
  background: "#22c55e",
  color: "#052e16",
  fontWeight: 900,
  padding: "0 16px",
  cursor: "pointer",
};

const baselineMessageStyle: React.CSSProperties = {
  margin: "12px 0 0",
  color: "#bbf7d0",
  fontWeight: 800,
};

const labelStyle: React.CSSProperties = {
  display: "grid",
  gap: "8px",
  color: "#dbeafe",
  fontWeight: 800,
  fontSize: "14px",
  marginBottom: "16px",
};

const emphasizedLabel: React.CSSProperties = {
  color: "#ffffff",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  minHeight: "46px",
  borderRadius: "8px",
  border: "1px solid rgba(148, 163, 184, 0.35)",
  background: "#0f172a",
  color: "#ffffff",
  padding: "11px 12px",
  fontSize: "16px",
};

const emphasizedInput: React.CSSProperties = {
  borderColor: "#38bdf8",
  boxShadow: "0 0 0 2px rgba(56, 189, 248, 0.14)",
};

const fileInput: React.CSSProperties = {
  ...inputStyle,
  padding: "10px",
};

const textareaStyle: React.CSSProperties = {
  ...inputStyle,
  resize: "vertical",
  minHeight: "116px",
};

const submitButton: React.CSSProperties = {
  width: "100%",
  minHeight: "52px",
  border: "none",
  borderRadius: "8px",
  background: "#38bdf8",
  color: "#082f49",
  fontWeight: 900,
  fontSize: "17px",
  cursor: "pointer",
};

const sidePanel: React.CSSProperties = {
  border: "1px solid rgba(148, 163, 184, 0.22)",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.82)",
  padding: "20px",
  alignSelf: "start",
};

const sideTitle: React.CSSProperties = {
  margin: "0 0 14px",
  color: "#ffffff",
};

const stepList: React.CSSProperties = {
  display: "grid",
  gap: "10px",
};

const step: React.CSSProperties = {
  padding: "12px",
  borderRadius: "8px",
  background: "rgba(30, 41, 59, 0.82)",
  color: "#e5e7eb",
  fontWeight: 700,
};

const errorBox: React.CSSProperties = {
  marginBottom: "16px",
  padding: "12px 14px",
  borderRadius: "8px",
  background: "rgba(127, 29, 29, 0.35)",
  border: "1px solid rgba(248, 113, 113, 0.45)",
  color: "#fecaca",
  fontWeight: 700,
};

const successBox: React.CSSProperties = {
  marginTop: "18px",
  padding: "16px",
  borderRadius: "8px",
  background: "rgba(6, 78, 59, 0.42)",
  border: "1px solid rgba(52, 211, 153, 0.42)",
};

const successTitle: React.CSSProperties = {
  margin: "0 0 8px",
  color: "#d1fae5",
};

const successMessage: React.CSSProperties = {
  margin: "0 0 12px",
  color: "#a7f3d0",
};

const summaryList: React.CSSProperties = {
  display: "grid",
  gap: "10px",
};

const summaryRow: React.CSSProperties = {
  display: "grid",
  gap: "4px",
  paddingBottom: "10px",
  borderBottom: "1px solid rgba(167, 243, 208, 0.22)",
  color: "#d1fae5",
};
