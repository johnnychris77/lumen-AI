import React, { useEffect, useState, useCallback } from "react";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token") ?? "";
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

// ── Types ────────────────────────────────────────────────────────────────────

interface InspectionStep {
  id: number;
  step_number: number;
  step_type: string;
  step_title: string;
  step_instructions: string;
  ai_recommendation: string;
  technician_response: string;
  finding_category: string;
  severity: string;
  confidence: number;
  completed_at: string | null;
  notes: string;
}

interface Session {
  id: number;
  technician_id: string;
  instrument_name: string;
  instrument_id: string;
  session_status: string;
  started_at: string;
  completed_at: string | null;
  total_steps: number;
  completed_steps: number;
  copilot_mode: string;
  risk_level: string;
  session_notes: string;
  escalation_reason: string;
  steps: InspectionStep[];
}

interface Escalation {
  id: number;
  session_id: number;
  escalation_type: string;
  severity: string;
  description: string;
  auto_generated: boolean;
  resolved: boolean;
  resolved_by: string;
  created_at: string;
}

interface Dashboard {
  active_sessions: number;
  completed_today: number;
  escalations_open: number;
  escalations_resolved: number;
  avg_session_duration_minutes: number;
  pass_rate_pct: number;
  high_risk_instruments: string[];
  top_finding_categories: { category: string; count: number; pct: number }[];
  protocol_compliance_pct: number;
  technician_performance: { technician_id: string; sessions: number; pass_rate: number }[];
  data_source: string;
}

// ── Style helpers ────────────────────────────────────────────────────────────

const container: React.CSSProperties = {
  fontFamily: "'Inter', sans-serif",
  padding: "24px",
  background: "#f8fafc",
  borderRadius: "12px",
  border: "1px solid #e2e8f0",
};

const heading: React.CSSProperties = {
  fontSize: "22px",
  fontWeight: 700,
  color: "#1e293b",
  marginBottom: "4px",
};

const subheading: React.CSSProperties = {
  fontSize: "13px",
  color: "#64748b",
  marginBottom: "20px",
};

const tabBar: React.CSSProperties = {
  display: "flex",
  gap: "8px",
  marginBottom: "20px",
  borderBottom: "2px solid #e2e8f0",
};

function tabStyle(active: boolean): React.CSSProperties {
  return {
    padding: "8px 18px",
    fontWeight: active ? 700 : 500,
    color: active ? "#2563eb" : "#64748b",
    borderBottom: active ? "2px solid #2563eb" : "2px solid transparent",
    cursor: "pointer",
    background: "none",
    border: "none",
    borderBottom: active ? "2px solid #2563eb" : "2px solid transparent",
    fontSize: "14px",
    marginBottom: "-2px",
  };
}

function statusBadge(status: string): React.CSSProperties {
  const colors: Record<string, string> = {
    active: "#22c55e",
    completed: "#3b82f6",
    escalated: "#ef4444",
    paused: "#f59e0b",
  };
  return {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: "12px",
    fontSize: "11px",
    fontWeight: 600,
    color: "#fff",
    background: colors[status] ?? "#94a3b8",
  };
}

function riskBadge(risk: string): React.CSSProperties {
  const colors: Record<string, string> = {
    low: "#22c55e",
    medium: "#f59e0b",
    high: "#ef4444",
    critical: "#7c3aed",
    unknown: "#94a3b8",
  };
  return {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: "12px",
    fontSize: "11px",
    fontWeight: 600,
    color: "#fff",
    background: colors[risk] ?? "#94a3b8",
  };
}

function severityColor(sev: string): string {
  const m: Record<string, string> = {
    critical: "#7c3aed",
    high: "#ef4444",
    medium: "#f59e0b",
    low: "#22c55e",
    none: "#94a3b8",
  };
  return m[sev] ?? "#94a3b8";
}

const card: React.CSSProperties = {
  background: "#fff",
  borderRadius: "10px",
  padding: "16px 20px",
  border: "1px solid #e2e8f0",
};

const kpiGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
  gap: "12px",
  marginBottom: "20px",
};

const kpiCard: React.CSSProperties = {
  background: "#fff",
  borderRadius: "10px",
  padding: "14px 16px",
  border: "1px solid #e2e8f0",
  textAlign: "center",
};

