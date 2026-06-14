const findingTypeStats = [
  { label: "Rust", value: 7 },
  { label: "Blood", value: 5 },
  { label: "Bone fragment", value: 4 },
  { label: "Discoloration", value: 6 },
  { label: "Lint", value: 8 },
  { label: "Plastic/metal fragment", value: 3 },
  { label: "Tissue", value: 4 },
  { label: "Other", value: 2 },
];

const facilityStats = [
  { label: "ORC", value: 11 },
  { label: "St. Francis", value: 8 },
  { label: "St. Mary’s", value: 7 },
  { label: "Memorial Regional", value: 6 },
  { label: "Southside", value: 4 },
  { label: "Rappahannock General", value: 3 },
];

const riskStats = [
  { label: "Low", value: 9 },
  { label: "Medium", value: 13 },
  { label: "High", value: 12 },
  { label: "Critical", value: 5 },
];

const capaStats = [
  { label: "Open", value: 6 },
  { label: "In Progress", value: 5 },
  { label: "Pending Verification", value: 4 },
  { label: "Closed", value: 9 },
  { label: "Overdue", value: 2 },
];

const activityTrend = [
  { label: "Mon", inspections: 18, findings: 7 },
  { label: "Tue", inspections: 21, findings: 9 },
  { label: "Wed", inspections: 19, findings: 8 },
  { label: "Thu", inspections: 24, findings: 10 },
  { label: "Fri", inspections: 17, findings: 5 },
];

const maxFindingType = Math.max(...findingTypeStats.map((item) => item.value));
const maxFacility = Math.max(...facilityStats.map((item) => item.value));
const maxRisk = Math.max(...riskStats.map((item) => item.value));
const maxCapa = Math.max(...capaStats.map((item) => item.value));
const maxActivity = Math.max(...activityTrend.map((item) => Math.max(item.inspections, item.findings)));

export default function AnalyticsDashboardPage() {
  const totalFindings = findingTypeStats.reduce((total, item) => total + item.value, 0);
  const highCritical = riskStats
    .filter((item) => item.label === "High" || item.label === "Critical")
    .reduce((total, item) => total + item.value, 0);
  const openCapas = capaStats
    .filter((item) => item.label !== "Closed")
    .reduce((total, item) => total + item.value, 0);
  const closedCapas = capaStats.find((item) => item.label === "Closed")?.value || 0;
  const totalInspections = activityTrend.reduce((total, item) => total + item.inspections, 0);

  return (
    <main style={pageShell}>
      <section style={hero}>
        <nav style={topNav} aria-label="Analytics navigation">
          <a href="/operations" style={navLink}>Operations Dashboard</a>
          <a href="/inspection/new" style={navLink}>New Inspection</a>
          <a href="/findings" style={navLink}>Findings Queue</a>
          <a href="/capa" style={navLink}>CAPA Queue</a>
          <a href="/" style={navLink}>Public Landing</a>
        </nav>

        <p style={eyebrow}>Pilot performance</p>
        <h1 style={title}>Quality Analytics</h1>
        <p style={subtitle}>
          Track SPD quality trends, high-risk findings, CAPA activity, and pilot performance.
        </p>
      </section>

      <section style={summaryGrid} aria-label="Quality analytics summary">
        <SummaryCard label="Total Inspections" value={totalInspections} tone="#38bdf8" />
        <SummaryCard label="Total Findings" value={totalFindings} tone="#a78bfa" />
        <SummaryCard label="High/Critical Findings" value={highCritical} tone="#f87171" />
        <SummaryCard label="Open CAPAs" value={openCapas} tone="#f59e0b" />
        <SummaryCard label="Closed CAPAs" value={closedCapas} tone="#34d399" />
      </section>

      <section style={analyticsGrid}>
        <Panel title="Findings by Type">
          {findingTypeStats.map((item) => <BarRow key={item.label} item={item} max={maxFindingType} />)}
        </Panel>

        <Panel title="Findings by Facility">
          {facilityStats.map((item) => <BarRow key={item.label} item={item} max={maxFacility} />)}
        </Panel>

        <Panel title="Risk Level Distribution">
          {riskStats.map((item) => <BarRow key={item.label} item={item} max={maxRisk} />)}
        </Panel>

        <Panel title="CAPA Status Summary">
          {capaStats.map((item) => <BarRow key={item.label} item={item} max={maxCapa} />)}
        </Panel>

        <div style={widePanel}>
          <h2 style={panelTitle}>Pilot Activity Trend</h2>
          <div style={trendGrid}>
            {activityTrend.map((item) => (
              <div key={item.label} style={trendCard}>
                <div style={trendDay}>{item.label}</div>
                <BarLine label="Inspections" value={item.inspections} max={maxActivity} tone="#38bdf8" />
                <BarLine label="Findings" value={item.findings} max={maxActivity} tone="#f87171" />
              </div>
            ))}
          </div>
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

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={panel}>
      <h2 style={panelTitle}>{title}</h2>
      <div style={barList}>{children}</div>
    </section>
  );
}

function BarRow({ item, max }: { item: { label: string; value: number }; max: number }) {
  return (
    <div style={barRow}>
      <div style={barMeta}>
        <span>{item.label}</span>
        <strong>{item.value}</strong>
      </div>
      <div style={barTrack}>
        <div style={{ ...barFill, width: `${Math.max(8, (item.value / max) * 100)}%` }} />
      </div>
    </div>
  );
}

function BarLine({ label, value, max, tone }: { label: string; value: number; max: number; tone: string }) {
  return (
    <div style={barRow}>
      <div style={barMeta}>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div style={barTrack}>
        <div style={{ ...barFill, background: tone, width: `${Math.max(8, (value / max) * 100)}%` }} />
      </div>
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
  maxWidth: "820px",
  color: "#cbd5e1",
  fontSize: "17px",
  lineHeight: 1.6,
};

const summaryGrid: React.CSSProperties = {
  maxWidth: "1360px",
  margin: "0 auto 18px",
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
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

const analyticsGrid: React.CSSProperties = {
  maxWidth: "1360px",
  margin: "0 auto",
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))",
  gap: "18px",
};

const panel: React.CSSProperties = {
  border: "1px solid rgba(148, 163, 184, 0.22)",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.82)",
  padding: "18px",
};

const widePanel: React.CSSProperties = {
  ...panel,
  gridColumn: "1 / -1",
};

const panelTitle: React.CSSProperties = {
  margin: "0 0 16px",
  color: "#ffffff",
  fontSize: "20px",
};

const barList: React.CSSProperties = {
  display: "grid",
  gap: "14px",
};

const barRow: React.CSSProperties = {
  display: "grid",
  gap: "8px",
};

const barMeta: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  color: "#e5e7eb",
  fontWeight: 800,
};

const barTrack: React.CSSProperties = {
  height: "10px",
  borderRadius: "999px",
  background: "rgba(51, 65, 85, 0.86)",
  overflow: "hidden",
};

const barFill: React.CSSProperties = {
  height: "100%",
  borderRadius: "999px",
  background: "#38bdf8",
};

const trendGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
  gap: "14px",
};

const trendCard: React.CSSProperties = {
  display: "grid",
  gap: "12px",
  padding: "14px",
  borderRadius: "8px",
  background: "rgba(30, 41, 59, 0.82)",
};

const trendDay: React.CSSProperties = {
  color: "#ffffff",
  fontWeight: 900,
  fontSize: "18px",
};
