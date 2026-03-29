import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import InspectionHistory from "./pages/InspectionHistory";

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function statusPill(status: string) {
  const base: React.CSSProperties = {
    display: "inline-block",
    padding: "4px 10px",
    borderRadius: "999px",
    fontSize: "12px",
    fontWeight: 700,
    textTransform: "capitalize",
  };

  switch ((status || "").toLowerCase()) {
    case "completed":
    case "ok":
    case "enabled":
    case "sent":
    case "configured":
      return { ...base, background: "#dcfce7", color: "#166534" };
    case "queued":
      return { ...base, background: "#fef3c7", color: "#92400e" };
    case "running":
      return { ...base, background: "#dbeafe", color: "#1d4ed8" };
    case "failed":
    case "disabled":
    case "not sent":
    case "not configured":
      return { ...base, background: "#fee2e2", color: "#991b1b" };
    default:
      return { ...base, background: "#e5e7eb", color: "#374151" };
  }
}

function priorityPill(priority: string) {
  const base: React.CSSProperties = {
    display: "inline-block",
    padding: "4px 10px",
    borderRadius: "999px",
    fontSize: "12px",
    fontWeight: 700,
    textTransform: "capitalize",
  };

  switch ((priority || "").toLowerCase()) {
    case "critical":
      return { ...base, background: "#7f1d1d", color: "#ffffff" };
    case "high":
      return { ...base, background: "#fee2e2", color: "#991b1b" };
    case "medium":
      return { ...base, background: "#fef3c7", color: "#92400e" };
    default:
      return { ...base, background: "#dcfce7", color: "#166534" };
  }
}

type SummaryItem = { label: string; count: number };

type Summary = {
  total_inspections: number;
  completed: number;
  queued: number;
  running: number;
  failed: number;
  top_issues: SummaryItem[];
  top_instruments: SummaryItem[];
};

type Inspection = {
  id: number;
  created_at?: string;
  file_name?: string;
  stain_detected?: boolean;
  confidence?: number;
  material_type?: string;
  status?: string;
  model_name?: string;
  model_version?: string;
  inference_timestamp?: string | null;
  instrument_type?: string;
  detected_issue?: string;
  inference_mode?: string;
  risk_score?: number;
  vendor_name?: string;
  alert_status?: string;
  alert_owner?: string;
  alert_notes?: string;
  alert_acknowledged_at?: string | null;
  alert_resolved_at?: string | null;
};

type AgentItem = {
  inspection_id: number;
  priority: string;
  risk_score: number;
  escalation_needed: boolean;
  recommended_actions: string[];
  summary: string;
};

type VendorIssue = {
  label: string;
  count: number;
};

type VendorItem = {
  vendor_name: string;
  total_inspections: number;
  escalations: number;
  avg_confidence: number;
  top_issues: VendorIssue[];
};

type AlertItem = {
  inspection_id: number;
  file_name: string;
  vendor_name: string;
  instrument_type: string;
  detected_issue: string;
  risk_score: number;
  status: string;
  message: string;
};

type AlertStatus = {
  enabled: boolean;
  channels: {
    slack: { configured: boolean; enabled: boolean };
    teams: { configured: boolean; enabled: boolean };
    email: { configured: boolean; enabled: boolean };
  };
};

type DispatchResult = {
  enabled: boolean;
  results: Array<{
    channel: string;
    sent: boolean;
    reason?: string;
    status_code?: number;
    response_text?: string;
  }>;
  message?: string;
  dispatch_batch_id?: string;
};

type DispatchResponse = {
  inspection_id: number;
  alert: AlertItem;
  dispatch: DispatchResult;
  source_alert_event_id?: number;
};

type AlertAuditItem = {
  id: number;
  inspection_id: number;
  vendor_name: string;
  instrument_type: string;
  detected_issue: string;
  risk_score: number;
  channel: string;
  sent: boolean;
  status_code: string;
  failure_reason: string;
  dispatch_batch_id: string;
  created_at: string;
};

type ChannelHealthItem = {
  channel: string;
  last_attempt_at: string | null;
  last_attempt_sent: boolean;
  last_status_code: string;
  last_failure_reason: string;
  last_dispatch_batch_id: string;
  last_success_at: string | null;
};

type ModelPerformanceSummary = {
  summary: {
    total_reviewed: number;
    total_approved: number;
    total_overridden: number;
    agreement_rate: number;
    override_rate: number;
  };
  by_vendor: { label: string; reviewed: number; approved: number; overridden: number; agreement_rate: number; override_rate: number }[];
  by_issue: { label: string; reviewed: number; approved: number; overridden: number; agreement_rate: number; override_rate: number }[];
  by_reviewer: { label: string; reviewed: number; approved: number; overridden: number; agreement_rate: number; override_rate: number }[];
  timeseries: { date: string; reviewed: number; approved: number; overridden: number; agreement_rate: number; override_rate: number }[];
};

type ReviewAnalyticsSummary = {
  total_reviewed: number;
  total_pending: number;
  total_approved: number;
  total_overridden: number;
  agreement_rate: number;
  override_rate: number;
  top_override_issues: { label: string; count: number }[];
  top_override_vendors: { label: string; count: number }[];
  top_reviewers: { label: string; count: number }[];
};

type QAReviewItem = {
  id: number;
  file_name: string;
  vendor_name: string;
  status: string;
  stain_detected: boolean;
  confidence: number;
  material_type: string;
  instrument_type: string;
  detected_issue: string;
  risk_score: number;
  qa_review_status: string;
};

type ChannelHealthItem = {
  channel: string;
  last_attempt_at: string | null;
  last_attempt_sent: boolean;
  last_status_code: string;
  last_failure_reason: string;
  last_dispatch_batch_id: string;
  last_success_at: string | null;
};

