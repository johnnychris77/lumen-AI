/**
 * v4.9 — LumenAI OS: Project Phoenix — Self-Improving Healthcare
 * Intelligence Platform.
 *
 * Frontend route `/phoenix`, API prefix `/api/phoenix`. Phoenix never
 * modifies production automatically — every recommendation and
 * innovation idea requires an explicit human decision at every stage.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const TABS = [
  "Learning Engine", "Recommendations", "AI Observatory", "Workflow Optimization",
  "Knowledge Evolution", "Competency Intelligence", "Innovation Pipeline", "Maturity Index",
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

export default function PhoenixIntelligenceCenter() {
  const [activeTab, setActiveTab] = useState<Tab>("Learning Engine");

  const [learningEngine, setLearningEngine] = useState<Record<string, unknown> | null>(null);
  const [recommendations, setRecommendations] = useState<Record<string, unknown>[] | null>(null);
  const [observatory, setObservatory] = useState<Record<string, unknown> | null>(null);
  const [workflowOpt, setWorkflowOpt] = useState<Record<string, unknown> | null>(null);
  const [knowledgeEvolution, setKnowledgeEvolution] = useState<Record<string, unknown> | null>(null);
  const [competencyResult, setCompetencyResult] = useState<Record<string, unknown> | null>(null);
  const [ideas, setIdeas] = useState<Record<string, unknown>[] | null>(null);
  const [ideaForm, setIdeaForm] = useState({ title: "", description: "", clinical_impact: "medium", technical_complexity: "medium", priority: "medium" });
  const [maturityHistory, setMaturityHistory] = useState<Record<string, unknown>[] | null>(null);

  useEffect(() => {
    api.get("/api/phoenix/learning-engine/summary").then(setLearningEngine).catch(() => {});
  }, []);

  useEffect(() => {
    if (activeTab === "Recommendations") api.get("/api/phoenix/recommendations").then((r: Record<string, unknown>) => setRecommendations(r.recommendations as Record<string, unknown>[])).catch(() => {});
    if (activeTab === "AI Observatory") api.get("/api/phoenix/observatory/summary").then(setObservatory).catch(() => {});
    if (activeTab === "Workflow Optimization") api.get("/api/phoenix/workflow-optimization/summary").then(setWorkflowOpt).catch(() => {});
    if (activeTab === "Knowledge Evolution") api.get("/api/phoenix/knowledge-evolution/summary").then(setKnowledgeEvolution).catch(() => {});
    if (activeTab === "Innovation Pipeline") api.get("/api/phoenix/innovation/ideas").then((r: Record<string, unknown>) => setIdeas(r.ideas as Record<string, unknown>[])).catch(() => {});
    if (activeTab === "Maturity Index") api.get("/api/phoenix/maturity/history").then((r: Record<string, unknown>) => setMaturityHistory(r.history as Record<string, unknown>[])).catch(() => {});
  }, [activeTab]);

  async function generateRecommendations() {
    const res = await api.post<Record<string, unknown>>("/api/phoenix/recommendations/generate", {});
    setRecommendations(res.recommendations as Record<string, unknown>[]);
  }

  async function runCompetencyIntelligence() {
    const res = await api.post<Record<string, unknown>>("/api/phoenix/competency-intelligence/run", {});
    setCompetencyResult(res);
  }

  async function createIdea() {
    if (!ideaForm.title.trim()) return;
    await api.post("/api/phoenix/innovation/ideas", ideaForm);
    setIdeaForm({ title: "", description: "", clinical_impact: "medium", technical_complexity: "medium", priority: "medium" });
    api.get("/api/phoenix/innovation/ideas").then((r: Record<string, unknown>) => setIdeas(r.ideas as Record<string, unknown>[])).catch(() => {});
  }

  async function computeMaturity() {
    await api.post("/api/phoenix/maturity/compute", {});
    api.get("/api/phoenix/maturity/history").then((r: Record<string, unknown>) => setMaturityHistory(r.history as Record<string, unknown>[])).catch(() => {});
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Phoenix — Self-Improving Intelligence</h1>
      <p className="text-xs text-slate-400">
        Continuously analyzes platform performance, knowledge quality, AI output review outcomes, workflow efficiency, and
        operational outcomes. Phoenix never modifies production automatically — every recommendation requires
        human governance and approval at every stage.
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

      {activeTab === "Learning Engine" && (
        <Section title="Phoenix Learning Engine">{learningEngine && <Json data={learningEngine} />}</Section>
      )}

      {activeTab === "Recommendations" && (
        <Section title="Improvement Recommendations">
          <button className="mb-3 rounded bg-indigo-600 px-4 py-1 text-sm text-white" onClick={generateRecommendations}>
            Generate Recommendations
          </button>
          {recommendations?.map((r) => (
            <div key={String(r.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              <span className="font-medium">{String(r.title)}</span> — {String(r.recommendation_type)} (confidence {String(r.confidence)}, status {String(r.status)})
            </div>
          ))}
        </Section>
      )}

      {activeTab === "AI Observatory" && (
        <Section title="AI Performance Observatory">{observatory && <Json data={observatory} />}</Section>
      )}

      {activeTab === "Workflow Optimization" && (
        <Section title="Workflow Optimization Engine">{workflowOpt && <Json data={workflowOpt} />}</Section>
      )}

      {activeTab === "Knowledge Evolution" && (
        <Section title="Knowledge Evolution Center">{knowledgeEvolution && <Json data={knowledgeEvolution} />}</Section>
      )}

      {activeTab === "Competency Intelligence" && (
        <Section title="Competency Intelligence">
          <button className="mb-3 rounded bg-indigo-600 px-4 py-1 text-sm text-white" onClick={runCompetencyIntelligence}>
            Run Detectors
          </button>
          {competencyResult && <Json data={competencyResult} />}
        </Section>
      )}

      {activeTab === "Innovation Pipeline" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Innovation Backlog">
            {ideas?.map((idea) => (
              <div key={String(idea.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
                <span className="font-medium">{String(idea.title)}</span> — {String(idea.priority)} priority ({String(idea.approval_status)})
              </div>
            ))}
          </Section>
          <Section title="Submit an Idea">
            <div className="space-y-2 text-sm">
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Title" value={ideaForm.title}
                onChange={(e) => setIdeaForm({ ...ideaForm, title: e.target.value })} />
              <textarea className="w-full rounded border border-slate-300 p-2" placeholder="Description" value={ideaForm.description}
                onChange={(e) => setIdeaForm({ ...ideaForm, description: e.target.value })} />
              <select className="w-full rounded border border-slate-300 p-2" value={ideaForm.priority}
                onChange={(e) => setIdeaForm({ ...ideaForm, priority: e.target.value })}>
                <option value="low">Low priority</option><option value="medium">Medium priority</option>
                <option value="high">High priority</option><option value="critical">Critical priority</option>
              </select>
              <button className="rounded bg-indigo-600 px-4 py-2 text-white" onClick={createIdea}>Submit Idea</button>
            </div>
          </Section>
        </div>
      )}

      {activeTab === "Maturity Index" && (
        <Section title="Platform Maturity Index">
          <button className="mb-3 rounded bg-indigo-600 px-4 py-1 text-sm text-white" onClick={computeMaturity}>
            Compute New Snapshot
          </button>
          {maturityHistory && <Json data={maturityHistory} />}
        </Section>
      )}
    </div>
  );
}
