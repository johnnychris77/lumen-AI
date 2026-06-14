const activityRows = [
  {
    id: "SPD-1042",
    facility: "ORC",
    instrument: "Laparoscopic grasper",
    finding: "Blood residue flagged",
    risk: "High",
    status: "Review",
    date: "Today",
  },
  {
    id: "SPD-1041",
    facility: "St. Francis",
    instrument: "Orthopedic cutter",
    finding: "Rust on hinge",
    risk: "High",
    status: "CAPA",
    date: "Today",
  },
  {
    id: "SPD-1039",
    facility: "Memorial Regional",
    instrument: "Forceps",
    finding: "Discoloration",
    risk: "Medium",
    status: "Open",
    date: "Yesterday",
  },
  {
    id: "SPD-1037",
    facility: "Southside",
    instrument: "Tray liner",
    finding: "Lint found during pack",
    risk: "Low",
    status: "Closed",
    date: "2 days ago",
  },
];

const workflowSteps = ["Capture", "Classify", "Review", "CAPA", "Close"];

function riskStyle(risk: string): React.CSSProperties {
  if (risk === "High") {
    return { ...badge, background: "#7f1d1d", color: "#fecaca" };
  }
  if (risk === "Medium") {
    return { ...badge, background: "#78350f", color: "#fde68a" };
  }
  return { ...badge, background: "#064e3b", color: "#a7f3d0" };
}

function statusStyle(status: string): React.CSSProperties {
  if (status === "CAPA") {
    return { ...badge, background: "#1e3a8a", color: "#bfdbfe" };
  }
  if (status === "Review") {
    return { ...badge, background: "#4c1d95", color: "#ddd6fe" };
  }
  if (status === "Closed") {
    return { ...badge, background: "#065f46", color: "#bbf7d0" };
  }
  return { ...badge, background: "#374151", color: "#e5e7eb" };
}