const table: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "13px",
};

const th: React.CSSProperties = {
  padding: "8px 12px",
  background: "#f1f5f9",
  textAlign: "left",
  fontWeight: 600,
  color: "#475569",
  borderBottom: "1px solid #e2e8f0",
};

const td: React.CSSProperties = {
  padding: "8px 12px",
  borderBottom: "1px solid #f1f5f9",
  color: "#1e293b",
};

// ── Sub-components ───────────────────────────────────────────────────────────

function ProgressBar({ value, total }: { value: number; total: number }) {
  const pct = total > 0 ? Math.min((value / total) * 100, 100) : 0;
  return (
    <div style={{ background: "#e2e8f0", borderRadius: "4px", height: "6px", width: "120px" }}>
      <div
        style={{
          width: `${pct}%`,
          height: "100%",
          background: pct === 100 ? "#22c55e" : "#3b82f6",
          borderRadius: "4px",
        }}
      />
    </div>
  );
}

function SessionCard({ session, expanded, onToggle }: {
  session: Session;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div style={{ ...card, marginBottom: "10px" }}>
      <div
        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
        onClick={onToggle}
      >
        <div>
          <span style={{ fontWeight: 600, fontSize: "15px" }}>{session.instrument_name}</span>
          <span style={{ marginLeft: "10px", color: "#64748b", fontSize: "12px" }}>#{session.id}</span>
          <span style={{ marginLeft: "12px", ...statusBadge(session.session_status) }}>
            {session.session_status.toUpperCase()}
          </span>
          <span style={{ marginLeft: "8px", ...riskBadge(session.risk_level) }}>
            {session.risk_level.toUpperCase()} RISK
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ textAlign: "right", fontSize: "12px", color: "#64748b" }}>
            <div>Tech: {session.technician_id}</div>
            <div>{session.completed_steps}/{session.total_steps} steps</div>
          </div>
          <ProgressBar value={session.completed_steps} total={session.total_steps} />
          <span style={{ color: "#94a3b8", fontSize: "18px" }}>{expanded ? "▲" : "▼"}</span>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: "14px", borderTop: "1px solid #f1f5f9", paddingTop: "12px" }}>
          {session.escalation_reason && (
            <div style={{
              background: "#fef2f2",
              border: "1px solid #fca5a5",
              borderRadius: "6px",
              padding: "8px 12px",
              marginBottom: "10px",
              fontSize: "12px",
              color: "#b91c1c",
            }}>
              Escalation: {session.escalation_reason}
            </div>
          )}
          <table style={table}>
            <thead>
              <tr>
                <th style={th}>#</th>
                <th style={th}>Step</th>
                <th style={th}>Type</th>
                <th style={th}>Response</th>
                <th style={th}>Finding</th>
                <th style={th}>Severity</th>
              </tr>
            </thead>
            <tbody>
              {session.steps.map((step) => (
                <tr key={step.id}>
                  <td style={td}>{step.step_number}</td>
                  <td style={td}>{step.step_title}</td>
                  <td style={td}>{step.step_type}</td>
                  <td style={td}>
                    {step.technician_response ? (
                      <span style={{
                        fontWeight: 600,
                        color: step.technician_response === "pass" ? "#16a34a" : "#dc2626",
                      }}>
                        {step.technician_response.toUpperCase()}
                      </span>
                    ) : (
                      <span style={{ color: "#94a3b8" }}>Pending</span>
                    )}
                  </td>
                  <td style={td}>{step.finding_category || "—"}</td>
                  <td style={td}>
                    {step.severity !== "none" && step.severity ? (
                      <span style={{
                        color: "#fff",
                        background: severityColor(step.severity),
                        padding: "1px 8px",
                        borderRadius: "10px",
                        fontSize: "11px",
                        fontWeight: 600,
                      }}>
                        {step.severity.toUpperCase()}
                      </span>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Tabs ─────────────────────────────────────────────────────────────────────

function ActiveSessionsTab() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${BASE}/api/copilot/sessions`, { headers: authHeaders() });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setSessions(data.sessions ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <p style={{ color: "#64748b" }}>Loading sessions…</p>;
  if (error) return <p style={{ color: "#ef4444" }}>Error: {error}</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "14px" }}>
        <span style={{ fontWeight: 600, color: "#1e293b" }}>{sessions.length} active session{sessions.length !== 1 ? "s" : ""}</span>
        <button
          onClick={load}
          style={{ fontSize: "12px", color: "#3b82f6", background: "none", border: "none", cursor: "pointer" }}
        >
          Refresh
        </button>
      </div>
      {sessions.length === 0 ? (
        <p style={{ color: "#94a3b8", fontStyle: "italic" }}>No active sessions at this time.</p>
      ) : (
        sessions.map((s) => (
          <SessionCard
            key={s.id}
            session={s}
            expanded={expandedId === s.id}
            onToggle={() => setExpandedId(expandedId === s.id ? null : s.id)}
          />
        ))
      )}
    </div>
  );
}

function EscalationsTab() {
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [resolving, setResolving] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${BASE}/api/copilot/escalations`, { headers: authHeaders() });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setEscalations(data.escalations ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const resolve = async (id: number) => {
    setResolving(id);
    try {
      const r = await fetch(`${BASE}/api/copilot/escalations/${id}/resolve`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ resolved_by: "dashboard-user", notes: "Resolved via dashboard" }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      await load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : String(e));
    } finally {
      setResolving(null);
    }
  };

  if (loading) return <p style={{ color: "#64748b" }}>Loading escalations…</p>;
  if (error) return <p style={{ color: "#ef4444" }}>Error: {error}</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "14px" }}>
        <span style={{ fontWeight: 600, color: "#1e293b" }}>{escalations.length} open escalation{escalations.length !== 1 ? "s" : ""}</span>
        <button
          onClick={load}
          style={{ fontSize: "12px", color: "#3b82f6", background: "none", border: "none", cursor: "pointer" }}
        >
          Refresh
        </button>
      </div>
      {escalations.length === 0 ? (
        <p style={{ color: "#94a3b8", fontStyle: "italic" }}>No open escalations.</p>
      ) : (
        <table style={table}>
          <thead>
            <tr>
              <th style={th}>ID</th>
              <th style={th}>Session</th>
              <th style={th}>Type</th>
              <th style={th}>Severity</th>
              <th style={th}>Description</th>
              <th style={th}>Created</th>
              <th style={th}>Action</th>
            </tr>
          </thead>
          <tbody>
            {escalations.map((esc) => (
              <tr key={esc.id}>
                <td style={td}>{esc.id}</td>
                <td style={td}>#{esc.session_id}</td>
                <td style={td}>{esc.escalation_type}</td>
                <td style={td}>
                  <span style={{
                    color: "#fff",
                    background: severityColor(esc.severity),
                    padding: "1px 8px",
                    borderRadius: "10px",
                    fontSize: "11px",
                    fontWeight: 600,
                  }}>
                    {esc.severity.toUpperCase()}
                  </span>
                </td>
                <td style={{ ...td, maxWidth: "300px", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {esc.description}
                </td>
                <td style={td}>{new Date(esc.created_at).toLocaleString()}</td>
                <td style={td}>
                  <button
                    onClick={() => resolve(esc.id)}
                    disabled={resolving === esc.id}
                    style={{
                      padding: "4px 12px",
                      background: "#22c55e",
                      color: "#fff",
                      border: "none",
                      borderRadius: "6px",
                      cursor: "pointer",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    {resolving === esc.id ? "…" : "Resolve"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function DashboardTab() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${BASE}/api/copilot/dashboard`, { headers: authHeaders() });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData(await r.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <p style={{ color: "#64748b" }}>Loading dashboard…</p>;
  if (error) return <p style={{ color: "#ef4444" }}>Error: {error}</p>;
  if (!data) return null;

  const maxFinding = Math.max(...(data.top_finding_categories.map((f) => f.count)), 1);

  return (
    <div>
      {data.data_source === "mock" && (
        <div style={{
          background: "#fefce8",
          border: "1px solid #fde047",
          borderRadius: "6px",
          padding: "6px 12px",
          marginBottom: "14px",
          fontSize: "12px",
          color: "#854d0e",
        }}>
          Showing sample data — no real sessions yet.
        </div>
      )}

      {/* KPI Cards */}
      <div style={kpiGrid}>
        {[
          { label: "Active Sessions", value: data.active_sessions, color: "#3b82f6" },
          { label: "Completed Today", value: data.completed_today, color: "#22c55e" },
          { label: "Open Escalations", value: data.escalations_open, color: "#ef4444" },
          { label: "Resolved Escalations", value: data.escalations_resolved, color: "#8b5cf6" },
          { label: "Pass Rate", value: `${data.pass_rate_pct}%`, color: "#22c55e" },
          { label: "Protocol Compliance", value: `${data.protocol_compliance_pct}%`, color: "#3b82f6" },
          { label: "Avg Duration (min)", value: data.avg_session_duration_minutes, color: "#f59e0b" },
        ].map(({ label, value, color }) => (
          <div key={label} style={kpiCard}>
            <div style={{ fontSize: "22px", fontWeight: 700, color }}>{value}</div>
            <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>{label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
        {/* Top Findings Bar Chart */}
        <div style={card}>
          <div style={{ fontWeight: 600, marginBottom: "12px", color: "#1e293b" }}>Top Finding Categories</div>
          {data.top_finding_categories.length === 0 ? (
            <p style={{ color: "#94a3b8", fontSize: "13px" }}>No findings recorded yet.</p>
          ) : (
            data.top_finding_categories.map((f) => (
              <div key={f.category} style={{ marginBottom: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "3px" }}>
                  <span style={{ fontWeight: 600, color: "#374151" }}>{f.category}</span>
                  <span style={{ color: "#64748b" }}>{f.count} ({f.pct}%)</span>
                </div>
                <div style={{ background: "#e2e8f0", borderRadius: "4px", height: "8px" }}>
                  <div style={{
                    width: `${(f.count / maxFinding) * 100}%`,
                    height: "100%",
                    background: "#3b82f6",
                    borderRadius: "4px",
                  }} />
                </div>
              </div>
            ))
          )}
        </div>

        {/* High Risk Instruments */}
        <div style={card}>
          <div style={{ fontWeight: 600, marginBottom: "12px", color: "#1e293b" }}>High Risk Instruments</div>
          {data.high_risk_instruments.length === 0 ? (
            <p style={{ color: "#94a3b8", fontSize: "13px" }}>No high-risk instruments identified.</p>
          ) : (
            <ul style={{ margin: 0, padding: "0 0 0 16px", fontSize: "13px", color: "#374151" }}>
              {data.high_risk_instruments.map((name) => (
                <li key={name} style={{ marginBottom: "4px" }}>{name}</li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Technician Performance */}
      <div style={card}>
        <div style={{ fontWeight: 600, marginBottom: "12px", color: "#1e293b" }}>Technician Performance</div>
        <table style={table}>
          <thead>
            <tr>
              <th style={th}>Technician</th>
              <th style={th}>Sessions</th>
              <th style={th}>Pass Rate</th>
            </tr>
          </thead>
          <tbody>
            {data.technician_performance.map((tech) => (
              <tr key={tech.technician_id}>
                <td style={td}>{tech.technician_id}</td>
                <td style={td}>{tech.sessions}</td>
                <td style={td}>
                  <span style={{
                    fontWeight: 600,
                    color: tech.pass_rate >= 90 ? "#16a34a" : tech.pass_rate >= 75 ? "#d97706" : "#dc2626",
                  }}>
                    {tech.pass_rate}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export function InspectionCopilotDashboard() {
  const [tab, setTab] = useState<"sessions" | "escalations" | "dashboard">("dashboard");

  return (
    <div style={container}>
      <div style={heading}>Autonomous Inspection Copilot</div>
      <div style={subheading}>
        AI-guided inspection sessions, real-time step recommendations, escalation engine, and protocol compliance analytics.
      </div>

      <div style={tabBar}>
        {(["dashboard", "sessions", "escalations"] as const).map((t) => (
          <button key={t} style={tabStyle(tab === t)} onClick={() => setTab(t)}>
            {t === "dashboard" ? "Dashboard" : t === "sessions" ? "Active Sessions" : "Escalations"}
          </button>
        ))}
      </div>

      {tab === "sessions" && <ActiveSessionsTab />}
      {tab === "escalations" && <EscalationsTab />}
      {tab === "dashboard" && <DashboardTab />}
    </div>
  );
}

export default InspectionCopilotDashboard;
