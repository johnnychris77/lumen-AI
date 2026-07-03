import React, { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";

function titleCase(value) {
  if (!value) return "Unknown";
  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function scoreTone(score) {
  if (score >= 85) return "#22c55e";
  if (score >= 70) return "#38bdf8";
  if (score >= 50) return "#f59e0b";
  return "#ef4444";
}

function priorityTone(priority) {
  if (!priority) return "#94a3b8";
  const normalized = String(priority).toLowerCase();
  if (normalized.includes("executive")) return "#ef4444";
  if (normalized.includes("leadership")) return "#f59e0b";
  if (normalized.includes("manager")) return "#38bdf8";
  return "#22c55e";
}

export default function VendorPerformanceScorecardCards() {
  const [data, setData] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let mounted = true;

    async function loadVendorPerformance() {
      try {
        setLoading(true);
        setErrorMessage("");

        const [healthResponse, scorecardResponse] = await Promise.all([
          apiFetch(`/api/enterprise/vendor-governance/performance-scorecard/health`, { raw: true }),
          apiFetch(`/api/enterprise/vendor-governance/performance-scorecard/`, { raw: true }),
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
          setErrorMessage(error.message || "Unable to load Vendor Performance Scorecard.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadVendorPerformance();

    return () => {
      mounted = false;
    };
  }, []);

  const topVendors = useMemo(() => {
    return [...(data?.vendor_performance_items || [])]
      .sort((a, b) => (a.vendor_score || 0) - (b.vendor_score || 0))
      .slice(0, 4);
  }, [data]);

  if (loading) {
    return (
      <section style={styles.panel}>
        <div style={styles.badge}>VENDOR PERFORMANCE</div>
        <h2 style={styles.title}>Loading Vendor Performance Scorecard...</h2>
        <p style={styles.muted}>Retrieving vendor performance scoring and executive accountability signals.</p>
      </section>
    );
  }

  if (errorMessage) {
    return (
      <section style={styles.panel}>
        <div style={styles.badge}>VENDOR PERFORMANCE</div>
        <h2 style={styles.title}>Vendor Performance Scorecard Unavailable</h2>
        <p style={styles.error}>{errorMessage}</p>
        <p style={styles.muted}>
          Confirm the backend endpoint is available at /api/enterprise/vendor-governance/performance-scorecard/.
        </p>
      </section>
    );
  }

  const averageScore = data?.average_vendor_score ?? 0;
  const status = data?.overall_vendor_performance_status || "unknown";

  return (
    <section style={styles.panel}>
      <div style={styles.headerRow}>
        <div>
          <div style={styles.badge}>v1.1 VENDOR PERFORMANCE</div>
          <h2 style={styles.title}>Vendor Performance Scorecard</h2>
          <p style={styles.muted}>
            Converts vendor events, repeat issues, CAPA linkage, and unresolved findings into executive vendor accountability.
          </p>
        </div>

        <div style={styles.scoreCard}>
          <div style={styles.scoreLabel}>Average Vendor Score</div>
          <div style={{ ...styles.scoreValue, color: scoreTone(averageScore) }}>{averageScore}</div>
          <div style={{ ...styles.statusText, color: priorityTone(status) }}>{titleCase(status)}</div>
        </div>
      </div>

      <div style={styles.metricGrid}>
        <MetricCard label="High Risk Vendors" value={data?.high_risk_vendor_count ?? 0} tone="#ef4444" />
        <MetricCard label="Repeat Event Vendors" value={data?.repeat_event_vendor_count ?? 0} tone="#f59e0b" />
        <MetricCard label="CAPA Linked Vendors" value={data?.capa_linked_vendor_count ?? 0} tone="#38bdf8" />
        <MetricCard label="Executive Review" value={data?.executive_review_count ?? 0} tone="#ef4444" />
        <MetricCard label="Leadership Watch" value={data?.leadership_watch_count ?? 0} tone="#f59e0b" />
      </div>

      <div style={styles.card}>
        <div style={styles.cardTop}>
          <strong style={styles.cardTitle}>Vendor Accountability Watchlist</strong>
          <span style={styles.smallPill}>{topVendors.length} vendors shown</span>
        </div>

        <div style={styles.itemList}>
          {topVendors.map((item) => (
            <div key={item.vendor_name} style={styles.vendorItem}>
              <div style={styles.itemHeader}>
                <strong>{item.vendor_name}</strong>
                <span style={{ ...styles.pill, borderColor: scoreTone(item.vendor_score) }}>
                  {item.vendor_score}
                </span>
              </div>
              <div style={styles.itemMeta}>
                <span>{titleCase(item.performance_band)}</span>
                <span style={{ color: priorityTone(item.governance_priority) }}>
                  {titleCase(item.governance_priority)}
                </span>
                <span>{item.unresolved_events} unresolved</span>
                <span>{item.capa_linked_events} CAPA-linked</span>
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
              <li key={`vendor-rec-${index}`}>{item}</li>
            ))}
          </ul>
        </div>

        <div style={styles.card}>
          <strong style={styles.cardTitle}>Next Actions</strong>
          <ul style={styles.list}>
            {(data?.next_actions || []).map((item, index) => (
              <li key={`vendor-action-${index}`}>
                <strong>{titleCase(item.priority)}:</strong> {item.action}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div style={styles.footer}>
        <span>Module: {health?.module || data?.module}</span>
        <span>Version: {data?.version || "v1"}</span>
        <span>Theme: Vendor Governance → Vendor Performance Scoring → Executive Accountability</span>
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
    border: "1px solid rgba(34, 197, 94, 0.35)",
    background: "linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(20, 83, 45, 0.55))",
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
    border: "1px solid rgba(34, 197, 94, 0.45)",
    background: "rgba(34, 197, 94, 0.14)",
    color: "#bbf7d0",
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
    border: "1px solid rgba(34, 197, 94, 0.35)",
    borderRadius: "20px",
    padding: "18px",
    background: "rgba(2, 6, 23, 0.45)",
    textAlign: "center",
  },
  scoreLabel: {
    color: "#bbf7d0",
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
  vendorItem: {
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
  itemMeta: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
    marginTop: "8px",
    color: "#bbf7d0",
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
    background: "rgba(34, 197, 94, 0.14)",
    color: "#bbf7d0",
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
