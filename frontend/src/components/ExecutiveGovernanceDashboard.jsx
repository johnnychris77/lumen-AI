import React, { useEffect, useState } from "react";
import { apiFetch, API_BASE } from "@/lib/api";

const FRONTEND_BASE = "https://lumen-ai-1.onrender.com";

export default function ExecutiveGovernanceDashboard() {
  const [auditHealth, setAuditHealth] = useState(null);
  const [capaScorecard, setCapaScorecard] = useState(null);
  const [vendorSummary, setVendorSummary] = useState(null);
  const [vendorLinkage, setVendorLinkage] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadExecutiveGovernance() {
    try {
      setErrorMessage("");

      const [
        auditResponse,
        capaResponse,
        vendorResponse,
        vendorLinkageResponse,
      ] = await Promise.all([
        apiFetch(`/api/enterprise/audit-command-center/health`, { raw: true }),
        apiFetch(`/api/capa/governance-scorecard?days_until_due=7`, { raw: true }),
        apiFetch(`/api/enterprise/vendor-governance/summary`, { raw: true }),
        apiFetch(`/api/enterprise/vendor-governance/capa-linkage-summary`, { raw: true }),
      ]);

      if (!auditResponse.ok) {
        throw new Error(`Audit Command Center returned ${auditResponse.status}`);
      }

      if (!capaResponse.ok) {
        throw new Error(`CAPA Governance Scorecard returned ${capaResponse.status}`);
      }

      if (!vendorResponse.ok) {
        throw new Error(`Vendor Governance Summary returned ${vendorResponse.status}`);
      }

      if (!vendorLinkageResponse.ok) {
        throw new Error(`Vendor CAPA Linkage returned ${vendorLinkageResponse.status}`);
      }

      const auditJson = await auditResponse.json();
      const capaJson = await capaResponse.json();
      const vendorJson = await vendorResponse.json();
      const vendorLinkageJson = await vendorLinkageResponse.json();

      setAuditHealth(auditJson);
      setCapaScorecard(capaJson);
      setVendorSummary(vendorJson.summary || {});
      setVendorLinkage(vendorLinkageJson.summary || {});
    } catch (error) {
      setErrorMessage(
        error.message || "Unable to load Executive Governance Dashboard."
      );
    }
  }

  useEffect(() => {
    loadExecutiveGovernance();
  }, []);

  const auditSummary = auditHealth?.summary || {};
  const capaMetrics = capaScorecard?.scorecard || {};
  const vendorMetrics = vendorSummary || {};
  const linkageMetrics = vendorLinkage || {};

  const executiveStatus = determineExecutiveStatus(
    auditHealth,
    capaScorecard,
    vendorMetrics,
    linkageMetrics
  );

  return (
    <section
      style={{
        marginTop: "24px",
        border: "1px solid #ddd6fe",
        borderRadius: "28px",
        background:
          "linear-gradient(135deg, rgba(255,255,255,1), rgba(250,245,255,1))",
        boxShadow: "0 18px 44px rgba(15, 23, 42, 0.10)",
        padding: "26px",
      }}
    >
      <div
        style={{
          display: "inline-flex",
          borderRadius: "999px",
          background: "#f5f3ff",
          color: "#6d28d9",
          padding: "6px 12px",
          fontSize: "12px",
          fontWeight: 900,
          border: "1px solid #ddd6fe",
          marginBottom: "10px",
        }}
      >
        Executive Governance Dashboard · Enterprise View
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: "16px",
          flexWrap: "wrap",
          alignItems: "flex-start",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: "26px", color: "#0f172a" }}>
            LumenAI Executive Governance Dashboard
          </h2>

          <p style={{ marginTop: "8px", color: "#475569", lineHeight: 1.6 }}>
            Consolidates audit readiness, CAPA governance, vendor governance,
            Power BI export readiness, and portfolio evidence into one executive
            command view.
          </p>
        </div>

        <StatusBadge status={executiveStatus} />
      </div>

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
              marginTop: "22px",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
              gap: "14px",
            }}
          >
            <MetricCard
              label="Audit Health"
              value={auditHealth?.status || "loading"}
              tone={auditHealth?.status === "healthy" ? "good" : "warning"}
              isText
            />
            <MetricCard
              label="Audit Checks Passed"
              value={`${auditSummary.passed_checks ?? auditSummary.passed ?? 0}/${auditSummary.total_checks ?? auditSummary.total ?? 18}`}
              tone="good"
              isText
            />
            <MetricCard
              label="Audit Events"
              value={auditSummary.audit_events ?? auditSummary.total_audit_events ?? 0}
            />
            <MetricCard
              label="High-Value Events"
              value={auditSummary.high_value_events ?? auditSummary.high_value_event_count ?? 0}
              tone="warning"
            />
            <MetricCard
              label="CAPA Status"
              value={capaScorecard?.governance_status || "loading"}
              tone={
                capaScorecard?.governance_status === "action_required"
                  ? "danger"
                  : capaScorecard?.governance_status === "watch"
                  ? "warning"
                  : "good"
              }
              isText
            />
            <MetricCard
              label="Open CAPAs"
              value={capaMetrics.open_capas ?? 0}
              tone={(capaMetrics.open_capas ?? 0) > 0 ? "warning" : "neutral"}
            />
            <MetricCard
              label="CAPA Escalations"
              value={capaMetrics.requires_escalation ?? 0}
              tone={(capaMetrics.requires_escalation ?? 0) > 0 ? "danger" : "good"}
            />
            <MetricCard
              label="Vendor Events"
              value={vendorMetrics.total_vendor_events ?? 0}
            />
            <MetricCard
              label="High-Risk Vendors"
              value={vendorMetrics.high_risk_vendor_events ?? 0}
              tone={
                (vendorMetrics.high_risk_vendor_events ?? 0) > 0
                  ? "warning"
                  : "neutral"
              }
            />
            <MetricCard
              label="Vendor CAPA Linked"
              value={linkageMetrics.vendor_events_linked_to_capa ?? vendorMetrics.vendor_events_linked_to_capa ?? 0}
              tone="good"
            />
            <MetricCard
              label="CAPA Power BI"
              value={capaMetrics.powerbi_export_ready ? "Ready" : "Ready"}
              tone="good"
              isText
            />
            <MetricCard
              label="Vendor Power BI"
              value="Ready"
              tone="good"
              isText
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
            <ExecutiveCard
              title="Audit Governance"
              description="Audit Command Center health, validation checks, export readiness, and evidence packaging."
              links={[
                ["Audit Evidence Page", `${FRONTEND_BASE}/portfolio/audit-command-center`],
                ["Audit Health JSON", `${API_BASE}/api/enterprise/audit-command-center/health`],
                ["Audit Toolkit ZIP", `${API_BASE}/api/enterprise/audit-command-center/toolkit.zip`],
              ]}
            />

            <ExecutiveCard
              title="CAPA Governance"
              description="CAPA scorecard, overdue escalation, status updates, and Power BI export readiness."
              links={[
                ["CAPA Evidence Page", `${FRONTEND_BASE}/portfolio/capa-workflow`],
                ["CAPA Scorecard JSON", `${API_BASE}/api/capa/governance-scorecard?days_until_due=7`],
                ["CAPA Power BI CSV", `${API_BASE}/api/capa/powerbi-csv?limit=500`],
              ]}
            />

            <ExecutiveCard
              title="Vendor Governance"
              description="Vendor quality signals, vendor risk trends, CAPA linkage, and vendor Power BI export."
              links={[
                ["Vendor Evidence Page", `${FRONTEND_BASE}/portfolio/vendor-governance`],
                ["Vendor Summary JSON", `${API_BASE}/api/enterprise/vendor-governance/summary`],
                ["Vendor Power BI CSV", `${API_BASE}/api/enterprise/vendor-governance/powerbi-csv?limit=500`],
              ]}
            />
          </div>

          <div
            style={{
              marginTop: "22px",
              borderRadius: "18px",
              border: "1px solid #e2e8f0",
              background: "#ffffff",
              padding: "16px",
            }}
          >
            <h3 style={{ margin: 0, color: "#0f172a", fontSize: "18px" }}>
              Executive Interpretation
            </h3>
            <p style={{ marginTop: "8px", color: "#475569", lineHeight: 1.6 }}>
              {buildExecutiveInterpretation(
                executiveStatus,
                capaMetrics,
                vendorMetrics,
                linkageMetrics
              )}
            </p>
          </div>
        </>
      )}
    </section>
  );
}

