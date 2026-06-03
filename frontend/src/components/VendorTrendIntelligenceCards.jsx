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

  if (normalized.includes("executive") || normalized.includes("worsening") || normalized.includes("high")) {
    return "#ef4444";
  }

  if (normalized.includes("leadership") || normalized.includes("watch")) {
    return "#f59e0b";
  }

  if (normalized.includes("improving") || normalized.includes("controlled")) {
    return "#22c55e";
  }

  return "#38bdf8";
}

function deltaLabel(delta) {
  if (delta > 0) return `+${delta}`;
  return String(delta ?? 0);
}

export default function VendorTrendIntelligenceCards() {
  const [health, setHealth] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const csvUrl = `${API_BASE}/api/v1-2/vendor/trend-intelligence/export.csv`;

  useEffect(() => {
    let mounted = true;

    async function loadVendorTrendIntelligence() {
      try {
        setLoading(true);
        setErrorMessage("");

        const [healthResponse, summaryResponse] = await Promise.all([
          fetch(`${API_BASE}/api/v1-2/vendor/trend-intelligence/health`),
          fetch(`${API_BASE}/api/v1-2/vendor/trend-intelligence/summary`),
        ]);

        if (!healthResponse.ok) {
          throw new Error(`Health request failed: ${healthResponse.status}`);
        }

        if (!summaryResponse.ok) {
          throw new Error(`Summary request failed: ${summaryResponse.status}`);
        }

        const healthJson = await healthResponse.json();
        const summaryJson = await summaryResponse.json();

        if (mounted) {
          setHealth(healthJson);
          setSummary(summaryJson);
        }
      } catch (error) {
        if (mounted) {
          setErrorMessage(error.message || "Unable to load Vendor Trend Intelligence.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadVendorTrendIntelligence();

    return () => {
      mounted = false;
    };
  }, []);

  const topVendorItems = useMemo(() => {
    return [...(summary?.vendor_trend_items || [])]
      .sort((a, b) => (a.current_vendor_score || 0) - (b.current_vendor_score || 0))
      .slice(0, 5);
  }, [summary]);

  if (loading) {
    return (
      <section style={styles.panel}>
        <div style={styles.badge}>v1.2 VENDOR TREND INTELLIGENCE</div>
        <h2 style={styles.title}>Loading Vendor Trend Intelligence...</h2>
        <p style={styles.muted}>Retrieving vendor score movement, repeat events, CAPA linkage, and executive review signals.</p>
      </section>
    );
  }

  if (errorMessage) {
    return (
      <section style={styles.panel}>
        <div style={styles.badge}>v1.2 VENDOR TREND INTELLIGENCE</div>
        <h2 style={styles.title}>Vendor Trend Intelligence Unavailable</h2>
        <p style={styles.error}>{errorMessage}</p>
        <p style={styles.muted}>
          Confirm the backend endpoint is available at /api/v1-2/vendor/trend-intelligence/summary.
        </p>
      </section>
    );
  }

  const trendStatus = summary?.vendor_trend_status || "unknown";
  const scoreDelta = summary?.vendor_score_delta ?? 0;

  return (
    <section style={styles.panel}>
      <div style={styles.headerRow}>
        <div>
          <div style={styles.badge}>v1.2 VENDOR TREND INTELLIGENCE</div>
          <h2 style={styles.title}>Vendor Trend Intelligence</h2>
          <p style={styles.muted}>
            Converts vendor score movement, repeat events, high-risk recurrence, and CAPA linkage into executive vendor governance intelligence.
          </p>
        </div>

        <div style={styles.statusCard}>
          <div style={styles.statusLabel}>Vendor Trend Status</div>
          <div style={{ ...styles.statusValue, color: statusTone(trendStatus) }}>
            {titleCase(trendStatus)}
          </div>
          <div style={styles.smallText}>{titleCase(summary?.trend_window)}</div>
        </div>
      </div>

      <div style={styles.metricGrid}>
        <MetricCard label="Average Vendor Score" value={summary?.average_vendor_score ?? 0} tone="#f59e0b" />
        <MetricCard label="Prior Average" value={summary?.prior_average_vendor_score ?? 0} tone="#38bdf8" />
        <MetricCard label="Score Delta" value={deltaLabel(scoreDelta)} tone={statusTone(summary?.vendor_score_trend_band)} />
        <MetricCard label="Repeat Events" value={summary?.repeat_event_vendor_count ?? 0} tone="#ef4444" />
        <MetricCard label="High Risk Vendors" value={summary?.high_risk_vendor_count ?? 0} tone="#ef4444" />
        <MetricCard label="CAPA Linked" value={summary?.capa_linked_vendor_count ?? 0} tone="#f59e0b" />
        <MetricCard label="Executive Review" value={summary?.executive_review_count ?? 0} tone="#ef4444" />
        <MetricCard label="Leadership Watch" value={summary?.leadership_watch_count ?? 0} tone="#f59e0b" />
      </div>

      <div style={styles.twoColumn}>
        <div style={styles.card}>
          <strong style={styles.cardTitle}>Vendor Trend Export</strong>
          <p style={styles.cardText}>
            Download the vendor trend intelligence CSV for Power BI, vendor business review, or executive governance reporting.
          </p>
          <a style={styles.button} href={csvUrl} target="_blank" rel="noreferrer">
            Open Vendor Trend CSV
          </a>
        </div>

        <div style={styles.card}>
          <strong style={styles.cardTitle}>Trend Signals</strong>
          <ul style={styles.list}>
            <li><strong>Vendor score trend:</strong> {titleCase(summary?.vendor_score_trend_band)}</li>
            <li><strong>Repeat-event vendors:</strong> {summary?.repeat_event_vendor_count ?? 0}</li>
            <li><strong>High-risk vendors:</strong> {summary?.high_risk_vendor_count ?? 0}</li>
            <li><strong>CAPA-linked vendors:</strong> {summary?.capa_linked_vendor_count ?? 0}</li>
          </ul>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTop}>
          <strong style={styles.cardTitle}>Vendor Trend Watchlist</strong>
          <span style={styles.smallPill}>{topVendorItems.length} vendors shown</span>
        </div>

        <div style={styles.itemList}>
          {topVendorItems.map((item) => (
            <div key={item.vendor_name} style={styles.trendItem}>
              <div style={styles.itemHeader}>
                <div>
                  <strong>{item.vendor_name}</strong>
                  <div style={styles.itemTitle}>{item.vendor_category}</div>
                </div>
                <span style={{ ...styles.scorePill, borderColor: statusTone(item.trend_band) }}>
                  {item.current_vendor_score}
                </span>
              </div>

              <div style={styles.itemMeta}>
                <span>{item.primary_site}</span>
                <span>{titleCase(item.latest_event_type)}</span>
                <span style={{ color: statusTone(item.trend_band) }}>{titleCase(item.trend_band)}</span>
                <span>Delta {deltaLabel(item.vendor_score_delta)}</span>
                <span>{item.repeat_event_count} repeat events</span>
                <span>{item.high_risk_event_count} high-risk events</span>
                <span>{item.capa_linked_event_count} CAPA-linked</span>
                <span style={{ color: statusTone(item.executive_priority) }}>
                  {titleCase(item.executive_priority)}
                </span>
              </div>

              {item.linked_capa_id ? (
                <div style={styles.capaText}>Linked CAPA: {item.linked_capa_id}</div>
              ) : null}

              <p style={styles.cardText}>{item.recommended_action}</p>
            </div>
          ))}
        </div>
      </div>

      <div style={styles.twoColumn}>
        <div style={styles.card}>
          <strong style={styles.cardTitle}>Executive Recommendations</strong>
          <ul style={styles.list}>
            {(summary?.executive_recommendations || []).map((item, index) => (
              <li key={`vendor-trend-rec-${index}`}>{item}</li>
            ))}
          </ul>
        </div>

        <div style={styles.card}>
          <strong style={styles.cardTitle}>Next Actions</strong>
          <ul style={styles.list}>
            {(summary?.next_actions || []).map((item, index) => (
              <li key={`vendor-trend-action-${index}`}>
                <strong>{titleCase(item.priority)}:</strong> {item.action}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div style={styles.footer}>
        <span>Module: {health?.module || summary?.module}</span>
        <span>Product phase: {summary?.product_phase || "v1.2"}</span>
        <span>Theme: Vendor Performance Scorecard → Vendor Trend Intelligence → Executive Vendor Review</span>
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
    border: "1px solid rgba(251, 191, 36, 0.35)",
    background: "linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(120, 53, 15, 0.52))",
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
    border: "1px solid rgba(251, 191, 36, 0.45)",
    background: "rgba(251, 191, 36, 0.14)",
    color: "#fde68a",
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
  statusCard: {
    border: "1px solid rgba(251, 191, 36, 0.35)",
    borderRadius: "20px",
    padding: "18px",
    background: "rgba(2, 6, 23, 0.45)",
    textAlign: "center",
  },
  statusLabel: {
    color: "#fde68a",
    fontSize: "12px",
    fontWeight: 800,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  statusValue: {
    fontSize: "30px",
    fontWeight: 950,
    marginTop: "12px",
  },
  smallText: {
    color: "#cbd5e1",
    fontSize: "12px",
    marginTop: "8px",
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
    marginBottom: 0,
  },
  button: {
    display: "inline-flex",
    padding: "10px 12px",
    borderRadius: "12px",
    background: "rgba(251, 191, 36, 0.18)",
    border: "1px solid rgba(251, 191, 36, 0.4)",
    color: "#fde68a",
    fontWeight: 900,
    textDecoration: "none",
    marginTop: "14px",
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
    background: "rgba(251, 191, 36, 0.14)",
    color: "#fde68a",
    fontSize: "12px",
    fontWeight: 900,
  },
  itemList: {
    display: "grid",
    gap: "12px",
  },
  trendItem: {
    border: "1px solid rgba(148, 163, 184, 0.22)",
    borderRadius: "16px",
    padding: "14px",
    background: "rgba(15, 23, 42, 0.55)",
  },
  itemHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "start",
    gap: "12px",
  },
  itemTitle: {
    color: "#e2e8f0",
    fontSize: "13px",
    marginTop: "4px",
  },
  itemMeta: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
    marginTop: "10px",
    color: "#fde68a",
    fontSize: "12px",
    fontWeight: 800,
  },
  scorePill: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minWidth: "46px",
    padding: "6px 10px",
    borderRadius: "999px",
    border: "1px solid",
    color: "#ffffff",
    fontWeight: 950,
  },
  capaText: {
    marginTop: "10px",
    color: "#fbbf24",
    fontSize: "12px",
    fontWeight: 800,
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
