import { useEffect, useState } from "react";
import type { CSSProperties } from "react";

type IntakeHistoryItem = {
  finding_id: number;
  vendor_name?: string;
  instrument_name?: string;
  finding_category?: string;
  severity?: string;
  risk_tier?: string;
  overall_score?: number;
  workflow_status?: string;
  human_review_status?: string;
  human_confirmed?: boolean;
  recommended_action?: string;
  created_at?: string;
};

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

type CapaItem = {
  capa_id: number;
  finding_id?: number | null;
  capa_number: string;
  title: string;
  status: string;
  due_date?: string;
  closed_at?: string;
  created_at?: string;
};

type AuditTrailItem = {
  id: number;
  action_type: string;
  actor_email: string;
  actor_role: string;
  resource_type: string;
  resource_id: string;
  status: string;
  compliance_flag: boolean;
  created_at: string;
};

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

const AUTH_TOKEN = import.meta.env.VITE_AUTH_TOKEN || "dev-token";

export default function EnterpriseGovernanceCommandCenter() {
  const [latestFinding, setLatestFinding] = useState<IntakeHistoryItem | null>(null);
  const [capaSummary, setCapaSummary] = useState<CapaSummary | null>(null);
  const [latestCapa, setLatestCapa] = useState<CapaItem | null>(null);
  const [auditCount, setAuditCount] = useState(0);
  const [latestAudit, setLatestAudit] = useState<AuditTrailItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function fetchJson(path: string, role = "viewer") {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: {
        Authorization: `Bearer ${AUTH_TOKEN}`,
        "X-LumenAI-Role": role,
        "X-LumenAI-Actor": "john-demo",
        "X-Tenant-Id": "bonsecours",
        "X-Tenant-Name": "Bon Secours",
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data?.detail || `Request failed (${response.status})`);
    }

    return data;
  }

  async function loadCommandCenter() {
    setLoading(true);
    setError("");

    try {
      const [historyData, capaSummaryData, capaListData, auditData] =
        await Promise.all([
          fetchJson("/api/enterprise/intake/history?limit=1"),
          fetchJson("/api/enterprise/capas/summary"),
          fetchJson("/api/enterprise/capas?limit=1"),
          fetchJson("/api/enterprise/audit-trail?limit=25", "auditor"),
        ]);

      const historyItems = Array.isArray(historyData.items) ? historyData.items : [];
      const capaItems = Array.isArray(capaListData.items) ? capaListData.items : [];
      const auditItems = Array.isArray(auditData.items) ? auditData.items : [];

      setLatestFinding(historyItems[0] || null);
      setCapaSummary(capaSummaryData || null);
      setLatestCapa(capaItems[0] || null);
      setAuditCount(auditItems.length);
      setLatestAudit(auditItems[0] || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown command center error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCommandCenter();
  }, []);

  const workflow = buildWorkflow(latestFinding, latestCapa);

  return (
    <section style={panelStyle}>
      <div style={eyebrowStyle}>Enterprise Governance Command Center</div>

      <div style={headerRowStyle}>
        <div>
          <h2 style={{ margin: "8px 0 8px", color: "#0f172a" }}>
            Executive Case Lifecycle View
          </h2>
          <p style={{ margin: 0, color: "#475569", lineHeight: 1.6 }}>
            One view of the latest enterprise finding, human review status, governance packet readiness,
            CAPA lifecycle, and audit trail activity.
          </p>
        </div>

        <button
          type="button"
          onClick={loadCommandCenter}
          disabled={loading}
          style={refreshButtonStyle(loading)}
        >
          {loading ? "Refreshing..." : "Refresh Command Center"}
        </button>
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      <div style={cardGridStyle}>
        <CommandCard
          label="Newest Finding"
          value={latestFinding ? `#${latestFinding.finding_id}` : "None"}
          subtext={
            latestFinding
              ? `${latestFinding.instrument_name || "Instrument"} • ${
                  latestFinding.severity || "Unassigned"
                }`
              : "Create an enterprise intake to begin."
          }
          tone="blue"
        />

        <CommandCard
          label="Human Review"
          value={
            latestFinding?.human_review_status ||
            latestFinding?.workflow_status ||
            "Pending"
          }
          subtext={
            latestFinding?.human_confirmed
              ? "Human confirmed"
              : "Awaiting human confirmation"
          }
          tone={latestFinding?.human_confirmed ? "green" : "amber"}
        />

        <CommandCard
          label="Latest CAPA"
          value={latestCapa ? latestCapa.capa_number : "None"}
          subtext={latestCapa ? `Status: ${latestCapa.status}` : "No CAPA opened yet."}
          tone={latestCapa ? statusTone(latestCapa.status) : "slate"}
        />

        <CommandCard
          label="Audit Events"
          value={auditCount}
          subtext={
            latestAudit
              ? `${formatAction(latestAudit.action_type)} by ${latestAudit.actor_email || "unknown"}`
              : "No audit events yet."
          }
          tone="purple"
        />

        <CommandCard
          label="Packet Status"
          value={latestFinding ? "Ready" : "Not Ready"}
          subtext={
            latestFinding
              ? "Governance JSON/PDF packet available"
              : "Create intake before packet export."
          }
          tone={latestFinding ? "green" : "slate"}
        />

        <CommandCard
          label="CAPA Closure Rate"
          value={capaSummary ? `${capaSummary.closure_rate}%` : "0%"}
          subtext={
            capaSummary
              ? `${capaSummary.closed_capas}/${capaSummary.total_capas} closed`
              : "No CAPA records available."
          }
          tone="green"
        />
      </div>

      <div style={workflowStyle}>
        {workflow.map((step, index) => (
          <div key={step.label} style={workflowStepStyle(step.complete)}>
            <div style={workflowCircleStyle(step.complete)}>{index + 1}</div>
            <div>
              <div style={workflowLabelStyle}>{step.label}</div>
              <div style={workflowSubtextStyle}>{step.subtext}</div>
            </div>
          </div>
        ))}
      </div>

      {capaSummary ? (
        <div style={riskMessageStyle(capaSummary.overdue_capas)}>
          {capaSummary.risk_message}
        </div>
      ) : null}
    </section>
  );
}