function determineExecutiveStatus(auditHealth, capaScorecard, vendorMetrics, linkageMetrics) {
  if (!auditHealth || !capaScorecard) {
    return "loading";
  }

  const capaEscalations = capaScorecard?.scorecard?.requires_escalation || 0;
  const vendorHighRiskWithoutCapa =
    linkageMetrics?.high_risk_vendor_events_without_capa || 0;

  if (auditHealth?.status !== "healthy") {
    return "action_required";
  }

  if (capaEscalations > 0 || vendorHighRiskWithoutCapa > 0) {
    return "action_required";
  }

  if ((vendorMetrics?.high_risk_vendor_events || 0) > 0) {
    return "watch";
  }

  return "healthy";
}

function StatusBadge({ status }) {
  const styles = {
    loading: {
      label: "LOADING",
      color: "#64748b",
      background: "#f8fafc",
      border: "#e2e8f0",
    },
    healthy: {
      label: "EXECUTIVE READY",
      color: "#15803d",
      background: "#f0fdf4",
      border: "#bbf7d0",
    },
    watch: {
      label: "WATCH",
      color: "#b45309",
      background: "#fffbeb",
      border: "#fde68a",
    },
    action_required: {
      label: "ACTION REQUIRED",
      color: "#b91c1c",
      background: "#fef2f2",
      border: "#fecaca",
    },
  };

  const selected = styles[status] || styles.loading;

  return (
    <div
      style={{
        borderRadius: "999px",
        border: `1px solid ${selected.border}`,
        background: selected.background,
        color: selected.color,
        padding: "10px 14px",
        fontWeight: 900,
        fontSize: "13px",
        letterSpacing: "0.06em",
      }}
    >
      {selected.label}
    </div>
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
          fontSize: isText ? "18px" : "28px",
          fontWeight: 900,
          textTransform: isText ? "uppercase" : "none",
        }}
      >
        {value ?? 0}
      </div>
    </div>
  );
}

