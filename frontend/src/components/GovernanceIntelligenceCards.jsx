import React, { useEffect, useMemo, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "https://lumen-ai-53u4.onrender.com";

function statusLabel(status) {
  if (!status) return "Unknown";
  return String(status)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function scoreTone(score) {
  if (score >= 85) return "#22c55e";
  if (score >= 70) return "#f59e0b";
  return "#ef4444";
}

export default function GovernanceIntelligenceCards() {
  const [data, setData] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadGovernanceIntelligence() {
      try {
        setLoading(true);
        setErrorMessage("");

        const [healthResponse, summaryResponse] = await Promise.all([
          fetch(`${API_BASE}/api/enterprise/governance-intelligence/health`),
          fetch(`${API_BASE}/api/enterprise/governance-intelligence/summary`),
        ]);

        if (!healthResponse.ok) {
          throw new Error(`Health request failed: ${healthResponse.status}`);
        }

        if (!summaryResponse.ok) {
          throw new Error(`Summary request failed: ${summaryResponse.status}`);
        }

        const healthJson = await healthResponse.json();
        const summaryJson = await summaryResponse.json();

        if (isMounted) {
          setHealth(healthJson);
          setData(summaryJson);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(error.message || "Unable to load governance intelligence.");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadGovernanceIntelligence();

    return () => {
      isMounted = false;
    };
  }, []);

  const signals = useMemo(() => {
    if (!data?.signals) return [];
    return [
      {
        key: "audit",
        title: "Audit Governance",
        signal: data.signals.audit,
      },
      {
        key: "capa",
        title: "CAPA Governance",
        signal: data.signals.capa,
      },
      {
        key: "vendor",
        title: "Vendor Governance",
        signal: data.signals.vendor,
      },
      {
        key: "powerbi",
        title: "Power BI Readiness",
        signal: data.signals.powerbi_readiness,
      },
    ];
  }, [data]);

  if (loading) {
    return (
      <section style={styles.panel}>
        <div style={styles.badge}>GOVERNANCE INTELLIGENCE</div>
        <h2 style={styles.title}>Loading Governance Intelligence...</h2>
        <p style={styles.muted}>Retrieving executive governance signals from the v1.1 API.</p>
      </section>
    );
  }

  if (errorMessage) {
    return (
      <section style={styles.panel}>
        <div style={styles.badge}>GOVERNANCE INTELLIGENCE</div>
        <h2 style={styles.title}>Governance Intelligence Unavailable</h2>
        <p style={styles.error}>{errorMessage}</p>
        <p style={styles.muted}>
          Confirm the backend endpoint is available at /api/enterprise/governance-intelligence/summary.
        </p>
      </section>
    );
  }

  const score = data?.governance_health_score ?? 0;

  return (
    <section style={styles.panel}>
      <div style={styles.headerRow}>
        <div>
          <div style={styles.badge}>v1.1 GOVERNANCE INTELLIGENCE</div>
          <h2 style={styles.title}>Executive Governance Intelligence</h2>
          <p style={styles.muted}>
            Converts Audit, CAPA, Vendor Governance, and Power BI readiness into executive decision support.
          </p>
        </div>

        <div style={styles.scoreCard}>
          <div style={styles.scoreLabel}>Health Score</div>
          <div style={{ ...styles.scoreValue, color: scoreTone(score) }}>{score}</div>
          <div style={styles.statusText}>{statusLabel(data?.overall_governance_status)}</div>
        </div>
      </div>

      <div style={styles.grid}>
        {signals.map(({ key, title, signal }) => (
          <div key={key} style={styles.card}>
            <div style={styles.cardTop}>
              <strong style={styles.cardTitle}>{title}</strong>
              <span style={{ ...styles.pill, borderColor: scoreTone(signal?.score || 0) }}>
                {signal?.score ?? "—"}
              </span>
            </div>
            <div style={styles.statusText}>{statusLabel(signal?.status)}</div>
            <p style={styles.cardText}>{signal?.interpretation || "No interpretation available."}</p>
          </div>
        ))}
      </div>

      <div style={styles.twoColumn}>
        <div style={styles.card}>
          <strong style={styles.cardTitle}>Executive Recommendations</strong>
          <ul style={styles.list}>
            {(data?.executive_recommendations || []).map((item, index) => (
              <li key={`rec-${index}`}>{item}</li>
            ))}
          </ul>
        </div>

        <div style={styles.card}>
          <strong style={styles.cardTitle}>Next Actions</strong>
          <ul style={styles.list}>
            {(data?.next_actions || []).map((item, index) => (
              <li key={`action-${index}`}>
                <strong>{statusLabel(item.priority)}:</strong> {item.action}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div style={styles.footer}>
        <span>Module: {health?.module || data?.module}</span>
        <span>Version: {data?.version || "v1"}</span>
        <span>Strategic Theme: Predictive Governance Intelligence</span>
      </div>
    </section>
  );
}

const styles = {
  panel: {
    marginTop: "28px",
    padding: "24px",
    borderRadius: "24px",
    border: "1px solid rgba(96, 165, 250, 0.35)",
    background: "linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(30, 41, 59, 0.95))",
    boxShadow: "0 24px 70px rgba(0,0,0,0.35)",
    color: "#ffffff",
  },
  headerRow: {
    display: "grid",
    gridTemplateColumns: "1fr minmax(160px, 220px)",
    gap: "18px",
    alignItems: "start",
  },
  badge: {
    display: "inline-block",
    padding: "6px 10px",
    borderRadius: "999px",
    border: "1px solid rgba(96, 165, 250, 0.45)",
    background: "rgba(59, 130, 246, 0.14)",
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
    color: "#cbd5e1",
    lineHeight: 1.6,
    margin: 0,
  },
  error: {
    color: "#fecaca",
    lineHeight: 1.6,
  },
  scoreCard: {
    border: "1px solid rgba(148, 163, 184, 0.35)",
    borderRadius: "20px",
    padding: "18px",
    background: "rgba(2, 6, 23, 0.45)",
    textAlign: "center",
  },
  scoreLabel: {
    color: "#94a3b8",
    fontSize: "12px",
    fontWeight: 800,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  scoreValue: {
    fontSize: "52px",
    fontWeight: 950,
    marginTop: "8px",
  },
  statusText: {
    color: "#bfdbfe",
    fontSize: "13px",
    fontWeight: 800,
    marginTop: "6px",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "16px",
    marginTop: "22px",
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
  },
  cardTop: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "12px",
  },
  cardTitle: {
    color: "#ffffff",
    fontSize: "16px",
  },
  cardText: {
    color: "#cbd5e1",
    lineHeight: 1.55,
    marginBottom: 0,
  },
  pill: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minWidth: "42px",
    padding: "6px 10px",
    borderRadius: "999px",
    border: "1px solid",
    color: "#ffffff",
    fontWeight: 900,
  },
  list: {
    color: "#cbd5e1",
    lineHeight: 1.75,
    paddingLeft: "20px",
    marginBottom: 0,
  },
  footer: {
    display: "flex",
    flexWrap: "wrap",
    gap: "12px",
    marginTop: "18px",
    color: "#94a3b8",
    fontSize: "12px",
  },
};
