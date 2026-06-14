import { useMemo, useState } from "react";

const sampleFindings = [
  {
    id: "F-1007",
    facility: "ORC",
    department: "Prep and Pack",
    tray: "Orthopedic major set",
    instrument: "Bone cutter",
    vendor: "Acme Surgical",
    findingType: "Rust",
    riskLevel: "High",
    status: "New",
    date: "Today",
  },
  {
    id: "F-1006",
    facility: "St. Francis",
    department: "Decontamination",
    tray: "Laparoscopic set",
    instrument: "Laparoscopic grasper",
    vendor: "Northline Medical",
    findingType: "Blood",
    riskLevel: "Critical",
    status: "Under Review",
    date: "Today",
  },
  {
    id: "F-1005",
    facility: "St. Mary’s",
    department: "Prep and Pack",
    tray: "Spine tray",
    instrument: "Kerrison rongeur",
    vendor: "SterilePro",
    findingType: "Bone fragment",
    riskLevel: "Critical",
    status: "CAPA Needed",
    date: "Yesterday",
  },
  {
    id: "F-1004",
    facility: "Memorial Regional",
    department: "Sterilization",
    tray: "Minor procedure set",
    instrument: "Forceps",
    vendor: "Acme Surgical",
    findingType: "Discoloration",
    riskLevel: "Medium",
    status: "New",
    date: "Yesterday",
  },
  {
    id: "F-1003",
    facility: "Southside",
    department: "Sterile Storage",
    tray: "General tray",
    instrument: "Tray liner",
    vendor: "Regional Supply",
    findingType: "Lint",
    riskLevel: "Low",
    status: "Closed",
    date: "2 days ago",
  },
  {
    id: "F-1002",
    facility: "Rappahannock General",
    department: "Prep and Pack",
    tray: "Vascular tray",
    instrument: "Tray basin",
    vendor: "Northline Medical",
    findingType: "Plastic/metal fragment",
    riskLevel: "High",
    status: "CAPA Needed",
    date: "2 days ago",
  },
  {
    id: "F-1001",
    facility: "ORC",
    department: "Decontamination",
    tray: "ENT set",
    instrument: "Suction tip",
    vendor: "SterilePro",
    findingType: "Tissue",
    riskLevel: "High",
    status: "Under Review",
    date: "3 days ago",
  },
  {
    id: "F-1000",
    facility: "Memorial Regional",
    department: "OR",
    tray: "General backup set",
    instrument: "Clamp",
    vendor: "Regional Supply",
    findingType: "Other",
    riskLevel: "Medium",
    status: "New",
    date: "3 days ago",
  },
];

type Finding = typeof sampleFindings[number];

function riskStyle(risk: string): React.CSSProperties {
  if (risk === "Critical") return { ...badge, background: "#450a0a", color: "#fecaca" };
  if (risk === "High") return { ...badge, background: "#7f1d1d", color: "#fecaca" };
  if (risk === "Medium") return { ...badge, background: "#78350f", color: "#fde68a" };
  return { ...badge, background: "#064e3b", color: "#a7f3d0" };
}

function statusStyle(status: string): React.CSSProperties {
  if (status === "CAPA Needed") return { ...badge, background: "#1e3a8a", color: "#bfdbfe" };
  if (status === "Under Review") return { ...badge, background: "#4c1d95", color: "#ddd6fe" };
  if (status === "Closed") return { ...badge, background: "#065f46", color: "#bbf7d0" };
  return { ...badge, background: "#374151", color: "#e5e7eb" };
}

