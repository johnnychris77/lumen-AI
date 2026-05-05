import React, { useEffect, useState } from "react";
import {
  analyzeVisualInspection,
  fetchVisualInspectionReviews,
  finalizeVisualInspectionReview,
  createInspectionFromVisualReview,
  createCapaFromVisualReview,
} from "../api/visualInspectionApi.js";

const initialForm = {
  facility: "St. Mary’s Hospital",
  department: "SPD",
  instrument_name: "Frazier suction",
  instrument_category: "Cannulated instrument",
  vendor: "Medtronic",
  tray_name: "Neuro basic tray",
  evidence_url: "/evidence/images/frazier-borescope-demo.png",
  suspected_debris_type: "Suspected blood residue",
  quality_issue_type: "Bioburden / retained debris",
  image_quality_score: 86,
  lumen_visibility_score: 72,
  estimated_affected_area_percent: 35,
  organic_material_suspected: true,
  lumen_obstruction: false,
  repeat_finding: false,
  technician_certainty_score: 82,
};

const technicianDecisionOptions = [
  "Pass",
  "Monitor / Document Observation",
  "Reclean Required",
  "Reclean + Second Inspection Required",
  "Quarantine / Remove From Service + Escalate",
];

export default function VisualInspectionIntelligencePanel() {
  const [form, setForm] = useState(initialForm);
  const [review, setReview] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [technicianDecision, setTechnicianDecision] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [creatingInspection, setCreatingInspection] = useState(false);
  const [creatingCapa, setCreatingCapa] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadReviews() {
    const data = await fetchVisualInspectionReviews();
    setReviews(data.items || []);
  }

  useEffect(() => {
    loadReviews().catch((err) => setError(err.message));
  }, []);

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleAnalyze(event) {
    event.preventDefault();

    try {
      setLoading(true);
      setError("");
      setMessage("");

      const data = await analyzeVisualInspection({
        ...form,
        image_quality_score: Number(form.image_quality_score),
        lumen_visibility_score: Number(form.lumen_visibility_score),
        estimated_affected_area_percent: Number(form.estimated_affected_area_percent),
        technician_certainty_score: Number(form.technician_certainty_score),
      });

      setReview(data);
      setTechnicianDecision(data.recommended_disposition || "");
      setOverrideReason("");
      setMessage("Visual inspection intelligence generated.");
      await loadReviews();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleFinalize() {
    if (!review) return;

    try {
      setFinalizing(true);
      setError("");
      setMessage("");

      const result = await finalizeVisualInspectionReview(review.review_id, {
        technician_decision: technicianDecision,
        override_reason: overrideReason,
      });

      setReview(result.review);
      setMessage("Technician decision finalized.");
      await loadReviews();
    } catch (err) {
      setError(err.message);
    } finally {
      setFinalizing(false);
    }
  }

  async function handleCreateInspectionFromReview() {
    if (!review) return;

    try {
      setCreatingInspection(true);
      setError("");
      setMessage("");

      const result = await createInspectionFromVisualReview(review.review_id, {
        inspector: "Dashboard User",
        tenant_id: "bonsecours",
        tenant_name: "Bon Secours",
      });

      setReview(result.visual_review);
      setMessage(`Inspection intake created: ${result.inspection.inspection_id}`);
      await loadReviews();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingInspection(false);
    }
  }

  async function handleCreateCapaFromVisualReview() {
    if (!review) return;

    try {
      setCreatingCapa(true);
      setError("");
      setMessage("");

      const result = await createCapaFromVisualReview(review.review_id, {
        owner: "Infection Prevention / SPD Leadership",
        due_days: 7,
        inspector: "Dashboard User",
        tenant_id: "bonsecours",
        tenant_name: "Bon Secours",
      });

      setReview(result.visual_review);
      setMessage(`CAPA created from visual review: ${result.capa.capa_id}`);
      await loadReviews();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingCapa(false);
    }
  }

  return (
    <section style={sectionWrapper}>
      <div style={{ marginBottom: "18px" }}>
        <h2 style={titleStyle}>Visual Inspection Intelligence Module</h2>
        <p style={subtitleStyle}>
          Standardize lumen inspection decisions by classifying suspected debris, scoring severity, and recommending reclean, second inspection, or escalation.
        </p>
      </div>

      {message && <div style={successStyle}>{message}</div>}
      {error && <div style={errorStyle}>{error}</div>}

      <div style={layoutStyle}>
        <form onSubmit={handleAnalyze} style={cardStyle}>
          <h3 style={cardTitleStyle}>Inspection Intelligence Input</h3>

          <div style={gridStyle}>
            <Input label="Facility" value={form.facility} onChange={(value) => updateField("facility", value)} />
            <Input label="Instrument Name" value={form.instrument_name} onChange={(value) => updateField("instrument_name", value)} />
            <Input label="Instrument Category" value={form.instrument_category} onChange={(value) => updateField("instrument_category", value)} />
            <Input label="Vendor" value={form.vendor} onChange={(value) => updateField("vendor", value)} />
            <Input label="Tray Name" value={form.tray_name} onChange={(value) => updateField("tray_name", value)} />
            <Input label="Evidence URL" value={form.evidence_url} onChange={(value) => updateField("evidence_url", value)} />

            <Select
              label="Suspected Debris Type"
              value={form.suspected_debris_type}
              onChange={(value) => updateField("suspected_debris_type", value)}
              options={[
                "Suspected blood residue",
                "Suspected tissue residue",
                "Suspected bone fragment",
                "Suspected detergent or chemical residue",
                "Water spot or mineral deposit",
                "Fiber or lint contamination",
                "Unknown retained foreign material",
                "No debris observed",
              ]}
            />

            <Select
              label="Quality Issue Type"
              value={form.quality_issue_type}
              onChange={(value) => updateField("quality_issue_type", value)}
              options={[
                "Bioburden / retained debris",
                "Stain / discoloration",
                "Rust / corrosion",
                "Pitting",
                "Crack / structural defect",
                "Surface damage",
                "Moisture / wetness",
                "Lumen obstruction",
                "Documentation concern",
                "No quality issue observed",
              ]}
            />

            <Input type="number" label="Image Quality Score" value={form.image_quality_score} onChange={(value) => updateField("image_quality_score", value)} />
            <Input type="number" label="Lumen Visibility Score" value={form.lumen_visibility_score} onChange={(value) => updateField("lumen_visibility_score", value)} />
            <Input type="number" label="Affected Area %" value={form.estimated_affected_area_percent} onChange={(value) => updateField("estimated_affected_area_percent", value)} />
            <Input type="number" label="Technician Certainty Score" value={form.technician_certainty_score} onChange={(value) => updateField("technician_certainty_score", value)} />
          </div>

          <div style={checkboxGridStyle}>
            <Checkbox label="Organic Material Suspected" checked={form.organic_material_suspected} onChange={(value) => updateField("organic_material_suspected", value)} />
            <Checkbox label="Lumen Obstruction" checked={form.lumen_obstruction} onChange={(value) => updateField("lumen_obstruction", value)} />
            <Checkbox label="Repeat Finding" checked={form.repeat_finding} onChange={(value) => updateField("repeat_finding", value)} />
          </div>

          <button type="submit" disabled={loading} style={primaryButtonStyle}>
            {loading ? "Analyzing..." : "Analyze Visual Inspection"}
          </button>
        </form>

        <RecommendationPanel
          review={review}
          technicianDecision={technicianDecision}
          setTechnicianDecision={setTechnicianDecision}
          overrideReason={overrideReason}
          setOverrideReason={setOverrideReason}
          onFinalize={handleFinalize}
          finalizing={finalizing}
          onCreateInspection={handleCreateInspectionFromReview}
          creatingInspection={creatingInspection}
          onCreateCapa={handleCreateCapaFromVisualReview}
          creatingCapa={creatingCapa}
        />
      </div>

      <ReviewHistory reviews={reviews} />
    </section>
  );
}

function RecommendationPanel({
  review,
  technicianDecision,
  setTechnicianDecision,
  overrideReason,
  setOverrideReason,
  onFinalize,
  finalizing,
  onCreateInspection,
  creatingInspection,
  onCreateCapa,
  creatingCapa,
}) {
  if (!review) {
    return (
      <div style={cardStyle}>
        <h3 style={cardTitleStyle}>Recommendation Panel</h3>
        <p style={subtitleStyle}>
          Run an analysis to generate severity score, confidence score, and recommended disposition.
        </p>
      </div>
    );
  }

  const differsFromRecommendation =
    technicianDecision && technicianDecision !== review.recommended_disposition;

  return (
    <div style={cardStyle}>
      <h3 style={cardTitleStyle}>Recommendation Panel</h3>

      <div style={scoreGridStyle}>
        <ScoreCard label="Severity Score" value={review.severity_score} tone={review.severity_score >= 70 ? "danger" : "warning"} />
        <ScoreCard label="Confidence Score" value={review.confidence_score} tone={review.confidence_score >= 75 ? "success" : "warning"} />
      </div>

      <InfoBlock title="Recommended Disposition">
        <strong>{review.recommended_disposition}</strong>
      </InfoBlock>

      <div style={decisionGridStyle}>
        <DecisionFlag label="Reclean Required" value={review.reclean_required} />
        <DecisionFlag label="Second Inspection Required" value={review.second_inspection_required} />
        <DecisionFlag label="Quarantine Required" value={review.quarantine_required} />
        <DecisionFlag label="IP Review Recommended" value={review.ip_review_recommended} />
        <DecisionFlag label="Vendor Escalation" value={review.vendor_escalation_recommended} />
        <DecisionFlag label="CAPA Recommended" value={review.capa_recommended} />
      </div>

      <InfoBlock title="Finalize Technician Decision">
        <Select
          label="Technician Final Decision"
          value={technicianDecision}
          onChange={setTechnicianDecision}
          options={technicianDecisionOptions}
        />

        {differsFromRecommendation && (
          <TextArea
            label="Override Reason Required"
            value={overrideReason}
            onChange={setOverrideReason}
          />
        )}

        <button onClick={onFinalize} disabled={finalizing} style={primaryButtonStyle}>
          {finalizing ? "Finalizing..." : "Finalize Technician Decision"}
        </button>

        {review.inspection_id ? (
          <div style={successStyle}>
            Inspection intake linked: {review.inspection_id}
          </div>
        ) : (
          <button
            onClick={onCreateInspection}
            disabled={creatingInspection}
            style={{ ...primaryButtonStyle, background: "#0f766e", borderColor: "#0f766e" }}
          >
            {creatingInspection ? "Creating Inspection..." : "Create Inspection Intake From Visual Review"}
          </button>
        )}

        <button
          onClick={onCreateCapa}
          disabled={creatingCapa || review.review_status === "CAPA Created"}
          style={{ ...primaryButtonStyle, background: "#7c3aed", borderColor: "#7c3aed" }}
        >
          {creatingCapa ? "Creating CAPA..." : "Create CAPA From Visual Review"}
        </button>
      </InfoBlock>
    </div>
  );
}

function ReviewHistory({ reviews }) {
  return (
    <div style={{ ...cardStyle, marginTop: "20px" }}>
      <h3 style={cardTitleStyle}>Visual Review History</h3>

      {!reviews.length ? (
        <p style={subtitleStyle}>No visual inspection reviews yet.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Review ID</th>
                <th style={thStyle}>Instrument</th>
                <th style={thStyle}>Debris Type</th>
                <th style={thStyle}>Quality Issue</th>
                <th style={thStyle}>Severity</th>
                <th style={thStyle}>Confidence</th>
                <th style={thStyle}>Disposition</th>
                <th style={thStyle}>Status</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map((item) => (
                <tr key={item.review_id}>
                  <td style={tdMonoStyle}>{shortenId(item.review_id)}</td>
                  <td style={tdStyle}>{item.instrument_name}</td>
                  <td style={tdStyle}>{item.suspected_debris_type}</td>
                  <td style={tdStyle}>{item.quality_issue_type}</td>
                  <td style={tdStyle}>{item.severity_score}</td>
                  <td style={tdStyle}>{item.confidence_score}</td>
                  <td style={tdStyle}>{item.recommended_disposition}</td>
                  <td style={tdStyle}>{item.review_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ScoreCard({ label, value, tone }) {
  const color =
    tone === "danger" ? "#991b1b" : tone === "success" ? "#166534" : "#92400e";
  const background =
    tone === "danger" ? "#fef2f2" : tone === "success" ? "#ecfdf5" : "#fffbeb";

  return (
    <div style={{ ...infoBlockStyle, background, borderColor: color }}>
      <div style={labelStyle}>{label}</div>
      <div style={{ fontSize: "34px", fontWeight: 950, color }}>{value}</div>
    </div>
  );
}

function DecisionFlag({ label, value }) {
  return (
    <div style={infoBlockStyle}>
      <div style={labelStyle}>{label}</div>
      <div style={{ fontWeight: 900, color: value ? "#991b1b" : "#166534" }}>
        {value ? "Yes" : "No"}
      </div>
    </div>
  );
}

function Input({ label, value, onChange, type = "text" }) {
  return (
    <label style={labelWrapperStyle}>
      <span style={labelStyle}>{label}</span>
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} style={inputStyle} />
    </label>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <label style={labelWrapperStyle}>
      <span style={labelStyle}>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} style={inputStyle}>
        {options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    </label>
  );
}

function TextArea({ label, value, onChange }) {
  return (
    <label style={labelWrapperStyle}>
      <span style={labelStyle}>{label}</span>
      <textarea rows={3} value={value} onChange={(event) => onChange(event.target.value)} style={inputStyle} />
    </label>
  );
}

function Checkbox({ label, checked, onChange }) {
  return (
    <label style={{ display: "flex", gap: "8px", alignItems: "center", fontWeight: 800 }}>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}

function InfoBlock({ title, children }) {
  return (
    <div style={infoBlockStyle}>
      <div style={labelStyle}>{title}</div>
      <div style={{ marginTop: "8px" }}>{children}</div>
    </div>
  );
}

function shortenId(id = "") {
  if (id.length <= 18) return id;
  return `${id.slice(0, 12)}...${id.slice(-6)}`;
}

const sectionWrapper = {
  marginTop: "28px",
  border: "1px solid #c7d2fe",
  background: "#eef2ff",
  borderRadius: "22px",
  padding: "22px",
};

const titleStyle = { fontSize: "26px", fontWeight: 950, color: "#111827", margin: 0 };
const subtitleStyle = { color: "#6b7280", marginTop: "6px" };

const layoutStyle = {
  display: "grid",
  gridTemplateColumns: "minmax(0, 1.4fr) minmax(340px, 0.8fr)",
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

const cardTitleStyle = { marginTop: 0, fontSize: "20px", fontWeight: 900, color: "#111827" };

const gridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
  gap: "12px",
};

const checkboxGridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
  gap: "10px",
  marginTop: "12px",
};

const scoreGridStyle = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" };

const decisionGridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
  gap: "10px",
};

const labelWrapperStyle = { display: "block", marginBottom: "12px" };
const labelStyle = { display: "block", fontSize: "13px", color: "#374151", fontWeight: 900 };

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
  border: "1px solid #4f46e5",
  background: "#4f46e5",
  color: "#ffffff",
  borderRadius: "12px",
  padding: "11px 14px",
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
  marginTop: "12px",
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

const infoBlockStyle = {
  border: "1px solid #e5e7eb",
  background: "#f9fafb",
  borderRadius: "14px",
  padding: "12px",
  marginBottom: "12px",
};

const tableStyle = { width: "100%", borderCollapse: "collapse", fontSize: "14px" };

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
