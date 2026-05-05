import React, { useEffect, useState } from "react";
import {
  createInspectionIntake,
  fetchInspections,
  createCapaFromInspection,
} from "../api/inspectionApi.js";

const initialForm = {
  facility: "St. Mary’s Hospital",
  department: "SPD",
  instrument_name: "Frazier suction",
  instrument_category: "Cannulated instrument",
  vendor: "Medtronic",
  tray_name: "Neuro basic tray",
  finding_type: "bioburden suspected",
  finding_detail: "Brown retained debris observed inside lumen during borescope inspection",
  evidence_url: "/evidence/images/frazier-suction-demo.png",
  inspector: "Dashboard User",
};

export default function InspectionIntakeModule() {
  const [form, setForm] = useState(initialForm);
  const [latestInspection, setLatestInspection] = useState(null);
  const [inspections, setInspections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creatingCapaId, setCreatingCapaId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadInspections() {
    const data = await fetchInspections();
    setInspections(data.items || []);
  }

  useEffect(() => {
    loadInspections().catch((err) => setError(err.message));
  }, []);

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      setLoading(true);
      setError("");
      setMessage("");

      const inspection = await createInspectionIntake(form);
      setLatestInspection(inspection);
      setMessage("Inspection intake created and classified.");
      await loadInspections();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateCapa(inspectionId) {
    try {
      setCreatingCapaId(inspectionId);
      setError("");
      setMessage("");

      const result = await createCapaFromInspection(inspectionId, {
        owner: "Infection Prevention / SPD Leadership",
        due_days: 7,
      });

      setLatestInspection(result.inspection);
      setMessage(`CAPA created: ${result.capa.capa_id}`);
      await loadInspections();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingCapaId("");
    }
  }

  return (
    <section style={sectionWrapper}>
      <div style={{ marginBottom: "18px" }}>
        <h2 style={titleStyle}>Inspection Intake Module</h2>
        <p style={subtitleStyle}>
          Capture inspection findings, classify risk, recommend routing, and trigger CAPA creation.
        </p>
      </div>

      {message && <div style={successStyle}>{message}</div>}
      {error && <div style={errorStyle}>{error}</div>}

      <div style={layoutStyle}>
        <form onSubmit={handleSubmit} style={cardStyle}>
          <h3 style={cardTitleStyle}>New Inspection Intake</h3>

          <div style={gridStyle}>
            <Input label="Facility" value={form.facility} onChange={(value) => updateField("facility", value)} />
            <Input label="Department" value={form.department} onChange={(value) => updateField("department", value)} />
            <Input label="Instrument Name" value={form.instrument_name} onChange={(value) => updateField("instrument_name", value)} />
            <Input label="Instrument Category" value={form.instrument_category} onChange={(value) => updateField("instrument_category", value)} />
            <Input label="Vendor" value={form.vendor} onChange={(value) => updateField("vendor", value)} />
            <Input label="Tray Name" value={form.tray_name} onChange={(value) => updateField("tray_name", value)} />
            <Input label="Finding Type" value={form.finding_type} onChange={(value) => updateField("finding_type", value)} />
            <Input label="Inspector" value={form.inspector} onChange={(value) => updateField("inspector", value)} />
          </div>

          <TextArea
            label="Finding Detail"
            value={form.finding_detail}
            onChange={(value) => updateField("finding_detail", value)}
          />

          <Input
            label="Evidence URL"
            value={form.evidence_url}
            onChange={(value) => updateField("evidence_url", value)}
          />

          <button type="submit" disabled={loading} style={primaryButtonStyle}>
            {loading ? "Classifying..." : "Submit Inspection Intake"}
          </button>
        </form>

        <RiskRecommendationPanel
          inspection={latestInspection}
          onCreateCapa={handleCreateCapa}
          creatingCapaId={creatingCapaId}
        />
      </div>

      <InspectionHistoryTable
        inspections={inspections}
        onCreateCapa={handleCreateCapa}
        creatingCapaId={creatingCapaId}
      />
    </section>
  );
}

function RiskRecommendationPanel({ inspection, onCreateCapa, creatingCapaId }) {
  if (!inspection) {
    return (
      <div style={cardStyle}>
        <h3 style={cardTitleStyle}>Risk Recommendation Panel</h3>
        <p style={subtitleStyle}>
          Submit an inspection finding to see LumenAI classification, risk level, routing, and CAPA recommendation.
        </p>
      </div>
    );
  }

  return (
    <div style={cardStyle}>
      <h3 style={cardTitleStyle}>Risk Recommendation Panel</h3>

      <div style={recommendationHeaderStyle}>
        <Badge label={inspection.risk_level} tone={inspection.risk_level === "High" ? "danger" : "warning"} />
        <Badge label={inspection.classification} tone="info" />
      </div>

      <InfoBlock title="Recommended Routing">
        {inspection.recommended_routing}
      </InfoBlock>

      <InfoBlock title="Recommended Containment">
        {inspection.recommended_containment}
      </InfoBlock>

      <InfoBlock title="Decision Support">
        <div style={{ display: "grid", gap: "8px" }}>
          <div><strong>CAPA Required:</strong> {inspection.capa_required ? "Yes" : "No"}</div>
          <div><strong>IP Review:</strong> {inspection.ip_review_recommended ? "Yes" : "No"}</div>
          <div><strong>Vendor Escalation:</strong> {inspection.vendor_escalation_recommended ? "Yes" : "No"}</div>
        </div>
      </InfoBlock>

      {inspection.capa_id ? (
        <div style={successStyle}>CAPA created: {inspection.capa_id}</div>
      ) : (
        <button
          onClick={() => onCreateCapa(inspection.inspection_id)}
          disabled={creatingCapaId === inspection.inspection_id}
          style={primaryButtonStyle}
        >
          {creatingCapaId === inspection.inspection_id ? "Creating CAPA..." : "Create CAPA From Inspection"}
        </button>
      )}
    </div>
  );
}

function InspectionHistoryTable({ inspections, onCreateCapa, creatingCapaId }) {
  return (
    <div style={{ ...cardStyle, marginTop: "20px" }}>
      <h3 style={cardTitleStyle}>Inspection History</h3>

      {!inspections.length ? (
        <p style={subtitleStyle}>No inspection records yet.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Inspection ID</th>
                <th style={thStyle}>Facility</th>
                <th style={thStyle}>Instrument</th>
                <th style={thStyle}>Finding</th>
                <th style={thStyle}>Risk</th>
                <th style={thStyle}>Recommendation</th>
                <th style={thStyle}>CAPA</th>
                <th style={thStyle}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {inspections.map((item) => (
                <tr key={item.inspection_id}>
                  <td style={tdMonoStyle}>{shortenId(item.inspection_id)}</td>
                  <td style={tdStyle}>{item.facility}</td>
                  <td style={tdStyle}>{item.instrument_name}</td>
                  <td style={tdStyle}>{item.finding_type}</td>
                  <td style={tdStyle}>
                    <Badge label={item.risk_level} tone={item.risk_level === "High" ? "danger" : "neutral"} />
                  </td>
                  <td style={tdStyle}>{item.recommended_routing}</td>
                  <td style={tdMonoStyle}>{item.capa_id ? shortenId(item.capa_id) : "None"}</td>
                  <td style={tdStyle}>
                    {!item.capa_id && item.capa_required ? (
                      <button
                        onClick={() => onCreateCapa(item.inspection_id)}
                        disabled={creatingCapaId === item.inspection_id}
                        style={smallButtonStyle}
                      >
                        {creatingCapaId === item.inspection_id ? "Creating..." : "Create CAPA"}
                      </button>
                    ) : (
                      <span style={{ color: "#6b7280" }}>
                        {item.capa_id ? "CAPA linked" : "No CAPA required"}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Input({ label, value, onChange }) {
  return (
    <label style={labelWrapperStyle}>
      <span style={labelStyle}>{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        style={inputStyle}
      />
    </label>
  );
}

function TextArea({ label, value, onChange }) {
  return (
    <label style={labelWrapperStyle}>
      <span style={labelStyle}>{label}</span>
      <textarea
        rows={4}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        style={inputStyle}
      />
    </label>
  );
}

function InfoBlock({ title, children }) {
  return (
    <div style={infoBlockStyle}>
      <div style={labelStyle}>{title}</div>
      <div style={{ marginTop: "6px", color: "#374151" }}>{children}</div>
    </div>
  );
}

function Badge({ label, tone = "neutral" }) {
  const tones = {
    neutral: { background: "#f3f4f6", color: "#374151" },
    danger: { background: "#fee2e2", color: "#991b1b" },
    warning: { background: "#fef3c7", color: "#92400e" },
    info: { background: "#dbeafe", color: "#1e40af" },
  };

  const style = tones[tone] || tones.neutral;

  return (
    <span
      style={{
        background: style.background,
        color: style.color,
        borderRadius: "999px",
        padding: "5px 10px",
        fontSize: "12px",
        fontWeight: 900,
        display: "inline-block",
      }}
    >
      {label}
    </span>
  );
}

function shortenId(id = "") {
  if (id.length <= 18) return id;
  return `${id.slice(0, 12)}...${id.slice(-6)}`;
}

const sectionWrapper = {
  marginTop: "28px",
  border: "1px solid #dbeafe",
  background: "#eff6ff",
  borderRadius: "22px",
  padding: "22px",
};

const titleStyle = {
  fontSize: "26px",
  fontWeight: 950,
  color: "#111827",
  margin: 0,
};

const subtitleStyle = {
  color: "#6b7280",
  marginTop: "6px",
};

const layoutStyle = {
  display: "grid",
  gridTemplateColumns: "minmax(0, 1.4fr) minmax(320px, 0.8fr)",
  gap: "18px",
  alignItems: "start",
};

const cardStyle = {
  border: "1px solid #e5e7eb",
  background: "#ffffff",
  borderRadius: "18px",
  padding: "18px",
  boxShadow: "0 8px 24px rgba(15, 23, 42, 0.06)",
};

const cardTitleStyle = {
  marginTop: 0,
  fontSize: "20px",
  fontWeight: 900,
  color: "#111827",
};

const gridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
  gap: "12px",
};

const labelWrapperStyle = {
  display: "block",
  marginBottom: "12px",
};

const labelStyle = {
  display: "block",
  fontSize: "13px",
  color: "#374151",
  fontWeight: 900,
};

const inputStyle = {
  marginTop: "6px",
  width: "100%",
  border: "1px solid #d1d5db",
  borderRadius: "12px",
  padding: "10px",
  fontSize: "14px",
  fontFamily: "inherit",
  boxSizing: "border-box",
};

const primaryButtonStyle = {
  marginTop: "14px",
  border: "1px solid #2563eb",
  background: "#2563eb",
  color: "#ffffff",
  borderRadius: "12px",
  padding: "11px 14px",
  fontWeight: 900,
  cursor: "pointer",
};

const smallButtonStyle = {
  border: "1px solid #2563eb",
  background: "#eff6ff",
  color: "#1e40af",
  borderRadius: "999px",
  padding: "7px 10px",
  fontWeight: 900,
  cursor: "pointer",
};

const successStyle = {
  border: "1px solid #86efac",
  background: "#ecfdf5",
  color: "#166534",
  borderRadius: "12px",
  padding: "12px",
  fontWeight: 800,
  marginBottom: "14px",
};

const errorStyle = {
  border: "1px solid #fecaca",
  background: "#fef2f2",
  color: "#991b1b",
  borderRadius: "12px",
  padding: "12px",
  fontWeight: 800,
  marginBottom: "14px",
};

const recommendationHeaderStyle = {
  display: "flex",
  gap: "8px",
  flexWrap: "wrap",
  marginBottom: "14px",
};

const infoBlockStyle = {
  border: "1px solid #e5e7eb",
  background: "#f9fafb",
  borderRadius: "14px",
  padding: "12px",
  marginBottom: "12px",
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "14px",
};

const thStyle = {
  textAlign: "left",
  padding: "10px",
  borderBottom: "1px solid #e5e7eb",
  color: "#6b7280",
  fontSize: "12px",
  textTransform: "uppercase",
};

const tdStyle = {
  padding: "12px 10px",
  borderBottom: "1px solid #f3f4f6",
  verticalAlign: "top",
};

const tdMonoStyle = {
  ...tdStyle,
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  fontSize: "12px",
};