export default function FindingsQueuePage() {
  const [findings, setFindings] = useState<Finding[]>(sampleFindings);
  const [notice, setNotice] = useState("");

  const summary = useMemo(() => {
    return {
      total: findings.length,
      highCritical: findings.filter((finding) => ["High", "Critical"].includes(finding.riskLevel)).length,
      capaNeeded: findings.filter((finding) => finding.status === "CAPA Needed").length,
      closed: findings.filter((finding) => finding.status === "Closed").length,
    };
  }, [findings]);

  function updateStatus(id: string, status: string, action: string) {
    setFindings((current) =>
      current.map((finding) => finding.id === id ? { ...finding, status } : finding)
    );
    setNotice(`${action} saved in pilot mode for finding ${id}.`);
  }

  return (
    <main style={pageShell}>
      <section style={hero}>
        <nav style={topNav} aria-label="Findings navigation">
          <a href="/operations" style={navLink}>Operations Dashboard</a>
          <a href="/inspection/new" style={navLink}>New Inspection</a>
          <a href="/capa" style={navLink}>CAPA Queue</a>
          <a href="/analytics" style={navLink}>Analytics</a>
          <a href="/" style={navLink}>Public Landing</a>
        </nav>

        <p style={eyebrow}>Daily review queue</p>
        <h1 style={title}>Findings Queue</h1>
        <p style={subtitle}>Review, prioritize, and route SPD quality findings for action.</p>
      </section>

      <section style={summaryGrid} aria-label="Findings summary">
        <SummaryCard label="Total Findings" value={summary.total} tone="#38bdf8" />
        <SummaryCard label="High/Critical Findings" value={summary.highCritical} tone="#f87171" />
        <SummaryCard label="CAPA Needed" value={summary.capaNeeded} tone="#a78bfa" />
        <SummaryCard label="Closed Findings" value={summary.closed} tone="#34d399" />
      </section>

      <section style={panel}>
        <div style={panelHeader}>
          <div>
            <h2 style={panelTitle}>Review Worklist</h2>
            <p style={panelHint}>Pilot sample findings for daily SPD review and routing.</p>
          </div>
        </div>

        {notice ? <div style={noticeBox}>{notice}</div> : null}

        <div style={tableWrap}>
          <table style={table}>
            <thead>
              <tr>
                <th style={th}>ID</th>
                <th style={th}>Facility</th>
                <th style={th}>Department</th>
                <th style={th}>Tray</th>
                <th style={th}>Instrument</th>
                <th style={th}>Vendor</th>
                <th style={th}>Finding Type</th>
                <th style={th}>Risk Level</th>
                <th style={th}>Status</th>
                <th style={th}>Date</th>
                <th style={th}>Action</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((finding) => (
                <tr key={finding.id} style={tr}>
                  <td style={tdStrong}>{finding.id}</td>
                  <td style={td}>{finding.facility}</td>
                  <td style={td}>{finding.department}</td>
                  <td style={td}>{finding.tray}</td>
                  <td style={td}>{finding.instrument}</td>
                  <td style={td}>{finding.vendor}</td>
                  <td style={td}>{finding.findingType}</td>
                  <td style={td}><span style={riskStyle(finding.riskLevel)}>{finding.riskLevel}</span></td>
                  <td style={td}><span style={statusStyle(finding.status)}>{finding.status}</span></td>
                  <td style={tdMuted}>{finding.date}</td>
                  <td style={td}>
                    <div style={actionGroup}>
                      <button type="button" style={smallButton} onClick={() => updateStatus(finding.id, "Under Review", "Review")}>Review</button>
                      <button type="button" style={smallButton} onClick={() => updateStatus(finding.id, "CAPA Needed", "Create CAPA")}>Create CAPA</button>
                      <button type="button" style={smallButton} onClick={() => updateStatus(finding.id, "Closed", "Close")}>Close</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

function SummaryCard({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div style={{ ...summaryCard, borderColor: `${tone}66` }}>
      <div style={{ ...summaryAccent, background: tone }} />
      <div style={summaryLabel}>{label}</div>
      <div style={summaryValue}>{value}</div>
    </div>
  );
}

const pageShell: React.CSSProperties = {
  minHeight: "100vh",
  padding: "28px",
  background: "linear-gradient(180deg, #07111f 0%, #0f172a 48%, #111827 100%)",
  color: "#e5e7eb",
  fontFamily: "Arial, sans-serif",
};

const hero: React.CSSProperties = {
  maxWidth: "1360px",
  margin: "0 auto 22px",
};

const topNav: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  flexWrap: "wrap",
  marginBottom: "22px",
};

const navLink: React.CSSProperties = {
  color: "#cbd5e1",
  textDecoration: "none",
  fontWeight: 800,
  padding: "10px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(148, 163, 184, 0.24)",
  background: "rgba(15, 23, 42, 0.72)",
};

const eyebrow: React.CSSProperties = {
  margin: "0 0 10px",
  color: "#67e8f9",
  fontWeight: 900,
  textTransform: "uppercase",
  fontSize: "13px",
};

const title: React.CSSProperties = {
  margin: 0,
  color: "#ffffff",
  fontSize: "42px",
  lineHeight: 1.08,
};

const subtitle: React.CSSProperties = {
  maxWidth: "780px",
  color: "#cbd5e1",
  fontSize: "17px",
  lineHeight: 1.6,
};

const summaryGrid: React.CSSProperties = {
  maxWidth: "1360px",
  margin: "0 auto 18px",
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
  gap: "14px",
};

const summaryCard: React.CSSProperties = {
  position: "relative",
  overflow: "hidden",
  border: "1px solid rgba(148, 163, 184, 0.22)",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.78)",
  padding: "18px",
  minHeight: "106px",
};

const summaryAccent: React.CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  height: "3px",
};

const summaryLabel: React.CSSProperties = {
  color: "#94a3b8",
  fontSize: "13px",
  fontWeight: 800,
  textTransform: "uppercase",
};

const summaryValue: React.CSSProperties = {
  marginTop: "16px",
  color: "#ffffff",
  fontSize: "34px",
  fontWeight: 900,
};

const panel: React.CSSProperties = {
  maxWidth: "1360px",
  margin: "0 auto",
  border: "1px solid rgba(148, 163, 184, 0.22)",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.82)",
  padding: "18px",
};

