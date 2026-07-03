import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export default function CapaEscalationCards() {
  const [data, setData] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadEscalationSummary() {
    try {
      setErrorMessage("");

      const response = await apiFetch(`/api/capa/escalation-summary?days_until_due=7`
      , { raw: true });

      if (!response.ok) {
        throw new Error(`CAPA escalation summary returned ${response.status}`);
      }

      const json = await response.json();
      setData(json);
    } catch (error) {
      setErrorMessage(
        error.message || "Unable to load CAPA escalation summary."
      );
    }
  }

  useEffect(() => {
    loadEscalationSummary();
  }, []);

  const summary = data?.summary || {
    open_capas: 0,
    overdue: 0,
    due_soon: 0,
    high_risk_overdue: 0,
    requires_escalation: 0,
  };

  return (
    <section
      style={{
        marginTop: "24px",
        border: "1px solid #fed7aa",
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
          background: "#fff7ed",
          color: "#c2410c",
          padding: "6px 12px",
          fontSize: "12px",
          fontWeight: 800,
          border: "1px solid #fed7aa",
          marginBottom: "10px",
        }}
      >
        CAPA Escalation · Due Date Governance
      </div>

      <h2 style={{ margin: 0, fontSize: "24px", color: "#0f172a" }}>
        CAPA Overdue and Escalation Summary
      </h2>

      <p style={{ marginTop: "8px", color: "#475569", lineHeight: 1.6 }}>
        Identifies open CAPAs that are overdue, due soon, high-risk overdue, or
        require escalation for governance follow-up.
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
              label="Open CAPAs"
              value={summary.open_capas}
              tone="neutral"
            />
            <MetricCard
              label="Overdue"
              value={summary.overdue}
              tone={summary.overdue > 0 ? "danger" : "neutral"}
            />
            <MetricCard
              label="Due Soon"
              value={summary.due_soon}
              tone={summary.due_soon > 0 ? "warning" : "neutral"}
            />
            <MetricCard
              label="High-Risk Overdue"
              value={summary.high_risk_overdue}
              tone={summary.high_risk_overdue > 0 ? "danger" : "neutral"}
            />
            <MetricCard
              label="Requires Escalation"
              value={summary.requires_escalation}
              tone={summary.requires_escalation > 0 ? "danger" : "neutral"}
            />
          </div>

          <div
            style={{
              marginTop: "22px",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "14px",
            }}
          >
            <EscalationList
              title="Overdue CAPAs"
              items={data?.overdue || []}
              emptyText="No overdue CAPAs."
            />
            <EscalationList
              title="Due Soon CAPAs"
              items={data?.due_soon || []}
              emptyText="No CAPAs due within 7 days."
            />
            <EscalationList
              title="High-Risk Overdue"
              items={data?.high_risk_overdue || []}
              emptyText="No high-risk overdue CAPAs."
            />
          </div>
        </>
      )}
    </section>
  );
}

function MetricCard({ label, value, tone }) {
  const styles = {
    neutral: {
      border: "#e2e8f0",
      background: "#f8fafc",
      value: "#0f172a",
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
          fontSize: "28px",
          fontWeight: 900,
        }}
      >
        {value ?? 0}
      </div>
    </div>
  );
}

function EscalationList({ title, items, emptyText }) {
  return (
    <div
      style={{
        borderRadius: "18px",
        border: "1px solid #e2e8f0",
        background: "#f8fafc",
        padding: "16px",
      }}
    >
      <h3 style={{ margin: 0, color: "#0f172a", fontSize: "17px" }}>
        {title}
      </h3>

      {items.length === 0 ? (
        <p style={{ marginTop: "10px", color: "#64748b" }}>{emptyText}</p>
      ) : (
        <div style={{ marginTop: "12px", display: "grid", gap: "10px" }}>
          {items.slice(0, 5).map((item) => (
            <div
              key={item.id}
              style={{
                borderRadius: "14px",
                background: "#ffffff",
                border: "1px solid #e2e8f0",
                padding: "12px",
              }}
            >
              <div style={{ fontWeight: 900, color: "#0f172a" }}>
                {item.title}
              </div>
              <div style={{ marginTop: "6px", color: "#475569" }}>
                Owner: {item.owner || "Unassigned"}
              </div>
              <div style={{ marginTop: "4px", color: "#475569" }}>
                Due: {item.due_date || "Not assigned"}
              </div>
              <div
                style={{
                  marginTop: "6px",
                  color: item.days_remaining < 0 ? "#b91c1c" : "#b45309",
                  fontWeight: 800,
                }}
              >
                {item.days_remaining < 0
                  ? `${Math.abs(item.days_remaining)} days overdue`
                  : `${item.days_remaining} days remaining`}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
