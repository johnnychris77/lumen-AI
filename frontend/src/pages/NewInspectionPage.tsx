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

type FormState = {
  facility: string;
  department: string;
  trayName: string;
  instrumentName: string;
  vendor: string;
  findingType: string;
  riskLevel: string;
  notes: string;
};

type CapturedInspection = FormState & {
  photoName: string;
};

const initialForm: FormState = {
  facility: "",
  department: "",
  trayName: "",
  instrumentName: "",
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

export default function NewInspectionPage() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [photo, setPhoto] = useState<File | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [captured, setCaptured] = useState<CapturedInspection | null>(null);

  function updateField(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function validate() {
    const missing = [
      ["Facility", form.facility],
      ["Department", form.department],
      ["Tray Name", form.trayName],
      ["Instrument Name", form.instrumentName],
      ["Finding Type", form.findingType],
      ["Risk Level", form.riskLevel],
    ]
      .filter(([, value]) => !String(value).trim())
      .map(([label]) => `${label} is required.`);

    setErrors(missing);
    return missing.length === 0;
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
      instrument_name: form.instrumentName,
      vendor: form.vendor,
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
      setCaptured({ ...form, photoName: photo?.name || "" });
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
            <TextField label="Instrument Name" value={form.instrumentName} onChange={(value) => updateField("instrumentName", value)} required />
            <TextField label="Vendor" value={form.vendor} onChange={(value) => updateField("vendor", value)} />
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
            <div style={step}>2. Identify tray, instrument, and vendor.</div>
            <div style={step}>3. Classify finding and risk.</div>
            <div style={step}>4. Add photo or notes when useful.</div>
          </div>

          {message && captured ? (
            <div style={successBox}>
              <h2 style={successTitle}>Inspection captured</h2>
              <p style={successMessage}>{message}</p>
              <div style={summaryList}>
                <SummaryRow label="Facility" value={captured.facility} />
                <SummaryRow label="Instrument" value={captured.instrumentName} />
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
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}) {
  return (
    <label style={labelStyle}>
      <span>{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} required={required} style={inputStyle} />
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
  required,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  required?: boolean;
}) {
  return (
    <label style={labelStyle}>
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} required={required} style={inputStyle}>
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

const labelStyle: React.CSSProperties = {
  display: "grid",
  gap: "8px",
  color: "#dbeafe",
  fontWeight: 800,
  fontSize: "14px",
  marginBottom: "16px",
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