const panelHeader: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "16px",
  marginBottom: "14px",
};

const panelTitle: React.CSSProperties = {
  margin: 0,
  color: "#ffffff",
  fontSize: "20px",
};

const panelHint: React.CSSProperties = {
  margin: "8px 0 0",
  color: "#94a3b8",
  fontSize: "14px",
};

const noticeBox: React.CSSProperties = {
  marginBottom: "14px",
  padding: "12px 14px",
  borderRadius: "8px",
  border: "1px solid rgba(56, 189, 248, 0.36)",
  background: "rgba(14, 116, 144, 0.18)",
  color: "#cffafe",
  fontWeight: 700,
};

const tableWrap: React.CSSProperties = {
  overflowX: "auto",
};

const table: React.CSSProperties = {
  width: "100%",
  minWidth: "1120px",
  borderCollapse: "collapse",
};

const th: React.CSSProperties = {
  textAlign: "left",
  color: "#94a3b8",
  fontSize: "12px",
  textTransform: "uppercase",
  padding: "12px",
  borderBottom: "1px solid rgba(148, 163, 184, 0.22)",
};

const tr: React.CSSProperties = {
  borderBottom: "1px solid rgba(148, 163, 184, 0.14)",
};

const td: React.CSSProperties = {
  padding: "13px 12px",
  color: "#e5e7eb",
  verticalAlign: "top",
};

const tdStrong: React.CSSProperties = {
  ...td,
  color: "#ffffff",
  fontWeight: 800,
};

const tdMuted: React.CSSProperties = {
  ...td,
  color: "#cbd5e1",
};

const badge: React.CSSProperties = {
  display: "inline-block",
  padding: "5px 9px",
  borderRadius: "999px",
  fontSize: "12px",
  fontWeight: 900,
  whiteSpace: "nowrap",
};

const actionGroup: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "8px",
};

const smallButton: React.CSSProperties = {
  border: "1px solid rgba(148, 163, 184, 0.32)",
  borderRadius: "8px",
  background: "rgba(30, 41, 59, 0.84)",
  color: "#e5e7eb",
  cursor: "pointer",
  fontWeight: 800,
  padding: "8px 10px",
};
