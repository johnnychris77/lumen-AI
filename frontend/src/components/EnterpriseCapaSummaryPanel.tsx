import { useEffect, useState } from "react";
import type { CSSProperties } from "react";

type CapaSummary = {
  total_capas: number;
  open_capas: number;
  in_progress_capas: number;
  pending_review_capas: number;
  closed_capas: number;
  overdue_capas: number;
  cancelled_capas: number;
  average_days_open: number;
  closure_rate: number;
  risk_message: string;
};

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

const AUTH_TOKEN = import.meta.env.VITE_AUTH_TOKEN || "dev-token";

export default function EnterpriseCapaSummaryPanel() {
  const [summary, setSummary] = useState<CapaSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadSummary() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/api/enterprise/capas/summary`, {
        headers: {
          Authorization: `Bearer ${AUTH_TOKEN}`,
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
          "X-Tenant-Id": "bonsecours",
          "X-Tenant-Name": "Bon Secours",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || `CAPA summary request failed (${response.status})`);
      }

      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown CAPA summary error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSummary();
  }, []);

  return (
    <section style={panelStyle}>
      <div style={eyebrowStyle}>Executive CAPA Risk Rollup</div>

      <div style={headerRowStyle}>
        <div>
          <h2 style={{ margin: "8px 0 8px", color: "#0f172a" }}>
            CAPA Executive Summary
          </h2>
          <p style={{ margin: 0, color: "#475569", lineHeight: 1.6 }}>
            Summarizes corrective-action workload, closure risk, overdue exposure,
            and executive follow-up priorities.
          </p>
        </div>

        <button
          type="button"
          onClick={loadSummary}
          disabled={loading}
          style={refreshButtonStyle(loading)}
        >
          {loading ? "Refreshing..." : "Refresh CAPA Summary"}
        </button>
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      {summary ? (
        <>
          <div style={cardGridStyle}>
            <MetricCard label="Total CAPAs" value={summary.total_capas} />
            <MetricCard label="Open" value={summary.open_capas} tone="purple" />
            <MetricCard label="In Progress" value={summary.in_progress_capas} tone="blue" />
            <MetricCard label="Pending Review" value={summary.pending_review_capas} tone="amber" />
            <MetricCard label="Closed" value={summary.closed_capas} tone="green" />
            <MetricCard label="Overdue" value={summary.overdue_capas} tone="red" />
            <MetricCard label="Closure Rate" value={`${summary.closure_rate}%`} tone="green" />
            <MetricCard label="Avg Days Open" value={summary.average_days_open} tone="blue" />
          </div>

          <div style={riskMessageStyle(summary.overdue_capas)}>
            {summary.risk_message}
          </div>
        </>
      ) : !error ? (
        <div style={emptyStyle}>No CAPA summary available yet.</div>
      ) : null}
    </section>
  );
}

function MetricCard({
  label,
  value,
  tone = "slate",
}: {
  label: string;
  value: number | string;
  tone?: "slate" | "purple" | "blue" | "amber" | "green" | "red";
}) {
  return (
    <div style={metricCardStyle(tone)}>
      <div style={metricLabelStyle}>{label}</div>
      <div style={metricValueStyle(tone)}>{value}</div>
    </div>
  );
}

const toneMap = {
  slate: "#334155",
  purple: "#7e22ce",
  blue: "#1d4ed8",
  amber: "#a16207",
  green: "#166534",
  red: "#991b1b",
};

const panelStyle: CSSProperties = {
  margin: "20px 0",
  padding: "20px",
  borderRadius: "18px",
  border: "1px solid #bfdbfe",
  background: "linear-gradient(135deg, #eff6ff 0%, #ffffff 100%)",
  boxShadow: "0 12px 28px rgba(15, 23, 42, 0.08)",
};

const eyebrowStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 800,
  color: "#1d4ed8",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
};

const headerRowStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "center",
  flexWrap: "wrap",
};

function refreshButtonStyle(loading: boolean): CSSProperties {
  return {
    border: "0",
    borderRadius: "12px",
    padding: "10px 14px",
    fontWeight: 800,
    cursor: loading ? "not-allowed" : "pointer",
    background: loading ? "#94a3b8" : "#1d4ed8",
    color: "#ffffff",
  };
}

const errorStyle: CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 700,
};

const emptyStyle: CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "12px",
  background: "#ffffff",
  border: "1px solid #bfdbfe",
  color: "#475569",
};

const cardGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
  gap: "12px",
  marginTop: "16px",
};

function metricCardStyle(tone: keyof typeof toneMap): CSSProperties {
  return {
    padding: "14px",
    borderRadius: "16px",
    background: "#ffffff",
    border: `1px solid ${toneMap[tone]}33`,
    boxShadow: "0 8px 18px rgba(15, 23, 42, 0.06)",
  };
}

const metricLabelStyle: CSSProperties = {
  fontSize: "12px",
  color: "#64748b",
  fontWeight: 800,
};

function metricValueStyle(tone: keyof typeof toneMap): CSSProperties {
  return {
    marginTop: "6px",
    fontSize: "28px",
    fontWeight: 950,
    color: toneMap[tone],
  };
}

function riskMessageStyle(overdue: number): CSSProperties {
  return {
    marginTop: "16px",
    padding: "14px",
    borderRadius: "14px",
    background: overdue > 0 ? "#fef2f2" : "#ecfdf5",
    border: overdue > 0 ? "1px solid #fecaca" : "1px solid #bbf7d0",
    color: overdue > 0 ? "#991b1b" : "#166534",
    fontWeight: 900,
  };
}
