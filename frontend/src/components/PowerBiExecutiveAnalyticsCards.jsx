import React, { useEffect, useMemo, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "https://lumen-ai-53u4.onrender.com";

function titleCase(value) {
  if (!value) return "Unknown";
  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function statusTone(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized.includes("ready") || normalized.includes("controlled")) return "#22c55e";
  if (normalized.includes("watch")) return "#f59e0b";
  if (normalized.includes("required") || normalized.includes("high")) return "#ef4444";
  return "#38bdf8";
}

function priorityTone(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized.includes("executive")) return "#ef4444";
  if (normalized.includes("leadership")) return "#f59e0b";
  if (normalized.includes("manager")) return "#38bdf8";
  return "#22c55e";
}

export default function PowerBiExecutiveAnalyticsCards() {
  const [health, setHealth] = useState(null);
  const [summary, setSummary] = useState(null);
  const [dictionary, setDictionary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const csvUrl = `${API_BASE}/api/v1-2/power-bi/executive-analytics/export.csv`;
  const dictionaryUrl = `${API_BASE}/api/v1-2/power-bi/executive-analytics/data-dictionary`;

  useEffect(() => {
    let mounted = true;

    async function loadPowerBiAnalytics() {
      try {
        setLoading(true);
        setErrorMessage("");

        const [healthResponse, summaryResponse, dictionaryResponse] = await Promise.all([
          fetch(`${API_BASE}/api/v1-2/power-bi/executive-analytics/health`),
          fetch(`${API_BASE}/api/v1-2/power-bi/executive-analytics/summary`),
          fetch(dictionaryUrl),
        ]);

        if (!healthResponse.ok) {
          throw new Error(`Health request failed: ${healthResponse.status}`);
        }

        if (!summaryResponse.ok) {
          throw new Error(`Summary request failed: ${summaryResponse.status}`);
        }

        if (!dictionaryResponse.ok) {
          throw new Error(`Data dictionary request failed: ${dictionaryResponse.status}`);
        }

        const healthJson = await healthResponse.json();
        const summaryJson = await summaryResponse.json();
        const dictionaryJson = await dictionaryResponse.json();

        if (mounted) {
          setHealth(healthJson);
          setSummary(summaryJson);
          setDictionary(dictionaryJson);
        }
      } catch (error) {
        if (mounted) {
          setErrorMessage(error.message || "Unable to load Power BI Executive Analytics.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadPowerBiAnalytics();

    return () => {
      mounted = false;
    };
  }, [dictionaryUrl]);

  const rows = summary?.rows || [];

  const topRows = useMemo(() => {
    return [...rows]
      .sort((a, b) => {
        const aPriority = String(a.executive_priority || "").includes("executive") ? 0 : 1;
        const bPriority = String(b.executive_priority || "").includes("executive") ? 0 : 1;
        return aPriority - bPriority || String(a.domain).localeCompare(String(b.domain));
      })
      .slice(0, 6);
  }, [rows]);

  if (loading) {
    return (
      <section style={styles.panel}>
        <div style={styles.badge}>v1.2 POWER BI ANALYTICS</div>
        <h2 style={styles.title}>Loading Power BI Executive Analytics...</h2>
        <p style={styles.muted}>Retrieving CSV export readiness, data dictionary, and unified executive governance dataset.</p>
      </section>
    );
  }

  if (errorMessage) {
    return (
      <section style={styles.panel}>
        <div style={styles.badge}>v1.2 POWER BI ANALYTICS</div>
        <h2 style={styles.title}>Power BI Executive Analytics Unavailable</h2>
        <p style={styles.error}>{errorMessage}</p>
        <p style={styles.muted}>
          Confirm the backend endpoint is available at /api/v1-2/power-bi/executive-analytics/summary.
        </p>
      </section>
    );
  }

  const readinessStatus = summary?.power_bi_readiness_status || "unknown";

  return (
    <section style={styles.panel}>
      <div style={styles.headerRow}>
        <div>
          <div style={styles.badge}>v1.2 POWER BI ANALYTICS</div>
          <h2 style={styles.title}>Power BI Executive Analytics</h2>
          <p style={styles.muted}>
            Converts Governance Intelligence, CAPA Predictive Risk, and Vendor Performance metrics into a Power BI-ready executive dataset.
          </p>
        </div>

        <div style={styles.readinessCard}>
          <div style={styles.readinessLabel}>Power BI Readiness</div>
          <div style={{ ...styles.readinessValue, color: statusTone(readinessStatus) }}>
            {titleCase(readinessStatus)}
          </div>
          <div style={styles.smallText}>{summary?.dataset_name || "Executive governance dataset"}</div>
        </div>
      </div>

      <div style={styles.metricGrid}>
        <MetricCard label="Rows" value={summary?.row_count ?? 0} tone="#38bdf8" />
        <MetricCard label="Domains" value={summary?.domain_count ?? 0} tone="#22c55e" />
        <MetricCard label="Action Required" value={summary?.action_required_count ?? 0} tone="#ef4444" />
        <MetricCard label="Executive Review" value={summary?.executive_review_count ?? 0} tone="#f59e0b" />
        <MetricCard label="High Risk" value={summary?.high_risk_count ?? 0} tone="#ef4444" />
        <MetricCard label="Dictionary Fields" value={dictionary?.field_count ?? 0} tone="#a78bfa" />
      </div>

      <div style={styles.twoColumn}>
        <div style={styles.card}>
          <strong style={styles.cardTitle}>Power BI Export Links</strong>
          <p style={styles.cardText}>
            Use these links to validate export readiness or connect to Power BI web/CSV ingestion workflows.
          </p>
          <div style={styles.buttonRow}>
            <a style={styles.button} href={csvUrl} target="_blank" rel="noreferrer">
              Open CSV Export
            </a>
            <a style={styles.button} href={dictionaryUrl} target="_blank" rel="noreferrer">
              Open Data Dictionary
            </a>
          </div>
        </div>

        <div style={styles.card}>
          <strong style={styles.cardTitle}>Available Exports</strong>
          <ul style={styles.list}>
            {(summary?.available_exports || []).map((item, index) => (
              <li key={`export-${index}`}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTop}>
          <strong style={styles.cardTitle}>Executive Dataset Preview</strong>
          <span style={styles.smallPill}>{topRows.length} metric rows shown</span>
        </div>

        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Domain</th>
                <th style={styles.th}>Metric</th>
                <th style={styles.th}>Value</th>
                <th style={styles.th}>Status</th>
                <th style={styles.th}>Risk</th>
                <th style={styles.th}>Priority</th>
              </tr>
            </thead>
            <tbody>
              {topRows.map((row) => (
                <tr key={`${row.domain}-${row.metric_key}`}>
                  <td style={styles.td}>{titleCase(row.domain)}</td>
                  <td style={styles.td}>{row.metric_label}</td>
                  <td style={styles.tdStrong}>{row.metric_value}</td>
                  <td style={{ ...styles.td, color: statusTone(row.status) }}>{titleCase(row.status)}</td>
                  <td style={{ ...styles.td, color: statusTone(row.risk_band) }}>{titleCase(row.risk_band)}</td>
                  <td style={{ ...styles.td, color: priorityTone(row.executive_priority) }}>
                    {titleCase(row.executive_priority)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={styles.twoColumn}>
        <div style={styles.card}>
          <strong style={styles.cardTitle}>Executive Recommendations</strong>
          <ul style={styles.list}>
            {(summary?.executive_recommendations || []).map((item, index) => (
              <li key={`powerbi-rec-${index}`}>{item}</li>
            ))}
          </ul>
        </div>

        <div style={styles.card}>
          <strong style={styles.cardTitle}>Next Actions</strong>
          <ul style={styles.list}>
            {(summary?.next_actions || []).map((item, index) => (
              <li key={`powerbi-action-${index}`}>
                <strong>{titleCase(item.priority)}:</strong> {item.action}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div style={styles.footer}>
        <span>Module: {health?.module || summary?.module}</span>
        <span>Product phase: {summary?.product_phase || "v1.2"}</span>
        <span>Theme: Executive Governance Intelligence → Power BI Analytics → CSV Export Readiness</span>
      </div>
    </section>
  );
}

function MetricCard({ label, value, tone }) {
  return (
    <div style={styles.metricCard}>
      <div style={styles.metricLabel}>{label}</div>
      <div style={{ ...styles.metricValue, color: tone }}>{value}</div>
    </div>
  );
}

const styles = {
  panel: {
    marginTop: "28px",
    padding: "24px",
    borderRadius: "24px",
    border: "1px solid rgba(96, 165, 250, 0.35)",
    background: "linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(30, 64, 175, 0.56))",
    boxShadow: "0 24px 70px rgba(0,0,0,0.35)",
    color: "#ffffff",
  },
  headerRow: {
    display: "grid",
    gridTemplateColumns: "1fr minmax(220px, 300px)",
    gap: "18px",
    alignItems: "start",
  },
  badge: {
    display: "inline-block",
    padding: "6px 10px",
    borderRadius: "999px",
    border: "1px solid rgba(96, 165, 250, 0.45)",
    background: "rgba(96, 165, 250, 0.14)",
    color: "#bfdbfe",
    fontSize: "12px",
    fontWeight: 900,
    letterSpacing: "0.08em",
  },
  title: {
    margin: "12px 0 8px",
    fontSize: "28px",
    lineHeight: 1.15,
  },
  muted: {
    color: "#e2e8f0",
    lineHeight: 1.6,
    margin: 0,
  },
  error: {
    color: "#fecaca",
    lineHeight: 1.6,
  },
  readinessCard: {
    border: "1px solid rgba(96, 165, 250, 0.35)",
    borderRadius: "20px",
    padding: "18px",
    background: "rgba(2, 6, 23, 0.45)",
    textAlign: "center",
  },
  readinessLabel: {
    color: "#bfdbfe",
    fontSize: "12px",
    fontWeight: 800,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  readinessValue: {
    fontSize: "34px",
    fontWeight: 950,
    marginTop: "12px",
  },
  smallText: {
    color: "#cbd5e1",
    fontSize: "12px",
    marginTop: "8px",
    overflowWrap: "anywhere",
  },
  metricGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(145px, 1fr))",
    gap: "14px",
    marginTop: "22px",
  },
  metricCard: {
    border: "1px solid rgba(148, 163, 184, 0.25)",
    borderRadius: "18px",
    padding: "16px",
    background: "rgba(2, 6, 23, 0.38)",
    textAlign: "center",
  },
  metricLabel: {
    color: "#cbd5e1",
    fontSize: "12px",
    fontWeight: 900,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  metricValue: {
    marginTop: "8px",
    fontSize: "32px",
    fontWeight: 950,
  },
  twoColumn: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: "16px",
    marginTop: "16px",
  },
  card: {
    border: "1px solid rgba(148, 163, 184, 0.28)",
    borderRadius: "20px",
    padding: "18px",
    background: "rgba(2, 6, 23, 0.42)",
    marginTop: "16px",
  },
  cardTop: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "12px",
    marginBottom: "14px",
  },
  cardTitle: {
    color: "#ffffff",
    fontSize: "16px",
  },
  cardText: {
    color: "#cbd5e1",
    lineHeight: 1.55,
  },
  buttonRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: "10px",
    marginTop: "14px",
  },
  button: {
    display: "inline-flex",
    padding: "10px 12px",
    borderRadius: "12px",
    background: "rgba(96, 165, 250, 0.18)",
    border: "1px solid rgba(96, 165, 250, 0.4)",
    color: "#bfdbfe",
    fontWeight: 900,
    textDecoration: "none",
  },
  list: {
    color: "#e2e8f0",
    lineHeight: 1.75,
    paddingLeft: "20px",
    marginBottom: 0,
  },
  smallPill: {
    display: "inline-flex",
    padding: "6px 10px",
    borderRadius: "999px",
    background: "rgba(96, 165, 250, 0.14)",
    color: "#bfdbfe",
    fontSize: "12px",
    fontWeight: 900,
  },
  tableWrap: {
    overflowX: "auto",
    marginTop: "10px",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    minWidth: "760px",
  },
  th: {
    textAlign: "left",
    color: "#bfdbfe",
    fontSize: "12px",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    padding: "10px",
    borderBottom: "1px solid rgba(148, 163, 184, 0.3)",
  },
  td: {
    color: "#e2e8f0",
    padding: "10px",
    borderBottom: "1px solid rgba(148, 163, 184, 0.18)",
    fontSize: "13px",
  },
  tdStrong: {
    color: "#ffffff",
    padding: "10px",
    borderBottom: "1px solid rgba(148, 163, 184, 0.18)",
    fontSize: "14px",
    fontWeight: 950,
  },
  footer: {
    display: "flex",
    flexWrap: "wrap",
    gap: "12px",
    marginTop: "18px",
    color: "#cbd5e1",
    fontSize: "12px",
  },
};
