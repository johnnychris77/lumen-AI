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

function buildAuditCommandCenterDataDictionaryPdfUrl() {
  return `${API_BASE}/api/enterprise/audit-command-center.powerbi.data-dictionary.pdf`;
}

function buildAuditCommandCenterToolkitZipUrl(limit = 1000) {
  const safeLimit = Math.max(1, Math.min(Number(limit) || 1000, 5000));
  return `${API_BASE}/api/enterprise/audit-command-center.toolkit.zip?limit=${safeLimit}`;
}


type AuditCommandCenterHealthCheck = {
  check_name: string;
  status: string;
  message: string;
  endpoint?: string;
};

type AuditCommandCenterHealth = {
  status: string;
  health_type: string;
  overall_status: string;
  generated_at: string;
  toolkit_name: string;
  toolkit_version: string;
  dataset_name: string;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  warning_checks: number;
  total_audit_events: number;
  export_event_count: number;
  pdf_export_count: number;
  csv_export_count: number;
  zip_export_count: number;
  powerbi_event_count: number;
  high_value_compliance_event_count: number;
  checks: AuditCommandCenterHealthCheck[];
  recommended_action: string;
};

async function fetchAuditCommandCenterHealth(): Promise<AuditCommandCenterHealth> {
  const response = await fetch(`${API_BASE}/api/enterprise/audit-command-center.health`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-LumenAI-Role": "viewer",
      "X-LumenAI-Actor": "john-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Audit Command Center health check failed (${response.status})`);
  }

  return data;
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
  const [health, setHealth] = useState<AuditCommandCenterHealth | null>(null);
  const [limit, setLimit] = useState("25");
  const [loading, setLoading] = useState(false);
  const [healthLoading, setHealthLoading] = useState(false);
  const [error, setError] = useState("");
  const [healthError, setHealthError] = useState("");

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

  async function downloadAuditCommandCenterDataDictionaryPdf() {
    setError("");

    try {
      const response = await fetch(buildAuditCommandCenterDataDictionaryPdfUrl(), {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Audit Command Center Data Dictionary PDF download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "lumenai-audit-command-center-powerbi-data-dictionary.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown Audit Command Center Data Dictionary PDF download error");
    }
  }

  async function downloadAuditCommandCenterToolkitZip() {
    setError("");

    try {
      const response = await fetch(buildAuditCommandCenterToolkitZipUrl(Number(limit) || 1000), {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Audit Command Center Toolkit ZIP download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "lumenai-enterprise-audit-command-center-toolkit.zip";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown Audit Command Center Toolkit ZIP download error");
    }
  }

  async function loadHealth() {
    setHealthLoading(true);
    setHealthError("");

    try {
      const data = await fetchAuditCommandCenterHealth();
      setHealth(data);
    } catch (err) {
      setHealthError(err instanceof Error ? err.message : "Unknown Audit Command Center health error");
    } finally {
      setHealthLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
    loadHealth();
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

          <div style={auditCommandCompletionBadgeStyle}>
            <span style={auditCommandCompletionIconStyle}>✓</span>
            <div>
              <strong>Audit Command Center Toolkit Complete</strong>
              <p style={auditCommandCompletionTextStyle}>
                Dashboard, PDF export, CSV export, Power BI CSV, Data Dictionary PDF, and Toolkit ZIP are available.
              </p>
            </div>
          </div>
        </div>

        <div style={buttonGroupStyle}>
          <button type="button" onClick={loadDashboard} style={refreshButtonStyle}>
            {loading ? "Refreshing..." : "Refresh Audit"}
          </button>

          <button type="button" onClick={loadHealth} style={healthButtonStyle}>
            {healthLoading ? "Checking..." : "Refresh Health"}
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

          <button type="button" onClick={downloadAuditCommandCenterDataDictionaryPdf} style={dataDictionaryButtonStyle}>
            Download Data Dictionary PDF
          </button>

          <button type="button" onClick={downloadAuditCommandCenterToolkitZip} style={toolkitZipButtonStyle}>
            Download Toolkit ZIP
          </button>
        </div>
      </div>

      <div style={auditCommandSummaryCardStyle}>
        <div style={auditCommandSummaryHeaderStyle}>
          <div>
            <div style={auditCommandSummaryEyebrowStyle}>Audit Toolkit</div>
            <h3 style={auditCommandSummaryTitleStyle}>Enterprise Audit Command Center Package</h3>
          </div>
          <span style={auditCommandSummaryBadgeStyle}>Complete</span>
        </div>

        <div style={auditCommandSummaryGridStyle}>
          <AuditToolkitAsset label="Dashboard" status="Ready" />
          <AuditToolkitAsset label="Audit PDF" status="Ready" />
          <AuditToolkitAsset label="Audit CSV" status="Ready" />
          <AuditToolkitAsset label="Power BI CSV" status="Ready" />
          <AuditToolkitAsset label="Data Dictionary PDF" status="Ready" />
          <AuditToolkitAsset label="Toolkit ZIP" status="Ready" />
        </div>

        <p style={auditCommandSummaryTextStyle}>
          The Audit Command Center supports survey readiness, export traceability,
          audit-log review, Power BI analytics, leadership reporting, and compliance evidence review.
        </p>
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
          <div style={auditHealthCardStyle}>
            <div style={auditHealthHeaderStyle}>
              <div>
                <div style={auditHealthEyebrowStyle}>Toolkit Health</div>
                <h3 style={auditHealthTitleStyle}>Audit Command Center Health Check</h3>
              </div>
              {health ? (
                <span style={auditHealthBadgeStyle(health.overall_status)}>
                  {health.overall_status}
                </span>
              ) : (
                <span style={auditHealthBadgeStyle("pending")}>pending</span>
              )}
            </div>

            {healthError ? <div style={auditHealthErrorStyle}>{healthError}</div> : null}

            {health ? (
              <>
                <div style={auditHealthGridStyle}>
                  <AuditHealthMetric label="Toolkit Version" value={health.toolkit_version} />
                  <AuditHealthMetric label="Dataset" value={health.dataset_name} />
                  <AuditHealthMetric label="Total Checks" value={String(health.total_checks)} />
                  <AuditHealthMetric label="Passed" value={String(health.passed_checks)} />
                  <AuditHealthMetric label="Failed" value={String(health.failed_checks)} />
                  <AuditHealthMetric label="Warnings" value={String(health.warning_checks)} />
                  <AuditHealthMetric label="Audit Events" value={String(health.total_audit_events)} />
                  <AuditHealthMetric label="High-Value Events" value={String(health.high_value_compliance_event_count)} />
                </div>

                <div style={auditHealthActionStyle}>
                  <strong>Recommended Action</strong>
                  <p>{health.recommended_action}</p>
                </div>

                <details style={auditHealthDetailsStyle}>
                  <summary style={auditHealthSummaryStyle}>
                    View health checks ({health.checks?.length || 0})
                  </summary>

                  <div style={auditHealthCheckListStyle}>
                    {(health.checks || []).map((check) => (
                      <div key={check.check_name} style={auditHealthCheckItemStyle}>
                        <span style={auditHealthCheckBadgeStyle(check.status)}>{check.status}</span>
                        <div>
                          <strong>{check.check_name}</strong>
                          <p>{check.message}</p>
                          {check.endpoint ? <code style={auditHealthEndpointStyle}>{check.endpoint}</code> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              </>
            ) : (
              <p style={auditHealthEmptyStyle}>Audit Command Center health has not loaded yet.</p>
            )}
          </div>

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

function AuditToolkitAsset({ label, status }: { label: string; status: string }) {
  return (
    <div style={auditToolkitAssetStyle}>
      <span style={auditToolkitAssetLabelStyle}>{label}</span>
      <strong style={auditToolkitAssetStatusStyle}>{status}</strong>
    </div>
  );
}

function AuditHealthMetric({ label, value }: { label: string; value?: string }) {
  return (
    <div style={auditHealthMetricStyle}>
      <span style={auditHealthMetricLabelStyle}>{label}</span>
      <strong style={auditHealthMetricValueStyle}>{value || "Not available"}</strong>
    </div>
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


const dataDictionaryButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#0ea5e9",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};


const toolkitZipButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#111827",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};



const auditCommandCompletionBadgeStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  alignItems: "flex-start",
  marginTop: "14px",
  padding: "12px 14px",
  borderRadius: "16px",
  border: "1px solid #bbf7d0",
  background: "linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)",
  color: "#166534",
  maxWidth: "820px",
};

const auditCommandCompletionIconStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: "24px",
  height: "24px",
  borderRadius: "999px",
  background: "#16a34a",
  color: "#ffffff",
  fontWeight: 900,
  flex: "0 0 auto",
};

const auditCommandCompletionTextStyle: React.CSSProperties = {
  margin: "4px 0 0",
  color: "#166534",
  lineHeight: 1.45,
  fontSize: "13px",
};



const auditCommandSummaryCardStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "16px",
  borderRadius: "20px",
  border: "1px solid #bfdbfe",
  background: "linear-gradient(135deg, #eff6ff 0%, #ffffff 100%)",
  boxShadow: "0 8px 24px rgba(37, 99, 235, 0.08)",
};

const auditCommandSummaryHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
};

const auditCommandSummaryEyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#2563eb",
};

const auditCommandSummaryTitleStyle: React.CSSProperties = {
  margin: "4px 0 0",
  fontSize: "18px",
  fontWeight: 900,
  color: "#1e3a8a",
};

const auditCommandSummaryBadgeStyle: React.CSSProperties = {
  borderRadius: "999px",
  padding: "6px 10px",
  background: "#dcfce7",
  color: "#166534",
  fontWeight: 900,
  fontSize: "12px",
  whiteSpace: "nowrap",
};

const auditCommandSummaryGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
  gap: "10px",
  marginTop: "14px",
};

const auditToolkitAssetStyle: React.CSSProperties = {
  padding: "10px",
  borderRadius: "14px",
  border: "1px solid #dbeafe",
  background: "#ffffff",
};

const auditToolkitAssetLabelStyle: React.CSSProperties = {
  display: "block",
  color: "#1e3a8a",
  fontWeight: 800,
  fontSize: "13px",
};

const auditToolkitAssetStatusStyle: React.CSSProperties = {
  display: "block",
  marginTop: "4px",
  color: "#166534",
  fontSize: "12px",
};

const auditCommandSummaryTextStyle: React.CSSProperties = {
  margin: "12px 0 0",
  color: "#475569",
  lineHeight: 1.5,
  fontSize: "13px",
};



const healthButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#15803d",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};

const auditHealthCardStyle: React.CSSProperties = {
  marginTop: "18px",
  padding: "16px",
  borderRadius: "20px",
  border: "1px solid #bbf7d0",
  background: "linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)",
  boxShadow: "0 8px 24px rgba(22, 101, 52, 0.08)",
};

const auditHealthHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
};

const auditHealthEyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#15803d",
};

const auditHealthTitleStyle: React.CSSProperties = {
  margin: "4px 0 0",
  fontSize: "18px",
  fontWeight: 900,
  color: "#14532d",
};

function auditHealthBadgeStyle(status: string): React.CSSProperties {
  const normalized = (status || "").toLowerCase();
  const isHealthy = normalized === "healthy";
  const isWarning = normalized === "warning";
  const isPending = normalized === "pending";

  return {
    borderRadius: "999px",
    padding: "6px 10px",
    fontSize: "12px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: isHealthy ? "#dcfce7" : isWarning ? "#ffedd5" : isPending ? "#e2e8f0" : "#fee2e2",
    color: isHealthy ? "#166534" : isWarning ? "#9a3412" : isPending ? "#334155" : "#991b1b",
    whiteSpace: "nowrap",
  };
}

const auditHealthGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
  gap: "10px",
  marginTop: "14px",
};

const auditHealthMetricStyle: React.CSSProperties = {
  padding: "10px",
  borderRadius: "14px",
  border: "1px solid #bbf7d0",
  background: "#ffffff",
};

const auditHealthMetricLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "11px",
  fontWeight: 900,
  textTransform: "uppercase",
  color: "#64748b",
};

const auditHealthMetricValueStyle: React.CSSProperties = {
  display: "block",
  marginTop: "4px",
  color: "#0f172a",
  fontSize: "13px",
};

const auditHealthActionStyle: React.CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "14px",
  background: "#ffffff",
  border: "1px solid #bbf7d0",
  color: "#14532d",
};

const auditHealthDetailsStyle: React.CSSProperties = {
  marginTop: "12px",
};

const auditHealthSummaryStyle: React.CSSProperties = {
  cursor: "pointer",
  fontWeight: 900,
  color: "#166534",
};

const auditHealthCheckListStyle: React.CSSProperties = {
  display: "grid",
  gap: "8px",
  marginTop: "10px",
};

const auditHealthCheckItemStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  padding: "10px",
  borderRadius: "12px",
  border: "1px solid #e2e8f0",
  background: "#ffffff",
};

function auditHealthCheckBadgeStyle(status: string): React.CSSProperties {
  const normalized = (status || "").toLowerCase();

  return {
    alignSelf: "flex-start",
    borderRadius: "999px",
    padding: "4px 8px",
    fontSize: "11px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: normalized === "pass" ? "#dcfce7" : normalized === "warning" ? "#ffedd5" : "#fee2e2",
    color: normalized === "pass" ? "#166534" : normalized === "warning" ? "#9a3412" : "#991b1b",
  };
}

const auditHealthEndpointStyle: React.CSSProperties = {
  display: "inline-block",
  marginTop: "4px",
  fontSize: "11px",
  color: "#334155",
};

const auditHealthErrorStyle: React.CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 800,
};

const auditHealthEmptyStyle: React.CSSProperties = {
  margin: "12px 0 0",
  color: "#64748b",
};
