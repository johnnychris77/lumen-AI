import { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://lumen-ai-53u4.onrender.com";

type AuditEvent = {
  audit_id: number | null;
  tenant_id: string;
  tenant_name: string;
  action_type: string;
  resource_type: string;
  resource_id: string;
  actor: string;
  created_at: string;
  details?: Record<string, unknown>;
};

type AuditCommandCenterResponse = {
  status: string;
  dashboard_type: string;
  generated_at: string;
  total_audit_events: number;
  export_event_count: number;
  pdf_export_count: number;
  csv_export_count: number;
  zip_export_count: number;
  health_check_count: number;
  validation_event_count: number;
  production_lock_event_count: number;
  powerbi_event_count: number;
  high_value_compliance_event_count: number;
  audit_signal: string;
  executive_summary: string;
  recommended_leadership_actions: string[];
  recent_audit_events: AuditEvent[];
  high_value_compliance_events: AuditEvent[];
};

function buildAuditCommandCenterPdfUrl(limit = 25) {
  const safeLimit = Math.max(1, Math.min(Number(limit) || 25, 100));
  return `${API_BASE}/api/enterprise/audit-command-center.pdf?limit=${safeLimit}`;
}

function buildAuditCommandCenterCsvUrl(limit = 100) {
  const safeLimit = Math.max(1, Math.min(Number(limit) || 100, 1000));
  return `${API_BASE}/api/enterprise/audit-command-center.csv?limit=${safeLimit}`;
}

function buildAuditCommandCenterPowerBiCsvUrl(limit = 1000) {
  const safeLimit = Math.max(1, Math.min(Number(limit) || 1000, 5000));
  return `${API_BASE}/api/enterprise/audit-command-center.powerbi.csv?limit=${safeLimit}`;
}

async function fetchAuditCommandCenter(limit = 25): Promise<AuditCommandCenterResponse> {
  const response = await fetch(`${API_BASE}/api/enterprise/audit-command-center?limit=${limit}`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-LumenAI-Role": "viewer",
      "X-LumenAI-Actor": "john-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Audit Command Center failed (${response.status})`);
  }

  return data;
}

export default function EnterpriseAuditCommandCenter() {
  const [dashboard, setDashboard] = useState<AuditCommandCenterResponse | null>(null);
  const [limit, setLimit] = useState("25");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const safeLimit = Math.max(1, Math.min(Number(limit) || 25, 100));
      const data = await fetchAuditCommandCenter(safeLimit);
      setDashboard(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown Audit Command Center error");
    } finally {
      setLoading(false);
    }
  }

  async function downloadAuditCommandCenterPdf() {
    setError("");

    try {
      const response = await fetch(buildAuditCommandCenterPdfUrl(Number(limit) || 25), {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Audit Command Center PDF download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "lumenai-enterprise-audit-command-center.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown Audit Command Center PDF download error");
    }
  }

  async function downloadAuditCommandCenterCsv() {
    setError("");

    try {
      const response = await fetch(buildAuditCommandCenterCsvUrl(Number(limit) || 100), {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Audit Command Center CSV download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "lumenai-enterprise-audit-command-center.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown Audit Command Center CSV download error");
    }
  }

  async function downloadAuditCommandCenterPowerBiCsv() {
    setError("");

    try {
      const response = await fetch(buildAuditCommandCenterPowerBiCsvUrl(Number(limit) || 1000), {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Audit Command Center Power BI CSV download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "lumenai-enterprise-audit-command-center-powerbi.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown Audit Command Center Power BI CSV download error");
    }
  }

  useEffect(() => {
    loadDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const recentEvents = dashboard?.recent_audit_events || [];
  const highValueEvents = dashboard?.high_value_compliance_events || [];

  return (
    <section style={panelStyle}>
      <div style={headerRowStyle}>
        <div>
          <div style={eyebrowStyle}>Enterprise Governance</div>
          <h2 style={titleStyle}>Audit Command Center</h2>
          <p style={subtitleStyle}>
            Centralized audit visibility for exports, health checks, validation events,
            production locks, and high-value compliance activity.
          </p>
        </div>

        <div style={buttonGroupStyle}>
          <button type="button" onClick={loadDashboard} style={refreshButtonStyle}>
            {loading ? "Refreshing..." : "Refresh Audit"}
          </button>

          <button type="button" onClick={downloadAuditCommandCenterPdf} style={pdfButtonStyle}>
            Download Audit PDF
          </button>

          <button type="button" onClick={downloadAuditCommandCenterCsv} style={csvButtonStyle}>
            Download Audit CSV
          </button>

          <button type="button" onClick={downloadAuditCommandCenterPowerBiCsv} style={powerBiCsvButtonStyle}>
            Download Power BI CSV
          </button>
        </div>
      </div>

      <div style={controlRowStyle}>
        <label style={labelStyle}>
          Limit
          <input
            value={limit}
            onChange={(event) => setLimit(event.target.value)}
            style={inputStyle}
            inputMode="numeric"
          />
        </label>

        <span style={statusBadgeStyle(dashboard?.audit_signal || "pending")}>
          {dashboard?.audit_signal || "pending"}
        </span>

        {dashboard?.generated_at ? (
          <span style={timestampStyle}>
            Generated: {new Date(dashboard.generated_at).toLocaleString()}
          </span>
        ) : null}
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      {dashboard ? (
        <>
          <div style={metricGridStyle}>
            <MetricCard label="Total Audit Events" value={dashboard.total_audit_events} />
            <MetricCard label="Export Events" value={dashboard.export_event_count} />
            <MetricCard label="PDF Exports" value={dashboard.pdf_export_count} />
            <MetricCard label="CSV Exports" value={dashboard.csv_export_count} />
            <MetricCard label="ZIP Exports" value={dashboard.zip_export_count} />
            <MetricCard label="Health Checks" value={dashboard.health_check_count} />
            <MetricCard label="Validation Events" value={dashboard.validation_event_count} />
            <MetricCard label="Production Locks" value={dashboard.production_lock_event_count} />
            <MetricCard label="Power BI Events" value={dashboard.powerbi_event_count} />
            <MetricCard label="High-Value Compliance" value={dashboard.high_value_compliance_event_count} />
          </div>

          <div style={summaryCardStyle}>
            <h3 style={sectionTitleStyle}>Executive Summary</h3>
            <p style={summaryTextStyle}>{dashboard.executive_summary}</p>
          </div>

          <div style={actionsCardStyle}>
            <h3 style={sectionTitleStyle}>Recommended Leadership Actions</h3>
            <ul style={actionListStyle}>
              {(dashboard.recommended_leadership_actions || []).map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </div>

          <div style={tableCardStyle}>
            <div style={tableHeaderStyle}>
              <h3 style={sectionTitleStyle}>Recent Audit Events</h3>
              <span style={smallBadgeStyle}>{recentEvents.length} shown</span>
            </div>

            <div style={tableWrapStyle}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>ID</th>
                    <th style={thStyle}>Action</th>
                    <th style={thStyle}>Resource</th>
                    <th style={thStyle}>Resource ID</th>
                    <th style={thStyle}>Actor</th>
                    <th style={thStyle}>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {recentEvents.map((event) => (
                    <tr key={`${event.audit_id}-${event.created_at}`}>
                      <td style={tdStyle}>{event.audit_id}</td>
                      <td style={tdStyle}>{event.action_type}</td>
                      <td style={tdStyle}>{event.resource_type}</td>
                      <td style={tdStyle}>{event.resource_id}</td>
                      <td style={tdStyle}>{event.actor || "—"}</td>
                      <td style={tdStyle}>
                        {event.created_at ? new Date(event.created_at).toLocaleString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <details style={detailsStyle}>
            <summary style={detailsSummaryStyle}>
              View High-Value Compliance Events ({highValueEvents.length})
            </summary>

            <div style={eventGridStyle}>
              {highValueEvents.map((event) => (
                <div key={`high-${event.audit_id}-${event.created_at}`} style={eventCardStyle}>
                  <div style={eventTopLineStyle}>
                    <strong>#{event.audit_id}</strong>
                    <span>{event.created_at ? new Date(event.created_at).toLocaleString() : "—"}</span>
                  </div>
                  <div style={eventActionStyle}>{event.action_type}</div>
                  <div style={eventResourceStyle}>{event.resource_type}</div>
                  <div style={eventResourceStyle}>{event.resource_id}</div>
                </div>
              ))}
            </div>
          </details>
        </>
      ) : (
        <p style={emptyStyle}>Audit Command Center has not loaded yet.</p>
      )}
    </section>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={metricCardStyle}>
      <span style={metricLabelStyle}>{label}</span>
      <strong style={metricValueStyle}>{value}</strong>
    </div>
  );
}

const panelStyle: React.CSSProperties = {
  marginTop: "20px",
  padding: "20px",
  borderRadius: "24px",
  border: "1px solid #cbd5e1",
  background: "linear-gradient(135deg, #f8fafc 0%, #ffffff 100%)",
  boxShadow: "0 12px 32px rgba(15, 23, 42, 0.08)",
};

const headerRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "16px",
  alignItems: "flex-start",
  flexWrap: "wrap",
};

const eyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#2563eb",
};

const titleStyle: React.CSSProperties = {
  margin: "4px 0 0",
  fontSize: "24px",
  fontWeight: 900,
  color: "#0f172a",
};

const subtitleStyle: React.CSSProperties = {
  margin: "8px 0 0",
  color: "#475569",
  lineHeight: 1.5,
  maxWidth: "780px",
};

const refreshButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#2563eb",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};

const controlRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  alignItems: "center",
  flexWrap: "wrap",
  marginTop: "16px",
};

const labelStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  color: "#334155",
  fontWeight: 800,
};

const inputStyle: React.CSSProperties = {
  width: "80px",
  border: "1px solid #cbd5e1",
  borderRadius: "10px",
  padding: "8px 10px",
  fontWeight: 800,
};

function statusBadgeStyle(signal: string): React.CSSProperties {
  const active = signal === "audit_activity_present";

  return {
    borderRadius: "999px",
    padding: "6px 10px",
    fontSize: "12px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: active ? "#dcfce7" : "#e2e8f0",
    color: active ? "#166534" : "#334155",
  };
}

const timestampStyle: React.CSSProperties = {
  color: "#64748b",
  fontSize: "13px",
  fontWeight: 700,
};

const errorStyle: React.CSSProperties = {
  marginTop: "12px",
  padding: "12px",
  borderRadius: "14px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 800,
};

const metricGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
  gap: "12px",
  marginTop: "18px",
};

const metricCardStyle: React.CSSProperties = {
  padding: "14px",
  borderRadius: "18px",
  border: "1px solid #e2e8f0",
  background: "#ffffff",
};

const metricLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "11px",
  fontWeight: 900,
  textTransform: "uppercase",
  color: "#64748b",
};

const metricValueStyle: React.CSSProperties = {
  display: "block",
  marginTop: "6px",
  color: "#0f172a",
  fontSize: "26px",
  fontWeight: 900,
};

const summaryCardStyle: React.CSSProperties = {
  marginTop: "18px",
  padding: "16px",
  borderRadius: "18px",
  background: "#eff6ff",
  border: "1px solid #bfdbfe",
};

const actionsCardStyle: React.CSSProperties = {
  marginTop: "14px",
  padding: "16px",
  borderRadius: "18px",
  background: "#f0fdf4",
  border: "1px solid #bbf7d0",
};

const sectionTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: "16px",
  fontWeight: 900,
  color: "#0f172a",
};

const summaryTextStyle: React.CSSProperties = {
  margin: "8px 0 0",
  color: "#1e3a8a",
  lineHeight: 1.5,
};

const actionListStyle: React.CSSProperties = {
  margin: "8px 0 0",
  paddingLeft: "18px",
  color: "#14532d",
  lineHeight: 1.6,
};

const tableCardStyle: React.CSSProperties = {
  marginTop: "18px",
  padding: "16px",
  borderRadius: "18px",
  background: "#ffffff",
  border: "1px solid #e2e8f0",
};

const tableHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "center",
};

const smallBadgeStyle: React.CSSProperties = {
  borderRadius: "999px",
  padding: "5px 9px",
  background: "#f1f5f9",
  color: "#334155",
  fontSize: "12px",
  fontWeight: 800,
};

const tableWrapStyle: React.CSSProperties = {
  overflowX: "auto",
  marginTop: "12px",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "13px",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "10px",
  borderBottom: "1px solid #cbd5e1",
  color: "#334155",
  fontSize: "12px",
  textTransform: "uppercase",
};

const tdStyle: React.CSSProperties = {
  padding: "10px",
  borderBottom: "1px solid #e2e8f0",
  color: "#334155",
  verticalAlign: "top",
};

const detailsStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "14px",
  borderRadius: "18px",
  background: "#fefce8",
  border: "1px solid #fde68a",
};

const detailsSummaryStyle: React.CSSProperties = {
  cursor: "pointer",
  fontWeight: 900,
  color: "#854d0e",
};

const eventGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
  gap: "10px",
  marginTop: "12px",
};

const eventCardStyle: React.CSSProperties = {
  padding: "12px",
  borderRadius: "14px",
  background: "#ffffff",
  border: "1px solid #fde68a",
};

const eventTopLineStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "8px",
  color: "#64748b",
  fontSize: "12px",
};

const eventActionStyle: React.CSSProperties = {
  marginTop: "8px",
  fontWeight: 900,
  color: "#0f172a",
};

const eventResourceStyle: React.CSSProperties = {
  marginTop: "4px",
  color: "#475569",
  fontSize: "12px",
};

const emptyStyle: React.CSSProperties = {
  margin: "16px 0 0",
  color: "#64748b",
};

const buttonGroupStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  flexWrap: "wrap",
  alignItems: "center",
};

const pdfButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#0f172a",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};


const csvButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#16a34a",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};


const powerBiCsvButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#7c3aed",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};