type AlertAuditItem = {
  id: number;
  inspection_id: number;
  vendor_name: string;
  instrument_type: string;
  detected_issue: string;
  risk_score: number;
  channel: string;
  sent: boolean;
  status_code: string;
  failure_reason: string;
  dispatch_batch_id: string;
  created_at: string;
};

function DashboardHome() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recent, setRecent] = useState<Inspection[]>([]);
  const [agentFeed, setAgentFeed] = useState<AgentItem[]>([]);
  const [vendors, setVendors] = useState<VendorItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertStatus, setAlertStatus] = useState<AlertStatus | null>(null);
  const [alertAudit, setAlertAudit] = useState<AlertAuditItem[]>([]);
  const [channelHealth, setChannelHealth] = useState<ChannelHealthItem[]>([]);
  const [qaPending, setQaPending] = useState<QAReviewItem[]>([]);
  const [reviewAnalytics, setReviewAnalytics] = useState<ReviewAnalyticsSummary | null>(null);
  const [modelPerformance, setModelPerformance] = useState<ModelPerformanceSummary | null>(null);
  const [lastDispatch, setLastDispatch] = useState<DispatchResponse | null>(null);
  const [dispatchingId, setDispatchingId] = useState<number | null>(null);
  const [resendingAuditId, setResendingAuditId] = useState<number | null>(null);
  const [health, setHealth] = useState("checking");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const token = useMemo(() => localStorage.getItem("token") || "", []);

  async function refreshAudit(headers: HeadersInit = {}) {
    const auditRes = await fetch(`${API_BASE}/alerts/history?limit=12`, { headers });
    if (auditRes.ok) {
      const auditData = await auditRes.json();
      setAlertAudit(Array.isArray(auditData.items) ? auditData.items : []);
    }
  }

  useEffect(() => {
    let ignore = false;

    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const headers = token ? { Authorization: `Bearer ${token}` } : {};

        const [
          summaryRes,
          historyRes,
          healthRes,
          agentRes,
          vendorRes,
          alertsRes,
          alertStatusRes,
          alertAuditRes,
          channelHealthRes,
          qaPendingRes,
          reviewAnalyticsRes,
          modelPerformanceRes,
        ] = await Promise.all([
          fetch(`${API_BASE}/history/summary`, { headers }),
          fetch(`${API_BASE}/history?limit=8`, { headers }),
          fetch(`${API_BASE}/health`),
          fetch(`${API_BASE}/agent/feed?limit=8`, { headers }),
          fetch(`${API_BASE}/analytics/vendors`, { headers }),
          fetch(`${API_BASE}/alerts/feed`, { headers }),
          fetch(`${API_BASE}/alerts/status`, { headers }),
          fetch(`${API_BASE}/alerts/history?limit=12`, { headers }),
          fetch(`${API_BASE}/alerts/channel-health`, { headers }),
          fetch(`${API_BASE}/qa-review/pending`, { headers }),
          fetch(`${API_BASE}/review-analytics/summary`, { headers }),
          fetch(`${API_BASE}/model-performance/summary`, { headers }),
        ]);

        if (!summaryRes.ok) throw new Error(`Summary request failed (${summaryRes.status})`);
        if (!historyRes.ok) throw new Error(`History request failed (${historyRes.status})`);
        if (!agentRes.ok) throw new Error(`Agent request failed (${agentRes.status})`);
        if (!vendorRes.ok) throw new Error(`Vendor analytics request failed (${vendorRes.status})`);
        if (!alertsRes.ok) throw new Error(`Alerts request failed (${alertsRes.status})`);
        if (!alertStatusRes.ok) throw new Error(`Alert status request failed (${alertStatusRes.status})`);
        if (!alertAuditRes.ok) throw new Error(`Alert audit request failed (${alertAuditRes.status})`);
        if (!channelHealthRes.ok) throw new Error(`Channel health request failed (${channelHealthRes.status})`);
        if (!qaPendingRes.ok) throw new Error(`QA pending request failed (${qaPendingRes.status})`);
        if (!reviewAnalyticsRes.ok) throw new Error(`Review analytics request failed (${reviewAnalyticsRes.status})`);
        if (!modelPerformanceRes.ok) throw new Error(`Model performance request failed (${modelPerformanceRes.status})`);

        const summaryData = await summaryRes.json();
        const historyData = await historyRes.json();
        const agentData = await agentRes.json();
        const vendorData = await vendorRes.json();
        const alertsData = await alertsRes.json();
        const alertStatusData = await alertStatusRes.json();
        const alertAuditData = await alertAuditRes.json();
        const channelHealthData = await channelHealthRes.json();
        const qaPendingData = await qaPendingRes.json();
        const reviewAnalyticsData = await reviewAnalyticsRes.json();
        const modelPerformanceData = await modelPerformanceRes.json();

        let healthStatus = "unavailable";
        if (healthRes.ok) {
          try {
            const healthJson = await healthRes.json();
            healthStatus = healthJson.status || "ok";
          } catch {
            healthStatus = "ok";
          }
        }

        if (!ignore) {
          setSummary(summaryData);
          setRecent(Array.isArray(historyData.items) ? historyData.items : []);
          setAgentFeed(Array.isArray(agentData.items) ? agentData.items : []);
          setVendors(Array.isArray(vendorData.items) ? vendorData.items : []);
          setAlerts(Array.isArray(alertsData.items) ? alertsData.items : []);
          setAlertStatus(alertStatusData);
          setAlertAudit(Array.isArray(alertAuditData.items) ? alertAuditData.items : []);
          setChannelHealth(Array.isArray(channelHealthData.items) ? channelHealthData.items : []);
          setQaPending(Array.isArray(qaPendingData.items) ? qaPendingData.items : []);
          setReviewAnalytics(reviewAnalyticsData);
          setModelPerformance(modelPerformanceData);
          setHealth(healthStatus);
        }
      } catch (err: any) {
        if (!ignore) {
          setError(err?.message || "Failed to load dashboard.");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    loadDashboard();
    return () => {
      ignore = true;
    };
  }, [token]);

  async function sendTestAlert(inspectionId: number) {
    try {
      setDispatchingId(inspectionId);
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${API_BASE}/alerts/send/${inspectionId}`, {
        method: "POST",
        headers,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Alert send failed (${res.status}): ${text}`);
      }

      const data = await res.json();
      setLastDispatch(data);
      await refreshAudit(headers);
    } catch (err: any) {
      setLastDispatch({
        inspection_id: inspectionId,
        alert: {
          inspection_id: inspectionId,
          file_name: "",
          vendor_name: "",
          instrument_type: "",
          detected_issue: "",
          risk_score: 0,
          status: "failed",
          message: err?.message || "Alert send failed",
        },
        dispatch: {
          enabled: false,
          results: [],
          message: err?.message || "Alert send failed",
        },
      });
    } finally {
      setDispatchingId(null);
    }
  }

  async function resendAuditEvent(alertEventId: number) {
    try {
      setResendingAuditId(alertEventId);
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${API_BASE}/alerts/resend/${alertEventId}`, {
        method: "POST",
        headers,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Alert resend failed (${res.status}): ${text}`);
      }

      const data = await res.json();
      setLastDispatch(data);
      await refreshAudit(headers);
    } catch (err: any) {
      setLastDispatch({
        inspection_id: 0,
        source_alert_event_id: alertEventId,
        alert: {
          inspection_id: 0,
          file_name: "",
          vendor_name: "",
          instrument_type: "",
          detected_issue: "",
          risk_score: 0,
          status: "failed",
          message: err?.message || "Alert resend failed",
        },
        dispatch: {
          enabled: false,
          results: [],
          message: err?.message || "Alert resend failed",
        },
      });
    } finally {
      setResendingAuditId(null);
    }
  }


  async function acknowledgeAlert(inspectionId: number) {
    try {
      const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
      const res = await fetch(`${API_BASE}/alerts/${inspectionId}/acknowledge`, {
        method: "POST",
        headers,
        body: JSON.stringify({ notes: "Acknowledged from dashboard" }),
      });
      if (!res.ok) throw new Error(`Acknowledge failed (${res.status})`);
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert("Failed to acknowledge alert");
    }
  }

  async function resolveAlert(inspectionId: number) {
    try {
      const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
      const res = await fetch(`${API_BASE}/alerts/${inspectionId}/resolve`, {
        method: "POST",
        headers,
        body: JSON.stringify({ notes: "Resolved from dashboard" }),
      });
      if (!res.ok) throw new Error(`Resolve failed (${res.status})`);
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert("Failed to resolve alert");
    }
  }


  async function approveQaReview(inspectionId: number) {
    try {
      const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
      const res = await fetch(`${API_BASE}/qa-review/${inspectionId}`, {
        method: "POST",
        headers,
        body: JSON.stringify({ approve_model: true, notes: "Approved by QA from dashboard" }),
      });
      if (!res.ok) throw new Error(`QA approve failed (${res.status})`);
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert("Failed to approve QA review");
    }
  }

  async function overrideQaReview(inspectionId: number) {
    try {
      const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
      const res = await fetch(`${API_BASE}/qa-review/${inspectionId}`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          approve_model: false,
          notes: "Overridden by QA from dashboard",
          override_detected_issue: "clean",
          override_risk_score: 0,
          override_stain_detected: false,
        }),
      });
      if (!res.ok) throw new Error(`QA override failed (${res.status})`);
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert("Failed to override QA review");
    }
  }

  const csvExportUrl = `${API_BASE}/history/export.csv`;
  const jsonExportUrl = `${API_BASE}/history/export.json`;
  const xlsxExportUrl = `${API_BASE}/history/export.xlsx`;
  const bundleExportUrl = `${API_BASE}/history/export.bundle.zip`;

  const vendorCsvExportUrl = `${API_BASE}/analytics/vendors/export.csv`;
  const vendorJsonExportUrl = `${API_BASE}/analytics/vendors/export.json`;
  const vendorXlsxExportUrl = `${API_BASE}/analytics/vendors/export.xlsx`;
  const vendorBundleExportUrl = `${API_BASE}/analytics/vendors/export.bundle.zip`;

  const alertAuditCsvExportUrl = `${API_BASE}/alerts/history/export.csv`;
  const alertAuditJsonExportUrl = `${API_BASE}/alerts/history/export.json`;
  const alertAuditXlsxExportUrl = `${API_BASE}/alerts/history/export.xlsx`;
  const alertAuditBundleExportUrl = `${API_BASE}/alerts/history/export.bundle.zip`;

  const criticalCount = agentFeed.filter((x) => x.priority === "critical").length;
  const highCount = agentFeed.filter((x) => x.priority === "high").length;
  const escalationCount = agentFeed.filter((x) => x.escalation_needed).length;
  const totalVendors = vendors.length;
  const topVendor = vendors[0]?.vendor_name || "—";
  const topVendorEscalations = vendors[0]?.escalations || 0;
  const liveQueuedCount = recent.filter((x) => (x.status || "").toLowerCase() === "queued").length;
  const liveCompletedCount = recent.filter((x) => (x.status || "").toLowerCase() === "completed").length;
  const auditSentCount = alertAudit.filter((x) => x.sent).length;
  const auditFailedCount = alertAudit.filter((x) => !x.sent).length;

  return (
    <div style={{ padding: "24px", maxWidth: "1360px", margin: "0 auto" }}>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ marginBottom: "8px" }}>LumenAI Phase 2 Command Dashboard</h1>
        <p style={{ color: "#4b5563", margin: 0 }}>
          Real-time surgical instrument quality intelligence for SPD teams,
          surgical vendors, and device manufacturers.
        </p>
      </div>

      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "24px" }}>
        <Link to="/history" style={secondaryButton}>Open Full History</Link>
        <a href={`${API_BASE}/health`} target="_blank" rel="noreferrer" style={secondaryButton}>API Health</a>
      </div>

      {loading && <p>Loading Phase 2 dashboard...</p>}
      {!loading && error && <div style={errorBox}>{error}</div>}

      {!loading && !error && summary && (
        <>
          <div style={{ display: "grid", gap: "16px", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", marginBottom: "24px" }}>
            <div style={card}><div style={cardLabel}>Total Inspections</div><div style={cardValue}>{summary.total_inspections}</div></div>
            <div style={card}><div style={cardLabel}>Completed</div><div style={cardValue}>{summary.completed}</div></div>
            <div style={card}><div style={cardLabel}>Escalations Needed</div><div style={cardValue}>{escalationCount}</div></div>
            <div style={card}><div style={cardLabel}>Active Alerts</div><div style={cardValue}>{alerts.length}</div></div>
            <div style={card}><div style={cardLabel}>System Health</div><div style={cardValueSmall}><span style={statusPill(health)}>{health}</span></div></div>
          </div>

          <div style={{ display: "grid", gap: "16px", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", marginBottom: "24px" }}>
            <div style={card}><div style={cardLabel}>Critical Priority</div><div style={cardValue}>{criticalCount}</div></div>
            <div style={card}><div style={cardLabel}>High Priority</div><div style={cardValue}>{highCount}</div></div>
            <div style={card}><div style={cardLabel}>Tracked Vendors</div><div style={cardValue}>{totalVendors}</div></div>
            <div style={card}><div style={cardLabel}>Top Vendor by Escalations</div><div style={cardValueSmall}>{topVendor} ({topVendorEscalations})</div></div>
            <div style={card}><div style={cardLabel}>Live Stream Queued / Completed</div><div style={cardValueSmall}>{liveQueuedCount} / {liveCompletedCount}</div></div>
          </div>

          <div style={{ display: "grid", gap: "16px", gridTemplateColumns: "1.05fr 0.95fr", marginBottom: "24px" }}>
            <div style={card}>
              <h2 style={sectionTitle}>Alert Control Center</h2>

              <div style={{ display: "grid", gap: "12px", marginBottom: "16px" }}>
                <div style={controlRow}><span>Global Alerts</span><span style={statusPill(alertStatus?.enabled ? "enabled" : "disabled")}>{alertStatus?.enabled ? "enabled" : "disabled"}</span></div>
                <div style={controlRow}><span>Slack</span><span style={statusPill(alertStatus?.channels.slack.configured ? "configured" : "not configured")}>{alertStatus?.channels.slack.configured ? "configured" : "not configured"}</span></div>
                <div style={controlRow}><span>Teams</span><span style={statusPill(alertStatus?.channels.teams.configured ? "configured" : "not configured")}>{alertStatus?.channels.teams.configured ? "configured" : "not configured"}</span></div>
                <div style={controlRow}><span>Email</span><span style={statusPill(alertStatus?.channels.email.configured ? "configured" : "not configured")}>{alertStatus?.channels.email.configured ? "configured" : "not configured"}</span></div>
              </div>

              <div style={{ marginBottom: "16px" }}>
                <h3 style={subTitle}>Send Test Alert</h3>
                {alerts.length === 0 ? (
                  <p style={muted}>No alert-ready inspections available.</p>
                ) : (
                  <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                    {alerts.slice(0, 3).map((item) => (
                      <button
                        key={item.inspection_id}
                        onClick={() => sendTestAlert(item.inspection_id)}
                        disabled={dispatchingId === item.inspection_id}
                        style={buttonStyle}
                      >
                        {dispatchingId === item.inspection_id ? `Sending #${item.inspection_id}...` : `Send Alert #${item.inspection_id}`}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <h3 style={subTitle}>Last Dispatch Result</h3>
                {!lastDispatch ? (
                  <p style={muted}>No alert dispatch attempted yet.</p>
                ) : (
                  <div style={agentCard}>
                    {lastDispatch.source_alert_event_id ? <div><strong>Source Audit Event:</strong> #{lastDispatch.source_alert_event_id}</div> : null}
                    <div><strong>Inspection:</strong> #{lastDispatch.inspection_id}</div>
                    <div style={{ marginTop: "6px" }}><strong>Dispatch Enabled:</strong> {lastDispatch.dispatch.enabled ? "Yes" : "No"}</div>
                    {lastDispatch.dispatch.dispatch_batch_id && <div style={{ marginTop: "6px" }}><strong>Dispatch Batch:</strong> {lastDispatch.dispatch.dispatch_batch_id}</div>}
                    {lastDispatch.dispatch.message && <div style={{ marginTop: "6px", color: "#6b7280" }}>{lastDispatch.dispatch.message}</div>}
                    {lastDispatch.dispatch.results?.length > 0 && (
                      <div style={{ marginTop: "10px", display: "grid", gap: "8px" }}>
                        {lastDispatch.dispatch.results.map((r, idx) => (
                          <div key={idx} style={controlRow}>
                            <span>{r.channel}</span>
                            <span style={statusPill(r.sent ? "sent" : "not sent")}>{r.sent ? "sent" : "not sent"}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div style={card}>
              <h2 style={sectionTitle}>SPD Alert Queue</h2>
              {alerts.length === 0 ? (
                <p style={muted}>No active alerts.</p>
              ) : (
                <div style={{ display: "grid", gap: "12px" }}>
                  {alerts.slice(0, 8).map((item) => (
                    <div key={item.inspection_id} style={alertCard}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", alignItems: "center" }}>
                        <strong>Inspection #{item.inspection_id}</strong>
                        <span style={priorityPill(item.risk_score >= 80 ? "critical" : item.risk_score >= 50 ? "medium" : "low")}>Risk {item.risk_score}</span>
                      </div>
                      <div style={{ marginTop: "8px", color: "#374151", fontSize: "14px" }}>{item.message}</div>
                      <div style={{ marginTop: "8px", fontSize: "13px", color: "#6b7280" }}>Vendor: {item.vendor_name || "unknown"} · Instrument: {item.instrument_type || "unknown"}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div style={{ display: "grid", gap: "16px", gridTemplateColumns: "1fr 1fr", marginBottom: "24px" }}>
            <div style={card}>
              <h2 style={sectionTitle}>Vendor Intelligence</h2>
              {vendors.length === 0 ? (
                <p style={muted}>No vendor analytics available.</p>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table style={table}>
                    <thead style={{ background: "#f9fafb" }}>
                      <tr><th style={th}>Vendor</th><th style={th}>Inspections</th><th style={th}>Escalations</th><th style={th}>Avg Confidence</th><th style={th}>Top Issue</th><th style={th}>Scorecard</th><th style={th}>Scorecard</th></tr>
                    </thead>
                    <tbody>
                      {vendors.slice(0, 8).map((vendor) => (
                        <tr key={vendor.vendor_name} style={{ borderTop: "1px solid #e5e7eb" }}>
                          <td style={td}>{vendor.vendor_name}</td>
                          <td style={td}>{vendor.total_inspections}</td>
                          <td style={td}>{vendor.escalations}</td>
                          <td style={td}>{vendor.avg_confidence.toFixed(2)}</td>
                          <td style={td}>{vendor.top_issues[0]?.label || "—"}</td>
                          <td style={td}>
                            <a
                              href={`${API_BASE}/analytics/vendors/${encodeURIComponent(vendor.vendor_name)}/scorecard.pdf`}
                              target="_blank"
                              rel="noreferrer"
                              style={secondaryButtonInline}
                            >
                              Download PDF
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div style={card}>
              <h2 style={sectionTitle}>SPD Agent Feed</h2>
              {agentFeed.length === 0 ? (
                <p style={muted}>No agent recommendations available.</p>
              ) : (
                <div style={{ display: "grid", gap: "12px" }}>
                  {agentFeed.map((item) => (
                    <div key={item.inspection_id} style={agentCard}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", alignItems: "center" }}>
                        <strong>Inspection #{item.inspection_id}</strong>
                        <span style={priorityPill(item.priority)}>{item.priority}</span>
                      </div>
                      <div style={{ marginTop: "8px", color: "#374151", fontSize: "14px" }}>{item.summary}</div>
                      <div style={{ marginTop: "8px", fontSize: "13px", color: "#6b7280" }}>Risk score: {item.risk_score} · Escalation: {item.escalation_needed ? "Yes" : "No"}</div>
                      <ul style={{ marginTop: "10px", paddingLeft: "18px", color: "#111827" }}>
                        {item.recommended_actions.map((action, idx) => <li key={idx}>{action}</li>)}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div style={{ display: "grid", gap: "16px", gridTemplateColumns: "1.15fr 0.85fr", marginBottom: "24px" }}>
            <div style={card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", gap: "12px", flexWrap: "wrap" }}>
                <h2 style={sectionTitle}>Recent Live Stream Activity & Reports</h2>
                <Link to="/history" style={{ textDecoration: "none" }}>View all</Link>
              </div>

              {recent.length === 0 ? (
                <p style={muted}>No recent inspections found.</p>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table style={table}>
                    <thead style={{ background: "#f9fafb" }}>
                      <tr><th style={th}>ID</th><th style={th}>File</th><th style={th}>Vendor</th><th style={th}>Status</th><th style={th}>Instrument</th><th style={th}>Issue</th><th style={th}>Risk</th><th style={th}>Created</th><th style={th}>Report</th></tr>
                    </thead>
                    <tbody>
                      {recent.map((item) => (
                        <tr key={item.id} style={{ borderTop: "1px solid #e5e7eb" }}>
                          <td style={td}>{item.id}</td>
                          <td style={td}>{item.file_name || "—"}</td>
                          <td style={td}>{item.vendor_name || "unknown"}</td>
                          <td style={td}><span style={statusPill(item.status || "unknown")}>{item.status || "unknown"}</span></td>
                          <td style={td}>{item.instrument_type || "unknown"}</td>
                          <td style={td}>{item.detected_issue || "unknown"}</td>
                          <td style={td}>{typeof item.risk_score === "number" ? item.risk_score : "—"}</td>
                          <td style={td}>
                            <span style={statusPill(item.alert_status || "open")}>
                              {item.alert_status || "open"}
                            </span>
                          </td>
                          <td style={td}>{formatDate(item.created_at)}</td>
                          <td style={td}>
                            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                              {(item.status || "").toLowerCase() === "completed" ? (
                                <a href={`${API_BASE}/reports/${item.id}.pdf`} target="_blank" rel="noreferrer" style={secondaryButtonInline}>Open PDF</a>
                              ) : (
                                <span style={muted}>Pending</span>
                              )}
                              {(item.alert_status || "open") === "open" ? (
                                <button onClick={() => acknowledgeAlert(item.id)} style={buttonStyle}>Acknowledge</button>
                              ) : null}
                              {(item.alert_status || "open") !== "resolved" ? (
                                <button onClick={() => resolveAlert(item.id)} style={buttonStyle}>Resolve</button>
                              ) : null}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div style={{ display: "grid", gap: "16px" }}>
              <div style={card}>
                <h2 style={sectionTitle}>Vendor Scorecard Exports</h2>
                <p style={{ color: "#4b5563", marginTop: 0 }}>
                  Export vendor performance scorecards for hospitals, suppliers, and executive review.
                </p>

                <div style={{ display: "grid", gap: "12px" }}>
                  <a href={vendorCsvExportUrl} style={primaryButton}>Export Vendor CSV</a>
                  <div style={exportHint}>Flat scorecard format for Excel, Power BI, and Tableau.</div>
                  <a href={vendorXlsxExportUrl} style={primaryButton}>Export Vendor Excel Workbook</a>
                  <div style={exportHint}>Includes vendor summary sheet and top issue detail.</div>
                  <a href={vendorJsonExportUrl} style={secondaryButton}>Export Vendor JSON</a>
                  <div style={exportHint}>Useful for custom integrations and partner analytics pipelines.</div>
                  <a href={vendorBundleExportUrl} style={secondaryButton}>Download Vendor Bundle</a>
                  <div style={exportHint}>ZIP package containing CSV, JSON, and XLSX vendor scorecards.</div>
                </div>
              </div>




              <div style={card}>
                <h2 style={sectionTitle}>Model Performance Tracking</h2>
                {!modelPerformance ? (
                  <p style={muted}>No model performance analytics yet.</p>
                ) : (
                  <div style={{ display: "grid", gap: "12px" }}>
                    <div style={controlRow}><span>Total Reviewed</span><strong>{modelPerformance.summary.total_reviewed}</strong></div>
                    <div style={controlRow}><span>Agreement Rate</span><strong>{(modelPerformance.summary.agreement_rate * 100).toFixed(1)}%</strong></div>
                    <div style={controlRow}><span>Override Rate</span><strong>{(modelPerformance.summary.override_rate * 100).toFixed(1)}%</strong></div>

                    <div style={{ marginTop: "8px" }}>
                      <strong>Top Vendors by Override Rate</strong>
                      <div style={{ display: "grid", gap: "8px", marginTop: "8px" }}>
                        {modelPerformance.by_vendor.slice(0, 5).map((item) => (
                          <div key={item.label} style={listRow}>
                            <span>{item.label}</span>
                            <strong>{(item.override_rate * 100).toFixed(1)}%</strong>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{ marginTop: "8px" }}>
                      <strong>Top Issues by Override Rate</strong>
                      <div style={{ display: "grid", gap: "8px", marginTop: "8px" }}>
                        {modelPerformance.by_issue.slice(0, 5).map((item) => (
                          <div key={item.label} style={listRow}>
                            <span>{item.label}</span>
                            <strong>{(item.override_rate * 100).toFixed(1)}%</strong>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{ marginTop: "8px" }}>
                      <strong>Reviewer Override Patterns</strong>
                      <div style={{ display: "grid", gap: "8px", marginTop: "8px" }}>
                        {modelPerformance.by_reviewer.slice(0, 5).map((item) => (
                          <div key={item.label} style={listRow}>
                            <span>{item.label}</span>
                            <strong>{(item.override_rate * 100).toFixed(1)}%</strong>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{ display: "grid", gap: "10px", marginTop: "12px" }}>
                      <a href={`${API_BASE}/model-performance/export.csv`} style={primaryButton}>Export Performance CSV</a>
                      <a href={`${API_BASE}/model-performance/export.xlsx`} style={primaryButton}>Export Performance Excel</a>
                      <a href={`${API_BASE}/model-performance/export.json`} style={secondaryButton}>Export Performance JSON</a>
                      <a href={`${API_BASE}/model-performance/export.bundle.zip`} style={secondaryButton}>Download Performance Bundle</a>
                    </div>
                  </div>
                )}
              </div>

              <div style={card}>
                <h2 style={sectionTitle}>Review Analytics</h2>
                {!reviewAnalytics ? (
                  <p style={muted}>No review analytics yet.</p>
                ) : (
                  <div style={{ display: "grid", gap: "12px" }}>
                    <div style={controlRow}><span>Total Reviewed</span><strong>{reviewAnalytics.total_reviewed}</strong></div>
                    <div style={controlRow}><span>Pending</span><strong>{reviewAnalytics.total_pending}</strong></div>
                    <div style={controlRow}><span>Approved</span><strong>{reviewAnalytics.total_approved}</strong></div>
                    <div style={controlRow}><span>Overridden</span><strong>{reviewAnalytics.total_overridden}</strong></div>
                    <div style={controlRow}><span>Agreement Rate</span><strong>{(reviewAnalytics.agreement_rate * 100).toFixed(1)}%</strong></div>
                    <div style={controlRow}><span>Override Rate</span><strong>{(reviewAnalytics.override_rate * 100).toFixed(1)}%</strong></div>

                    <div style={{ marginTop: "8px" }}>
                      <strong>Top Override Issues</strong>
                      <div style={{ display: "grid", gap: "8px", marginTop: "8px" }}>
                        {reviewAnalytics.top_override_issues.slice(0, 5).map((item) => (
                          <div key={item.label} style={listRow}>
                            <span>{item.label}</span><strong>{item.count}</strong>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{ display: "grid", gap: "10px", marginTop: "12px" }}>
                      <a href={`${API_BASE}/review-analytics/feedback-dataset.csv`} style={primaryButton}>Export Feedback CSV</a>
                      <a href={`${API_BASE}/review-analytics/feedback-dataset.xlsx`} style={primaryButton}>Export Feedback Excel</a>
                      <a href={`${API_BASE}/review-analytics/feedback-dataset.json`} style={secondaryButton}>Export Feedback JSON</a>
                      <a href={`${API_BASE}/review-analytics/feedback-dataset.bundle.zip`} style={secondaryButton}>Download Retraining Bundle</a>
                    </div>
                  </div>
                )}
              </div>

              <div style={card}>
                <h2 style={sectionTitle}>QA Review Queue</h2>
                {qaPending.length === 0 ? (
                  <p style={muted}>No pending QA reviews.</p>
                ) : (
                  <div style={{ display: "grid", gap: "12px" }}>
                    {qaPending.slice(0, 8).map((item) => (
                      <div key={item.id} style={agentCard}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", alignItems: "center" }}>
                          <strong>Inspection #{item.id}</strong>
                          <span style={statusPill(item.qa_review_status || "pending")}>{item.qa_review_status || "pending"}</span>
                        </div>
                        <div style={{ marginTop: "8px", fontSize: "14px", color: "#374151" }}>
                          {item.vendor_name} · {item.instrument_type} · {item.detected_issue}
                        </div>
                        <div style={{ marginTop: "8px", fontSize: "12px", color: "#6b7280" }}>
                          Confidence: {typeof item.confidence === "number" ? item.confidence.toFixed(2) : "—"} · Risk: {item.risk_score ?? "—"}
                        </div>
                        <div style={{ marginTop: "10px", display: "flex", gap: "8px", flexWrap: "wrap" }}>
                          <button onClick={() => approveQaReview(item.id)} style={buttonStyle}>Approve</button>
                          <button onClick={() => overrideQaReview(item.id)} style={buttonStyle}>Override to Clean</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={card}>
                <h2 style={sectionTitle}>Channel Health</h2>
                {channelHealth.length === 0 ? (
                  <p style={muted}>No channel health data yet.</p>
                ) : (
                  <div style={{ display: "grid", gap: "10px", marginBottom: "8px" }}>
                    {channelHealth.map((item) => (
                      <div key={item.channel} style={agentCard}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", alignItems: "center" }}>
                          <strong>{item.channel}</strong>
                          <span style={statusPill(item.last_attempt_sent ? "sent" : "not sent")}>
                            {item.last_attempt_sent ? "healthy" : "attention"}
                          </span>
                        </div>
                        <div style={{ marginTop: "6px", fontSize: "12px", color: "#6b7280" }}>
                          Last success: {formatDate(item.last_success_at)}
                        </div>
                        <div style={{ marginTop: "6px", fontSize: "12px", color: "#6b7280" }}>
                          Last attempt: {formatDate(item.last_attempt_at)}
                        </div>
                        {item.last_failure_reason ? (
                          <div style={{ marginTop: "8px", fontSize: "12px", color: "#991b1b" }}>
                            {item.last_failure_reason}
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={card}>
                <h2 style={sectionTitle}>Alert Audit Center</h2>

                <div style={{ display: "grid", gap: "10px", marginBottom: "16px" }}>
                  <div style={controlRow}><span>Recent Audit Events</span><strong>{alertAudit.length}</strong></div>
                  <div style={controlRow}><span>Sent</span><span style={statusPill("sent")}>{auditSentCount}</span></div>
                  <div style={controlRow}><span>Not Sent</span><span style={statusPill("not sent")}>{auditFailedCount}</span></div>
                </div>

                <div style={{ display: "grid", gap: "12px", marginBottom: "16px" }}>
                  <a href={alertAuditCsvExportUrl} style={primaryButton}>Export Alert Audit CSV</a>
                  <a href={alertAuditXlsxExportUrl} style={primaryButton}>Export Alert Audit Excel</a>
                  <a href={alertAuditJsonExportUrl} style={secondaryButton}>Export Alert Audit JSON</a>
                  <a href={alertAuditBundleExportUrl} style={secondaryButton}>Download Alert Audit Bundle</a>
                </div>

                {alertAudit.length === 0 ? (
                  <p style={muted}>No audit events recorded yet.</p>
                ) : (
                  <div style={{ display: "grid", gap: "10px" }}>
                    {alertAudit.slice(0, 6).map((item) => (
                      <div key={item.id} style={agentCard}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", alignItems: "center" }}>
                          <strong>#{item.id} · {item.channel}</strong>
                          <span style={statusPill(item.sent ? "sent" : "not sent")}>
                            {item.sent ? "sent" : "not sent"}
                          </span>
                        </div>
                        <div style={{ marginTop: "6px", fontSize: "14px", color: "#374151" }}>
                          Inspection #{item.inspection_id} · {item.vendor_name} · {item.detected_issue}
                        </div>
                        <div style={{ marginTop: "6px", fontSize: "12px", color: "#6b7280" }}>
                          Batch: {item.dispatch_batch_id}
                        </div>
                        <div style={{ marginTop: "6px", fontSize: "12px", color: "#6b7280" }}>
                          {formatDate(item.created_at)}
                        </div>
                        {item.failure_reason ? (
                          <div style={{ marginTop: "8px", fontSize: "12px", color: "#991b1b" }}>
                            {item.failure_reason}
                          </div>
                        ) : null}
                        {!item.sent ? (
                          <div style={{ marginTop: "10px" }}>
                            <button
                              onClick={() => resendAuditEvent(item.id)}
                              disabled={resendingAuditId === item.id}
                              style={buttonStyle}
                            >
                              {resendingAuditId === item.id ? `Resending #${item.id}...` : `Resend #${item.id}`}
                            </button>
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={card}>
                <h2 style={sectionTitle}>Export Center</h2>
                <p style={{ color: "#4b5563", marginTop: 0 }}>
                  Download LumenAI inspection data for Excel, Power BI, Tableau,
                  investor decks, hospital QA analysis, or vendor defect reporting.
                </p>

                <div style={{ display: "grid", gap: "12px" }}>
                  <a href={csvExportUrl} style={primaryButton}>Export CSV</a>
                  <div style={exportHint}>Best for Excel, Power BI, and Tableau import.</div>
                  <a href={xlsxExportUrl} style={primaryButton}>Export Excel Workbook</a>
                  <div style={exportHint}>Includes inspection rows plus leadership summary sheet.</div>
                  <a href={jsonExportUrl} style={secondaryButton}>Export JSON</a>
                  <div style={exportHint}>Useful for engineering pipelines and integrations.</div>
                  <a href={bundleExportUrl} style={secondaryButton}>Download Full Export Bundle</a>
                  <div style={exportHint}>ZIP package containing CSV, JSON, XLSX, and summary artifacts.</div>
                </div>
              </div>
            </div>
          </div>

          <div style={{ marginTop: "12px", color: "#6b7280", fontSize: "14px" }}>
            Phase 2 now supports live stream ingestion, vendor intelligence, SPD alerts, autonomous agent recommendations, a full alert audit center, and resend actions for failed alerts.
          </div>
        </>
      )}
    </div>
  );
}

function Layout() {
  return (
    <BrowserRouter>
      <div style={{ borderBottom: "1px solid #e5e7eb", padding: "12px 24px", background: "#ffffff" }}>
        <div style={{ maxWidth: "1360px", margin: "0 auto", display: "flex", gap: "16px", alignItems: "center", flexWrap: "wrap" }}>
          <Link to="/" style={{ fontWeight: 700, textDecoration: "none", color: "#111827" }}>LumenAI</Link>
          <Link to="/history">History</Link>
        </div>
      </div>

      <Routes>
        <Route path="/" element={<DashboardHome />} />
        <Route path="/history" element={<InspectionHistory />} />
      </Routes>
    </BrowserRouter>
  );
}

const card: React.CSSProperties = {
  border: "1px solid #e5e7eb",
  borderRadius: "14px",
  padding: "20px",
  background: "#ffffff",
};

const agentCard: React.CSSProperties = {
  border: "1px solid #e5e7eb",
  borderRadius: "12px",
  padding: "14px",
  background: "#fafafa",
};

const alertCard: React.CSSProperties = {
  border: "1px solid #fecaca",
  borderRadius: "12px",
  padding: "14px",
  background: "#fff7f7",
};

const cardLabel: React.CSSProperties = {
  fontSize: "13px",
  color: "#6b7280",
  marginBottom: "10px",
};

const cardValue: React.CSSProperties = {
  fontSize: "32px",
  fontWeight: 800,
  color: "#111827",
};

const cardValueSmall: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#111827",
};

const sectionTitle: React.CSSProperties = {
  marginTop: 0,
  marginBottom: "12px",
};

const subTitle: React.CSSProperties = {
  marginTop: 0,
  marginBottom: "10px",
  fontSize: "15px",
};

const listRow: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  padding: "8px 0",
  borderBottom: "1px solid #f3f4f6",
};

const controlRow: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "center",
  padding: "8px 0",
  borderBottom: "1px solid #f3f4f6",
};

const primaryButton: React.CSSProperties = {
  display: "inline-block",
  padding: "10px 14px",
  borderRadius: "10px",
  background: "#111827",
  color: "#ffffff",
  textDecoration: "none",
  fontWeight: 600,
};

const secondaryButton: React.CSSProperties = {
  display: "inline-block",
  padding: "10px 14px",
  borderRadius: "10px",
  background: "#f3f4f6",
  color: "#111827",
  textDecoration: "none",
  fontWeight: 600,
  border: "1px solid #d1d5db",
};

const secondaryButtonInline: React.CSSProperties = {
  display: "inline-block",
  padding: "6px 10px",
  borderRadius: "8px",
  background: "#f3f4f6",
  color: "#111827",
  textDecoration: "none",
  fontWeight: 600,
  border: "1px solid #d1d5db",
  fontSize: "13px",
};

const buttonStyle: React.CSSProperties = {
  padding: "10px 14px",
  borderRadius: "10px",
  background: "#111827",
  color: "#ffffff",
  border: "none",
  cursor: "pointer",
  fontWeight: 600,
};

const exportHint: React.CSSProperties = {
  color: "#6b7280",
  fontSize: "13px",
  marginTop: "-4px",
};

const errorBox: React.CSSProperties = {
  background: "#fee2e2",
  color: "#991b1b",
  padding: "12px 16px",
  borderRadius: "8px",
};

const muted: React.CSSProperties = {
  color: "#6b7280",
};

const table: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: "12px",
  overflow: "hidden",
};

const th: React.CSSProperties = {
  textAlign: "left",
  padding: "12px",
  fontSize: "13px",
  color: "#374151",
  whiteSpace: "nowrap",
};

const td: React.CSSProperties = {
  padding: "12px",
  fontSize: "14px",
  color: "#111827",
  verticalAlign: "top",
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Layout />
  </React.StrictMode>
);