function buildWorkflow(finding: IntakeHistoryItem | null, capa: CapaItem | null) {
  return [
    {
      label: "Intake Created",
      complete: Boolean(finding),
      subtext: finding ? `Finding #${finding.finding_id}` : "Waiting for intake",
    },
    {
      label: "Human Review",
      complete: Boolean(finding?.human_confirmed || finding?.human_review_status),
      subtext: finding?.human_review_status || "Pending review",
    },
    {
      label: "Governance Packet",
      complete: Boolean(finding),
      subtext: finding ? "Packet ready" : "Not ready",
    },
    {
      label: "CAPA Opened",
      complete: Boolean(capa),
      subtext: capa ? capa.capa_number : "No CAPA",
    },
    {
      label: "CAPA Active",
      complete: Boolean(capa && capa.status !== "closed"),
      subtext: capa ? capa.status : "No active CAPA",
    },
    {
      label: "CAPA Closed",
      complete: Boolean(capa?.status === "closed"),
      subtext: capa?.closed_at ? formatDate(capa.closed_at) : "Not closed",
    },
  ];
}

function CommandCard({
  label,
  value,
  subtext,
  tone,
}: {
  label: string;
  value: number | string;
  subtext: string;
  tone: keyof typeof toneMap;
}) {
  return (
    <div style={commandCardStyle(tone)}>
      <div style={cardLabelStyle}>{label}</div>
      <div style={cardValueStyle(tone)}>{value}</div>
      <div style={cardSubtextStyle}>{subtext}</div>
    </div>
  );
}

function formatAction(action?: string) {
  if (!action) return "Unknown Action";
  return action
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function statusTone(status?: string): keyof typeof toneMap {
  const s = (status || "").toLowerCase();
  if (s === "closed") return "green";
  if (s === "overdue") return "red";
  if (s === "pending_review") return "amber";
  if (s === "in_progress") return "blue";
  if (s === "open") return "purple";
  return "slate";
}

const toneMap = {
  slate: "#334155",
  blue: "#1d4ed8",
  green: "#166534",
  amber: "#a16207",
  purple: "#7e22ce",
  red: "#991b1b",
};

const panelStyle: CSSProperties = {
  margin: "20px 0",
  padding: "22px",
  borderRadius: "20px",
  border: "1px solid #bae6fd",
  background: "linear-gradient(135deg, #f0f9ff 0%, #ffffff 100%)",
  boxShadow: "0 16px 36px rgba(15, 23, 42, 0.10)",
};

const eyebrowStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 900,
  color: "#0369a1",
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
    fontWeight: 900,
    cursor: loading ? "not-allowed" : "pointer",
    background: loading ? "#94a3b8" : "#0284c7",
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
  fontWeight: 800,
};

const cardGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "12px",
  marginTop: "18px",
};

function commandCardStyle(tone: keyof typeof toneMap): CSSProperties {
  return {
    padding: "14px",
    borderRadius: "16px",
    background: "#ffffff",
    border: `1px solid ${toneMap[tone]}33`,
    boxShadow: "0 8px 20px rgba(15, 23, 42, 0.07)",
  };
}

const cardLabelStyle: CSSProperties = {
  fontSize: "12px",
  color: "#64748b",
  fontWeight: 900,
};

function cardValueStyle(tone: keyof typeof toneMap): CSSProperties {
  return {
    marginTop: "6px",
    fontSize: "24px",
    fontWeight: 950,
    color: toneMap[tone],
    wordBreak: "break-word",
  };
}

const cardSubtextStyle: CSSProperties = {
  marginTop: "6px",
  fontSize: "13px",
  color: "#475569",
  lineHeight: 1.45,
};

const workflowStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "10px",
  marginTop: "18px",
};

function workflowStepStyle(complete: boolean): CSSProperties {
  return {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "12px",
    borderRadius: "14px",
    background: complete ? "#ecfdf5" : "#f8fafc",
    border: complete ? "1px solid #bbf7d0" : "1px solid #e2e8f0",
  };
}

function workflowCircleStyle(complete: boolean): CSSProperties {
  return {
    width: "28px",
    height: "28px",
    borderRadius: "999px",
    display: "grid",
    placeItems: "center",
    color: "#ffffff",
    background: complete ? "#16a34a" : "#94a3b8",
    fontWeight: 900,
    flexShrink: 0,
  };
}

const workflowLabelStyle: CSSProperties = {
  fontWeight: 900,
  color: "#0f172a",
};

const workflowSubtextStyle: CSSProperties = {
  marginTop: "2px",
  color: "#64748b",
  fontSize: "12px",
};

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
