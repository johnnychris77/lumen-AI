import React, { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

export default function AuditToCapaIntegrationCard() {
  const [data, setData] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    async function loadSummary() {
      try {
        setErrorMessage("");
        const response = await fetch(
          `${API_BASE}/api/enterprise/audit-to-capa/summary`
        );

        if (!response.ok) {
          throw new Error(`Audit-to-CAPA summary returned ${response.status}`);
        }

        const json = await response.json();
        setData(json);
      } catch (error) {
        setErrorMessage(error.message || "Unable to load integration summary.");
      }
    }

    loadSummary();
  }, []);

  return (
    <section
      style={{
        marginTop: "24px",
        border: "1px solid #bfdbfe",
        borderRadius: "24px",
        background: "#ffffff",
        boxShadow: "0 12px 32px rgba(15, 23, 42, 0.08)",
        padding: "24px",
      }}
    >
      <div
        style={{
          display: "inline-flex",
          borderRadius: "999px",
          background: "#eff6ff",
          color: "#1d4ed8",
          padding: "6px 12px",
          fontSize: "12px",
          fontWeight: 800,
          border: "1px solid #bfdbfe",
          marginBottom: "10px",
        }}
      >
        Audit-to-CAPA Integration · Governance Bridge
      </div>

      <h2 style={{ margin: 0, fontSize: "24px", color: "#0f172a" }}>
        Audit Signal to Corrective Action Pathway
      </h2>

      <p style={{ marginTop: "8px", color: "#475569", lineHeight: 1.6 }}>
        Connects Enterprise Audit Command Center visibility to CAPA workflow
        execution, creating a traceable path from high-value audit signals to
        accountable corrective and preventive action.
      </p>

      {errorMessage && (
        <div
          style={{
            marginTop: "16px",
            borderRadius: "16px",
            border: "1px solid #fecaca",
            background: "#fef2f2",
            color: "#991b1b",
            padding: "14px",
            fontWeight: 700,
          }}
        >
          {errorMessage}
        </div>
      )}

      {data && (
        <>
          <div
            style={{
              marginTop: "20px",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "14px",
            }}
          >
            <MetricCard
              label="Audit Events"
              value={data.audit_command_center?.audit_events}
            />
            <MetricCard
              label="High-Value Events"
              value={data.audit_command_center?.high_value_events}
            />
            <MetricCard
              label="Open CAPAs"
              value={data.capa_workflow?.summary?.open}
            />
            <MetricCard
              label="High-Risk CAPAs"
              value={data.capa_workflow?.summary?.high_risk}
            />
          </div>

          <div
            style={{
              marginTop: "20px",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "14px",
            }}
          >
            {(data.workflow?.flow || []).map((step, index) => (
              <div
                key={step}
                style={{
                  border: "1px solid #e2e8f0",
                  borderRadius: "18px",
                  background: "#f8fafc",
                  padding: "16px",
                }}
              >
                <div
                  style={{
                    color: "#1d4ed8",
                    fontWeight: 900,
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  Step {index + 1}
                </div>
                <div
                  style={{
                    marginTop: "6px",
                    color: "#0f172a",
                    fontWeight: 800,
                  }}
                >
                  {step}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function MetricCard({ label, value }) {
  return (
    <div
      style={{
        borderRadius: "18px",
        border: "1px solid #e2e8f0",
        background: "#f8fafc",
        padding: "16px",
      }}
    >
      <div
        style={{
          color: "#64748b",
          fontSize: "12px",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          fontWeight: 800,
        }}
      >
        {label}
      </div>
      <div
        style={{
          marginTop: "6px",
          color: "#0f172a",
          fontSize: "24px",
          fontWeight: 900,
        }}
      >
        {value ?? "—"}
      </div>
    </div>
  );
}
