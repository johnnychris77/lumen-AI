import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "@/lib/api";

interface QueueItem {
  inspection_id: number;
  instrument_type: string;
  facility_name: string | null;
  workflow_state: string;
  risk_tier: string;
  minutes_waiting: number | null;
}

interface WorkQueue {
  pending_inspections: QueueItem[];
  high_risk_inspections: QueueItem[];
  supervisor_reviews: QueueItem[];
  repair_holds: QueueItem[];
  total_pending: number;
}

const workflowSteps = ["Image Capture", "AI Analysis", "Supervisor Review", "Reclean / Repair", "Completed"];

function riskStyle(risk: string): React.CSSProperties {
  if (risk === "Critical") return { ...badge, background: "#450a0a", color: "#fecaca" };
  if (risk === "High Risk") return { ...badge, background: "#7f1d1d", color: "#fecaca" };
  if (risk === "Moderate Risk") return { ...badge, background: "#78350f", color: "#fde68a" };
  return { ...badge, background: "#064e3b", color: "#a7f3d0" };
}

function statusStyle(status: string): React.CSSProperties {
  if (status === "Repair") return { ...badge, background: "#1e3a8a", color: "#bfdbfe" };
  if (status === "Supervisor Review") return { ...badge, background: "#4c1d95", color: "#ddd6fe" };
  if (status === "Completed") return { ...badge, background: "#065f46", color: "#bbf7d0" };
  return { ...badge, background: "#374151", color: "#e5e7eb" };
}

function formatWait(minutes: number | null): string {
  if (minutes == null) return "—";
  if (minutes < 60) return `${minutes}m ago`;
  return `${Math.floor(minutes / 60)}h ago`;
}

export default function OperationsDashboard() {
  const [queue, setQueue] = useState<WorkQueue | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    apiFetch<WorkQueue>("/api/inspection-work-queue")
      .then((d) => { if (!cancelled) setQueue(d); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); });
    return () => { cancelled = true; };
  }, []);

  const recent = queue?.pending_inspections.slice(0, 8) ?? [];

  return (
    <main style={pageShell}>
      <section style={hero}>
        <div style={banner}>
          Live SPD operations — real inspection, workflow-state, and risk data from the Smart Inspection Queue.
        </div>

        <div style={heroGrid}>
          <div>
            <p style={eyebrow}>Daily SPD workflow</p>
            <h1 style={title}>LumenAI SPD Quality Operations</h1>
            <p style={subtitle}>
              Daily inspection, review, and quality workspace for sterile processing teams.
            </p>
          </div>

          <div style={quickActions} aria-label="Quick actions">
            <Link to="/inspection/new" style={primaryAction}>New Inspection</Link>
            <Link to="/inspection-work-queue" style={secondaryAction}>Smart Work Queue</Link>
            <Link to="/findings" style={secondaryAction}>Findings Queue</Link>
            <Link to="/operations-board" style={secondaryAction}>Operations Board</Link>
          </div>
        </div>
      </section>

      {error && (
        <section style={{ ...panelLarge, marginBottom: 18, borderColor: "rgba(248, 113, 113, 0.4)" }}>
          <p style={{ color: "#fca5a5", margin: 0 }}>Failed to load live operations data: {error}</p>
        </section>
      )}

      {!error && queue === null && (
        <section style={panelLarge}>
          <p style={{ color: "#94a3b8", margin: 0 }}>Loading…</p>
        </section>
      )}

      {queue && (
        <>
          <section style={kpiGrid} aria-label="Operations KPIs">
            <KpiCard label="Pending Inspections" value={String(queue.total_pending)} tone="#38bdf8" />
            <KpiCard label="Supervisor Reviews" value={String(queue.supervisor_reviews.length)} tone="#a78bfa" />
            <KpiCard label="Repair Holds" value={String(queue.repair_holds.length)} tone="#f59e0b" />
            <KpiCard label="High-Risk Inspections" value={String(queue.high_risk_inspections.length)} tone="#f87171" />
          </section>

          <section style={contentGrid}>
            <div style={panelLarge}>
              <div style={panelHeader}>
                <div>
                  <h2 style={panelTitle}>Recent Activity</h2>
                  <p style={panelHint}>Highest-priority pending inspections, live from the Smart Inspection Queue.</p>
                </div>
              </div>

              {recent.length === 0 ? (
                <p style={{ color: "#94a3b8" }}>No pending inspections right now.</p>
              ) : (
                <div style={tableWrap}>
                  <table style={table}>
                    <thead>
                      <tr>
                        <th style={th}>ID</th>
                        <th style={th}>Facility</th>
                        <th style={th}>Instrument</th>
                        <th style={th}>Risk</th>
                        <th style={th}>Status</th>
                        <th style={th}>Waiting</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recent.map((row) => (
                        <tr key={row.inspection_id} style={tr}>
                          <td style={tdStrong}>#{row.inspection_id}</td>
                          <td style={td}>{row.facility_name ?? "—"}</td>
                          <td style={td}>{row.instrument_type}</td>
                          <td style={td}><span style={riskStyle(row.risk_tier)}>{row.risk_tier}</span></td>
                          <td style={td}><span style={statusStyle(row.workflow_state)}>{row.workflow_state}</span></td>
                          <td style={tdMuted}>{formatWait(row.minutes_waiting)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <aside style={panel}>
              <h2 style={panelTitle}>Workflow States</h2>
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
        </>
      )}
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
