import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "@/lib/api";

interface QueueItem {
  inspection_id: number;
  instrument_type: string;
  facility_name: string | null;
  workflow_state: string;
  risk_tier: string;
  disposition: string;
  minutes_waiting: number | null;
  assigned_technician: string | null;
}

interface WorkQueue {
  pending_inspections: QueueItem[];
}

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
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

export default function FindingsQueuePage() {
  const [items, setItems] = useState<QueueItem[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    apiFetch<WorkQueue>("/api/inspection-work-queue")
      .then((d) => { if (!cancelled) setItems(d.pending_inspections); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); });
    return () => { cancelled = true; };
  }, []);

  const summary = items
    ? {
        total: items.length,
        highCritical: items.filter((i) => ["High Risk", "Critical"].includes(i.risk_tier)).length,
        repairPending: items.filter((i) => i.workflow_state === "Repair").length,
        supervisorReview: items.filter((i) => i.workflow_state === "Supervisor Review").length,
      }
    : null;

  return (
    <main style={pageShell}>
      <section style={hero}>
        <p style={eyebrow}>Daily review queue</p>
        <h1 style={title}>Findings Queue</h1>
        <p style={subtitle}>Real, live inspections awaiting review or action — backed by the Smart Inspection Queue.</p>
      </section>

      {error && (
        <section style={{ ...panel, marginBottom: 18, borderColor: "rgba(248, 113, 113, 0.4)" }}>
          <p style={{ color: "#fca5a5", margin: 0 }}>Failed to load the findings queue: {error}</p>
        </section>
      )}

      {!error && items === null && (
        <section style={panel}>
          <p style={{ color: "#94a3b8", margin: 0 }}>Loading…</p>
        </section>
      )}

      {summary && (
        <section style={summaryGrid} aria-label="Findings summary">
          <SummaryCard label="Total Pending" value={summary.total} tone="#38bdf8" />
          <SummaryCard label="High/Critical Risk" value={summary.highCritical} tone="#f87171" />
          <SummaryCard label="Awaiting Supervisor Review" value={summary.supervisorReview} tone="#a78bfa" />
          <SummaryCard label="Repair Pending" value={summary.repairPending} tone="#f59e0b" />
        </section>
      )}

      {items && (
        <section style={panel}>
          <div style={panelHeader}>
            <div>
              <h2 style={panelTitle}>Review Worklist</h2>
              <p style={panelHint}>
                Live pending inspections, ranked by priority.{" "}
                <Link to="/inspection-work-queue" style={{ color: "#67e8f9" }}>Open the full Smart Inspection Queue →</Link>
              </p>
            </div>
          </div>

          {items.length === 0 ? (
            <p style={{ color: "#94a3b8" }}>No inspections are currently pending review.</p>
          ) : (
            <div style={tableWrap}>
              <table style={table}>
                <thead>
                  <tr>
                    <th style={th}>Inspection</th>
                    <th style={th}>Facility</th>
                    <th style={th}>Instrument</th>
                    <th style={th}>Risk</th>
                    <th style={th}>Status</th>
                    <th style={th}>Disposition</th>
                    <th style={th}>Waiting</th>
                    <th style={th}>Assigned</th>
                    <th style={th}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.inspection_id} style={tr}>
                      <td style={tdStrong}>#{item.inspection_id}</td>
                      <td style={td}>{item.facility_name ?? "—"}</td>
                      <td style={td}>{item.instrument_type}</td>
                      <td style={td}><span style={riskStyle(item.risk_tier)}>{item.risk_tier}</span></td>
                      <td style={td}><span style={statusStyle(item.workflow_state)}>{item.workflow_state}</span></td>
                      <td style={td}>{item.disposition}</td>
                      <td style={tdMuted}>{formatWait(item.minutes_waiting)}</td>
                      <td style={td}>{item.assigned_technician ?? "Unassigned"}</td>
                      <td style={td}>
                        <Link to={`/inspection/${item.inspection_id}/vision-session`} style={smallButtonLink}>Review →</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
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

const smallButtonLink: React.CSSProperties = {
  border: "1px solid rgba(148, 163, 184, 0.32)",
  borderRadius: "8px",
  background: "rgba(30, 41, 59, 0.84)",
  color: "#e5e7eb",
  cursor: "pointer",
  fontWeight: 800,
  padding: "8px 10px",
  textDecoration: "none",
  display: "inline-block",
};
