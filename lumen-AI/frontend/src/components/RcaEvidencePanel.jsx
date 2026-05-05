import React, { useState } from "react";
import { addCapaUpdate, addCapaEvidence } from "../api/capaApi.js";

function TextAreaField({ label, value, onChange, placeholder }) {
  return (
    <label style={{ display: "block" }}>
      <div style={{ fontSize: "13px", fontWeight: 800, color: "#374151" }}>
        {label}
      </div>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        rows={3}
        style={{
          marginTop: "6px",
          width: "100%",
          border: "1px solid #d1d5db",
          borderRadius: "12px",
          padding: "10px",
          fontSize: "14px",
          fontFamily: "inherit",
          resize: "vertical",
        }}
      />
    </label>
  );
}

function InputField({ label, value, onChange, placeholder }) {
  return (
    <label style={{ display: "block" }}>
      <div style={{ fontSize: "13px", fontWeight: 800, color: "#374151" }}>
        {label}
      </div>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        style={{
          marginTop: "6px",
          width: "100%",
          border: "1px solid #d1d5db",
          borderRadius: "12px",
          padding: "10px",
          fontSize: "14px",
          fontFamily: "inherit",
        }}
      />
    </label>
  );
}

function shortenId(id = "") {
  if (id.length <= 18) return id;
  return `${id.slice(0, 12)}...${id.slice(-6)}`;
}

export default function RcaEvidencePanel({
  selectedCapa,
  onClose,
  onSaved,
  setError,
}) {
  const [rootCause, setRootCause] = useState("");
  const [correctiveAction, setCorrectiveAction] = useState("");
  const [preventiveAction, setPreventiveAction] = useState("");
  const [closureSummary, setClosureSummary] = useState("");
  const [evidenceName, setEvidenceName] = useState("");
  const [evidenceType, setEvidenceType] = useState("image");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [saving, setSaving] = useState(false);

  if (!selectedCapa) return null;

  async function handleSave() {
    try {
      setSaving(true);
      setError("");

      if (rootCause.trim()) {
        await addCapaUpdate(
          selectedCapa.capa_id,
          "root_cause",
          rootCause.trim(),
          "Dashboard User"
        );
      }

      if (correctiveAction.trim()) {
        await addCapaUpdate(
          selectedCapa.capa_id,
          "corrective_action",
          correctiveAction.trim(),
          "Dashboard User"
        );
      }

      if (preventiveAction.trim()) {
        await addCapaUpdate(
          selectedCapa.capa_id,
          "preventive_action",
          preventiveAction.trim(),
          "Dashboard User"
        );
      }

      if (closureSummary.trim()) {
        await addCapaUpdate(
          selectedCapa.capa_id,
          "closure_summary",
          closureSummary.trim(),
          "Dashboard User"
        );
      }

      if (evidenceName.trim() || evidenceUrl.trim()) {
        if (!evidenceName.trim() || !evidenceUrl.trim()) {
          throw new Error(
            "Evidence name and evidence URL are both required when adding evidence."
          );
        }

        await addCapaEvidence(
          selectedCapa.capa_id,
          evidenceName.trim(),
          evidenceType.trim() || "document",
          evidenceUrl.trim(),
          "Dashboard User"
        );
      }

      await onSaved("RCA / evidence saved.");
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        background: "#ffffff",
        border: "1px solid #c4b5fd",
        borderRadius: "18px",
        padding: "20px",
        marginBottom: "24px",
        boxShadow: "0 8px 24px rgba(91, 33, 182, 0.10)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: "12px",
          alignItems: "flex-start",
          marginBottom: "16px",
        }}
      >
        <div>
          <h3 style={{ fontSize: "20px", fontWeight: 900, color: "#111827" }}>
            Add RCA / Evidence
          </h3>
          <p style={{ color: "#6b7280", marginTop: "4px", fontSize: "14px" }}>
            CAPA: {shortenId(selectedCapa.capa_id)} · {selectedCapa.instrument_name} · {selectedCapa.facility}
          </p>
        </div>

        <button
          onClick={onClose}
          style={{
            border: "1px solid #d1d5db",
            background: "#ffffff",
            borderRadius: "999px",
            padding: "8px 12px",
            cursor: "pointer",
            fontWeight: 700,
          }}
        >
          Close Panel
        </button>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "16px",
        }}
      >
        <TextAreaField
          label="Root Cause"
          value={rootCause}
          onChange={setRootCause}
          placeholder="Retained material observed during borescope inspection after routine processing."
        />

        <TextAreaField
          label="Corrective Action"
          value={correctiveAction}
          onChange={setCorrectiveAction}
          placeholder="Instrument removed from service. Related tray held for review. SPD leadership and IP notified."
        />

        <TextAreaField
          label="Preventive Action"
          value={preventiveAction}
          onChange={setPreventiveAction}
          placeholder="Add targeted borescope audit for similar cannulated instruments."
        />

        <TextAreaField
          label="Closure Summary"
          value={closureSummary}
          onChange={setClosureSummary}
          placeholder="Issue reviewed, containment completed, and follow-up audit scheduled."
        />
      </div>

      <div style={{ marginTop: "18px" }}>
        <h4 style={{ fontSize: "16px", fontWeight: 900, color: "#111827" }}>
          Evidence Link
        </h4>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "16px",
            marginTop: "12px",
          }}
        >
          <InputField
            label="Evidence Name"
            value={evidenceName}
            onChange={setEvidenceName}
            placeholder="Borescope retained debris image"
          />

          <InputField
            label="Evidence Type"
            value={evidenceType}
            onChange={setEvidenceType}
            placeholder="image, document, audit, vendor_response"
          />

          <InputField
            label="Evidence URL"
            value={evidenceUrl}
            onChange={setEvidenceUrl}
            placeholder="/evidence/images/demo-frazier-retained-debris.png"
          />
        </div>
      </div>

      <div
        style={{
          display: "flex",
          gap: "10px",
          justifyContent: "flex-end",
          marginTop: "18px",
        }}
      >
        <button
          onClick={onClose}
          disabled={saving}
          style={{
            border: "1px solid #d1d5db",
            background: "#ffffff",
            borderRadius: "12px",
            padding: "10px 14px",
            cursor: saving ? "not-allowed" : "pointer",
            fontWeight: 800,
          }}
        >
          Cancel
        </button>

        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            border: "1px solid #7c3aed",
            background: "#7c3aed",
            color: "#ffffff",
            borderRadius: "12px",
            padding: "10px 14px",
            cursor: saving ? "not-allowed" : "pointer",
            fontWeight: 900,
          }}
        >
          {saving ? "Saving..." : "Save RCA / Evidence"}
        </button>
      </div>
    </div>
  );
}
