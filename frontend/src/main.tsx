import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import InspectionHistory from "./pages/InspectionHistory";

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

function formatDate(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function statusPill(status) {
  const base = {
    display: "inline-block",
    padding: "4px 10px",
    borderRadius: "999px",
    fontSize: "12px",
    fontWeight: 700,
  };

  switch ((status || "").toLowerCase()) {
    case "completed":
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

function DashboardHome() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const token = useMemo(() => localStorage.getItem("token") || "dev-token", []);

  useEffect(() => {
    let ignore = false;

    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const res = await fetch(`${API_BASE}/history?limit=8`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(`Dashboard request failed (${res.status}): ${text}`);
        }

        const data = await res.json();
        const normalized = Array.isArray(data) ? data : data.items || [];

        if (!ignore) {
          setItems(normalized);
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message || "Failed to load dashboard data.");
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

  const total = items.length;
  const completed = items.filter((x) => String(x.status).toLowerCase() === "completed").length;
  const pending = items.filter((x) =>
    ["queued", "running"].includes(String(x.status).toLowerCase())
  ).length;
  const reportsReady = items.filter((x) => String(x.status).toLowerCase() === "completed").length;

  return (
    <div style={{ padding: "24px", maxWidth: "1200px", margin: "0 auto" }}>
      <section
        style={{
          background: "linear-gradient(135deg, #111827, #1f2937)",
          color: "white",
          borderRadius: "20px",
          padding: "28px",
          marginBottom: "24px",
        }}
      >
        <div style={{ maxWidth: "760px" }}>
          <div
            style={{
              display: "inline-block",
              padding: "6px 10px",
              borderRadius: "999px",
              background: "rgba(255,255,255,0.12)",
              fontSize: "12px",
              fontWeight: 700,
              marginBottom: "14px",
            }}
          >
            Executive Demo Dashboard
          </div>
          <h1 style={{ margin: "0 0 10px 0", fontSize: "34px", lineHeight: 1.15 }}>
            LumenAI
          </h1>
          <p style={{ margin: 0, color: "#d1d5db", fontSize: "16px", lineHeight: 1.6 }}>
            AI-powered instrument inspection workflow with asynchronous analysis,
            model traceability, operational history, and report-ready outputs.
          </p>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "20px" }}>
            <Link to="/history" style={primaryHeroButton}>
              View Inspection History
            </Link>
            <a href="/api/health" target="_blank" rel="noreferrer" style={secondaryHeroButton}>
              System Health
            </a>
          </div>
        </div>
      </section>

      <section
        style={{
          display: "grid",
          gap: "16px",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          marginBottom: "24px",
        }}
      >
        <MetricCard label="Recent Inspections" value={String(total)} help="Latest dashboard sample" />
        <MetricCard label="Completed Analyses" value={String(completed)} help="Finished processing jobs" />
        <MetricCard label="Pending Queue" value={String(pending)} help="Queued or running jobs" />
        <MetricCard label="Reports Available" value={String(reportsReady)} help="Completed report-ready items" />
      </section>

      <section
        style={{
          display: "grid",
          gap: "16px",
          gridTemplateColumns: "2fr 1fr",
          alignItems: "start",
        }}
      >
        <div style={panel}>
          <div style={panelHeader}>
            <div>
              <h2 style={{ margin: 0 }}>Recent Inspections</h2>
              <p style={panelSubtext}>
                Most recent async analyses with model output and status visibility.
              </p>
            </div>
            <Link to="/history">Open full history</Link>
          </div>

          {loading && <p>Loading dashboard data...</p>}

          {!loading && error && (
            <div style={errorBox}>
              {error}
            </div>
          )}

          {!loading && !error && items.length === 0 && (
            <div style={emptyBox}>
              No inspections found yet.
            </div>
          )}

          {!loading && !error && items.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  background: "#fff",
                }}
              >
                <thead style={{ background: "#f9fafb" }}>
                  <tr>
                    <th style={th}>ID</th>
                    <th style={th}>File</th>
                    <th style={th}>Status</th>
                    <th style={th}>Confidence</th>
                    <th style={th}>Material</th>
                    <th style={th}>Model</th>
                    <th style={th}>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} style={{ borderTop: "1px solid #e5e7eb" }}>
                      <td style={td}>{item.id}</td>
                      <td style={td}>{item.file_name || "—"}</td>
                      <td style={td}>
                        <span style={statusPill(item.status)}>{item.status || "unknown"}</span>
                      </td>
                      <td style={td}>
                        {typeof item.confidence === "number" ? item.confidence.toFixed(2) : "—"}
                      </td>
                      <td style={td}>{item.material_type || "—"}</td>
                      <td style={td}>
                        <div>{item.model_name || "—"}</div>
                        <div style={{ color: "#6b7280", fontSize: "12px" }}>
                          v{item.model_version || "—"}
                        </div>
                      </td>
                      <td style={td}>{formatDate(item.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div style={{ display: "grid", gap: "16px" }}>
          <div style={panel}>
            <h2 style={{ marginTop: 0 }}>Demo Story</h2>
            <p style={panelSubtext}>
              LumenAI demonstrates a complete workflow from upload through
              asynchronous analysis, model traceability, history review, and PDF report access.
            </p>
            <ul style={{ paddingLeft: "18px", marginBottom: 0, color: "#374151", lineHeight: 1.7 }}>
              <li>Async queue-backed processing</li>
              <li>Model metadata traceability</li>
              <li>Operational history visibility</li>
              <li>Report-ready inspection outputs</li>
            </ul>
          </div>

          <div style={panel}>
            <h2 style={{ marginTop: 0 }}>Quick Actions</h2>
            <div style={{ display: "grid", gap: "10px" }}>
              <Link to="/history" style={actionTile}>View Full Inspection History</Link>
              <a href="/api/health" target="_blank" rel="noreferrer" style={actionTile}>Check API Health</a>
              <a href="/docs" target="_blank" rel="noreferrer" style={actionTile}>Open API Docs</a>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function MetricCard({ label, value, help }) {
  return (
    <div style={metricCard}>
      <div style={{ color: "#6b7280", fontSize: "13px", marginBottom: "8px" }}>{label}</div>
      <div style={{ fontSize: "32px", fontWeight: 800, color: "#111827", marginBottom: "6px" }}>
        {value}
      </div>
      <div style={{ color: "#6b7280", fontSize: "13px" }}>{help}</div>
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
            maxWidth: "1200px",
            margin: "0 auto",
            display: "flex",
            gap: "16px",
            alignItems: "center",
          }}
        >
          <Link to="/" style={{ fontWeight: 800, textDecoration: "none", color: "#111827" }}>
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

const metricCard = {
  border: "1px solid #e5e7eb",
  borderRadius: "16px",
  padding: "18px",
  background: "#fff",
};

const panel = {
  border: "1px solid #e5e7eb",
  borderRadius: "16px",
  padding: "20px",
  background: "#fff",
};

const panelHeader = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
  marginBottom: "12px",
};

const panelSubtext = {
  color: "#6b7280",
  marginTop: "6px",
  marginBottom: 0,
  lineHeight: 1.6,
};

const errorBox = {
  background: "#fee2e2",
  color: "#991b1b",
  padding: "12px 16px",
  borderRadius: "8px",
};

const emptyBox = {
  background: "#f9fafb",
  border: "1px solid #e5e7eb",
  padding: "16px",
  borderRadius: "8px",
};

const th = {
  textAlign: "left",
  padding: "12px",
  fontSize: "13px",
  color: "#374151",
  whiteSpace: "nowrap",
};

const td = {
  padding: "12px",
  fontSize: "14px",
  color: "#111827",
  verticalAlign: "top",
};

const primaryHeroButton = {
  display: "inline-block",
  padding: "10px 14px",
  borderRadius: "10px",
  background: "#ffffff",
  color: "#111827",
  textDecoration: "none",
  fontWeight: 700,
};

const secondaryHeroButton = {
  display: "inline-block",
  padding: "10px 14px",
  borderRadius: "10px",
  background: "rgba(255,255,255,0.08)",
  color: "#ffffff",
  textDecoration: "none",
  border: "1px solid rgba(255,255,255,0.18)",
  fontWeight: 700,
};

const actionTile = {
  display: "block",
  padding: "12px 14px",
  borderRadius: "10px",
  background: "#f9fafb",
  border: "1px solid #e5e7eb",
  textDecoration: "none",
  color: "#111827",
  fontWeight: 600,
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Layout />
  </React.StrictMode>
);
