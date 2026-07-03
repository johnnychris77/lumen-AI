import { lazy, Suspense, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { apiFetch } from "@/lib/api";

const BASE = import.meta.env.VITE_API_BASE_URL || "";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface Workflow {
  id: number;
  name: string;
  workflow_type: string;
  priority: string;
  sla_hours: number | null;
  approval_required: boolean;
  created_at: string;
}

interface Execution {
  id: number;
  workflow_id: number;
  resource_type: string;
  resource_id: string;
  status: string;
  priority: string;
  current_step: number;
  sla_due_at: string | null;
  created_at: string;
}

interface QueueItem {
  id: number;
  queue_type: string;
  title: string;
  priority: string;
  status: string;
  source_type: string | null;
  assigned_to: string | null;
  due_at: string | null;
  escalated: boolean;
  created_at: string;
}

interface RiskSnapshot {
  id: number;
  snapshot_type: string;
  period_label: string | null;
  risk_score: number;
  open_high_priority_items: number;
  overdue_items: number;
  active_escalations: number;
  total_open_queue_items: number;
  created_at: string;
}

interface CopilotRec {
  id: number;
  recommendation_type: string;
  title: string;
  confidence: number;
  review_status: string;
  human_review_required: boolean;
  reviewed_by: string | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Badges
// ---------------------------------------------------------------------------
function PriorityBadge({ p }: { p: string }) {
  const variants: Record<string, string> = {
    critical: "bg-red-100 text-red-800",
    high: "bg-orange-100 text-orange-800",
    normal: "bg-slate-100 text-slate-700",
    low: "bg-green-100 text-green-700",
  };
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${variants[p] || variants.normal}`}>
      {p}
    </span>
  );
}

function StatusBadge({ s }: { s: string }) {
  const variants: Record<string, string> = {
    completed: "bg-green-100 text-green-800",
    in_progress: "bg-blue-100 text-blue-800",
    awaiting_approval: "bg-yellow-100 text-yellow-800",
    escalated: "bg-red-100 text-red-800",
    pending: "bg-slate-100 text-slate-700",
    open: "bg-slate-100 text-slate-700",
    claimed: "bg-blue-100 text-blue-800",
    cancelled: "bg-slate-200 text-slate-500",
    accepted: "bg-green-100 text-green-800",
    rejected: "bg-red-100 text-red-800",
  };
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${variants[s] || variants.pending}`}>
      {s.replace(/_/g, " ")}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Tab: Orchestration
// ---------------------------------------------------------------------------
function OrchestrationTab({ tenant }: { tenant: string }) {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [wfType, setWfType] = useState("capa");
  const [wfName, setWfName] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const load = () => {
    apiFetch(`/api/operations/workflows?tenant_id=${tenant}`, { raw: true, headers: authHeaders() })
      .then((r) => r.json())
      .then(setWorkflows);
  };

  useEffect(() => { load(); }, [tenant]);

  const create = () => {
    if (!wfName.trim()) return;
    setLoading(true);
    apiFetch(`/api/operations/workflows?tenant_id=${tenant}`, { raw: true,
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        name: wfName,
        workflow_type: wfType,
        approval_required: true,
        sla_hours: 72,
        created_by: localStorage.getItem("user") || "admin",
      }),
    })
      .then((r) => r.json())
      .then(() => { setMsg("Workflow created."); setWfName(""); load(); })
      .finally(() => setLoading(false));
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader><CardTitle>Create Workflow Definition</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-48">
            <label className="block text-xs text-slate-500 mb-1">Name</label>
            <Input value={wfName} onChange={(e) => setWfName(e.target.value)} placeholder="Workflow name" />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Type</label>
            <select
              className="border border-slate-200 rounded px-2 py-1.5 text-sm"
              value={wfType}
              onChange={(e) => setWfType(e.target.value)}
            >
              {["capa", "inspection", "escalation", "notification"].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <Button onClick={create} disabled={loading}>Create</Button>
          {msg && <span className="text-xs text-green-700">{msg}</span>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Active Workflows</CardTitle></CardHeader>
        <CardContent>
          {workflows.length === 0 ? (
            <p className="text-sm text-slate-400">No workflows defined yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-slate-500">
                    <th className="py-2 pr-4 text-left">Name</th>
                    <th className="py-2 pr-4 text-left">Type</th>
                    <th className="py-2 pr-4 text-left">Priority</th>
                    <th className="py-2 pr-4 text-left">SLA (h)</th>
                    <th className="py-2 pr-4 text-left">Approval</th>
                  </tr>
                </thead>
                <tbody>
                  {workflows.map((w) => (
                    <tr key={w.id} className="border-b last:border-0 hover:bg-slate-50">
                      <td className="py-2 pr-4 font-medium">{w.name}</td>
                      <td className="py-2 pr-4">
                        <Badge variant="outline">{w.workflow_type}</Badge>
                      </td>
                      <td className="py-2 pr-4"><PriorityBadge p={w.priority} /></td>
                      <td className="py-2 pr-4">{w.sla_hours ?? "—"}</td>
                      <td className="py-2 pr-4">{w.approval_required ? "Required" : "Auto"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Work Queues
// ---------------------------------------------------------------------------
function WorkQueuesTab({ tenant }: { tenant: string }) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [queueFilter, setQueueFilter] = useState("technician");

  const load = () => {
    apiFetch(`/api/operations/work-queue?tenant_id=${tenant}&queue_type=${queueFilter}`,
      { raw: true, headers: authHeaders() }
    )
      .then((r) => r.json())
      .then(setItems);
  };

  useEffect(() => { load(); }, [tenant, queueFilter]);

  const claim = (id: number) => {
    const email = localStorage.getItem("user") || "user@hospital.org";
    apiFetch(`/api/operations/work-queue/${id}/claim?tenant_id=${tenant}&claimed_by=${encodeURIComponent(email)}`,
      { raw: true, method: "POST", headers: authHeaders() }
    ).then(() => load());
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {["technician", "manager", "executive", "vendor"].map((qt) => (
          <Button
            key={qt}
            variant={queueFilter === qt ? "default" : "outline"}
            onClick={() => setQueueFilter(qt)}
          >
            {qt.charAt(0).toUpperCase() + qt.slice(1)}
          </Button>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{queueFilter.charAt(0).toUpperCase() + queueFilter.slice(1)} Queue</CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <p className="text-sm text-slate-400">Queue is empty.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-slate-500">
                    <th className="py-2 pr-4 text-left">Title</th>
                    <th className="py-2 pr-4 text-left">Priority</th>
                    <th className="py-2 pr-4 text-left">Status</th>
                    <th className="py-2 pr-4 text-left">Assigned</th>
                    <th className="py-2 pr-4 text-left">Escalated</th>
                    <th className="py-2 pr-4 text-left">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className="border-b last:border-0 hover:bg-slate-50">
                      <td className="py-2 pr-4 font-medium">{item.title}</td>
                      <td className="py-2 pr-4"><PriorityBadge p={item.priority} /></td>
                      <td className="py-2 pr-4"><StatusBadge s={item.status} /></td>
                      <td className="py-2 pr-4 text-xs text-slate-500">{item.assigned_to ?? "Unassigned"}</td>
                      <td className="py-2 pr-4">
                        {item.escalated ? <span className="text-red-600 text-xs font-medium">Yes</span> : "—"}
                      </td>
                      <td className="py-2 pr-4">
                        {item.status === "open" && (
                          <Button size="sm" variant="outline" onClick={() => claim(item.id)}>
                            Claim
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Command Center
// ---------------------------------------------------------------------------
function CommandCenterTab({ tenant }: { tenant: string }) {
  const [dashboard, setDashboard] = useState<Record<string, unknown> | null>(null);
  const [snapshots, setSnapshots] = useState<RiskSnapshot[]>([]);

  useEffect(() => {
    apiFetch(`/api/operations/command-center/dashboard?tenant_id=${tenant}`, { raw: true,
      headers: authHeaders(),
    })
      .then((r) => r.json())
      .then(setDashboard);

    apiFetch(`/api/operations/command-center/snapshots?tenant_id=${tenant}`, { raw: true,
      headers: authHeaders(),
    })
      .then((r) => r.json())
      .then(setSnapshots);
  }, [tenant]);

  const risk = (dashboard?.risk as Record<string, number>) || {};
  const workload = (dashboard?.workload as Record<string, unknown>) || {};
  const byQueue = (workload.by_queue as Record<string, number>) || {};

  return (
    <div className="space-y-6">
      {dashboard && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "High Priority Open", value: risk.open_high_priority_items ?? 0 },
              { label: "Active Escalations", value: risk.active_escalations ?? 0 },
              { label: "Overdue Items", value: risk.overdue_items ?? 0 },
              { label: "Total Open", value: (workload.total_open as number) ?? 0 },
            ].map((kpi) => (
              <Card key={kpi.label}>
                <CardContent className="pt-4">
                  <p className="text-xs text-slate-500">{kpi.label}</p>
                  <p className="text-2xl font-semibold mt-1">{kpi.value}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader><CardTitle>Queue Depth by Role</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(byQueue).map(([role, count]) => (
                  <div key={role} className="text-center">
                    <p className="text-2xl font-semibold">{count}</p>
                    <p className="text-xs text-slate-500 capitalize">{role}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <p className="text-xs text-slate-400">
            Human review required. All figures are point-in-time snapshots.
          </p>
        </>
      )}

      {snapshots.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Historical Snapshots</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-slate-500">
                    <th className="py-2 pr-4 text-left">Type</th>
                    <th className="py-2 pr-4 text-left">Period</th>
                    <th className="py-2 pr-4 text-left">Risk Score</th>
                    <th className="py-2 pr-4 text-left">Escalations</th>
                    <th className="py-2 pr-4 text-left">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshots.map((s) => (
                    <tr key={s.id} className="border-b last:border-0 hover:bg-slate-50">
                      <td className="py-2 pr-4"><Badge variant="outline">{s.snapshot_type}</Badge></td>
                      <td className="py-2 pr-4">{s.period_label ?? "—"}</td>
                      <td className="py-2 pr-4">{s.risk_score.toFixed(2)}</td>
                      <td className="py-2 pr-4">{s.active_escalations}</td>
                      <td className="py-2 pr-4 text-xs text-slate-500">
                        {new Date(s.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Executions
// ---------------------------------------------------------------------------
function ExecutionsTab({ tenant }: { tenant: string }) {
  const [executions, setExecutions] = useState<Execution[]>([]);

  useEffect(() => {
    apiFetch(`/api/operations/executions?tenant_id=${tenant}`, { raw: true, headers: authHeaders() })
      .then((r) => r.json())
      .then(setExecutions);
  }, [tenant]);

  const approve = (id: number) => {
    apiFetch(`/api/operations/executions/${id}/approve?tenant_id=${tenant}`,
      { raw: true,
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          approved_by: localStorage.getItem("user") || "admin@hospital.org",
          approved: true,
        }),
      }
    ).then(() =>
      apiFetch(`/api/operations/executions?tenant_id=${tenant}`, { raw: true, headers: authHeaders() })
        .then((r) => r.json())
        .then(setExecutions)
    );
  };

  return (
    <Card>
      <CardHeader><CardTitle>Workflow Executions</CardTitle></CardHeader>
      <CardContent>
        {executions.length === 0 ? (
          <p className="text-sm text-slate-400">No executions yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-xs text-slate-500">
                  <th className="py-2 pr-4 text-left">ID</th>
                  <th className="py-2 pr-4 text-left">Resource</th>
                  <th className="py-2 pr-4 text-left">Priority</th>
                  <th className="py-2 pr-4 text-left">Status</th>
                  <th className="py-2 pr-4 text-left">SLA Due</th>
                  <th className="py-2 pr-4 text-left">Action</th>
                </tr>
              </thead>
              <tbody>
                {executions.map((e) => (
                  <tr key={e.id} className="border-b last:border-0 hover:bg-slate-50">
                    <td className="py-2 pr-4 text-slate-500">#{e.id}</td>
                    <td className="py-2 pr-4 font-medium">{e.resource_type} / {e.resource_id}</td>
                    <td className="py-2 pr-4"><PriorityBadge p={e.priority} /></td>
                    <td className="py-2 pr-4"><StatusBadge s={e.status} /></td>
                    <td className="py-2 pr-4 text-xs text-slate-500">
                      {e.sla_due_at ? new Date(e.sla_due_at).toLocaleDateString() : "—"}
                    </td>
                    <td className="py-2 pr-4">
                      {e.status === "awaiting_approval" && (
                        <Button size="sm" onClick={() => approve(e.id)}>Approve</Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Tab: Copilot
// ---------------------------------------------------------------------------
function CopilotTab({ tenant }: { tenant: string }) {
  const [queryText, setQueryText] = useState("");
  const [queryType, setQueryType] = useState("prioritization");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [recs, setRecs] = useState<CopilotRec[]>([]);
  const [loading, setLoading] = useState(false);

  const loadRecs = () => {
    apiFetch(`/api/operations/copilot/recommendations?tenant_id=${tenant}`, { raw: true,
      headers: authHeaders(),
    })
      .then((r) => r.json())
      .then(setRecs);
  };

  useEffect(() => { loadRecs(); }, [tenant]);

  const submit = () => {
    if (!queryText.trim()) return;
    setLoading(true);
    setResult(null);
    apiFetch(`/api/operations/copilot/query?tenant_id=${tenant}`, { raw: true,
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        asked_by: localStorage.getItem("user") || "user@hospital.org",
        query_text: queryText,
        query_type: queryType,
      }),
    })
      .then((r) => r.json())
      .then((d) => { setResult(d); loadRecs(); })
      .finally(() => setLoading(false));
  };

  const review = (id: number, status: string) => {
    apiFetch(`/api/operations/copilot/recommendations/${id}/review?tenant_id=${tenant}`,
      { raw: true,
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          reviewed_by: localStorage.getItem("user") || "admin@hospital.org",
          review_status: status,
        }),
      }
    ).then(() => loadRecs());
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader><CardTitle>Operations Copilot Query</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            {["prioritization", "workload", "action", "status"].map((qt) => (
              <Button
                key={qt}
                size="sm"
                variant={queryType === qt ? "default" : "outline"}
                onClick={() => setQueryType(qt)}
              >
                {qt.charAt(0).toUpperCase() + qt.slice(1)}
              </Button>
            ))}
          </div>
          <Input
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            placeholder="Ask an operational question…"
          />
          <Button onClick={submit} disabled={loading}>
            {loading ? "Querying…" : "Ask Copilot"}
          </Button>

          {result && (
            <div className="rounded border border-slate-200 bg-slate-50 p-4 text-sm space-y-2">
              <p className="font-medium">Candidate Response</p>
              <p className="text-slate-700">{result.response_summary as string}</p>
              <p className="text-xs text-slate-500">
                Confidence: {((result.confidence as number) * 100).toFixed(0)}% |{" "}
                Human review required: Yes
              </p>
              <p className="text-xs text-amber-700 border border-amber-200 bg-amber-50 rounded p-2">
                {result.disclaimer as string}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Pending Recommendations</CardTitle></CardHeader>
        <CardContent>
          {recs.filter((r) => r.review_status === "pending").length === 0 ? (
            <p className="text-sm text-slate-400">No pending recommendations.</p>
          ) : (
            <div className="space-y-3">
              {recs
                .filter((r) => r.review_status === "pending")
                .map((rec) => (
                  <div key={rec.id} className="border rounded p-3 text-sm space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{rec.title}</p>
                      <Badge variant="outline">{rec.recommendation_type}</Badge>
                    </div>
                    <p className="text-xs text-slate-500">
                      Confidence: {((rec.confidence ?? 0) * 100).toFixed(0)}%
                    </p>
                    <p className="text-xs text-amber-700">Human review required before any action.</p>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => review(rec.id, "accepted")}>Accept</Button>
                      <Button size="sm" variant="outline" onClick={() => review(rec.id, "rejected")}>
                        Reject
                      </Button>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main console
// ---------------------------------------------------------------------------
const TABS = [
  { id: "orchestration", label: "Orchestration" },
  { id: "queues", label: "Work Queues" },
  { id: "executions", label: "Executions" },
  { id: "command-center", label: "Command Center" },
  { id: "copilot", label: "Copilot" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function AutonomousOperationsConsole() {
  const [tab, setTab] = useState<TabId>("orchestration");
  const [tenant, setTenant] = useState(
    localStorage.getItem("tenantId") || "demo-tenant"
  );

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Autonomous Operations Platform
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Orchestrate quality, compliance, and inspection workflows with human-in-the-loop controls.
        </p>
      </div>

      {/* Tenant selector */}
      <div className="flex items-center gap-2">
        <label className="text-xs text-slate-500">Tenant</label>
        <Input
          className="w-56"
          value={tenant}
          onChange={(e) => setTenant(e.target.value)}
        />
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? "border-slate-900 text-slate-900"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "orchestration" && <OrchestrationTab tenant={tenant} />}
      {tab === "queues" && <WorkQueuesTab tenant={tenant} />}
      {tab === "executions" && <ExecutionsTab tenant={tenant} />}
      {tab === "command-center" && <CommandCenterTab tenant={tenant} />}
      {tab === "copilot" && <CopilotTab tenant={tenant} />}
    </div>
  );
}
