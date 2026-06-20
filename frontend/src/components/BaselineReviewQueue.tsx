import { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://lumen-ai-53u4.onrender.com";

type BaselineReviewItem = {
  finding_id: number | null;
  facility: string;
  department: string;
  vendor: string;
  instrument_name: string;
  tray_name: string;
  finding_type: string;
  risk_level: string;
  score: number;
  score_confidence: string;
  baseline_source: string;
  baseline_status: string;
  score_basis: string;
  requires_baseline_review: boolean;
  manual_review_required: boolean;
  recommended_action: string;
};

type BaselineReviewQueueResponse = {
  status: string;
  queue_type: string;
  generated_at: string;
  queue_count: number;
  review_priority_count: number;
  queue_summary: string;
  recommended_next_step: string;
  items: BaselineReviewItem[];
};

async function fetchBaselineReviewQueue(limit = 50): Promise<BaselineReviewQueueResponse> {
  const safeLimit = Math.max(1, Math.min(Number(limit) || 50, 200));

  const response = await fetch(`${API_BASE}/api/enterprise/baseline-review-queue?limit=${safeLimit}`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("token") || ""}`,
      "X-LumenAI-Role": "viewer",
      "X-LumenAI-Actor": "john-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Baseline Review Queue failed (${response.status})`);
  }

  return data;
}

