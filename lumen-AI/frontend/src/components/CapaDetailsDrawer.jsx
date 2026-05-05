import React, { useEffect, useState } from "react";
import { fetchCapaById } from "../api/capaApi.js";

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: "18px" }}>
      <h4 style={{ fontSize: "14px", fontWeight: 900, color: "#111827" }}>
        {title}
      </h4>
      <div style={{ marginTop: "6px", color: "#374151", fontSize: "14px" }}>
        {children || <span style={{ color: "#9ca3af" }}>Not documented</span>}
      </div>
    </div>
  );
}

export default function CapaDetailsDrawer({ capaId, onClose, setError }) {
  const [capa, setCapa] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!capaId) return;

    async function load() {
      try {
        setLoading(true);
        setError("");
        const data = await fetchCapaById(capaId);
        setCapa(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [capaId, setError]);

  if (!capaId) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        width: "520px",
        maxWidth: "95vw",
        height: "100vh",
        background: "#ffffff",
        borderLeft: "1px solid #e5e7eb",
        boxShadow: "-12px 0 32px rgba(15, 23, 42, 0.15)",
        zIndex: 50,
        overflowY: "auto",
        padding: "24px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: "12px",
          alignItems: "flex-start",
          marginBottom: "18px",
        }}
      >
        <div>
          <h3 style={{ fontSize: "22px", fontWeight: 900, color: "#111827" }}>
            CAPA Details
          </h3>
          <p style={{ color: "#6b7280", fontSize: "13px", marginTop: "4px" }}>
            {capaId}
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
            fontWeight: 800,
          }}
        >
          Close
        </button>
      </div>

      {loading && <p>Loading CAPA details...</p>}

      {capa && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
              marginBottom: "20px",
            }}
          >
            <div style={cardStyle}>
              <div style={labelStyle}>Status</div>
              <div style={valueStyle}>{capa.status}</div>
            </div>

            <div style={cardStyle}>
              <div style={labelStyle}>Risk</div>
              <div style={valueStyle}>{capa.risk_level}</div>
            </div>

            <div style={cardStyle}>
              <div style={labelStyle}>Facility</div>
              <div style={valueStyle}>{capa.facility}</div>
            </div>

            <div style={cardStyle}>
              <div style={labelStyle}>Vendor</div>
              <div style={valueStyle}>{capa.vendor}</div>
            </div>
          </div>

          <Section title="Problem Statement">{capa.problem_statement}</Section>
          <Section title="Containment Action">{capa.containment_action}</Section>
          <Section title="Root Cause">{capa.root_cause}</Section>
          <Section title="Corrective Action">{capa.corrective_action}</Section>
          <Section title="Preventive Action">{capa.preventive_action}</Section>
          <Section title="Closure Summary">{capa.closure_summary}</Section>

          <Section title="Evidence Links">
            {capa.evidence_links?.length ? (
              <ul style={{ paddingLeft: "18px", margin: 0 }}>
                {capa.evidence_links.map((item) => (
                  <li key={item.evidence_id || item.url} style={{ marginBottom: "8px" }}>
                    <strong>{item.name}</strong>
                    <div style={{ fontSize: "13px", color: "#6b7280" }}>
                      {item.type} · {item.url}
                    </div>
                  </li>
                ))}
              </ul>
            ) : null}
          </Section>

          <Section title="Audit Trail">
            {capa.audit_trail?.length ? (
              <div style={{ display: "grid", gap: "10px" }}>
                {capa.audit_trail.map((item, index) => (
                  <div
                    key={`${item.timestamp}-${index}`}
                    style={{
                      border: "1px solid #e5e7eb",
                      borderRadius: "12px",
                      padding: "10px",
                      background: "#f9fafb",
                    }}
                  >
                    <div style={{ fontWeight: 900, color: "#111827" }}>
                      {item.action}
                    </div>
                    <div style={{ fontSize: "12px", color: "#6b7280", marginTop: "2px" }}>
                      {item.timestamp}
                    </div>
                    <div style={{ fontSize: "13px", color: "#374151", marginTop: "6px" }}>
                      {item.details || item.note}
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </Section>
        </>
      )}
    </div>
  );
}

const cardStyle = {
  border: "1px solid #e5e7eb",
  background: "#f9fafb",
  borderRadius: "14px",
  padding: "12px",
};

const labelStyle = {
  color: "#6b7280",
  fontSize: "12px",
  fontWeight: 800,
};

const valueStyle = {
  color: "#111827",
  fontSize: "14px",
  fontWeight: 900,
  marginTop: "4px",
};
