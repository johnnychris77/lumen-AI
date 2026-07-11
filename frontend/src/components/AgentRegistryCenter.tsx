/**
 * v5.4 — LumenAI Network: Project Nova — Agent Registry Center.
 *
 * Frontend route `/agents`, API prefix `/api/nova`. Distinct from the
 * pre-existing `/agent-trace` (Phase 22 Explainable Agent Trace, unchanged) —
 * this page is Nova's governed platform layer: registry, communication
 * bus, task orchestration, memory, human-agent collaboration,
 * marketplace, and observability.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const TABS = [
  "Registry", "Communication Bus", "Task Orchestration", "Human-Agent Collaboration",
  "Marketplace", "Observability",
] as const;
type Tab = (typeof TABS)[number];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {children}
    </div>
  );
}

function Json({ data }: { data: unknown }) {
  return <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(data, null, 2)}</pre>;
}

export default function AgentRegistryCenter() {
  const [activeTab, setActiveTab] = useState<Tab>("Registry");

  const [registry, setRegistry] = useState<Record<string, unknown> | null>(null);
  const [messages, setMessages] = useState<Record<string, unknown>[] | null>(null);
  const [taskRuns, setTaskRuns] = useState<Record<string, unknown>[] | null>(null);
  const [collabRequests, setCollabRequests] = useState<Record<string, unknown>[] | null>(null);
  const [marketplace, setMarketplace] = useState<Record<string, unknown> | null>(null);
  const [observability, setObservability] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (activeTab === "Registry") {
      api.post("/api/nova/agents/seed-core", {}).catch(() => {});
      api.get("/api/nova/agents").then(setRegistry).catch(() => {});
    }
    if (activeTab === "Communication Bus") {
      api.get("/api/nova/messages").then((r: Record<string, unknown>) => setMessages(r.messages as Record<string, unknown>[])).catch(() => {});
    }
    if (activeTab === "Task Orchestration") {
      api.get("/api/nova/task-runs").then((r: Record<string, unknown>) => setTaskRuns(r.task_runs as Record<string, unknown>[])).catch(() => {});
    }
    if (activeTab === "Human-Agent Collaboration") {
      api.get("/api/nova/collaboration-requests").then((r: Record<string, unknown>) => setCollabRequests(r.requests as Record<string, unknown>[])).catch(() => {});
    }
    if (activeTab === "Marketplace") api.get("/api/nova/marketplace/summary").then(setMarketplace).catch(() => {});
    if (activeTab === "Observability") api.get("/api/nova/observability/summary").then(setObservability).catch(() => {});
  }, [activeTab]);

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Agent Registry</h1>
      <p className="text-xs text-slate-400">
        LumenAI's specialized software agents — each wraps an existing deterministic service, never an
        autonomous large language model. Every agent output is advisory, requires human review, and no agent
        takes an irreversible clinical or operational action without authorization and governance.
      </p>

      <div className="flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`rounded px-3 py-1 text-sm ${activeTab === t ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {activeTab === "Registry" && (
        <Section title="Agent Registry — Nova Core Agents + Phase 22 Pipeline Agents">
          {registry && <Json data={registry} />}
        </Section>
      )}

      {activeTab === "Communication Bus" && (
        <Section title="Agent Communication Bus — logged inter-agent messages">
          {messages?.map((m) => (
            <div key={String(m.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              <span className="font-medium">{String(m.source_agent_key)}</span> → {String(m.target_agent_key)}
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Task Orchestration" && (
        <Section title="Agent Task Runs">
          {taskRuns?.map((t) => (
            <div key={String(t.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              <span className="font-medium">{String(t.pipeline_name)}</span> — {String(t.status)} (step{" "}
              {String(t.current_step_index)})
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Human-Agent Collaboration" && (
        <Section title="Collaboration Requests — assign, approve, reject, explain, escalate">
          {collabRequests?.map((r) => (
            <div key={String(r.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              <span className="font-medium">{String(r.agent_key)}</span> — {String(r.request_type)} (
              {String(r.status)})
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Marketplace" && (
        <Section title="Agent Marketplace">{marketplace && <Json data={marketplace} />}</Section>
      )}

      {activeTab === "Observability" && (
        <Section title="Agent Observability">{observability && <Json data={observability} />}</Section>
      )}
    </div>
  );
}