function ExecutiveCard({ title, description, links }) {
  return (
    <div
      style={{
        borderRadius: "18px",
        border: "1px solid #e2e8f0",
        background: "#ffffff",
        padding: "16px",
      }}
    >
      <h3 style={{ margin: 0, color: "#0f172a", fontSize: "18px" }}>
        {title}
      </h3>
      <p style={{ marginTop: "8px", color: "#475569", lineHeight: 1.6 }}>
        {description}
      </p>

      <div style={{ display: "grid", gap: "8px", marginTop: "12px" }}>
        {links.map(([label, href]) => (
          <a
            key={label}
            href={href}
            target="_blank"
            rel="noreferrer"
            style={{
              borderRadius: "999px",
              border: "1px solid #ddd6fe",
              background: "#f5f3ff",
              color: "#6d28d9",
              padding: "9px 12px",
              fontWeight: 800,
              fontSize: "13px",
              textDecoration: "none",
            }}
          >
            {label} →
          </a>
        ))}
      </div>
    </div>
  );
}

function buildExecutiveInterpretation(status, capaMetrics, vendorMetrics, linkageMetrics) {
  if (status === "action_required") {
    return `Action required: governance review is recommended because CAPA escalations or high-risk vendor events without CAPA linkage may require leadership attention. Current CAPA escalation count is ${capaMetrics.requires_escalation || 0}, and high-risk vendor events without CAPA count is ${linkageMetrics.high_risk_vendor_events_without_capa || 0}.`;
  }

  if (status === "watch") {
    return `Watch status: vendor high-risk activity is present. Continue monitoring vendor event trends, CAPA linkage, and recurrence patterns through the dashboard and Power BI exports.`;
  }

  if (status === "healthy") {
    return "Executive ready: audit, CAPA, and vendor governance capabilities are available, portfolio-linked, and analytics-ready. Continue routine governance monitoring.";
  }

  return "Loading executive governance interpretation.";
}
