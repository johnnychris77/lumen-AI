import { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_BASE ||
  "http://127.0.0.1:18012";


type ExportReadinessCard = {
  key: string;
  title: string;
  ready: boolean;
  status: string;
  url: string;
  description: string;
};

type ExportReadinessStatus = {
  status: string;
  finding_id: number;
  baseline_evidence_count: number;
  approved_baseline_count: number;
  evidence_attachment_count: number;
  readiness_summary: string;
  cards: ExportReadinessCard[];
};

async function fetchExportReadiness(findingId: string): Promise<ExportReadinessStatus> {
  const response = await fetch(`${API_BASE}/api/enterprise/intake/${findingId}/export-readiness-status`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-LumenAI-Role": "viewer",
      "X-LumenAI-Actor": "john-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Export readiness failed (${response.status})`);
  }

  return data;
}


export default function PacketActionButtonsPanel() {
  const [findingId, setFindingId] = useState("2");
  const [readiness, setReadiness] = useState<ExportReadinessStatus | null>(null);
  const [readinessError, setReadinessError] = useState("");
  const [readinessLoading, setReadinessLoading] = useState(false);

  async function loadReadiness() {
    setReadinessLoading(true);
    setReadinessError("");

    try {
      const data = await fetchExportReadiness(findingId);
      setReadiness(data);
    } catch (err) {
      setReadinessError(err instanceof Error ? err.message : "Unknown export readiness error");
    } finally {
      setReadinessLoading(false);
    }
  }

  useEffect(() => {
    loadReadiness();
  }, []);

  const [lastExport, setLastExport] = useState("");

  function recordExport(label: string) {
    const timestamp = new Date().toLocaleString();
    setLastExport(`${label} export opened for Finding #${findingId} at ${timestamp}. This action is audit-tracked by the backend when the export endpoint is requested.`);
  }

  function scrollToAuditTrail() {
    const auditTrail = document.getElementById("enterprise-audit-trail");
    if (auditTrail) {
      auditTrail.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  const governanceZipUrl = `${API_BASE}/api/enterprise/intake/${findingId}/governance-zip-bundle`;
  const vendorPdfUrl = `${API_BASE}/api/enterprise/intake/${findingId}/vendor-escalation-packet.pdf`;
  const ipPdfUrl = `${API_BASE}/api/enterprise/intake/${findingId}/infection-prevention-review-packet.pdf`;
  const executivePdfUrl = `${API_BASE}/api/enterprise/executive-quality-review-dashboard.pdf`;

  return (
    <section style={panelStyle}>
      <div>
        <div style={eyebrowStyle}>Packet Exports</div>
        <h2 style={titleStyle}>Governance & Review Export Actions</h2>
        <p style={subtitleStyle}>
          Download audit-ready governance, vendor escalation, infection prevention, and executive review packets.
        </p>
      </div>

      <div style={readinessHeaderStyle}>
        <div>
          <strong>Export Readiness Status</strong>
          <p style={readinessSummaryStyle}>
            {readiness?.readiness_summary || "Load export readiness to confirm available packets."}
          </p>
        </div>
        <button type="button" onClick={loadReadiness} disabled={readinessLoading} style={readinessButtonStyle}>
          {readinessLoading ? "Checking..." : "Check Readiness"}
        </button>
      </div>

      {readinessError ? <div style={readinessErrorStyle}>{readinessError}</div> : null}

      <div style={exportStatusGridStyle}>
        {(readiness?.cards || fallbackCards).map((card) => (
          <ExportStatusCard
            key={card.key}
            title={card.title}
            status={card.status}
            description={card.description}
            intent={card.ready ? "ready" : "warning"}
          />
        ))}
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

        <a href={governanceZipUrl} target="_blank" rel="noreferrer" style={primaryButtonStyle} onClick={() => recordExport("Governance ZIP Bundle")}>
          Download Governance ZIP
        </a>

        <a href={vendorPdfUrl} target="_blank" rel="noreferrer" style={warningButtonStyle} onClick={() => recordExport("Vendor Escalation PDF")}>
          Download Vendor PDF
        </a>

        <a href={ipPdfUrl} target="_blank" rel="noreferrer" style={infoButtonStyle} onClick={() => recordExport("Infection Prevention PDF")}>
          Download IP PDF
        </a>

        <a href={executivePdfUrl} target="_blank" rel="noreferrer" style={executiveButtonStyle} onClick={() => recordExport("Executive Quality PDF")}>
          Download Executive PDF
        </a>
      </div>

      {lastExport ? (
        <div style={confirmationStyle}>
          <strong>Export confirmation</strong>
          <p style={confirmationTextStyle}>{lastExport}</p>
          <p style={confirmationTextStyle}>
            Review the Enterprise Audit Trail panel to verify the backend audit event after the export completes.
          </p>
          <button type="button" onClick={scrollToAuditTrail} style={auditTrailButtonStyle}>
            View Audit Trail
          </button>
        </div>
      ) : null}
    </section>
  );
}

const fallbackCards: ExportReadinessCard[] = [
  {
    key: "governance_zip",
    title: "Governance ZIP Bundle",
    ready: true,
    status: "Ready",
    url: "",
    description: "Includes JSON packet, baseline evidence, evidence attachments, PDF summary, manifest, and README.",
  },
  {
    key: "vendor_escalation_pdf",
    title: "Vendor Escalation PDF",
    ready: true,
    status: "Ready",
    url: "",
    description: "Vendor-facing quality packet with finding context, baseline evidence, and recommended vendor action.",
  },
  {
    key: "infection_prevention_pdf",
    title: "Infection Prevention PDF",
    ready: true,
    status: "Ready",
    url: "",
    description: "IP-ready packet with patient-safety signal, infection-risk signal, and recommended documentation.",
  },
  {
    key: "executive_quality_pdf",
    title: "Executive Quality PDF",
    ready: true,
    status: "Ready",
    url: "",
    description: "Leadership-ready summary of findings, quality signal, vendor signals, CAPA status, and actions.",
  },
];

function ExportStatusCard({
  title,
  status,
  description,
  intent,
}: {
  title: string;
  status: string;
  description: string;
  intent: "ready" | "warning" | "error";
}) {
  return (
    <div style={exportStatusCardStyle(intent)}>
      <div style={exportStatusHeaderStyle}>
        <strong>{title}</strong>
        <span style={exportStatusBadgeStyle(intent)}>{status}</span>
      </div>
      <p style={exportStatusDescriptionStyle}>{description}</p>
    </div>
  );
}

const readinessHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
  marginTop: "16px",
  padding: "12px",
  borderRadius: "16px",
  background: "#f8fafc",
  border: "1px solid #e2e8f0",
};

const readinessSummaryStyle: React.CSSProperties = {
  margin: "4px 0 0",
  color: "#475569",
  lineHeight: 1.45,
};

const readinessButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#7c3aed",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
  whiteSpace: "nowrap",
};

const readinessErrorStyle: React.CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 800,
};

const exportStatusGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
  gap: "12px",
  marginTop: "16px",
};

function exportStatusCardStyle(intent: "ready" | "warning" | "error"): React.CSSProperties {
  const palette = {
    ready: { border: "#bbf7d0", background: "#f0fdf4" },
    warning: { border: "#fed7aa", background: "#fff7ed" },
    error: { border: "#fecaca", background: "#fef2f2" },
  }[intent];

  return {
    padding: "14px",
    borderRadius: "16px",
    border: `1px solid ${palette.border}`,
    background: palette.background,
  };
}

const exportStatusHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "10px",
  alignItems: "center",
  color: "#0f172a",
};

function exportStatusBadgeStyle(intent: "ready" | "warning" | "error"): React.CSSProperties {
  const palette = {
    ready: { background: "#dcfce7", color: "#166534" },
    warning: { background: "#ffedd5", color: "#9a3412" },
    error: { background: "#fee2e2", color: "#991b1b" },
  }[intent];

  return {
    borderRadius: "999px",
    padding: "4px 8px",
    fontSize: "12px",
    fontWeight: 900,
    background: palette.background,
    color: palette.color,
    whiteSpace: "nowrap",
  };
}

const exportStatusDescriptionStyle: React.CSSProperties = {
  margin: "8px 0 0",
  color: "#475569",
  lineHeight: 1.45,
  fontSize: "13px",
};

const panelStyle: React.CSSProperties = {
  padding: "20px",
  borderRadius: "22px",
  background: "#ffffff",
  border: "1px solid #e2e8f0",
  boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
};

const eyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#7c3aed",
};

const titleStyle: React.CSSProperties = {
  margin: "4px 0",
  fontSize: "24px",
  fontWeight: 900,
  color: "#0f172a",
};

const subtitleStyle: React.CSSProperties = {
  margin: 0,
  color: "#475569",
  lineHeight: 1.5,
};

const controlRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  alignItems: "end",
  flexWrap: "wrap",
  marginTop: "16px",
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

const baseButtonStyle: React.CSSProperties = {
  borderRadius: "14px",
  padding: "11px 14px",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
};

const primaryButtonStyle: React.CSSProperties = {
  ...baseButtonStyle,
  background: "#ede9fe",
  color: "#5b21b6",
};

const warningButtonStyle: React.CSSProperties = {
  ...baseButtonStyle,
  background: "#ffedd5",
  color: "#9a3412",
};

const infoButtonStyle: React.CSSProperties = {
  ...baseButtonStyle,
  background: "#e0f2fe",
  color: "#075985",
};

const executiveButtonStyle: React.CSSProperties = {
  ...baseButtonStyle,
  background: "#dbeafe",
  color: "#1e40af",
};


const confirmationStyle: React.CSSProperties = {
  marginTop: "14px",
  padding: "12px 14px",
  borderRadius: "16px",
  border: "1px solid #bbf7d0",
  background: "#f0fdf4",
  color: "#166534",
};

const confirmationTextStyle: React.CSSProperties = {
  margin: "6px 0 0",
  lineHeight: 1.5,
};


const auditTrailButtonStyle: React.CSSProperties = {
  marginTop: "10px",
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#166534",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};
