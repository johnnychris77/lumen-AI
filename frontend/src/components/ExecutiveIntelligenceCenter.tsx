/**
 * v4.6 — LumenAI OS: Project Vanguard — Healthcare Executive
 * Intelligence & Strategic Decision Platform.
 *
 * Frontend route `/executive`, API prefix `/api/vanguard` — deliberately
 * distinct from the pre-existing `/api/executive` mock-KPI endpoint (see
 * `app/models/vanguard_intelligence.py` for the naming-disambiguation
 * note). Every figure rendered here traces back to a real computation.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const TABS = ["Executive Intelligence", "Scorecards", "Financial", "Operational", "Benchmarking", "Governance", "AI Advisor"] as const;
type Tab = (typeof TABS)[number];

const SCORECARD_AUDIENCES = ["ceo", "coo", "cno", "cmo", "vp_surgical_services", "quality", "supply_chain", "spd_director"];
const BENCHMARK_TYPES = ["facilities", "markets", "service_lines", "inspection_programs", "instrument_health", "knowledge_maturity"];

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

export default function ExecutiveIntelligenceCenter() {
  const [activeTab, setActiveTab] = useState<Tab>("Executive Intelligence");
  const [center, setCenter] = useState<Record<string, unknown> | null>(null);
  const [audience, setAudience] = useState("ceo");
  const [scorecard, setScorecard] = useState<Record<string, unknown> | null>(null);
  const [financial, setFinancial] = useState<Record<string, unknown> | null>(null);
  const [operational, setOperational] = useState<Record<string, unknown> | null>(null);
  const [benchmarkType, setBenchmarkType] = useState("facilities");
  const [benchmark, setBenchmark] = useState<Record<string, unknown> | null>(null);
  const [governance, setGovernance] = useState<Record<string, unknown> | null>(null);
  const [advisorQuery, setAdvisorQuery] = useState("");
  const [advisorAnswer, setAdvisorAnswer] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/api/vanguard/executive-intelligence").then(setCenter).catch(() => {});
  }, []);

  useEffect(() => {
    if (activeTab === "Scorecards") api.get(`/api/vanguard/scorecards/${audience}`).then(setScorecard).catch(() => {});
    if (activeTab === "Financial") api.get("/api/vanguard/financial").then(setFinancial).catch(() => {});
    if (activeTab === "Operational") api.get("/api/vanguard/operational").then(setOperational).catch(() => {});
    if (activeTab === "Benchmarking") {
      api.get(`/api/vanguard/benchmarking/${benchmarkType}`).then(setBenchmark).catch((e) => setError(String(e)));
    }
    if (activeTab === "Governance") api.get("/api/vanguard/governance").then(setGovernance).catch(() => {});
  }, [activeTab, audience, benchmarkType]);

  async function askAdvisor() {
    if (!advisorQuery.trim()) return;
    const res = await api.post<Record<string, unknown>>("/api/catalyst/chat", { message: advisorQuery, persona: "executive" });
    setAdvisorAnswer(res);
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Executive Intelligence Center</h1>

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

      {activeTab === "Executive Intelligence" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          {center && (
            <>
              <Section title="Enterprise Readiness"><Json data={center.enterprise_readiness} /></Section>
              <Section title="Surgical Readiness"><Json data={center.surgical_readiness} /></Section>
              <Section title="SPD Quality"><Json data={center.spd_quality} /></Section>
              <Section title="Financial Impact"><Json data={center.financial_impact} /></Section>
              <Section title="Capacity"><Json data={center.capacity} /></Section>
              <Section title="Enterprise Risk"><Json data={center.enterprise_risk} /></Section>
              <Section title="AI Health"><Json data={center.ai_health} /></Section>
              <Section title="Knowledge Growth"><Json data={center.knowledge_growth} /></Section>
            </>
          )}
        </div>
      )}

      {activeTab === "Scorecards" && (
        <Section title="Executive Scorecard">
          <select className="mb-3 rounded border border-slate-300 p-1 text-sm" value={audience} onChange={(e) => setAudience(e.target.value)}>
            {SCORECARD_AUDIENCES.map((a) => <option key={a} value={a}>{a.replace(/_/g, " ").toUpperCase()}</option>)}
          </select>
          {scorecard && <Json data={scorecard.kpis} />}
        </Section>
      )}

      {activeTab === "Financial" && <Section title="Financial Intelligence">{financial && <Json data={financial} />}</Section>}

      {activeTab === "Operational" && <Section title="Operational Intelligence">{operational && <Json data={operational} />}</Section>}

      {activeTab === "Benchmarking" && (
        <Section title="Enterprise Benchmarking">
          <select className="mb-3 rounded border border-slate-300 p-1 text-sm" value={benchmarkType} onChange={(e) => setBenchmarkType(e.target.value)}>
            {BENCHMARK_TYPES.map((b) => <option key={b} value={b}>{b.replace(/_/g, " ")}</option>)}
          </select>
          {error && <p className="text-xs text-amber-600">{error}</p>}
          {benchmark && <Json data={benchmark.results} />}
        </Section>
      )}

      {activeTab === "Governance" && <Section title="Governance Dashboard">{governance && <Json data={governance} />}</Section>}

      {activeTab === "AI Advisor" && (
        <Section title="Executive AI Advisor">
          <div className="mb-3 flex gap-2">
            <input
              className="flex-1 rounded border border-slate-300 p-2 text-sm"
              placeholder='e.g. "What are our top enterprise risks?"'
              value={advisorQuery}
              onChange={(e) => setAdvisorQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && askAdvisor()}
            />
            <button className="rounded bg-indigo-600 px-4 py-2 text-sm text-white" onClick={askAdvisor}>Ask</button>
          </div>
          {advisorAnswer && (
            <div className="space-y-2 text-sm">
              <p className="font-medium">{String(advisorAnswer.answer)}</p>
              <Json data={advisorAnswer.data} />
            </div>
          )}
          <p className="mt-2 text-xs text-slate-400">
            Suggested: "What are our top enterprise risks?", "Which investment will reduce repair costs?",
            "Which facilities require attention?", "What quality trends should I discuss at tomorrow's executive meeting?"
          </p>
        </Section>
      )}
    </div>
  );
}
