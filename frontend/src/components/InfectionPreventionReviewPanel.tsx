import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || "http://127.0.0.1:18012";
const AUTH_TOKEN = localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || "";

type InfectionPreventionPacket = {
  status: string;
  finding_id: number;
  packet_type: string;
  ip_review_status: string;
  patient_safety_signal: string;
  infection_risk_signal: string;
  vendor_name: string;
  instrument_name: string;
  instrument_category: string;
  finding_category: string;
  finding_description: string;
  severity: string;
  confidence_score?: number | null;
  baseline_evidence_count: number;
  approved_baseline_count: number;
  comparison_score?: number | null;
  deviation_level: string;
  baseline_alignment: string;
  recommended_ip_action: string;
  recommended_documentation: string[];
  ip_review_summary: string;
};

async function fetchIpPacket(findingId: string): Promise<InfectionPreventionPacket> {
  const response = await fetch(
    `${API_BASE}/api/enterprise/intake/${findingId}/infection-prevention-review-packet`,
    {
      headers: {
        Authorization: `Bearer ${AUTH_TOKEN}`,
        "X-LumenAI-Role": "viewer",
        "X-LumenAI-Actor": "john-demo",
      },
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `IP review packet failed (${response.status})`);
  }

  return data;
}

export default function InfectionPreventionReviewPanel() {
  const [findingId, setFindingId] = useState("2");
  const [packet, setPacket] = useState<InfectionPreventionPacket | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadPacket() {
    setLoading(true);
    setError("");

    try {
      const data = await fetchIpPacket(findingId);
      setPacket(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown IP review packet error");
    } finally {
      setLoading(false);
    }
  }

  const pdfUrl = `${API_BASE}/api/enterprise/intake/${findingId}/infection-prevention-review-packet.pdf`;

  return (
    <section style={panelStyle}>
      <div style={headerRowStyle}>
        <div>
          <div style={eyebrowStyle}>Infection Prevention Review</div>
          <h2 style={titleStyle}>IP Review Packet</h2>
          <p style={subtitleStyle}>
            Patient-safety and infection-risk review view for bioburden, retained debris, lumened instrument concerns, and survey-readiness documentation.
          </p>
        </div>
      </div>

      <div style={controlRowStyle}>
        <label style={labelStyle}>
          Finding ID
          <input
            value={findingId}
            onChange={(event) => setFindingId(event.target.value)}
            style={inputStyle}
          />
        </label>

        <button type="button" onClick={loadPacket} disabled={loading} style={primaryButtonStyle}>
          {loading ? "Loading..." : "Load IP Review Packet"}
        </button>

        <a href={pdfUrl} target="_blank" rel="noreferrer" style={secondaryButtonStyle}>
          Download IP PDF
        </a>
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      {packet ? (
        <>
          <div style={signalCardStyle(packet.patient_safety_signal)}>
            <div>
              <div style={eyebrowStyle}>Patient Safety Signal</div>
              <h3 style={signalTitleStyle}>{formatLabel(packet.patient_safety_signal)}</h3>
              <p style={signalSummaryStyle}>{packet.ip_review_summary}</p>
            </div>
          </div>

          <div style={metricGridStyle}>
            <MetricCard label="IP Review Status" value={formatLabel(packet.ip_review_status)} />
            <MetricCard label="Infection Risk Signal" value={formatLabel(packet.infection_risk_signal)} />
            <MetricCard label="Severity" value={formatLabel(packet.severity)} intent={packet.severity === "critical" ? "critical" : "warning"} />
            <MetricCard label="Baseline Evidence" value={String(packet.baseline_evidence_count)} />
            <MetricCard label="Approved Baselines" value={String(packet.approved_baseline_count)} intent="success" />
            <MetricCard label="Comparison Score" value={packet.comparison_score === null || packet.comparison_score === undefined ? "N/A" : String(packet.comparison_score)} />
          </div>

          <div style={contentGridStyle}>
            <div style={cardStyle}>
              <h3 style={sectionTitleStyle}>Finding Context</h3>
              <InfoRow label="Vendor" value={packet.vendor_name} />
              <InfoRow label="Instrument" value={packet.instrument_name} />
              <InfoRow label="Instrument Category" value={packet.instrument_category} />
              <InfoRow label="Finding Category" value={packet.finding_category} />
              <InfoRow label="Description" value={packet.finding_description} />
            </div>

            <div style={cardStyle}>
              <h3 style={sectionTitleStyle}>Recommended IP Action</h3>
              <p style={bodyTextStyle}>{packet.recommended_ip_action}</p>
            </div>
          </div>

          <div style={cardStyle}>
            <h3 style={sectionTitleStyle}>Recommended Documentation</h3>
            <ul style={listStyle}>
              {packet.recommended_documentation.map((item) => (
                <li key={item} style={listItemStyle}>{item}</li>
              ))}
            </ul>
          </div>
        </>
      ) : (
        <div style={emptyStateStyle}>
          Load a finding to generate the Infection Prevention review panel.
        </div>
      )}
    </section>
  );
}

function MetricCard({
  label,
  value,
  intent = "neutral",
}: {
  label: string;
  value: string;
  intent?: "neutral" | "success" | "warning" | "critical";
}) {
  return (
    <div style={metricCardStyle(intent)}>
      <span style={metricLabelStyle}>{label}</span>
      <strong style={metricValueStyle}>{value}</strong>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value?: string }) {
  return (
    <div style={infoRowStyle}>
      <span style={infoLabelStyle}>{label}</span>
      <span style={infoValueStyle}>{value || "Not documented"}</span>
    </div>
  );
}

function formatLabel(value: string) {
  return (value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

const panelStyle: React.CSSProperties = {
  padding: "20px",
  borderRadius: "22px",
  background: "#f8fafc",
  border: "1px solid #e2e8f0",
};

const headerRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "16px",
  alignItems: "flex-start",
  marginBottom: "16px",
};

const eyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#0891b2",
};

const titleStyle: React.CSSProperties = {
  margin: "4px 0",
  fontSize: "26px",
  fontWeight: 900,
  color: "#0f172a",
};

const subtitleStyle: React.CSSProperties = {
  margin: 0,
  color: "#475569",
  lineHeight: 1.5,
  maxWidth: "850px",
};

const controlRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  alignItems: "end",
  flexWrap: "wrap",
  marginBottom: "16px",
};

