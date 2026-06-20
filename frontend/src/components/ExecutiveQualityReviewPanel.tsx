import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || "http://127.0.0.1:18012";
const AUTH_TOKEN = localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || "";
const EXECUTIVE_PDF_URL = `${API_BASE}/api/enterprise/executive-quality-review-dashboard.pdf`;

type TopVendorSignal = {
  vendor_name: string;
  finding_count: number;
};

type RecentFinding = {
  finding_id: number;
  vendor_id?: number | null;
  vendor_name?: string;
  instrument_id?: number | null;
  instrument_name?: string;
  finding_category?: string;
  severity?: string;
  confidence_score?: number | null;
  workflow_status?: string;
  created_at?: string;
};

type ExecutiveQualityDashboard = {
  status: string;
  dashboard_type: string;
  total_findings: number;
  critical_findings: number;
  high_findings: number;
  baseline_evidence_count: number;
  approved_baseline_count: number;
  vendor_escalation_ready_count: number;
  ip_review_recommended_count: number;
  open_capa_count: number;
  closed_capa_count: number;
  audit_event_count: number;
  governance_export_count: number;
  quality_signal: string;
  executive_summary: string;
  recommended_leadership_actions: string[];
  top_vendor_signals: TopVendorSignal[];
  recent_findings: RecentFinding[];
};

