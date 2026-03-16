import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import InspectionHistory from "./pages/InspectionHistory";

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function statusPill(status: string) {
  const base: React.CSSProperties = {
    display: "inline-block",
    padding: "4px 10px",
    borderRadius: "999px",
    fontSize: "12px",
    fontWeight: 700,
    textTransform: "capitalize",
  };

  switch ((status || "").toLowerCase()) {
    case "completed":
    case "ok":
      return { ...base, background: "#dcfce7", color: "#166534" };
    case "queued":
      return { ...base, background: "#fef3c7", color: "#92400e" };
    case "running":
      return { ...base, background: "#dbeafe", color: "#1d4ed8" };
    case "failed":
      return { ...base, background: "#fee2e2", color: "#991b1b" };
    default:
      return { ...base, background: "#e5e7eb", color: "#374151" };
  }
}

function priorityPill(priority: string) {
  const base: React.CSSProperties = {
    display: "inline-block",
    padding: "4px 10px",
    borderRadius: "999px",
    fontSize: "12px",
    fontWeight: 700,
    textTransform: "capitalize",
  };

  switch ((priority || "").toLowerCase()) {
    case "critical":
      return { ...base, background: "#7f1d1d", color: "#ffffff" };
    case "high":
      return { ...base, background: "#fee2e2", color: "#991b1b" };
    case "medium":
      return { ...base, background: "#fef3c7", color: "#92400e" };
    default:
      return { ...base, background: "#dcfce7", color: "#166534" };
  }
}

type SummaryItem = { label: string; count: number };

type Summary = {
  total_inspections: number;
  completed: number;
  queued: number;
  running: number;
  failed: number;
  top_issues: SummaryItem[];
  top_instruments: SummaryItem[];
};

type Inspection = {
  id: number;
  created_at?: string;
  file_name?: string;
  stain_detected?: boolean;
  confidence?: number;
  material_type?: string;
  status?: string;
  model_name?: string;
  model_version?: string;
  inference_timestamp?: string | null;
  instrument_type?: string;
  detected_issue?: string;
  inference_mode?: string;
  risk_score?: number;
  vendor_name?: string;
};

type AgentItem = {
  inspection_id: number;
  priority: string;
  risk_score: number;
  escalation_needed: boolean;
  recommended_actions: string[];
  summary: string;
};

type VendorIssue = {
  label: string;
  count: number;
};

type VendorItem = {
  vendor_name: string;
  total_inspections: number;
  escalations: number;
  avg_confidence: number;
  top_issues: VendorIssue[];
};

type AlertItem = {
  inspection_id: number;
  file_name: string;
  vendor_name: string;
  instrument_type: string;
  detected_issue: string;
  risk_score: number;
  status: string;
  message: string;
};