const labelStyle: React.CSSProperties = {
  display: "grid",
  gap: "6px",
  fontWeight: 900,
  color: "#334155",
};

const inputStyle: React.CSSProperties = {
  padding: "10px",
  borderRadius: "12px",
  border: "1px solid #cbd5e1",
  minWidth: "120px",
};

const primaryButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "14px",
  padding: "11px 14px",
  background: "#0e7490",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};

const secondaryButtonStyle: React.CSSProperties = {
  borderRadius: "14px",
  padding: "11px 14px",
  background: "#e0f2fe",
  color: "#075985",
  fontWeight: 900,
  textDecoration: "none",
};

function signalCardStyle(signal: string): React.CSSProperties {
  const elevated = signal === "elevated";
  const moderate = signal === "moderate";

  return {
    padding: "18px",
    borderRadius: "20px",
    border: `1px solid ${elevated ? "#fecaca" : moderate ? "#fed7aa" : "#bae6fd"}`,
    background: elevated
      ? "linear-gradient(135deg, #fef2f2 0%, #ffffff 100%)"
      : moderate
        ? "linear-gradient(135deg, #fff7ed 0%, #ffffff 100%)"
        : "linear-gradient(135deg, #ecfeff 0%, #ffffff 100%)",
    marginBottom: "16px",
  };
}

const signalTitleStyle: React.CSSProperties = {
  margin: "4px 0",
  fontSize: "22px",
  fontWeight: 900,
  color: "#0f172a",
};

const signalSummaryStyle: React.CSSProperties = {
  margin: 0,
  color: "#334155",
  lineHeight: 1.5,
};

const metricGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "12px",
  marginBottom: "16px",
};

function metricCardStyle(intent: "neutral" | "success" | "warning" | "critical"): React.CSSProperties {
  const styles = {
    neutral: { border: "#bae6fd", background: "#ffffff", color: "#075985" },
    success: { border: "#bbf7d0", background: "#f0fdf4", color: "#166534" },
    warning: { border: "#fed7aa", background: "#fff7ed", color: "#9a3412" },
    critical: { border: "#fecaca", background: "#fef2f2", color: "#991b1b" },
  }[intent];

  return {
    padding: "14px",
    borderRadius: "18px",
    border: `1px solid ${styles.border}`,
    background: styles.background,
    color: styles.color,
  };
}

const metricLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "12px",
  fontWeight: 900,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const metricValueStyle: React.CSSProperties = {
  display: "block",
  marginTop: "6px",
  fontSize: "18px",
};

const contentGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  gap: "14px",
  marginBottom: "16px",
};

const cardStyle: React.CSSProperties = {
  padding: "16px",
  borderRadius: "18px",
  border: "1px solid #e2e8f0",
  background: "#ffffff",
  boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
};

const sectionTitleStyle: React.CSSProperties = {
  margin: "0 0 10px",
  fontSize: "18px",
  fontWeight: 900,
  color: "#0f172a",
};

const bodyTextStyle: React.CSSProperties = {
  color: "#334155",
  lineHeight: 1.6,
  margin: 0,
};

const infoRowStyle: React.CSSProperties = {
  display: "grid",
  gap: "4px",
  padding: "8px 0",
  borderBottom: "1px solid #f1f5f9",
};

const infoLabelStyle: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: 900,
  textTransform: "uppercase",
  color: "#64748b",
};

const infoValueStyle: React.CSSProperties = {
  color: "#0f172a",
  fontWeight: 700,
};

const listStyle: React.CSSProperties = {
  margin: 0,
  paddingLeft: "20px",
  color: "#334155",
  lineHeight: 1.6,
};

const listItemStyle: React.CSSProperties = {
  marginBottom: "6px",
};

const errorStyle: React.CSSProperties = {
  marginBottom: "12px",
  padding: "12px",
  borderRadius: "14px",
  border: "1px solid #fecaca",
  background: "#fef2f2",
  color: "#991b1b",
  fontWeight: 800,
};

const emptyStateStyle: React.CSSProperties = {
  padding: "16px",
  borderRadius: "16px",
  background: "#ffffff",
  color: "#64748b",
  border: "1px dashed #cbd5e1",
};