async function fetchExecutiveDashboard(): Promise<ExecutiveQualityDashboard> {
  const response = await fetch(`${API_BASE}/api/enterprise/executive-quality-review-dashboard`, {
    headers: {
      Authorization: `Bearer ${AUTH_TOKEN}`,
      "X-LumenAI-Role": "viewer",
      "X-LumenAI-Actor": "john-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Executive dashboard failed (${response.status})`);
  }

  return data;
}

export default function ExecutiveQualityReviewPanel() {
  const [dashboard, setDashboard] = useState<ExecutiveQualityDashboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const data = await fetchExecutiveDashboard();
      setDashboard(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown dashboard error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  return (
    <section style={panelStyle}>
      <div style={headerRowStyle}>
        <div>
          <div style={eyebrowStyle}>Executive Quality Review</div>
          <h2 style={titleStyle}>Enterprise Quality Signal Dashboard</h2>
          <p style={subtitleStyle}>
            Leadership-ready view of LumenAI findings, baseline evidence, vendor signals, IP review readiness, CAPA activity, and audit/export activity.
          </p>
        </div>

        <div style={buttonRowStyle}>
          <button type="button" onClick={loadDashboard} disabled={loading} style={refreshButtonStyle}>
            {loading ? "Refreshing..." : "Refresh Dashboard"}
          </button>
          <a href={EXECUTIVE_PDF_URL} target="_blank" rel="noreferrer" style={pdfButtonStyle}>
            Download Executive PDF
          </a>
        </div>
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      {!dashboard && !error ? (
        <div style={emptyStateStyle}>Loading executive dashboard...</div>
      ) : null}

      {dashboard ? (
        <>
          <div style={signalCardStyle(dashboard.quality_signal)}>
            <div>
              <div style={eyebrowStyle}>Current Quality Signal</div>
              <h3 style={signalTitleStyle}>{formatLabel(dashboard.quality_signal)}</h3>
              <p style={signalSummaryStyle}>{dashboard.executive_summary}</p>
            </div>
          </div>

          <div style={metricGridStyle}>
            <MetricCard label="Total Findings" value={dashboard.total_findings} />
            <MetricCard label="Critical Findings" value={dashboard.critical_findings} intent="critical" />
            <MetricCard label="High Findings" value={dashboard.high_findings} intent="warning" />
            <MetricCard label="Baseline Evidence" value={dashboard.baseline_evidence_count} />
            <MetricCard label="Approved Baselines" value={dashboard.approved_baseline_count} intent="success" />
            <MetricCard label="Vendor Ready" value={dashboard.vendor_escalation_ready_count} intent="warning" />
            <MetricCard label="IP Review Recommended" value={dashboard.ip_review_recommended_count} intent="critical" />
            <MetricCard label="Open CAPAs" value={dashboard.open_capa_count} intent={dashboard.open_capa_count ? "warning" : "success"} />
            <MetricCard label="Closed CAPAs" value={dashboard.closed_capa_count} intent="success" />
            <MetricCard label="Audit Events" value={dashboard.audit_event_count} />
            <MetricCard label="Governance Exports" value={dashboard.governance_export_count} />
          </div>

          <div style={contentGridStyle}>
            <div style={cardStyle}>
              <h3 style={sectionTitleStyle}>Recommended Leadership Actions</h3>
              <ul style={listStyle}>
                {dashboard.recommended_leadership_actions.map((action) => (
                  <li key={action} style={listItemStyle}>{action}</li>
                ))}
              </ul>
            </div>

            <div style={cardStyle}>
              <h3 style={sectionTitleStyle}>Top Vendor Signals</h3>
              {dashboard.top_vendor_signals.length ? (
                <div style={vendorListStyle}>
                  {dashboard.top_vendor_signals.map((vendor) => (
                    <div key={vendor.vendor_name} style={vendorRowStyle}>
                      <span style={vendorNameStyle}>{vendor.vendor_name || "Unknown vendor"}</span>
                      <span style={vendorCountStyle}>{vendor.finding_count} finding{vendor.finding_count === 1 ? "" : "s"}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={mutedTextStyle}>No vendor signals available.</p>
              )}
            </div>
          </div>

          <div style={cardStyle}>
            <h3 style={sectionTitleStyle}>Recent Findings</h3>
            <div style={tableWrapStyle}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Finding</th>
                    <th style={thStyle}>Vendor</th>
                    <th style={thStyle}>Instrument</th>
                    <th style={thStyle}>Category</th>
                    <th style={thStyle}>Severity</th>
                    <th style={thStyle}>Confidence</th>
                    <th style={thStyle}>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.recent_findings.map((finding) => (
                    <tr key={finding.finding_id}>
                      <td style={tdStyle}>#{finding.finding_id}</td>
                      <td style={tdStyle}>{finding.vendor_name || "Unknown"}</td>
                      <td style={tdStyle}>{finding.instrument_name || "Unknown"}</td>
                      <td style={tdStyle}>{finding.finding_category || "Not documented"}</td>
                      <td style={tdStyle}>
                        <span style={severityBadgeStyle(finding.severity || "")}>
                          {formatLabel(finding.severity || "unknown")}
                        </span>
                      </td>
                      <td style={tdStyle}>{formatConfidence(finding.confidence_score)}</td>
                      <td style={tdStyle}>{formatDate(finding.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}

function MetricCard({
  label,
  value,
  intent = "neutral",
}: {
  label: string;
  value: number;
  intent?: "neutral" | "success" | "warning" | "critical";
}) {
  return (
    <div style={metricCardStyle(intent)}>
      <span style={metricLabelStyle}>{label}</span>
      <strong style={metricValueStyle}>{value}</strong>
    </div>
  );
}

function formatLabel(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatConfidence(value?: number | null) {
  if (value === null || value === undefined) return "";
  return `${Math.round(value * 100)}%`;
}

function formatDate(value?: string) {
  if (!value) return "";
  return value.split("T")[0];
}

const panelStyle: React.CSSProperties = {
  padding: "20px",
  borderRadius: "22px",
  background: "#f8fafc",
  border: "1px solid #e2e8f0",
};

const headerRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "16px",
  alignItems: "flex-start",
  marginBottom: "18px",
};

const eyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#2563eb",
};

const titleStyle: React.CSSProperties = {
  margin: "4px 0",
  fontSize: "26px",
  fontWeight: 900,
  color: "#0f172a",
};

const subtitleStyle: React.CSSProperties = {
  margin: 0,
  color: "#475569",
  lineHeight: 1.5,
  maxWidth: "850px",
};

const refreshButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#1d4ed8",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
  whiteSpace: "nowrap",
};

function signalCardStyle(signal: string): React.CSSProperties {
  const elevated = signal === "elevated_enterprise_risk";
  const active = signal === "active_quality_risk";

  return {
    padding: "18px",
    borderRadius: "20px",
    border: `1px solid ${elevated ? "#fecaca" : active ? "#fed7aa" : "#bbf7d0"}`,
    background: elevated
      ? "linear-gradient(135deg, #fef2f2 0%, #ffffff 100%)"
      : active
        ? "linear-gradient(135deg, #fff7ed 0%, #ffffff 100%)"
        : "linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)",
    marginBottom: "16px",
  };
}

const signalTitleStyle: React.CSSProperties = {
  margin: "4px 0",
  fontSize: "22px",
  fontWeight: 900,
  color: "#0f172a",
};

const signalSummaryStyle: React.CSSProperties = {
  margin: 0,
  color: "#334155",
  lineHeight: 1.5,
};

const metricGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
  gap: "12px",
  marginBottom: "16px",
};

function metricCardStyle(intent: "neutral" | "success" | "warning" | "critical"): React.CSSProperties {
  const styles = {
    neutral: { border: "#dbeafe", background: "#ffffff", color: "#1e3a8a" },
    success: { border: "#bbf7d0", background: "#f0fdf4", color: "#166534" },
    warning: { border: "#fed7aa", background: "#fff7ed", color: "#9a3412" },
    critical: { border: "#fecaca", background: "#fef2f2", color: "#991b1b" },
  }[intent];

  return {
    padding: "14px",
    borderRadius: "18px",
    border: `1px solid ${styles.border}`,
    background: styles.background,
    color: styles.color,
  };
}

const metricLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "12px",
  fontWeight: 900,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const metricValueStyle: React.CSSProperties = {
  display: "block",
  marginTop: "6px",
  fontSize: "26px",
};

const contentGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  gap: "14px",
  marginBottom: "16px",
};

const cardStyle: React.CSSProperties = {
  padding: "16px",
  borderRadius: "18px",
  border: "1px solid #e2e8f0",
  background: "#ffffff",
  boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
};

const sectionTitleStyle: React.CSSProperties = {
  margin: "0 0 10px",
  fontSize: "18px",
  fontWeight: 900,
  color: "#0f172a",
};

const listStyle: React.CSSProperties = {
  margin: 0,
  paddingLeft: "20px",
  color: "#334155",
  lineHeight: 1.6,
};

const listItemStyle: React.CSSProperties = {
  marginBottom: "6px",
};

const vendorListStyle: React.CSSProperties = {
  display: "grid",
  gap: "8px",
};

const vendorRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  padding: "10px",
  borderRadius: "12px",
  background: "#f8fafc",
};

const vendorNameStyle: React.CSSProperties = {
  fontWeight: 900,
  color: "#0f172a",
};

const vendorCountStyle: React.CSSProperties = {
  color: "#475569",
  fontWeight: 800,
};

const mutedTextStyle: React.CSSProperties = {
  color: "#64748b",
};

const tableWrapStyle: React.CSSProperties = {
  overflowX: "auto",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "10px",
  fontSize: "12px",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  color: "#475569",
  borderBottom: "1px solid #e2e8f0",
  background: "#f8fafc",
};

const tdStyle: React.CSSProperties = {
  padding: "10px",
  borderBottom: "1px solid #e2e8f0",
  color: "#334155",
  verticalAlign: "top",
};

function severityBadgeStyle(severity: string): React.CSSProperties {
  const normalized = severity.toLowerCase();
  const critical = normalized === "critical";
  const high = normalized === "high";

  return {
    display: "inline-block",
    borderRadius: "999px",
    padding: "4px 8px",
    fontSize: "12px",
    fontWeight: 900,
    background: critical ? "#fee2e2" : high ? "#ffedd5" : "#e0f2fe",
    color: critical ? "#991b1b" : high ? "#9a3412" : "#075985",
  };
}

const errorStyle: React.CSSProperties = {
  marginBottom: "12px",
  padding: "12px",
  borderRadius: "14px",
  border: "1px solid #fecaca",
  background: "#fef2f2",
  color: "#991b1b",
  fontWeight: 800,
};

const emptyStateStyle: React.CSSProperties = {
  padding: "16px",
  borderRadius: "16px",
  background: "#ffffff",
  color: "#64748b",
  border: "1px dashed #cbd5e1",
};

const buttonRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  alignItems: "center",
  flexWrap: "wrap",
  justifyContent: "flex-end",
};

const pdfButtonStyle: React.CSSProperties = {
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#dbeafe",
  color: "#1e40af",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
};
