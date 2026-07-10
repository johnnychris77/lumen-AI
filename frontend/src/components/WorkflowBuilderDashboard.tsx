/**
 * v4.1 — LumenAI OS: Project Forge — AI Workflow Builder & No-Code
 * Clinical Rules Engine. A lightweight custom SVG/HTML node canvas —
 * no existing diagram library exists in this codebase (confirmed before
 * writing this: no reactflow/dagre/konva/cytoscape in package.json), so
 * this is a small, self-contained drag-and-drop editor rather than a new
 * npm dependency. Zoom scales logical node coordinates directly (so the
 * browser's native scrollbars provide panning, without CSS-transform/
 * scroll interaction complexity); auto-layout is a real breadth-first
 * layering computed from the graph's own edges, not a cosmetic shuffle.
 */
import { useState } from "react";
import { api } from "@/lib/api";

const NODE_TYPES = [
  "start", "inspection", "ai_analysis", "anatomy_check", "coverage_check", "knowledge_lookup",
  "digital_twin_update", "clinical_reasoning", "supervisor_review", "conditional_branch",
  "notification", "approval", "repair_referral", "knowledge_capture", "export_report", "end",
] as const;

interface WFNode {
  key: string;
  type: string;
  label: string;
  x: number;
  y: number;
}

interface WFEdge {
  from: string;
  to: string;
  condition?: string;
}

interface WorkflowSummary {
  id: number;
  name: string;
  status: string;
  version: number;
  category: string;
  is_template?: boolean;
  marketplace_status?: string;
}

interface WorkflowDetail extends WorkflowSummary {
  nodes: WFNode[];
  edges: WFEdge[];
}

const NODE_WIDTH = 150;
const NODE_HEIGHT = 56;

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

function autoLayout(nodes: WFNode[], edges: WFEdge[]): WFNode[] {
  const start = nodes.find((n) => n.type === "start");
  if (!start) return nodes;
  const depth: Record<string, number> = { [start.key]: 0 };
  const queue = [start.key];
  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const edge of edges.filter((e) => e.from === current)) {
      if (!(edge.to in depth)) {
        depth[edge.to] = depth[current] + 1;
        queue.push(edge.to);
      }
    }
  }
  const layerCounts: Record<number, number> = {};
  return nodes.map((n) => {
    const d = depth[n.key] ?? 0;
    const indexInLayer = layerCounts[d] ?? 0;
    layerCounts[d] = indexInLayer + 1;
    return { ...n, x: d * 220, y: indexInLayer * 140 };
  });
}

const TABS = ["Builder", "Rules", "Templates", "Simulator", "Marketplace", "Approvals"] as const;
type Tab = (typeof TABS)[number];