function DashboardHome() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recent, setRecent] = useState<Inspection[]>([]);
  const [agentFeed, setAgentFeed] = useState<AgentItem[]>([]);
  const [vendors, setVendors] = useState<VendorItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [health, setHealth] = useState("checking");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const token = useMemo(() => localStorage.getItem("token") || "", []);

  useEffect(() => {
    let ignore = false;

    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const headers = token ? { Authorization: `Bearer ${token}` } : {};

        const [summaryRes, historyRes, healthRes, agentRes, vendorRes, alertsRes] =
          await Promise.all([
            fetch(`${API_BASE}/history/summary`, { headers }),
            fetch(`${API_BASE}/history?limit=8`, { headers }),
            fetch(`${API_BASE}/health`),
            fetch(`${API_BASE}/agent/feed?limit=8`, { headers }),
            fetch(`${API_BASE}/analytics/vendors`, { headers }),
            fetch(`${API_BASE}/alerts/feed`, { headers }),
          ]);

        if (!summaryRes.ok) throw new Error(`Summary request failed (${summaryRes.status})`);
        if (!historyRes.ok) throw new Error(`History request failed (${historyRes.status})`);
        if (!agentRes.ok) throw new Error(`Agent request failed (${agentRes.status})`);
        if (!vendorRes.ok) throw new Error(`Vendor analytics request failed (${vendorRes.status})`);
        if (!alertsRes.ok) throw new Error(`Alerts request failed (${alertsRes.status})`);

        const summaryData = await summaryRes.json();
        const historyData = await historyRes.json();
        const agentData = await agentRes.json();
        const vendorData = await vendorRes.json();
        const alertsData = await alertsRes.json();

        let healthStatus = "unavailable";
        if (healthRes.ok) {
          try {
            const healthJson = await healthRes.json();
            healthStatus = healthJson.status || "ok";
          } catch {
            healthStatus = "ok";
          }
        }

        if (!ignore) {
          setSummary(summaryData);
          setRecent(Array.isArray(historyData.items) ? historyData.items : []);
          setAgentFeed(Array.isArray(agentData.items) ? agentData.items : []);
          setVendors(Array.isArray(vendorData.items) ? vendorData.items : []);
          setAlerts(Array.isArray(alertsData.items) ? alertsData.items : []);
          setHealth(healthStatus);
        }
      } catch (err: any) {
        if (!ignore) {
          setError(err?.message || "Failed to load dashboard.");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    loadDashboard();
    return () => {
      ignore = true;
    };
  }, [token]);

  const csvExportUrl = `${API_BASE}/history/export.csv`;
  const jsonExportUrl = `${API_BASE}/history/export.json`;
  const xlsxExportUrl = `${API_BASE}/history/export.xlsx`;
  const bundleExportUrl = `${API_BASE}/history/export.bundle.zip`;

  const criticalCount = agentFeed.filter((x) => x.priority === "critical").length;
  const highCount = agentFeed.filter((x) => x.priority === "high").length;
  const escalationCount = agentFeed.filter((x) => x.escalation_needed).length;
  const totalVendors = vendors.length;
  const topVendor = vendors[0]?.vendor_name || "—";
  const topVendorEscalations = vendors[0]?.escalations || 0;
  const liveQueuedCount = recent.filter((x) => (x.status || "").toLowerCase() === "queued").length;
  const liveCompletedCount = recent.filter((x) => (x.status || "").toLowerCase() === "completed").length;

  return (
    <div style={{ padding: "24px", maxWidth: "1320px", margin: "0 auto" }}>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ marginBottom: "8px" }}>LumenAI Phase 2 Command Dashboard</h1>
        <p style={{ color: "#4b5563", margin: 0 }}>
          Real-time surgical instrument quality intelligence for SPD teams,
          surgical vendors, and device manufacturers.
        </p>
      </div>

      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "24px" }}>
        <Link to="/history" style={secondaryButton}>
          Open Full History
        </Link>
        <a href={`${API_BASE}/health`} target="_blank" rel="noreferrer" style={secondaryButton}>
          API Health
        </a>
      </div>

      {loading && <p>Loading Phase 2 dashboard...</p>}
      {!loading && error && <div style={errorBox}>{error}</div>}

      {!loading && !error && summary && (
        <>
          <div
            style={{
              display: "grid",
              gap: "16px",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              marginBottom: "24px",
            }}
          >
            <div style={card}>
              <div style={cardLabel}>Total Inspections</div>
              <div style={cardValue}>{summary.total_inspections}</div>
            </div>

            <div style={card}>
              <div style={cardLabel}>Completed</div>
              <div style={cardValue}>{summary.completed}</div>
            </div>

            <div style={card}>
              <div style={cardLabel}>Escalations Needed</div>
              <div style={cardValue}>{escalationCount}</div>
            </div>

            <div style={card}>
              <div style={cardLabel}>Active Alerts</div>
              <div style={cardValue}>{alerts.length}</div>
            </div>

            <div style={card}>
              <div style={cardLabel}>System Health</div>
              <div style={cardValueSmall}>
                <span style={statusPill(health)}>{health}</span>
              </div>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gap: "16px",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              marginBottom: "24px",
            }}
          >
            <div style={card}>
              <div style={cardLabel}>Critical Priority</div>
              <div style={cardValue}>{criticalCount}</div>
            </div>

            <div style={card}>
              <div style={cardLabel}>High Priority</div>
              <div style={cardValue}>{highCount}</div>
            </div>

            <div style={card}>
              <div style={cardLabel}>Tracked Vendors</div>
              <div style={cardValue}>{totalVendors}</div>
            </div>

            <div style={card}>
              <div style={cardLabel}>Top Vendor by Escalations</div>
              <div style={cardValueSmall}>
                {topVendor} ({topVendorEscalations})
              </div>
            </div>

            <div style={card}>
              <div style={cardLabel}>Live Stream Queued / Completed</div>
              <div style={cardValueSmall}>
                {liveQueuedCount} / {liveCompletedCount}
              </div>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gap: "16px",
              gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
              marginBottom: "24px",
            }}
          >
            <div style={card}>
              <h2 style={sectionTitle}>Top Detected Issues</h2>
              {summary.top_issues.length === 0 ? (
                <p style={muted}>No issue data yet.</p>
              ) : (
                <div style={{ display: "grid", gap: "10px" }}>
                  {summary.top_issues.map((item) => (
                    <div key={item.label} style={listRow}>
                      <span>{item.label}</span>
                      <strong>{item.count}</strong>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={card}>
              <h2 style={sectionTitle}>Top Instrument Types</h2>
              {summary.top_instruments.length === 0 ? (
                <p style={muted}>No instrument data yet.</p>
              ) : (
                <div style={{ display: "grid", gap: "10px" }}>
                  {summary.top_instruments.map((item) => (
                    <div key={item.label} style={listRow}>
                      <span>{item.label}</span>
                      <strong>{item.count}</strong>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gap: "16px",
              gridTemplateColumns: "1fr 1fr",
              marginBottom: "24px",
            }}
          >
            <div style={card}>
              <h2 style={sectionTitle}>SPD Alert Center</h2>
              {alerts.length === 0 ? (
                <p style={muted}>No active alerts.</p>
              ) : (
                <div style={{ display: "grid", gap: "12px" }}>
                  {alerts.slice(0, 8).map((item) => (
                    <div key={item.inspection_id} style={alertCard}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", alignItems: "center" }}>
                        <strong>Inspection #{item.inspection_id}</strong>
                        <span style={priorityPill(item.risk_score >= 80 ? "critical" : item.risk_score >= 50 ? "medium" : "low")}>
                          Risk {item.risk_score}
                        </span>
                      </div>
                      <div style={{ marginTop: "8px", color: "#374151", fontSize: "14px" }}>
                        {item.message}
                      </div>
                      <div style={{ marginTop: "8px", fontSize: "13px", color: "#6b7280" }}>
                        Vendor: {item.vendor_name || "unknown"} · Instrument: {item.instrument_type || "unknown"}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={card}>
              <h2 style={sectionTitle}>Vendor Intelligence</h2>
              {vendors.length === 0 ? (
                <p style={muted}>No vendor analytics available.</p>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table style={table}>
                    <thead style={{ background: "#f9fafb" }}>
                      <tr>
                        <th style={th}>Vendor</th>
                        <th style={th}>Inspections</th>
                        <th style={th}>Escalations</th>
                        <th style={th}>Avg Confidence</th>
                        <th style={th}>Top Issue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vendors.slice(0, 8).map((vendor) => (
                        <tr key={vendor.vendor_name} style={{ borderTop: "1px solid #e5e7eb" }}>
                          <td style={td}>{vendor.vendor_name}</td>
                          <td style={td}>{vendor.total_inspections}</td>
                          <td style={td}>{vendor.escalations}</td>
                          <td style={td}>{vendor.avg_confidence.toFixed(2)}</td>
                          <td style={td}>{vendor.top_issues[0]?.label || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gap: "16px",
              gridTemplateColumns: "1.15fr 1fr",
              marginBottom: "24px",
            }}
          >
            <div style={card}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "12px",
                  gap: "12px",
                  flexWrap: "wrap",
                }}
              >
                <h2 style={sectionTitle}>Recent Live Stream Activity & Reports</h2>
                <Link to="/history" style={{ textDecoration: "none" }}>
                  View all
                </Link>
              </div>

              {recent.length === 0 ? (
                <p style={muted}>No recent inspections found.</p>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table style={table}>
                    <thead style={{ background: "#f9fafb" }}>
                      <tr>
                        <th style={th}>ID</th>
                        <th style={th}>File</th>
                        <th style={th}>Vendor</th>
                        <th style={th}>Status</th>
                        <th style={th}>Instrument</th>
                        <th style={th}>Issue</th>
                        <th style={th}>Risk</th>
                        <th style={th}>Created</th>
                        <th style={th}>Report</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recent.map((item) => (
                        <tr key={item.id} style={{ borderTop: "1px solid #e5e7eb" }}>
                          <td style={td}>{item.id}</td>
                          <td style={td}>{item.file_name || "—"}</td>
                          <td style={td}>{item.vendor_name || "unknown"}</td>
                          <td style={td}>
                            <span style={statusPill(item.status || "unknown")}>
                              {item.status || "unknown"}
                            </span>
                          </td>
                          <td style={td}>{item.instrument_type || "unknown"}</td>
                          <td style={td}>{item.detected_issue || "unknown"}</td>
                          <td style={td}>{typeof item.risk_score === "number" ? item.risk_score : "—"}</td>
                          <td style={td}>{formatDate(item.created_at)}</td>
                          <td style={td}>
                            {(item.status || "").toLowerCase() === "completed" ? (
                              <a
                                href={`${API_BASE}/reports/${item.id}.pdf`}
                                target="_blank"
                                rel="noreferrer"
                                style={secondaryButtonInline}
                              >
                                Open PDF
                              </a>
                            ) : (
                              <span style={muted}>Pending</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div style={card}>
              <h2 style={sectionTitle}>SPD Agent Feed</h2>
              {agentFeed.length === 0 ? (
                <p style={muted}>No agent recommendations available.</p>
              ) : (
                <div style={{ display: "grid", gap: "12px" }}>
                  {agentFeed.map((item) => (
                    <div key={item.inspection_id} style={agentCard}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", alignItems: "center" }}>
                        <strong>Inspection #{item.inspection_id}</strong>
                        <span style={priorityPill(item.priority)}>{item.priority}</span>
                      </div>

                      <div style={{ marginTop: "8px", color: "#374151", fontSize: "14px" }}>
                        {item.summary}
                      </div>

                      <div style={{ marginTop: "8px", fontSize: "13px", color: "#6b7280" }}>
                        Risk score: {item.risk_score} · Escalation: {item.escalation_needed ? "Yes" : "No"}
                      </div>

                      <ul style={{ marginTop: "10px", paddingLeft: "18px", color: "#111827" }}>
                        {item.recommended_actions.map((action, idx) => (
                          <li key={idx}>{action}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div style={card}>
            <h2 style={sectionTitle}>Export Center</h2>
            <p style={{ color: "#4b5563", marginTop: 0 }}>
              Download LumenAI inspection data for Excel, Power BI, Tableau,
              investor decks, hospital QA analysis, or vendor defect reporting.
            </p>

            <div style={{ display: "grid", gap: "12px" }}>
              <a href={csvExportUrl} style={primaryButton}>Export CSV</a>
              <div style={exportHint}>Best for Excel, Power BI, and Tableau import.</div>

              <a href={xlsxExportUrl} style={primaryButton}>Export Excel Workbook</a>
              <div style={exportHint}>Includes inspection rows plus leadership summary sheet.</div>

              <a href={jsonExportUrl} style={secondaryButton}>Export JSON</a>
              <div style={exportHint}>Useful for engineering pipelines and integrations.</div>

              <a href={bundleExportUrl} style={secondaryButton}>Download Full Export Bundle</a>
              <div style={exportHint}>ZIP package containing CSV, JSON, XLSX, and summary artifacts.</div>
            </div>
          </div>

          <div style={{ marginTop: "12px", color: "#6b7280", fontSize: "14px" }}>
            Phase 2 now supports live stream ingestion, vendor intelligence, SPD alerts, and autonomous agent recommendations.
          </div>
        </>
      )}
    </div>
  );
}

function Layout() {
  return (
    <BrowserRouter>
      <div
        style={{
          borderBottom: "1px solid #e5e7eb",
          padding: "12px 24px",
          background: "#ffffff",
        }}
      >
        <div
          style={{
            maxWidth: "1320px",
            margin: "0 auto",
            display: "flex",
            gap: "16px",
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <Link to="/" style={{ fontWeight: 700, textDecoration: "none", color: "#111827" }}>
            LumenAI
          </Link>
          <Link to="/history">History</Link>
        </div>
      </div>

      <Routes>
        <Route path="/" element={<DashboardHome />} />
        <Route path="/history" element={<InspectionHistory />} />
      </Routes>
    </BrowserRouter>
  );
}

const card: React.CSSProperties = {
  border: "1px solid #e5e7eb",
  borderRadius: "14px",
  padding: "20px",
  background: "#ffffff",
};

const agentCard: React.CSSProperties = {
  border: "1px solid #e5e7eb",
  borderRadius: "12px",
  padding: "14px",
  background: "#fafafa",
};

const alertCard: React.CSSProperties = {
  border: "1px solid #fecaca",
  borderRadius: "12px",
  padding: "14px",
  background: "#fff7f7",
};

const cardLabel: React.CSSProperties = {
  fontSize: "13px",
  color: "#6b7280",
  marginBottom: "10px",
};

const cardValue: React.CSSProperties = {
  fontSize: "32px",
  fontWeight: 800,
  color: "#111827",
};

const cardValueSmall: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#111827",
};

const sectionTitle: React.CSSProperties = {
  marginTop: 0,
  marginBottom: "12px",
};

const listRow: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  padding: "10px 0",
  borderBottom: "1px solid #f3f4f6",
};

const primaryButton: React.CSSProperties = {
  display: "inline-block",
  padding: "10px 14px",
  borderRadius: "10px",
  background: "#111827",
  color: "#ffffff",
  textDecoration: "none",
  fontWeight: 600,
};

const secondaryButton: React.CSSProperties = {
  display: "inline-block",
  padding: "10px 14px",
  borderRadius: "10px",
  background: "#f3f4f6",
  color: "#111827",
  textDecoration: "none",
  fontWeight: 600,
  border: "1px solid #d1d5db",
};

const secondaryButtonInline: React.CSSProperties = {
  display: "inline-block",
  padding: "6px 10px",
  borderRadius: "8px",
  background: "#f3f4f6",
  color: "#111827",
  textDecoration: "none",
  fontWeight: 600,
  border: "1px solid #d1d5db",
  fontSize: "13px",
};

const exportHint: React.CSSProperties = {
  color: "#6b7280",
  fontSize: "13px",
  marginTop: "-4px",
};

const errorBox: React.CSSProperties = {
  background: "#fee2e2",
  color: "#991b1b",
  padding: "12px 16px",
  borderRadius: "8px",
};

const muted: React.CSSProperties = {
  color: "#6b7280",
};

const table: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: "12px",
  overflow: "hidden",
};

const th: React.CSSProperties = {
  textAlign: "left",
  padding: "12px",
  fontSize: "13px",
  color: "#374151",
  whiteSpace: "nowrap",
};

const td: React.CSSProperties = {
  padding: "12px",
  fontSize: "14px",
  color: "#111827",
  verticalAlign: "top",
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Layout />
  </React.StrictMode>
);
