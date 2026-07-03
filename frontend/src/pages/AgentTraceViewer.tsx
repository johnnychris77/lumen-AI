import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchJSON(path: string) {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

interface AgentInfo {
  name: string;
  version: string;
  capabilities: string[];
  depends_on: string[];
  pipeline_position: number;
  status: string;
  health: string;
}

interface TraceEntry {
  agent: string;
  version: string;
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}

function summarize(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "none";
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) return "—";
    return entries.slice(0, 3).map(([k, v]) => `${k}: ${summarize(v)}`).join(" · ");
  }
  return String(value);
}

function TraceCard({ entry, index, total }: { entry: TraceEntry; index: number; total: number }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="relative">
      <div className="rounded-lg border bg-white p-4">
        <button className="w-full text-left flex items-center justify-between" onClick={() => setExpanded((e) => !e)}>
          <div>
            <p className="text-xs text-gray-400">Step {index + 1} of {total}</p>
            <p className="font-semibold text-gray-900">{entry.agent}</p>
          </div>
          <span className="text-xs text-gray-400">v{entry.version}</span>
        </button>
        {expanded && (
          <div className="mt-3 grid md:grid-cols-2 gap-3 text-sm">
            <div>
              <p className="font-medium text-gray-700 mb-1">Input</p>
              <pre className="text-xs bg-gray-50 border rounded p-2 overflow-x-auto">{JSON.stringify(entry.input_summary, null, 2)}</pre>
            </div>
            <div>
              <p className="font-medium text-gray-700 mb-1">Output</p>
              <pre className="text-xs bg-gray-50 border rounded p-2 overflow-x-auto">{JSON.stringify(entry.output_summary, null, 2)}</pre>
            </div>
          </div>
        )}
        {!expanded && (
          <p className="text-xs text-gray-500 mt-2">{summarize(entry.output_summary)}</p>
        )}
      </div>
      {index < total - 1 && <div className="h-4 w-px bg-gray-300 mx-auto" />}
    </div>
  );
}

export default function AgentTraceViewer() {
  const [inspectionId, setInspectionId] = useState("");
  const [registry, setRegistry] = useState<AgentInfo[]>([]);
  const [trace, setTrace] = useState<TraceEntry[] | null>(null);
  const [finalRecommendation, setFinalRecommendation] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchJSON("/api/agents/registry").then((d) => setRegistry(d.agents)).catch(() => {});
  }, []);

  const runTrace = () => {
    if (!inspectionId) return;
    setLoading(true);
    setError(null);
    fetchJSON(`/api/agents/trace/${inspectionId}`)
      .then((d) => {
        setTrace(d.trace);
        setFinalRecommendation(d.final_recommendation);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  return (
    <div className="p-6 space-y-8 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Explainable Agent Trace</h1>
        <p className="text-sm text-gray-500 mt-1">
          Which specialized agent produced which decision — instrument identity through anatomy,
          findings, risk, and recommended action.
        </p>
      </div>

      <section>
        <SectionHeader title="Agent Registry" subtitle="The ten agents in the pipeline, in order." />
        <div className="grid md:grid-cols-2 gap-3">
          {registry.map((a) => (
            <div key={a.name} className="rounded-lg border bg-white p-3 text-sm flex items-center justify-between">
              <div>
                <span className="font-medium text-gray-900">{a.pipeline_position}. {a.name}</span>
                <p className="text-xs text-gray-500">{a.capabilities.join(", ")}</p>
              </div>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded ${a.health === "ok" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"}`}>
                {a.health}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <SectionHeader title="Trace an Inspection" subtitle="Enter an inspection ID to see the full agent-by-agent reasoning trace." />
        <div className="flex gap-2 mb-4">
          <input
            value={inspectionId}
            onChange={(e) => setInspectionId(e.target.value)}
            placeholder="Inspection ID"
            className="text-sm border rounded px-2 py-1 flex-1"
            onKeyDown={(e) => e.key === "Enter" && runTrace()}
          />
          <button onClick={runTrace} className="text-sm bg-blue-600 text-white rounded px-3 py-1">
            Trace
          </button>
        </div>
        {loading && <p className="text-sm text-gray-400">Running the agent pipeline…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {trace && (
          <div className="space-y-0">
            {trace.map((entry, i) => (
              <TraceCard key={entry.agent} entry={entry} index={i} total={trace.length} />
            ))}
          </div>
        )}
        {finalRecommendation && (
          <div className="mt-4 rounded-lg border border-blue-300 bg-blue-50 p-4">
            <p className="text-sm font-semibold text-blue-900">Final recommendation: {String(finalRecommendation.readiness_state)}</p>
            <p className="text-sm text-blue-800 mt-1">{String(finalRecommendation.explanation)}</p>
          </div>
        )}
      </section>

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
        ⚠ Every agent's output is advisory. The Supervisor Agent never fabricates a review — a real
        supervisor decision is required before any instrument's disposition is final.
      </p>
    </div>
  );
}