export default function BaselineReviewQueue() {
  const [queue, setQueue] = useState<BaselineReviewQueueResponse | null>(null);
  const [limit, setLimit] = useState("50");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadQueue() {
    setLoading(true);
    setError("");

    try {
      const data = await fetchBaselineReviewQueue(Number(limit) || 50);
      setQueue(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown baseline review queue error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const items = queue?.items || [];

  return (
    <section style={panelStyle}>
      <div style={headerRowStyle}>
        <div>
          <div style={eyebrowStyle}>Baseline Governance</div>
          <h2 style={titleStyle}>Baseline Review Queue</h2>
          <p style={subtitleStyle}>
            Low-confidence or no-baseline scores are routed here before being treated as final.
            This protects scoring integrity when vendor or hospital baseline evidence is missing.
          </p>
        </div>

        <button type="button" onClick={loadQueue} style={refreshButtonStyle}>
          {loading ? "Refreshing..." : "Refresh Queue"}
        </button>
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

        {queue?.generated_at ? (
          <span style={timestampStyle}>
            Generated: {new Date(queue.generated_at).toLocaleString()}
          </span>
        ) : null}
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      {queue ? (
        <>
          <div style={metricGridStyle}>
            <MetricCard label="Queue Count" value={queue.queue_count} />
            <MetricCard label="Review Priority" value={queue.review_priority_count} />
            <MetricCard label="Items Shown" value={items.length} />
          </div>

          <div style={summaryCardStyle}>
            <h3 style={sectionTitleStyle}>Queue Summary</h3>
            <p style={summaryTextStyle}>{queue.queue_summary}</p>
            <p style={nextStepTextStyle}>{queue.recommended_next_step}</p>
          </div>

          <div style={tableCardStyle}>
            <div style={tableHeaderStyle}>
              <h3 style={sectionTitleStyle}>Baseline Review Items</h3>
              <span style={smallBadgeStyle}>{items.length} shown</span>
            </div>

            {items.length > 0 ? (
              <div style={tableWrapStyle}>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={thStyle}>Finding</th>
                      <th style={thStyle}>Facility</th>
                      <th style={thStyle}>Vendor</th>
                      <th style={thStyle}>Instrument</th>
                      <th style={thStyle}>Finding Type</th>
                      <th style={thStyle}>Risk</th>
                      <th style={thStyle}>Score</th>
                      <th style={thStyle}>Confidence</th>
                      <th style={thStyle}>Baseline</th>
                      <th style={thStyle}>Review</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => (
                      <tr key={`${item.finding_id}-${item.instrument_name}-${item.finding_type}`}>
                        <td style={tdStyle}>{item.finding_id || "—"}</td>
                        <td style={tdStyle}>
                          <strong>{item.facility || "—"}</strong>
                          <div style={mutedTextStyle}>{item.department || ""}</div>
                        </td>
                        <td style={tdStyle}>{item.vendor || "—"}</td>
                        <td style={tdStyle}>
                          <strong>{item.instrument_name || "—"}</strong>
                          <div style={mutedTextStyle}>{item.tray_name || ""}</div>
                        </td>
                        <td style={tdStyle}>{item.finding_type || "—"}</td>
                        <td style={tdStyle}>
                          <span style={riskBadgeStyle(item.risk_level)}>{item.risk_level || "unknown"}</span>
                        </td>
                        <td style={tdStyle}>{item.score}</td>
                        <td style={tdStyle}>
                          <span style={confidenceBadgeStyle(item.score_confidence)}>
                            {item.score_confidence || "unknown"}
                          </span>
                        </td>
                        <td style={tdStyle}>
                          <strong>{item.baseline_source || "none"}</strong>
                          <div style={mutedTextStyle}>{item.baseline_status || "missing"}</div>
                        </td>
                        <td style={tdStyle}>
                          {item.requires_baseline_review ? "Required" : "Not required"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={emptyStyle}>No baseline review items are currently pending.</p>
            )}
          </div>

          {items.length > 0 ? (
            <details style={detailsStyle}>
              <summary style={detailsSummaryStyle}>View scoring basis and recommended actions</summary>

              <div style={itemGridStyle}>
                {items.map((item) => (
                  <div key={`detail-${item.finding_id}-${item.instrument_name}`} style={itemCardStyle}>
                    <div style={itemCardHeaderStyle}>
                      <strong>Finding #{item.finding_id || "—"}</strong>
                      <span style={confidenceBadgeStyle(item.score_confidence)}>
                        {item.score_confidence || "unknown"}
                      </span>
                    </div>

                    <p style={basisTextStyle}>{item.score_basis}</p>

                    <div style={actionBoxStyle}>
                      <strong>Recommended Action</strong>
                      <p>{item.recommended_action}</p>
                    </div>

                    <div style={flagRowStyle}>
                      <span>Baseline Review: {item.requires_baseline_review ? "Yes" : "No"}</span>
                      <span>Manual Review: {item.manual_review_required ? "Yes" : "No"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          ) : null}
        </>
      ) : (
        <p style={emptyStyle}>Baseline Review Queue has not loaded yet.</p>
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

function riskBadgeStyle(risk: string): React.CSSProperties {
  const normalized = (risk || "").toLowerCase();

  return {
    borderRadius: "999px",
    padding: "4px 8px",
    fontSize: "11px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: normalized === "high" || normalized === "critical" ? "#fee2e2" : normalized === "medium" || normalized === "moderate" ? "#ffedd5" : "#dcfce7",
    color: normalized === "high" || normalized === "critical" ? "#991b1b" : normalized === "medium" || normalized === "moderate" ? "#9a3412" : "#166534",
  };
}

function confidenceBadgeStyle(confidence: string): React.CSSProperties {
  const normalized = (confidence || "").toLowerCase();
  const isLow = normalized === "low";
  const isMedium = normalized === "medium";
  const isHigh = normalized === "high" || normalized === "medium_high";

  return {
    borderRadius: "999px",
    padding: "4px 8px",
    fontSize: "11px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: isHigh ? "#dcfce7" : isMedium ? "#ffedd5" : isLow ? "#fee2e2" : "#e2e8f0",
    color: isHigh ? "#166534" : isMedium ? "#9a3412" : isLow ? "#991b1b" : "#334155",
  };
}

const panelStyle: React.CSSProperties = {
  marginTop: "20px",
  padding: "20px",
  borderRadius: "24px",
  border: "1px solid #fde68a",
  background: "linear-gradient(135deg, #fffbeb 0%, #ffffff 100%)",
  boxShadow: "0 12px 32px rgba(146, 64, 14, 0.08)",
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
  color: "#b45309",
};

const titleStyle: React.CSSProperties = {
  margin: "4px 0 0",
  fontSize: "24px",
  fontWeight: 900,
  color: "#78350f",
};

const subtitleStyle: React.CSSProperties = {
  margin: "8px 0 0",
  color: "#57534e",
  lineHeight: 1.5,
  maxWidth: "820px",
};

const refreshButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#b45309",
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
  color: "#44403c",
  fontWeight: 800,
};

const inputStyle: React.CSSProperties = {
  width: "80px",
  border: "1px solid #fcd34d",
  borderRadius: "10px",
  padding: "8px 10px",
  fontWeight: 800,
};

const timestampStyle: React.CSSProperties = {
  color: "#78716c",
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
  border: "1px solid #fde68a",
  background: "#ffffff",
};

const metricLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "11px",
  fontWeight: 900,
  textTransform: "uppercase",
  color: "#78716c",
};

const metricValueStyle: React.CSSProperties = {
  display: "block",
  marginTop: "6px",
  color: "#78350f",
  fontSize: "26px",
  fontWeight: 900,
};

const summaryCardStyle: React.CSSProperties = {
  marginTop: "18px",
  padding: "16px",
  borderRadius: "18px",
  background: "#fef3c7",
  border: "1px solid #fcd34d",
};

const sectionTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: "16px",
  fontWeight: 900,
  color: "#78350f",
};

const summaryTextStyle: React.CSSProperties = {
  margin: "8px 0 0",
  color: "#78350f",
  lineHeight: 1.5,
};

const nextStepTextStyle: React.CSSProperties = {
  margin: "8px 0 0",
  color: "#92400e",
  fontWeight: 800,
};

const tableCardStyle: React.CSSProperties = {
  marginTop: "18px",
  padding: "16px",
  borderRadius: "18px",
  background: "#ffffff",
  border: "1px solid #fde68a",
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
  background: "#fffbeb",
  color: "#92400e",
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
  borderBottom: "1px solid #fcd34d",
  color: "#92400e",
  fontSize: "12px",
  textTransform: "uppercase",
};

const tdStyle: React.CSSProperties = {
  padding: "10px",
  borderBottom: "1px solid #fef3c7",
  color: "#44403c",
  verticalAlign: "top",
};

const mutedTextStyle: React.CSSProperties = {
  marginTop: "3px",
  color: "#78716c",
  fontSize: "12px",
};

const detailsStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "14px",
  borderRadius: "18px",
  background: "#fffbeb",
  border: "1px solid #fde68a",
};

const detailsSummaryStyle: React.CSSProperties = {
  cursor: "pointer",
  fontWeight: 900,
  color: "#92400e",
};

const itemGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
  gap: "10px",
  marginTop: "12px",
};

const itemCardStyle: React.CSSProperties = {
  padding: "12px",
  borderRadius: "14px",
  background: "#ffffff",
  border: "1px solid #fde68a",
};

const itemCardHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "8px",
  alignItems: "center",
};

const basisTextStyle: React.CSSProperties = {
  margin: "10px 0 0",
  color: "#44403c",
  lineHeight: 1.45,
};

const actionBoxStyle: React.CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#fef3c7",
  color: "#78350f",
};

const flagRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  flexWrap: "wrap",
  marginTop: "10px",
  color: "#92400e",
  fontSize: "12px",
  fontWeight: 800,
};

const emptyStyle: React.CSSProperties = {
  margin: "16px 0 0",
  color: "#78716c",
};