export default function WorkflowBuilderDashboard() {
  const [tab, setTab] = useState<Tab>("Builder");
  const [busy, setBusy] = useState(false);

  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [current, setCurrent] = useState<WorkflowDetail | null>(null);
  const [zoom, setZoom] = useState(1);
  const [dragKey, setDragKey] = useState<string | null>(null);
  const [linkMode, setLinkMode] = useState(false);
  const [linkSource, setLinkSource] = useState<string | null>(null);
  const [workflowName, setWorkflowName] = useState("New Workflow");

  const [templates, setTemplates] = useState<{ id: number; name: string; category: string }[]>([]);
  const [marketplace, setMarketplace] = useState<WorkflowSummary[]>([]);
  const [simResult, setSimResult] = useState<Record<string, unknown> | null>(null);
  const [simWorkflowId, setSimWorkflowId] = useState("");
  const [simInspectionId, setSimInspectionId] = useState("");
  const [chains, setChains] = useState<{ id: number; name: string; steps: string[] }[]>([]);

  async function loadWorkflows() {
    setBusy(true);
    try {
      const result = await api.get<{ workflows: WorkflowSummary[] }>("/api/forge/workflows");
      setWorkflows(result.workflows);
    } finally {
      setBusy(false);
    }
  }

  function newBlankWorkflow() {
    setCurrent({
      id: 0, name: workflowName, status: "draft", version: 1, category: "",
      nodes: [{ key: "start", type: "start", label: "Start", x: 0, y: 0 }], edges: [],
    });
  }

  async function saveWorkflow() {
    if (!current) return;
    setBusy(true);
    try {
      if (current.id === 0) {
        const created = await api.post<WorkflowDetail>("/api/forge/workflows", {
          name: current.name, nodes: current.nodes, edges: current.edges,
        });
        setCurrent(created);
      } else {
        const revised = await api.post<WorkflowDetail>(`/api/forge/workflows/${current.id}/revise`, {
          nodes: current.nodes, edges: current.edges,
        });
        setCurrent(revised);
      }
      await loadWorkflows();
    } finally {
      setBusy(false);
    }
  }

  async function publishWorkflow() {
    if (!current || current.id === 0) return;
    setBusy(true);
    try {
      const published = await api.post<WorkflowDetail>(`/api/forge/workflows/${current.id}/publish`);
      setCurrent(published);
      await loadWorkflows();
    } finally {
      setBusy(false);
    }
  }

  function addNode(type: string) {
    if (!current) return;
    const key = `${type}_${current.nodes.length}_${Date.now() % 10000}`;
    setCurrent({ ...current, nodes: [...current.nodes, { key, type, label: type.replace(/_/g, " "), x: 100, y: 100 }] });
  }

  function removeNode(key: string) {
    if (!current) return;
    setCurrent({
      ...current,
      nodes: current.nodes.filter((n) => n.key !== key),
      edges: current.edges.filter((e) => e.from !== key && e.to !== key),
    });
  }

  function onNodeMouseDown(key: string) {
    setDragKey(key);
  }

  function onCanvasMouseMove(e: React.MouseEvent) {
    if (!dragKey || !current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / zoom;
    const y = (e.clientY - rect.top) / zoom;
    setCurrent({
      ...current,
      nodes: current.nodes.map((n) => (n.key === dragKey ? { ...n, x: Math.max(0, x - NODE_WIDTH / 2), y: Math.max(0, y - NODE_HEIGHT / 2) } : n)),
    });
  }

  function onCanvasMouseUp() {
    setDragKey(null);
  }

  function onNodeClick(key: string) {
    if (!linkMode || !current) return;
    if (!linkSource) {
      setLinkSource(key);
      return;
    }
    if (linkSource !== key) {
      setCurrent({ ...current, edges: [...current.edges, { from: linkSource, to: key }] });
    }
    setLinkSource(null);
    setLinkMode(false);
  }

  function runAutoLayout() {
    if (!current) return;
    setCurrent({ ...current, nodes: autoLayout(current.nodes, current.edges) });
  }

  async function loadTemplates() {
    setBusy(true);
    try {
      const result = await api.get<{ templates: { id: number; name: string; category: string }[] }>("/api/forge/workflow-templates");
      setTemplates(result.templates);
    } finally {
      setBusy(false);
    }
  }

  async function importTemplate(category: string) {
    setBusy(true);
    try {
      await api.post(`/api/forge/workflow-templates/${category}/import`);
      await loadWorkflows();
    } finally {
      setBusy(false);
    }
  }

  async function loadMarketplace() {
    setBusy(true);
    try {
      const result = await api.get<{ listings: WorkflowSummary[] }>("/api/forge/marketplace");
      setMarketplace(result.listings);
    } finally {
      setBusy(false);
    }
  }

  async function runSimulation() {
    setBusy(true);
    try {
      const result = await api.post<Record<string, unknown>>("/api/forge/workflow-execution/simulate", {
        workflow_id: Number(simWorkflowId), inspection_id: Number(simInspectionId),
      });
      setSimResult(result);
    } finally {
      setBusy(false);
    }
  }

  async function loadChains() {
    setBusy(true);
    try {
      const result = await api.get<{ chains: { id: number; name: string; steps: string[] }[] }>("/api/forge/approval-chains");
      setChains(result.chains);
    } finally {
      setBusy(false);
    }
  }

  async function createDefaultChain() {
    setBusy(true);
    try {
      await api.post("/api/forge/approval-chains", { name: "Standard Chain" });
      await loadChains();
    } finally {
      setBusy(false);
    }
  }

  function selectTab(t: Tab) {
    setTab(t);
    if (t === "Builder") loadWorkflows();
    if (t === "Templates") loadTemplates();
    if (t === "Marketplace") loadMarketplace();
    if (t === "Approvals") loadChains();
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Workflow Builder — Project Forge</h2>
        <p className="text-sm text-slate-500">
          Visually design inspection workflows, clinical rules, and automation without writing code. Every workflow
          remains explainable, version-controlled, auditable, and governed.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => selectTab(t)}
            className={`px-4 py-2 text-sm font-medium rounded-t-md ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {busy && <p className="text-sm text-slate-400">Loading…</p>}

      {tab === "Builder" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 flex-wrap">
            <input
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
              placeholder="Workflow name"
            />
            <button onClick={newBlankWorkflow} className="rounded-md bg-slate-200 px-3 py-1.5 text-xs font-semibold">New Workflow</button>
            <button onClick={saveWorkflow} disabled={!current || busy} className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">Save</button>
            <button onClick={publishWorkflow} disabled={!current || current.id === 0 || busy} className="rounded-md bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">Publish</button>
            <button onClick={runAutoLayout} disabled={!current} className="rounded-md bg-slate-200 px-3 py-1.5 text-xs font-semibold disabled:opacity-50">Auto-Layout</button>
            <button onClick={() => setLinkMode((v) => !v)} disabled={!current} className={`rounded-md px-3 py-1.5 text-xs font-semibold disabled:opacity-50 ${linkMode ? "bg-amber-500 text-white" : "bg-slate-200"}`}>
              {linkMode ? "Click two nodes to connect…" : "Connect Nodes"}
            </button>
            <div className="flex items-center gap-1 ml-2">
              <button onClick={() => setZoom((z) => Math.max(0.4, z - 0.1))} className="rounded-md bg-slate-200 px-2 py-1 text-xs">−</button>
              <span className="text-xs text-slate-500 w-10 text-center">{Math.round(zoom * 100)}%</span>
              <button onClick={() => setZoom((z) => Math.min(2, z + 0.1))} className="rounded-md bg-slate-200 px-2 py-1 text-xs">+</button>
            </div>
          </div>

          <div className="flex gap-3">
            <Section title="Node Palette">
              <div className="flex flex-col gap-1 w-40">
                {NODE_TYPES.map((t) => (
                  <button
                    key={t}
                    onClick={() => addNode(t)}
                    disabled={!current}
                    className="text-left rounded-md border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50 disabled:opacity-50"
                  >
                    {t.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </Section>

            <div
              className="flex-1 relative overflow-auto rounded-lg border border-slate-200 bg-slate-50"
              style={{ height: 480 }}
              onMouseMove={onCanvasMouseMove}
              onMouseUp={onCanvasMouseUp}
              onMouseLeave={onCanvasMouseUp}
            >
              {current && (
                <div style={{ position: "relative", width: 2000, height: 1200 }}>
                  <svg style={{ position: "absolute", top: 0, left: 0, width: 2000, height: 1200, pointerEvents: "none" }}>
                    {current.edges.map((edge, i) => {
                      const from = current.nodes.find((n) => n.key === edge.from);
                      const to = current.nodes.find((n) => n.key === edge.to);
                      if (!from || !to) return null;
                      const x1 = (from.x + NODE_WIDTH / 2) * zoom;
                      const y1 = (from.y + NODE_HEIGHT / 2) * zoom;
                      const x2 = (to.x + NODE_WIDTH / 2) * zoom;
                      const y2 = (to.y + NODE_HEIGHT / 2) * zoom;
                      return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#64748b" strokeWidth={2} markerEnd="url(#arrow)" />;
                    })}
                    <defs>
                      <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                        <path d="M0,0 L6,3 L0,6 Z" fill="#64748b" />
                      </marker>
                    </defs>
                  </svg>
                  {current.nodes.map((node) => (
                    <div
                      key={node.key}
                      onMouseDown={() => onNodeMouseDown(node.key)}
                      onClick={() => onNodeClick(node.key)}
                      style={{
                        position: "absolute", left: node.x * zoom, top: node.y * zoom,
                        width: NODE_WIDTH * zoom, height: NODE_HEIGHT * zoom, cursor: "move",
                      }}
                      className={`rounded-md border-2 bg-white shadow-sm flex flex-col items-center justify-center text-center px-1 ${
                        linkSource === node.key ? "border-amber-500" : "border-slate-300"
                      }`}
                    >
                      <button
                        onClick={(e) => { e.stopPropagation(); removeNode(node.key); }}
                        className="absolute top-0 right-1 text-slate-400 hover:text-red-600 text-xs"
                      >
                        ×
                      </button>
                      <p className="text-xs font-semibold capitalize">{node.label.replace(/_/g, " ")}</p>
                    </div>
                  ))}
                </div>
              )}
              {!current && <p className="p-4 text-sm text-slate-400">Click "New Workflow" to start designing.</p>}
            </div>
          </div>

          <Section title={`Saved Workflows (${workflows.length})`}>
            <ul className="space-y-1 text-sm">
              {workflows.map((w) => (
                <li key={w.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                  <span className="font-medium">{w.name}</span>
                  <span className="text-xs text-slate-500">v{w.version} · {w.status}</span>
                </li>
              ))}
              {workflows.length === 0 && <p className="text-slate-400">No workflows saved yet</p>}
            </ul>
          </Section>
        </div>
      )}

      {tab === "Rules" && (
        <Section title="Clinical Rule Engine">
          <p className="text-sm text-slate-500">
            Rules are nested AND/OR/NOT condition trees evaluated over instrument family, finding, zone, severity,
            coverage %, confidence, and more — create and manage them via <code>/api/forge/workflow-rules</code>.
          </p>
        </Section>
      )}

      {tab === "Templates" && (
        <Section title="Workflow Templates">
          <ul className="space-y-1 text-sm">
            {templates.map((t) => (
              <li key={t.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{t.name}</span>
                <button onClick={() => importTemplate(t.category)} className="rounded-md bg-slate-900 px-2 py-1 text-xs font-semibold text-white">
                  Import
                </button>
              </li>
            ))}
            {templates.length === 0 && <p className="text-slate-400">No templates loaded</p>}
          </ul>
        </Section>
      )}

      {tab === "Simulator" && (
        <Section title="Workflow Simulator">
          <div className="flex gap-2 mb-3">
            <input value={simWorkflowId} onChange={(e) => setSimWorkflowId(e.target.value)} placeholder="Workflow ID" className="rounded-md border border-slate-300 px-2 py-1 text-sm w-32" />
            <input value={simInspectionId} onChange={(e) => setSimInspectionId(e.target.value)} placeholder="Inspection ID" className="rounded-md border border-slate-300 px-2 py-1 text-sm w-32" />
            <button onClick={runSimulation} className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white">Replay</button>
          </div>
          {simResult && (
            <pre className="text-xs bg-slate-50 rounded-md p-3 overflow-x-auto">{JSON.stringify(simResult, null, 2)}</pre>
          )}
        </Section>
      )}

      {tab === "Marketplace" && (
        <Section title="Forge Marketplace">
          <ul className="space-y-1 text-sm">
            {marketplace.map((w) => (
              <li key={w.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{w.name}</span>
                <span className="text-xs text-slate-500">{w.category} · {w.marketplace_status}</span>
              </li>
            ))}
            {marketplace.length === 0 && <p className="text-slate-400">No published community workflows yet</p>}
          </ul>
        </Section>
      )}

      {tab === "Approvals" && (
        <Section title="Approval Chains">
          <button onClick={createDefaultChain} className="mb-3 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white">
            Create Standard Chain (Technician → Supervisor → Manager → Director)
          </button>
          <ul className="space-y-1 text-sm">
            {chains.map((c) => (
              <li key={c.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{c.name}</span>
                <span className="text-xs text-slate-500">{c.steps.join(" → ")}</span>
              </li>
            ))}
            {chains.length === 0 && <p className="text-slate-400">No approval chains defined yet</p>}
          </ul>
        </Section>
      )}
    </div>
  );
}