export default function OperationsDashboard() {
  return (
    <main style={pageShell}>
      <section style={hero}>
        <nav style={topNav} aria-label="Operations navigation">
          <a href="/" style={navLink}>Public Landing</a>
          <a href="/dashboard" style={navLink}>Dashboard</a>
          <a href="/operations" style={activeNavLink}>Operations</a>
        </nav>

        <div style={banner}>
          Pilot mode: focused on inspection, findings, CAPA, and quality trend workflow.
        </div>

        <div style={heroGrid}>
          <div>
            <p style={eyebrow}>Daily SPD workflow</p>
            <h1 style={title}>LumenAI SPD Quality Operations</h1>
            <p style={subtitle}>
              Daily inspection, findings, CAPA, and quality review workspace for sterile processing teams.
            </p>
          </div>

          <div style={quickActions} aria-label="Quick actions">
            <a href="/inspection/new" style={primaryAction}>New Inspection</a>
            <a href="/findings" style={secondaryAction}>Findings Queue</a>
            <a href="/capa" style={secondaryAction}>CAPA Queue</a>
            <a href="/analytics" style={secondaryAction}>Analytics</a>
          </div>
        </div>
      </section>

      <section style={kpiGrid} aria-label="Operations KPIs">
        <KpiCard label="Open Findings" value="18" tone="#38bdf8" />
        <KpiCard label="Open CAPAs" value="6" tone="#a78bfa" />
        <KpiCard label="Pending Reviews" value="9" tone="#f59e0b" />
        <KpiCard label="High-Risk Events" value="4" tone="#f87171" />
      </section>

      <section style={contentGrid}>
        <div style={panelLarge}>
          <div style={panelHeader}>
            <div>
              <h2 style={panelTitle}>Recent Activity</h2>
              <p style={panelHint}>Pilot-safe sample activity for daily review.</p>
            </div>
          </div>

          <div style={tableWrap}>
            <table style={table}>
              <thead>
                <tr>
                  <th style={th}>ID</th>
                  <th style={th}>Facility</th>
                  <th style={th}>Instrument</th>
                  <th style={th}>Finding</th>
                  <th style={th}>Risk</th>
                  <th style={th}>Status</th>
                  <th style={th}>Date</th>
                </tr>
              </thead>
              <tbody>
                {activityRows.map((row) => (
                  <tr key={row.id} style={tr}>
                    <td style={tdStrong}>{row.id}</td>
                    <td style={td}>{row.facility}</td>
                    <td style={td}>{row.instrument}</td>
                    <td style={td}>{row.finding}</td>
                    <td style={td}><span style={riskStyle(row.risk)}>{row.risk}</span></td>
                    <td style={td}><span style={statusStyle(row.status)}>{row.status}</span></td>
                    <td style={tdMuted}>{row.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <aside style={panel}>
          <h2 style={panelTitle}>Pilot Workflow</h2>
          <div style={workflowList}>
            {workflowSteps.map((step, index) => (
              <div key={step} style={workflowStep}>
                <span style={stepNumber}>{index + 1}</span>
                <span>{step}</span>
              </div>
            ))}
          </div>
        </aside>
      </section>
    </main>
  );
}

function KpiCard({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div style={{ ...kpiCard, borderColor: `${tone}66` }}>
      <div style={{ ...kpiAccent, background: tone }} />
      <div style={kpiLabel}>{label}</div>
      <div style={kpiValue}>{value}</div>
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
  marginBottom: "18px",
};

const navLink: React.CSSProperties = {
  color: "#cbd5e1",
  textDecoration: "none",
  fontWeight: 700,
  padding: "9px 12px",
};

const activeNavLink: React.CSSProperties = {
  ...navLink,
  color: "#ffffff",
  borderBottom: "2px solid #38bdf8",
};

const banner: React.CSSProperties = {
  border: "1px solid rgba(56, 189, 248, 0.42)",
  background: "rgba(14, 116, 144, 0.2)",
  color: "#cffafe",
  padding: "12px 16px",
  borderRadius: "8px",
  marginBottom: "22px",
  fontWeight: 700,
};

const heroGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))",
  gap: "24px",
  alignItems: "end",
};

const eyebrow: React.CSSProperties = {
  margin: "0 0 10px",
  color: "#67e8f9",
  fontWeight: 800,
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
  maxWidth: "760px",
  color: "#cbd5e1",
  fontSize: "17px",
  lineHeight: 1.6,
};

const quickActions: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "10px",
};

const primaryAction: React.CSSProperties = {
  gridColumn: "1 / -1",
  textAlign: "center",
  padding: "12px 14px",
  borderRadius: "8px",
  background: "#38bdf8",
  color: "#082f49",
  textDecoration: "none",
  fontWeight: 900,
};

const secondaryAction: React.CSSProperties = {
  textAlign: "center",
  padding: "11px 12px",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.78)",
  border: "1px solid rgba(148, 163, 184, 0.26)",
  color: "#e2e8f0",
  textDecoration: "none",
  fontWeight: 800,
};

const kpiGrid: React.CSSProperties = {
  maxWidth: "1360px",
  margin: "0 auto 22px",
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
  gap: "14px",
};

const kpiCard: React.CSSProperties = {
  position: "relative",
  overflow: "hidden",
  border: "1px solid rgba(148, 163, 184, 0.22)",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.78)",
  padding: "18px",
  minHeight: "110px",
};

const kpiAccent: React.CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  height: "3px",
};

const kpiLabel: React.CSSProperties = {
  color: "#94a3b8",
  fontSize: "13px",
  fontWeight: 800,
  textTransform: "uppercase",
};

const kpiValue: React.CSSProperties = {
  marginTop: "16px",
  color: "#ffffff",
  fontSize: "34px",
  fontWeight: 900,
};

const contentGrid: React.CSSProperties = {
  maxWidth: "1360px",
  margin: "0 auto",
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))",
  gap: "18px",
};

const panelLarge: React.CSSProperties = {
  border: "1px solid rgba(148, 163, 184, 0.22)",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.82)",
  padding: "18px",
};

const panel: React.CSSProperties = {
  ...panelLarge,
  alignSelf: "start",
};

const panelHeader: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "16px",
  alignItems: "start",
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
  minWidth: "840px",
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

const workflowList: React.CSSProperties = {
  display: "grid",
  gap: "12px",
  marginTop: "18px",
};

const workflowStep: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "12px",
  padding: "13px",
  borderRadius: "8px",
  background: "rgba(30, 41, 59, 0.82)",
  color: "#e5e7eb",
  fontWeight: 800,
};

const stepNumber: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: "28px",
  height: "28px",
  borderRadius: "999px",
  background: "#38bdf8",
  color: "#082f49",
  fontWeight: 900,
};
