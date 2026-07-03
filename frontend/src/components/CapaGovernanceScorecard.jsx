import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export default function CapaGovernanceScorecard() {
  const [data, setData] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadScorecard() {
    try {
      setErrorMessage("");

      const response = await apiFetch(`/api/capa/governance-scorecard?days_until_due=7`
      , { raw: true });

      if (!response.ok) {
        throw new Error(`CAPA governance scorecard returned ${response.status}`);
      }

      const json = await response.json();
      setData(json);
    } catch (error) {
      setErrorMessage(
        error.message || "Unable to load CAPA governance scorecard."
      );
    }
  }

  useEffect(() => {
    loadScorecard();
  }, []);

  const scorecard = data?.scorecard || {
    total_capas: 0,
    open_capas: 0,
    closed_capas: 0,
    high_risk_capas: 0,
    overdue_capas: 0,
    due_soon_capas: 0,
    high_risk_overdue_capas: 0,
    requires_escalation: 0,
    closure_rate_percent: 0,
    powerbi_export_ready: false,
  };

  const governanceStatus = data?.governance_status || "loading";

  return (
    <section
      style={{
        marginTop: "24px",
        border: "1px solid #c7d2fe",
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
          background: "#eef2ff",
          color: "#4338ca",
          padding: "6px 12px",
          fontSize: "12px",
          fontWeight: 800,
          border: "1px solid #c7d2fe",
          marginBottom: "10px",
        }}
      >
        CAPA Governance Scorecard · Executive View
      </div>

      <h2 style={{ margin: 0, fontSize: "24px", color: "#0f172a" }}>
        CAPA Governance Performance
      </h2>

      <p style={{ marginTop: "8px", color: "#475569", lineHeight: 1.6 }}>
        Summarizes CAPA performance, escalation risk, closure rate, and Power BI
        export readiness for quality governance review.
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

      {!errorMessage && (
        <>
          <div
            style={{
              marginTop: "20px",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
              gap: "14px",
            }}
          >
            <MetricCard
              label="Governance Status"
              value={governanceStatus}
              tone={
                governanceStatus === "action_required"
                  ? "danger"
                  : governanceStatus === "watch"
                  ? "warning"
                  : "good"
              }
              isText
            />
            <MetricCard label="Total CAPAs" value={scorecard.total_capas} />
            <MetricCard label="Open CAPAs" value={scorecard.open_capas} />
            <MetricCard label="Closed CAPAs" value={scorecard.closed_capas} />
            <MetricCard
              label="High Risk"
              value={scorecard.high_risk_capas}
              tone={scorecard.high_risk_capas > 0 ? "warning" : "neutral"}
            />
            <MetricCard
              label="Overdue"
              value={scorecard.overdue_capas}
              tone={scorecard.overdue_capas > 0 ? "danger" : "neutral"}
            />
            <MetricCard
              label="Due Soon"
              value={scorecard.due_soon_capas}
              tone={scorecard.due_soon_capas > 0 ? "warning" : "neutral"}
            />
            <MetricCard
              label="Requires Escalation"
              value={scorecard.requires_escalation}
              tone={scorecard.requires_escalation > 0 ? "danger" : "good"}
            />
            <MetricCard
              label="Closure Rate"
              value={`${scorecard.closure_rate_percent ?? 0}%`}
              tone="neutral"
              isText
            />
            <MetricCard
              label="Power BI Export"
              value={scorecard.powerbi_export_ready ? "Ready" : "Pending"}
              tone={scorecard.powerbi_export_ready ? "good" : "warning"}
              isText
            />
          </div>

          <div
            style={{
              marginTop: "22px",
              borderRadius: "18px",
              border: "1px solid #e2e8f0",
              background: "#f8fafc",
              padding: "16px",
            }}
          >
            <h3 style={{ margin: 0, color: "#0f172a", fontSize: "17px" }}>
              Governance Interpretation
            </h3>
            <p style={{ marginTop: "8px", color: "#475569", lineHeight: 1.6 }}>
              {buildInterpretation(data?.governance_status, scorecard)}
            </p>
          </div>
        </>
      )}
    </section>
  );
}

function MetricCard({ label, value, tone = "neutral", isText = false }) {
  const styles = {
    neutral: {
      border: "#e2e8f0",
      background: "#f8fafc",
      value: "#0f172a",
    },
    good: {
      border: "#bbf7d0",
      background: "#f0fdf4",
      value: "#15803d",
    },
    warning: {
      border: "#fde68a",
      background: "#fffbeb",
      value: "#b45309",
    },
    danger: {
      border: "#fecaca",
      background: "#fef2f2",
      value: "#b91c1c",
    },
  };

  const selected = styles[tone] || styles.neutral;

  return (
    <div
      style={{
        borderRadius: "18px",
        border: `1px solid ${selected.border}`,
        background: selected.background,
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
          color: selected.value,
          fontSize: isText ? "20px" : "28px",
          fontWeight: 900,
          textTransform: isText ? "uppercase" : "none",
        }}
      >
        {value ?? 0}
      </div>
    </div>
  );
}

function buildInterpretation(status, scorecard) {
  if (status === "action_required") {
    return `Action required: ${scorecard.requires_escalation || 0} CAPA item(s) require escalation, including ${scorecard.overdue_capas || 0} overdue CAPA(s). Leadership review is recommended.`;
  }

  if (status === "watch") {
    return `Watch status: ${scorecard.due_soon_capas || 0} CAPA item(s) are due soon and should be monitored to prevent overdue escalation.`;
  }

  if (status === "healthy") {
    return "Healthy status: no overdue or due-soon CAPA escalation signals are currently present. Continue routine governance monitoring.";
  }

  return "Loading governance scorecard interpretation.";
}
