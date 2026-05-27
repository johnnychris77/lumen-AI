import { useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_BASE ||
  "http://127.0.0.1:18012";

export default function PacketActionButtonsPanel() {
  const [findingId, setFindingId] = useState("2");
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
