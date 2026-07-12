/**
 * LumenAI AI Specialist — Project Maestro: Operational Orchestration &
 * Decision Intelligence.
 *
 * Frontend route `/maestro`, API prefix `/api/maestro`. Maestro is a pure
 * read-and-synthesize leadership layer over every other specialist -- it
 * never replaces human leadership. Every recommendation is explainable,
 * evidence-based, auditable, role-aware, and subject to human approval;
 * "What should I do first today, and why?"
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Json = Record<string, unknown>;

const TABS = [
  "Leadership Workspace", "Priorities", "Recommendations", "Strategy Timeline", "Decision Journal", "Daily Briefs",
] as const;
type Tab = (typeof TABS)[number];

const BRIEF_TYPES = ["morning_brief", "afternoon_update", "end_of_day_summary", "weekend_readiness", "shift_handoff"];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {children}
    </div>
  );
}

function JsonView({ data }: { data: unknown }) {
  return <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(data, null, 2)}</pre>;
}

function PriorityList({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">No active priorities.</p>;
  return (
    <ol className="space-y-2">
      {items.map((item) => (
        <li key={item.id as number} className="rounded border border-slate-100 p-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-800">#{item.rank as number} — {item.subject as string}</span>
            <span className="text-xs text-slate-400">{item.category as string}</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">{item.rationale as string}</p>
          <p className="mt-1 text-xs text-slate-400">score {item.priority_score as number} · via {item.source_specialist as string}</p>
        </li>
      ))}
    </ol>
  );
}

function RecommendationList({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">No pending recommendations.</p>;
  return (
    <ol className="space-y-2">
      {items.map((item) => (
        <li key={item.id as number} className="rounded border border-slate-100 p-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-800">{item.subject as string}</span>
            <span className="text-xs text-slate-400">{item.status as string} · {item.timeline_horizon as string}</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">{item.rationale as string}</p>
          <p className="mt-1 text-xs text-slate-400">confidence: {item.confidence as string} · type: {item.recommendation_type as string}</p>
        </li>
      ))}
    </ol>
  );
}

export default function MaestroLeadershipWorkspace() {
  const [activeTab, setActiveTab] = useState<Tab>("Leadership Workspace");

  const [workspace, setWorkspace] = useState<Json | null>(null);
  const [priorities, setPriorities] = useState<Json[]>([]);
  const [recommendations, setRecommendations] = useState<Json[]>([]);
  const [timeline, setTimeline] = useState<Json | null>(null);
  const [journal, setJournal] = useState<Json[]>([]);
  const [briefType, setBriefType] = useState(BRIEF_TYPES[0]);
  const [brief, setBrief] = useState<Json | null>(null);

  function loadWorkspace() {
    api.get("/api/maestro/workspace").then(setWorkspace).catch(() => {});
  }

  useEffect(() => {
    if (activeTab === "Leadership Workspace") loadWorkspace();
    if (activeTab === "Priorities") api.get("/api/maestro/priorities").then((r: Json) => setPriorities((r.priorities as Json[]) || [])).catch(() => {});
    if (activeTab === "Recommendations") api.get("/api/maestro/recommendations").then((r: Json) => setRecommendations((r.recommendations as Json[]) || [])).catch(() => {});
    if (activeTab === "Strategy Timeline") api.get("/api/maestro/timeline").then(setTimeline).catch(() => {});
    if (activeTab === "Decision Journal") api.get("/api/maestro/decisions").then((r: Json) => setJournal((r.journal as Json[]) || [])).catch(() => {});
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === "Daily Briefs") {
      api.get(`/api/maestro/briefs/${briefType}/latest`).then(setBrief).catch(() => setBrief(null));
    }
  }, [activeTab, briefType]);

  function runOrchestration() {
    api.post("/api/maestro/run", {}).then(loadWorkspace).catch(() => {});
  }

  function generateBrief() {
    api.post(`/api/maestro/briefs/${briefType}/generate`, {}).then(setBrief).catch(() => {});
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Leadership Workspace</h1>
          <p className="text-xs text-slate-400">
            Maestro continuously coordinates every LumenAI specialist to recommend operational priorities for
            SPD leaders. It never replaces human leadership -- every recommendation is explainable,
            evidence-based, auditable, role-aware, and subject to human approval.
          </p>
        </div>
        <button onClick={runOrchestration} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white">
          Run Orchestration
        </button>
      </div>

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

      {activeTab === "Leadership Workspace" && workspace && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Top Priorities">
            <PriorityList items={(workspace.top_priorities as Json[]) || []} />
          </Section>
          <Section title="Operational Health">
            <JsonView data={workspace.operational_health} />
          </Section>
          <Section title="Open Risks">
            <JsonView data={workspace.open_risks} />
          </Section>
          <Section title="Today's Recommendations">
            <RecommendationList items={(workspace.todays_recommendations as Json[]) || []} />
          </Section>
          <Section title="Pending Executive Decisions">
            <RecommendationList items={(workspace.pending_executive_decisions as Json[]) || []} />
          </Section>
          <Section title="Shift Readiness">
            <JsonView data={workspace.shift_readiness} />
          </Section>
          <Section title="Enterprise Status">
            <JsonView data={workspace.enterprise_status} />
          </Section>
        </div>
      )}

      {activeTab === "Priorities" && (
        <Section title="Ranked Priorities">
          <PriorityList items={priorities} />
        </Section>
      )}

      {activeTab === "Recommendations" && (
        <Section title="Leadership Recommendations">
          <RecommendationList items={recommendations} />
        </Section>
      )}

      {activeTab === "Strategy Timeline" && timeline && (
        <Section title="Strategy Timeline (by horizon)">
          <JsonView data={timeline.horizons} />
        </Section>
      )}

      {activeTab === "Decision Journal" && (
        <Section title="Decision Journal">
          <JsonView data={journal} />
        </Section>
      )}

      {activeTab === "Daily Briefs" && (
        <Section title="Daily Operational Brief">
          <div className="mb-3 flex flex-wrap gap-1">
            {BRIEF_TYPES.map((bt) => (
              <button
                key={bt}
                onClick={() => setBriefType(bt)}
                className={`rounded px-2 py-1 text-xs ${briefType === bt ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}
              >
                {bt}
              </button>
            ))}
            <button onClick={generateBrief} className="rounded bg-emerald-600 px-2 py-1 text-xs text-white">
              Generate
            </button>
          </div>
          {brief ? (
            <div>
              <p className="mb-2 text-sm text-slate-700">{brief.narrative as string}</p>
              <JsonView data={brief.content} />
            </div>
          ) : (
            <p className="text-xs text-slate-400">No brief generated yet.</p>
          )}
        </Section>
      )}
    </div>
  );
}
