const capaRows = [
  {
    id: "CAPA-204",
    sourceFinding: "F-1006",
    facility: "St. Francis",
    instrument: "Laparoscopic grasper",
    findingType: "Blood",
    riskLevel: "Critical",
    owner: "SPD Manager",
    dueDate: "Today",
    status: "Open",
  },
  {
    id: "CAPA-203",
    sourceFinding: "F-1005",
    facility: "St. Mary’s",
    instrument: "Kerrison rongeur",
    findingType: "Bone fragment",
    riskLevel: "Critical",
    owner: "Quality Lead",
    dueDate: "Tomorrow",
    status: "In Progress",
  },
  {
    id: "CAPA-202",
    sourceFinding: "F-1007",
    facility: "ORC",
    instrument: "Bone cutter",
    findingType: "Rust",
    riskLevel: "High",
    owner: "Shift Supervisor",
    dueDate: "Jun 17",
    status: "Pending Verification",
  },
  {
    id: "CAPA-201",
    sourceFinding: "F-1002",
    facility: "Rappahannock General",
    instrument: "Tray basin",
    findingType: "Plastic/metal fragment",
    riskLevel: "High",
    owner: "SPD Manager",
    dueDate: "Overdue",
    status: "Overdue",
  },
  {
    id: "CAPA-200",
    sourceFinding: "F-1003",
    facility: "Southside",
    instrument: "Tray liner",
    findingType: "Lint",
    riskLevel: "Low",
    owner: "Quality Tech",
    dueDate: "Jun 12",
    status: "Closed",
  },
  {
    id: "CAPA-199",
    sourceFinding: "F-1004",
    facility: "Memorial Regional",
    instrument: "Forceps",
    findingType: "Discoloration",
    riskLevel: "Medium",
    owner: "Shift Supervisor",
    dueDate: "Jun 18",
    status: "In Progress",
  },
  {
    id: "CAPA-198",
    sourceFinding: "F-1001",
    facility: "ORC",
    instrument: "Suction tip",
    findingType: "Tissue",
    riskLevel: "High",
    owner: "Quality Lead",
    dueDate: "Jun 19",
    status: "Open",
  },
  {
    id: "CAPA-197",
    sourceFinding: "F-1000",
    facility: "Memorial Regional",
    instrument: "Clamp",
    findingType: "Other",
    riskLevel: "Medium",
    owner: "SPD Manager",
    dueDate: "Jun 20",
    status: "Pending Verification",
  },
];

function riskStyle(risk: string): React.CSSProperties {
  if (risk === "Critical") return { ...badge, background: "#450a0a", color: "#fecaca" };
  if (risk === "High") return { ...badge, background: "#7f1d1d", color: "#fecaca" };
  if (risk === "Medium") return { ...badge, background: "#78350f", color: "#fde68a" };
  return { ...badge, background: "#064e3b", color: "#a7f3d0" };
}

function statusStyle(status: string): React.CSSProperties {
  if (status === "Overdue") return { ...badge, background: "#7f1d1d", color: "#fecaca" };
  if (status === "Pending Verification") return { ...badge, background: "#1e3a8a", color: "#bfdbfe" };
  if (status === "In Progress") return { ...badge, background: "#4c1d95", color: "#ddd6fe" };
  if (status === "Closed") return { ...badge, background: "#065f46", color: "#bbf7d0" };
  return { ...badge, background: "#374151", color: "#e5e7eb" };
}

export default function CapaQueuePage() {
  const openCapas = capaRows.filter((row) => row.status !== "Closed").length;
  const highCritical = capaRows.filter((row) => ["High", "Critical"].includes(row.riskLevel)).length;
  const overdue = capaRows.filter((row) => row.status === "Overdue").length;
  const pendingVerification = capaRows.filter((row) => row.status === "Pending Verification").length;

  return (
    <main style={pageShell}>
      <section style={hero}>
        <nav style={topNav} aria-label="CAPA navigation">
          <a href="/operations" style={navLink}>Operations Dashboard</a>
          <a href="/inspection/new" style={navLink}>New Inspection</a>
          <a href="/findings" style={navLink}>Findings Queue</a>
          <a href="/analytics" style={navLink}>Analytics</a>
          <a href="/" style={navLink}>Public Landing</a>
        </nav>

        <p style={eyebrow}>Corrective action follow-up</p>
        <h1 style={title}>CAPA Queue</h1>
        <p style={subtitle}>Track corrective actions for SPD quality findings.</p>
      </section>

      <section style={summaryGrid} aria-label="CAPA summary">
        <SummaryCard label="Open CAPAs" value={openCapas} tone="#38bdf8" />
        <SummaryCard label="High/Critical CAPAs" value={highCritical} tone="#f87171" />
        <SummaryCard label="Overdue CAPAs" value={overdue} tone="#f59e0b" />
        <SummaryCard label="Pending Verification" value={pendingVerification} tone="#a78bfa" />
      </section>

      <section style={panel}>
        <div style={panelHeader}>
          <div>
            <h2 style={panelTitle}>CAPA Worklist</h2>
            <p style={panelHint}>Pilot sample corrective actions for manager review.</p>
          </div>
        </div>

        <div style={tableWrap}>
          <table style={table}>
            <thead>
              <tr>
                <th style={th}>CAPA ID</th>
                <th style={th}>Source Finding</th>
                <th style={th}>Facility</th>
                <th style={th}>Instrument</th>
                <th style={th}>Finding Type</th>
                <th style={th}>Risk Level</th>
                <th style={th}>Owner</th>
                <th style={th}>Due Date</th>
                <th style={th}>Status</th>
              </tr>
            </thead>
            <tbody>
              {capaRows.map((row) => (
                <tr key={row.id} style={tr}>
                  <td style={tdStrong}>{row.id}</td>
                  <td style={td}>{row.sourceFinding}</td>
                  <td style={td}>{row.facility}</td>
                  <td style={td}>{row.instrument}</td>
                  <td style={td}>{row.findingType}</td>
                  <td style={td}><span style={riskStyle(row.riskLevel)}>{row.riskLevel}</span></td>
                  <td style={td}>{row.owner}</td>
                  <td style={tdMuted}>{row.dueDate}</td>
                  <td style={td}><span style={statusStyle(row.status)}>{row.status}</span></td>
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

const tableWrap: React.CSSProperties = {
  overflowX: "auto",
};

const table: React.CSSProperties = {
  width: "100%",
  minWidth: "1040px",
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
