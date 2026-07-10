/**
 * v4.2 — LumenAI OS: Project Pulse — Real-Time Operations Center & Live
 * Clinical Intelligence. Composes fourteen live widgets plus event
 * stream, enterprise map, alerts, executive scores, workflow monitor,
 * AI ops, facility console, notifications, and replay into one command
 * center. Responsive grid classes (`grid-cols-1 md:grid-cols-*`)
 * throughout serve as the Pulse Mobile View (Section 13) — no separate
 * mobile app or framework exists in this codebase to extend, so a
 * responsive layout of the same real data is the mobile experience.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface CommandCenterData {
  enterprise_health: { enterprise_risk_score: number | null; drift_detected: boolean };
  facility_health: Record<string, unknown> | null;
  inspection_queue: { pending: number; throughput_24h: number };
  ai_analysis_queue: { pending: number; avg_inference_time_ms: number | null };
  supervisor_queue: { backlog: number; avg_review_time_minutes: number | null };
  repair_queue: { open: number };
  enterprise_alerts: PulseAlert[];
  digital_twin_health: { utilization_pct: number; bottleneck_station: string };
  knowledge_growth: { knowledge_confidence: number | null; recent_contributions: number };
  ai_model_health: Record<string, unknown>;
  system_status: { modules_registered: number; modules: string[] };
  integrations: { id: number; connector_key: string; status: string }[];
  notifications: { source: string; message: string; read: boolean }[];
  recent_activity: { id: number; action_type: string; module: string }[];
}

interface PulseAlert {
  id: number;
  alert_type: string;
  severity: string;
  evidence: string;
  confidence: number;
  recommendation: string;
  suggested_owner: string;
  status: string;
}

interface MapFacility {
  facility_id: string;
  facility_name: string;
  status_color: string;
  risk_score: number | null;
}

interface WorkflowMonitorEntry {
  execution_id: number;
  workflow_name: string;
  status: string;
  current_stage: string | null;
  waiting_state: string | null;
  responsible_user: string | null;
}

const TABS = [
  "Command Center", "Event Stream", "Enterprise Map", "Alerts", "Executive",
  "Workflow Monitor", "AI Ops", "Notifications", "Replay",
] as const;
type Tab = (typeof TABS)[number];

const STATUS_COLOR_CLASS: Record<string, string> = {
  green: "bg-emerald-500", yellow: "bg-yellow-400", orange: "bg-orange-500", red: "bg-red-600", gray: "bg-slate-300",
};

function Widget({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{title}</p>
      {children}
    </div>
  );
}

export default function PulseCommandCenterDashboard() {
  const [tab, setTab] = useState<Tab>("Command Center");
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState<CommandCenterData | null>(null);
  const [events, setEvents] = useState<{ id: number; event_type: string; created_at: string; payload: Record<string, unknown> }[]>([]);
  const [mapFacilities, setMapFacilities] = useState<MapFacility[]>([]);
  const [alerts, setAlerts] = useState<PulseAlert[]>([]);
  const [executive, setExecutive] = useState<Record<string, unknown> | null>(null);
  const [activeWorkflows, setActiveWorkflows] = useState<WorkflowMonitorEntry[]>([]);
  const [aiOps, setAiOps] = useState<Record<string, unknown> | null>(null);
  const [notifications, setNotifications] = useState<{ source: string; message: string; read: boolean }[]>([]);
  const [replayResult, setReplayResult] = useState<Record<string, unknown> | null>(null);
  const [shiftStart, setShiftStart] = useState(new Date().toISOString().slice(0, 16));

  async function loadCommandCenter() {
    setBusy(true);
    try {
      setData(await api.get<CommandCenterData>("/api/pulse/command-center"));
    } finally {
      setBusy(false);
    }
  }

  async function loadEvents() {
    setBusy(true);
    try {
      const result = await api.get<{ events: typeof events }>("/api/pulse/events");
      setEvents(result.events);
    } finally {
      setBusy(false);
    }
  }

  async function loadMap() {
    setBusy(true);
    try {
      const result = await api.get<{ facilities: MapFacility[] }>("/api/pulse/map");
      setMapFacilities(result.facilities);
    } finally {
      setBusy(false);
    }
  }

  async function loadAlerts() {
    setBusy(true);
    try {
      const result = await api.get<{ alerts: PulseAlert[] }>("/api/pulse/alerts");
      setAlerts(result.alerts);
    } finally {
      setBusy(false);
    }
  }

  async function generateAlerts() {
    setBusy(true);
    try {
      await api.post("/api/pulse/alerts/generate");
      await loadAlerts();
    } finally {
      setBusy(false);
    }
  }

  async function acknowledgeAlert(id: number) {
    setBusy(true);
    try {
      await api.post(`/api/pulse/alerts/${id}/acknowledge`);
      await loadAlerts();
    } finally {
      setBusy(false);
    }
  }

  async function loadExecutive() {
    setBusy(true);
    try {
      setExecutive(await api.get<Record<string, unknown>>("/api/pulse/executive"));
    } finally {
      setBusy(false);
    }
  }

  async function loadWorkflowMonitor() {
    setBusy(true);
    try {
      const result = await api.get<{ active_workflows: WorkflowMonitorEntry[] }>("/api/pulse/workflow-monitor");
      setActiveWorkflows(result.active_workflows);
    } finally {
      setBusy(false);
    }
  }

  async function loadAiOps() {
    setBusy(true);
    try {
      setAiOps(await api.get<Record<string, unknown>>("/api/pulse/ai-ops"));
    } finally {
      setBusy(false);
    }
  }

  async function loadNotifications() {
    setBusy(true);
    try {
      const result = await api.get<{ notifications: typeof notifications }>("/api/pulse/notifications");
      setNotifications(result.notifications);
    } finally {
      setBusy(false);
    }
  }

  async function runShiftReplay() {
    setBusy(true);
    try {
      const iso = new Date(shiftStart).toISOString();
      const result = await api.get<Record<string, unknown>>(`/api/pulse/replay/shift?shift_start=${encodeURIComponent(iso)}`);
      setReplayResult(result);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadCommandCenter();
  }, []);

  function selectTab(t: Tab) {
    setTab(t);
    if (t === "Event Stream") loadEvents();
    if (t === "Enterprise Map") loadMap();
    if (t === "Alerts") loadAlerts();
    if (t === "Executive") loadExecutive();
    if (t === "Workflow Monitor") loadWorkflowMonitor();
    if (t === "AI Ops") loadAiOps();
    if (t === "Notifications") loadNotifications();
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Pulse — Real-Time Operations Center</h2>
        <p className="text-sm text-slate-500">
          Live situational awareness for Sterile Processing leadership. Pulse does not replace human
          decision-making — every score and alert is decision support only.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200 flex-wrap overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => selectTab(t)}
            className={`px-3 py-2 text-xs md:text-sm font-medium rounded-t-md whitespace-nowrap ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {busy && <p className="text-sm text-slate-400">Loading…</p>}

      {tab === "Command Center" && data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <Widget title="Enterprise Health">
            <p className="text-2xl font-bold">{data.enterprise_health.enterprise_risk_score ?? "—"}</p>
            <p className="text-xs text-slate-500">{data.enterprise_health.drift_detected ? "Drift detected" : "Stable"}</p>
          </Widget>
          <Widget title="Inspection Queue">
            <p className="text-2xl font-bold">{data.inspection_queue.pending}</p>
            <p className="text-xs text-slate-500">{data.inspection_queue.throughput_24h} in last 24h</p>
          </Widget>
          <Widget title="AI Analysis Queue">
            <p className="text-2xl font-bold">{data.ai_analysis_queue.pending}</p>
            <p className="text-xs text-slate-500">{data.ai_analysis_queue.avg_inference_time_ms ?? "—"} ms avg</p>
          </Widget>
          <Widget title="Supervisor Queue">
            <p className="text-2xl font-bold">{data.supervisor_queue.backlog}</p>
            <p className="text-xs text-slate-500">{data.supervisor_queue.avg_review_time_minutes ?? "—"} min avg review</p>
          </Widget>
          <Widget title="Repair Queue">
            <p className="text-2xl font-bold">{data.repair_queue.open}</p>
          </Widget>
          <Widget title="Digital Twin Health">
            <p className="text-2xl font-bold">{data.digital_twin_health.utilization_pct}%</p>
            <p className="text-xs text-slate-500">Bottleneck: {data.digital_twin_health.bottleneck_station || "none"}</p>
          </Widget>
          <Widget title="Knowledge Growth">
            <p className="text-2xl font-bold">{data.knowledge_growth.recent_contributions}</p>
            <p className="text-xs text-slate-500">confidence {data.knowledge_growth.knowledge_confidence ?? "—"}</p>
          </Widget>
          <Widget title="System Status">
            <p className="text-2xl font-bold">{data.system_status.modules_registered}</p>
            <p className="text-xs text-slate-500">modules registered</p>
          </Widget>
          <Widget title="Enterprise Alerts">
            <ul className="text-xs space-y-1">
              {data.enterprise_alerts.slice(0, 5).map((a) => (
                <li key={a.id}>{a.alert_type.replace(/_/g, " ")} · {a.severity}</li>
              ))}
              {data.enterprise_alerts.length === 0 && <li className="text-slate-400">None active</li>}
            </ul>
          </Widget>
          <Widget title="Integrations">
            <ul className="text-xs space-y-1">
              {data.integrations.slice(0, 5).map((c) => <li key={c.id}>{c.connector_key} · {c.status}</li>)}
              {data.integrations.length === 0 && <li className="text-slate-400">None connected</li>}
            </ul>
          </Widget>
          <Widget title="Notifications">
            <ul className="text-xs space-y-1">
              {data.notifications.slice(0, 5).map((n, i) => <li key={i}>{n.message}</li>)}
              {data.notifications.length === 0 && <li className="text-slate-400">None</li>}
            </ul>
          </Widget>
          <Widget title="Recent Activity">
            <ul className="text-xs space-y-1">
              {data.recent_activity.slice(0, 5).map((a) => <li key={a.id}>{a.action_type} · {a.module}</li>)}
              {data.recent_activity.length === 0 && <li className="text-slate-400">None yet</li>}
            </ul>
          </Widget>
        </div>
      )}

      {tab === "Event Stream" && (
        <Widget title="Live Event Stream">
          <ul className="space-y-1 text-sm">
            {events.map((e) => (
              <li key={e.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{e.event_type}</span>
                <span className="text-xs text-slate-500">
                  {String(e.payload?.facility || "")} {String(e.payload?.severity || "")} · {e.created_at}
                </span>
              </li>
            ))}
            {events.length === 0 && <p className="text-slate-400">No events yet</p>}
          </ul>
        </Widget>
      )}

      {tab === "Enterprise Map" && (
        <Widget title="Enterprise Command Map">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
            {mapFacilities.map((f) => (
              <div key={f.facility_id} className="flex items-center gap-2 rounded-md border border-slate-100 p-2 text-sm">
                <span className={`inline-block h-3 w-3 rounded-full ${STATUS_COLOR_CLASS[f.status_color]}`} />
                <span>{f.facility_name}</span>
                <span className="ml-auto text-xs text-slate-500">{f.risk_score ?? "—"}</span>
              </div>
            ))}
            {mapFacilities.length === 0 && <p className="text-slate-400">No facilities yet</p>}
          </div>
        </Widget>
      )}

      {tab === "Alerts" && (
        <div className="space-y-3">
          <button onClick={generateAlerts} disabled={busy} className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">
            Generate Alerts
          </button>
          <Widget title="Active Alerts">
            <ul className="space-y-2 text-sm">
              {alerts.map((a) => (
                <li key={a.id} className="border-b border-slate-100 pb-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium capitalize">{a.alert_type.replace(/_/g, " ")}</span>
                    <span className="text-xs text-slate-500">{a.severity} · conf {a.confidence}</span>
                  </div>
                  <p className="text-xs text-slate-700 mt-1">{a.evidence}</p>
                  <p className="text-xs text-slate-500 mt-1">Recommendation: {a.recommendation} (owner: {a.suggested_owner})</p>
                  {a.status === "active" && (
                    <button onClick={() => acknowledgeAlert(a.id)} className="mt-1 rounded-md bg-slate-200 px-2 py-1 text-xs font-semibold">
                      Acknowledge
                    </button>
                  )}
                </li>
              ))}
              {alerts.length === 0 && <p className="text-slate-400">No alerts</p>}
            </ul>
          </Widget>
        </div>
      )}

      {tab === "Executive" && executive && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(executive).filter(([k]) => k !== "forecast_summary" && k !== "human_review_required").map(([k, v]) => (
            <Widget key={k} title={k.replace(/_/g, " ")}>
              <p className="text-xl font-bold">{v === null || v === undefined ? "—" : String(v)}</p>
            </Widget>
          ))}
        </div>
      )}

      {tab === "Workflow Monitor" && (
        <Widget title="Active Workflows">
          <ul className="space-y-1 text-sm">
            {activeWorkflows.map((w) => (
              <li key={w.execution_id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{w.workflow_name}</span>
                <span className="text-xs text-slate-500">{w.current_stage} · {w.waiting_state ?? "running"} · {w.responsible_user ?? ""}</span>
              </li>
            ))}
            {activeWorkflows.length === 0 && <p className="text-slate-400">No workflows currently running</p>}
          </ul>
        </Widget>
      )}

      {tab === "AI Ops" && aiOps && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Widget title="Model Version Distribution">
            <pre className="text-xs">{JSON.stringify(aiOps.model_version_distribution, null, 2)}</pre>
          </Widget>
          <Widget title="Confidence Distribution">
            <pre className="text-xs">{JSON.stringify(aiOps.confidence_distribution, null, 2)}</pre>
          </Widget>
          <Widget title="Drift & Rates">
            <p className="text-xs">Drift: {String(aiOps.model_drift_detected)}</p>
            <p className="text-xs">FP rate: {String(aiOps.false_positive_rate)}</p>
            <p className="text-xs">FN rate: {String(aiOps.false_negative_rate)}</p>
          </Widget>
          <Widget title="Hardware">
            <p className="text-xs">GPU: {String(aiOps.gpu_utilization)} · CPU: {String(aiOps.cpu_utilization)}</p>
            <p className="text-xs text-slate-400 mt-1">{String(aiOps.hardware_note)}</p>
          </Widget>
        </div>
      )}

      {tab === "Notifications" && (
        <Widget title="Notification Center">
          <ul className="space-y-1 text-sm">
            {notifications.map((n, i) => (
              <li key={i} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span>{n.message}</span>
                <span className="text-xs text-slate-500">{n.source}{n.read ? "" : " · unread"}</span>
              </li>
            ))}
            {notifications.length === 0 && <p className="text-slate-400">No notifications</p>}
          </ul>
        </Widget>
      )}

      {tab === "Replay" && (
        <Widget title="Operational Replay — Shift">
          <div className="flex flex-col sm:flex-row gap-2 mb-3">
            <input
              type="datetime-local" value={shiftStart} onChange={(e) => setShiftStart(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
            <button onClick={runShiftReplay} className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white">
              Replay Shift
            </button>
          </div>
          {replayResult && <pre className="text-xs bg-slate-50 rounded-md p-3 overflow-x-auto max-h-96">{JSON.stringify(replayResult, null, 2)}</pre>}
        </Widget>
      )}
    </div>
  );
}
