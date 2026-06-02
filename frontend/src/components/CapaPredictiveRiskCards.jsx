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

function scoreTone(score) {
  if (score >= 85) return "#ef4444";
  if (score >= 70) return "#f59e0b";
  if (score >= 50) return "#38bdf8";
  return "#22c55e";
}

function statusTone(status) {
  if (!status) return "#94a3b8";
  const normalized = String(status).toLowerCase();
  if (normalized.includes("action") || normalized.includes("critical")) return "#ef4444";
  if (normalized.includes("watch") || normalized.includes("high")) return "#f59e0b";
  if (normalized.includes("controlled")) return "#22c55e";
  return "#38bdf8";
}

export default function CapaPredictiveRiskCards() {
  const [data, setData] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let mounted = true;

    async function loadCapaRisk() {
      try {
        setLoading(true);
        setErrorMessage("");

        const [healthResponse, scorecardResponse] = await Promise.all([
          fetch(`${API_BASE}/api/capa/risk-scorecard/health`),
          fetch(`${API_BASE}/api/capa/risk-scorecard/`),
        ]);

        if (!healthResponse.ok) {
          throw new Error(`Health request failed: ${healthResponse.status}`);
        }

        if (!scorecardResponse.ok) {
          throw new Error(`Scorecard request failed: ${scorecardResponse.status}`);
        }

        const healthJson = await healthResponse.json();
        const scorecardJson = await scorecardResponse.json();

        if (mounted) {
          setHealth(healthJson);
          setData(scorecardJson);
        }
      } catch (error) {
        if (mounted) {
          setErrorMessage(error.message || "Unable to load CAPA predictive risk scorecard.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadCapaRisk();

    return () => {
      mounted = false;
    };
  }, []);

  const topRiskItems = useMemo(() => {
    return [...(data?.capa_risk_items || [])]
      .sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0))
      .slice(0, 4);
  }, [data]);

  if (loading) {
    return (
      <section style={styles.panel}>
        <div style={styles.badge}>CAPA PREDICTIVE RISK</div>
        <h2 style={styles.title}>Loading CAPA Predictive Risk Scorecard...</h2>
        <p style={styles.muted}>Retrieving CAPA risk scoring and executive prioritization signals.</p>
      </section>
    );
  }

  if (errorMessage) {
    return (
      <section style={styles.panel}>
        <div style={styles.badge}>CAPA PREDICTIVE RISK</div>
        <h2 style={styles.title}>CAPA Predictive Risk Unavailable</h2>
        <p style={styles.error}>{errorMessage}</p>
        <p style={styles.muted}>
          Confirm the backend endpoint is available at /api/capa/risk-scorecard/.
        </p>
      </section>
    );
  }

  const averageScore = data?.average_risk_score ?? 0;
  const status = data?.overall_capa_risk_status || "unknown";

  return (
    <section style={styles.panel}>
      <div style={styles.headerRow}>
        <div>
          <div style={styles.badge}>v1.1 CAPA PREDICTIVE RISK</div>
          <h2 style={styles.title}>CAPA Predictive Risk Scorecard</h2>
          <p style={styles.muted}>
            Prioritizes CAPAs by risk score, overdue status, executive priority, and recommended action.
          </p>
        </div>

        <div style={styles.scoreCard}>
          <div style={styles.scoreLabel}>Average Risk Score</div>
          <div style={{ ...styles.scoreValue, color: scoreTone(averageScore) }}>{averageScore}</div>
          <div style={{ ...styles.statusText, color: statusTone(status) }}>{titleCase(status)}</div>
        </div>
      </div>

      <div style={styles.metricGrid}>
        <MetricCard label="High Priority" value={data?.high_priority_count ?? 0} tone="#f59e0b" />
        <MetricCard label="Overdue" value={data?.overdue_count ?? 0} tone="#ef4444" />
        <MetricCard label="Critical" value={data?.critical_count ?? 0} tone="#ef4444" />
        <MetricCard label="Watch" value={data?.watch_count ?? 0} tone="#38bdf8" />
      </div>

      <div style={styles.card}>
        <div style={styles.cardTop}>
          <strong style={styles.cardTitle}>Top CAPA Risk Items</strong>
          <span style={styles.smallPill}>{topRiskItems.length} items shown</span>
        </div>

        <div style={styles.itemList}>
          {topRiskItems.map((item) => (
            <div key={item.capa_id} style={styles.riskItem}>
              <div style={styles.itemHeader}>
                <strong>{item.capa_id}</strong>
                <span style={{ ...styles.pill, borderColor: scoreTone(item.risk_score) }}>
                  {item.risk_score}
                </span>
              </div>
              <div style={styles.itemTitle}>{item.title}</div>
              <div style={styles.itemMeta}>
                <span>{titleCase(item.risk_band)}</span>
                <span>{titleCase(item.executive_priority)}</span>
                <span>{item.is_overdue ? "Overdue" : `${item.days_to_due} days to due`}</span>
              </div>
              <p style={styles.cardText}>{item.recommended_action}</p>
            </div>
          ))}
        </div>
      </div>

      <div style={styles.twoColumn}>
        <div style={styles.card}>
          <strong style={styles.cardTitle}>Executive Recommendations</strong>
          <ul style={styles.list}>
            {(data?.executive_recommendations || []).map((item, index) => (
              <li key={`capa-rec-${index}`}>{item}</li>
            ))}
          </ul>
        </div>

        <div style={styles.card}>
          <strong style={styles.cardTitle}>Next Actions</strong>
          <ul style={styles.list}>
            {(data?.next_actions || []).map((item, index) => (
              <li key={`capa-action-${index}`}>
                <strong>{titleCase(item.priority)}:</strong> {item.action}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div style={styles.footer}>
        <span>Module: {health?.module || data?.module}</span>
        <span>Version: {data?.version || "v1"}</span>
        <span>Theme: CAPA Governance → Predictive Risk Scoring → Executive Prioritization</span>
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
    border: "1px solid rgba(248, 113, 113, 0.35)",
    background: "linear-gradient(135deg, rgba(30, 41, 59, 0.98), rgba(127, 29, 29, 0.55))",
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
    border: "1px solid rgba(248, 113, 113, 0.45)",
    background: "rgba(239, 68, 68, 0.14)",
    color: "#fecaca",
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
  scoreCard: {
    border: "1px solid rgba(248, 113, 113, 0.35)",
    borderRadius: "20px",
    padding: "18px",
    background: "rgba(2, 6, 23, 0.45)",
    textAlign: "center",
  },
  scoreLabel: {
    color: "#fecaca",
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
    fontSize: "13px",
    fontWeight: 900,
    marginTop: "6px",
  },
  metricGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
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
    marginBottom: 0,
  },
  itemList: {
    display: "grid",
    gap: "12px",
  },
  riskItem: {
    border: "1px solid rgba(148, 163, 184, 0.22)",
    borderRadius: "16px",
    padding: "14px",
    background: "rgba(15, 23, 42, 0.55)",
  },
  itemHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "10px",
  },
  itemTitle: {
    color: "#f8fafc",
    marginTop: "6px",
    fontWeight: 800,
  },
  itemMeta: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
    marginTop: "8px",
    color: "#fecaca",
    fontSize: "12px",
    fontWeight: 800,
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
  smallPill: {
    display: "inline-flex",
    padding: "6px 10px",
    borderRadius: "999px",
    background: "rgba(248, 113, 113, 0.14)",
    color: "#fecaca",
    fontSize: "12px",
    fontWeight: 900,
  },
  list: {
    color: "#e2e8f0",
    lineHeight: 1.75,
    paddingLeft: "20px",
    marginBottom: 0,
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
