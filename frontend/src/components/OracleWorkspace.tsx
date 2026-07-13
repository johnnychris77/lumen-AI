/**
 * LumenAI AI Specialist — Project Oracle: Clinical Intelligence Scientist &
 * Discovery Engine.
 *
 * Frontend route `/oracle`, API prefix `/api/oracle`. Oracle surfaces
 * explainable research hypotheses and discovery signals from governed
 * enterprise data for scientific review -- it never changes a production
 * rule, policy, or model automatically, and it never claims causation.
 * Every output requires human scientific and clinical review before any
 * production use.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Json = Record<string, unknown>;

const TABS = ["Workspace", "Hypotheses", "Trends", "Digital Twin", "Model Observatory", "Knowledge", "Dashboard"] as const;
type Tab = (typeof TABS)[number];

const DISCOVERY_CATEGORIES = [
  "process_pattern", "instrument_reliability_trend", "education_effectiveness", "equipment_utilization",
  "staffing_workload_correlation", "policy_effectiveness", "cross_department_variation",
  "seasonal_temporal_pattern", "emerging_risk_signal", "ai_model_performance_drift",
  "digital_twin_divergence", "knowledge_gap",
];

const VALIDATION_STAGES = [
  "OBSERVATION", "HYPOTHESIS", "EVIDENCE_REVIEW", "SCIENTIFIC_VALIDATION", "PILOT_STUDY", "CLINICAL_REVIEW",
  "GOVERNANCE_APPROVAL", "PRODUCTION_KNOWLEDGE",
];

const ARTICLE_CATEGORIES = [
  "best_practice", "local_standard", "approved_workflow", "clinical_pearl", "lesson_learned", "faq",
  "competency_guidance", "manufacturer_clarification", "teaching_point", "supervisor_experience",
  "vendor_observation", "repair_observation",
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {children}
    </div>
  );
}

function confidenceColor(level: string): string {
  if (level === "strong") return "text-emerald-700";
  if (level === "moderate") return "text-amber-700";
  return "text-slate-500";
}

function CountBadges({ data }: { data: Json | null | undefined }) {
  const entries = data ? Object.entries(data).filter(([, v]) => (v as number) > 0) : [];
  if (!entries.length) return <p className="text-xs text-slate-400">No data yet.</p>;
  return (
    <ul className="space-y-1">
      {entries.map(([key, value]) => (
        <li key={key} className="flex items-center justify-between text-xs">
          <span className="text-slate-600">{key.replace(/_/g, " ")}</span>
          <span className="font-medium text-slate-700">{value as number}</span>
        </li>
      ))}
    </ul>
  );
}

function HypothesisCard({ h, onSelect }: { h: Json; onSelect: (id: number) => void }) {
  return (
    <li className="cursor-pointer rounded border border-slate-100 p-2 hover:bg-slate-50" onClick={() => onSelect(h.id as number)}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-800">{h.hypothesis_code as string} — {h.title as string}</span>
        <span className={`text-xs font-medium ${confidenceColor(h.confidence_level as string)}`}>{h.confidence_level as string}</span>
      </div>
      <p className="mt-1 text-xs text-slate-500">{(h.discovery_category as string)?.replace(/_/g, " ")} · {h.current_stage as string}</p>
      <p className="mt-1 text-xs text-slate-400">owner: {(h.research_owner as string) || "unassigned"}</p>
    </li>
  );
}

function HypothesisList({ items, onSelect }: { items: Json[]; onSelect: (id: number) => void }) {
  if (!items.length) return <p className="text-xs text-slate-400">None.</p>;
  return <ul className="space-y-2">{items.map((h) => <HypothesisCard key={h.id as number} h={h} onSelect={onSelect} />)}</ul>;
}

function StageHistoryView({ history }: { history: Json[] }) {
  if (!history.length) return <p className="text-xs text-slate-400">No stage history yet.</p>;
  return (
    <ol className="space-y-1 border-l border-slate-200 pl-3">
      {history.map((tr, i) => (
        <li key={i} className="text-xs">
          <span className="text-slate-400">{(tr.created_at as string)?.slice(0, 19).replace("T", " ")}</span>{" "}
          <span className="font-medium text-slate-600">{(tr.from_stage as string) || "—"} → {tr.to_stage as string}</span>{" "}
          <span className="text-slate-500">{tr.reason as string}</span>
        </li>
      ))}
    </ol>
  );
}

function EvidenceList({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">No evidence recorded.</p>;
  return (
    <ul className="space-y-1">
      {items.map((e, i) => (
        <li key={i} className="text-xs text-slate-600">
          <span className="font-medium">[{e.evidence_type as string}]</span> {e.summary as string} — {e.submitted_by as string}
        </li>
      ))}
    </ul>
  );
}

export default function OracleWorkspace() {
  const [activeTab, setActiveTab] = useState<Tab>("Workspace");
  const [workspace, setWorkspace] = useState<Json | null>(null);

  const [hypotheses, setHypotheses] = useState<Json[]>([]);
  const [stageFilter, setStageFilter] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Json | null>(null);
  const [stageHistory, setStageHistory] = useState<Json[]>([]);

  const [newCategory, setNewCategory] = useState(DISCOVERY_CATEGORIES[0]);
  const [newTitle, setNewTitle] = useState("");
  const [newObservation, setNewObservation] = useState("");
  const [newStatement, setNewStatement] = useState("");

  const [evidenceText, setEvidenceText] = useState("");
  const [gateNotes, setGateNotes] = useState("");

  const [trends, setTrends] = useState<Json[]>([]);
  const [trendCategory, setTrendCategory] = useState(DISCOVERY_CATEGORIES[0]);
  const [trendMetric, setTrendMetric] = useState("findings");

  const [twinInsights, setTwinInsights] = useState<Json[]>([]);
  const [instrumentIdentity, setInstrumentIdentity] = useState("");

  const [modelObs, setModelObs] = useState<Json[]>([]);

  const [suggestions, setSuggestions] = useState<Json[]>([]);
  const [suggTitle, setSuggTitle] = useState("");
  const [suggBody, setSuggBody] = useState("");
  const [suggRationale, setSuggRationale] = useState("");
  const [suggCategory, setSuggCategory] = useState(ARTICLE_CATEGORIES[4]);

  const [dashboard, setDashboard] = useState<Json | null>(null);
  const [registrySummary, setRegistrySummary] = useState<Json | null>(null);

  function loadWorkspace() {
    api.get("/api/oracle/workspace").then(setWorkspace).catch(() => {});
  }

  function loadHypotheses() {
    const q = stageFilter ? `?current_stage=${stageFilter}` : "";
    api.get(`/api/oracle/hypotheses${q}`).then((r: Json) => setHypotheses((r.hypotheses as Json[]) || [])).catch(() => {});
  }

  function loadDetail(id: number) {
    api.get(`/api/oracle/hypotheses/${id}`).then((r: Json) => {
      setDetail(r.hypothesis as Json);
      setStageHistory((r.stage_history as Json[]) || []);
    }).catch(() => {});
  }

  function selectHypothesis(id: number) {
    setSelectedId(id);
    loadDetail(id);
  }

  function createHypothesis() {
    api.post("/api/oracle/hypotheses", {
      discovery_category: newCategory, title: newTitle, observation_summary: newObservation,
      hypothesis_statement: newStatement,
    }).then(() => {
      loadHypotheses();
      setNewTitle(""); setNewObservation(""); setNewStatement("");
    }).catch(() => {});
  }

  function addEvidence() {
    if (!selectedId || !evidenceText.trim()) return;
    api.post(`/api/oracle/hypotheses/${selectedId}/evidence`, { evidence_summary: evidenceText }).then(() => {
      setEvidenceText("");
      loadDetail(selectedId);
    }).catch(() => {});
  }

  function advanceStage() {
    if (!selectedId) return;
    api.post(`/api/oracle/hypotheses/${selectedId}/advance`, { gate_check_notes: gateNotes }).then(() => {
      setGateNotes("");
      loadDetail(selectedId);
      loadHypotheses();
    }).catch(() => {});
  }

  function closeOut(outcome: string) {
    if (!selectedId) return;
    const reason = window.prompt(`Reason for marking this hypothesis '${outcome}'?`) || "";
    if (!reason.trim()) return;
    api.post(`/api/oracle/hypotheses/${selectedId}/close`, { outcome, reason }).then(() => {
      loadDetail(selectedId);
      loadHypotheses();
    }).catch(() => {});
  }

  function loadTrends() {
    api.get("/api/oracle/trends").then((r: Json) => setTrends((r.trends as Json[]) || [])).catch(() => {});
  }

  function detectTrend() {
    api.post("/api/oracle/trends/detect", { trend_category: trendCategory, metric_name: trendMetric }).then(() => loadTrends()).catch(() => {});
  }

  function promoteTrend(id: number) {
    const title = window.prompt("Hypothesis title for this promoted trend?") || "";
    if (!title.trim()) return;
    api.post(`/api/oracle/trends/${id}/promote`, { title }).then(() => { loadTrends(); loadHypotheses(); }).catch(() => {});
  }

  function loadTwinInsights() {
    api.get("/api/oracle/digital-twin").then((r: Json) => setTwinInsights((r.insights as Json[]) || [])).catch(() => {});
  }

  function recordApolloInsight() {
    api.post("/api/oracle/digital-twin/apollo", {}).then(() => loadTwinInsights()).catch(() => {});
  }

  function recordVulcanInsight() {
    if (!instrumentIdentity.trim()) return;
    api.post("/api/oracle/digital-twin/vulcan", { instrument_identity: instrumentIdentity }).then(() => loadTwinInsights()).catch(() => {});
  }

  function promoteTwin(id: number) {
    const title = window.prompt("Hypothesis title for this promoted insight?") || "";
    if (!title.trim()) return;
    api.post(`/api/oracle/digital-twin/${id}/promote`, { discovery_category: "digital_twin_divergence", title }).then(() => { loadTwinInsights(); loadHypotheses(); }).catch(() => {});
  }

  function loadModelObs() {
    api.get("/api/oracle/model-observations").then((r: Json) => setModelObs((r.observations as Json[]) || [])).catch(() => {});
  }

  function recordModelObservation() {
    api.post("/api/oracle/model-observations", {}).then(() => loadModelObs()).catch(() => {});
  }

  function promoteModelObs(id: number) {
    const title = window.prompt("Hypothesis title for this promoted observation?") || "";
    if (!title.trim()) return;
    api.post(`/api/oracle/model-observations/${id}/promote`, { title }).then(() => { loadModelObs(); loadHypotheses(); }).catch(() => {});
  }

  function loadSuggestions() {
    api.get("/api/oracle/knowledge-suggestions").then((r: Json) => setSuggestions((r.suggestions as Json[]) || [])).catch(() => {});
  }

  function createSuggestion() {
    api.post("/api/oracle/knowledge-suggestions", {
      hypothesis_id: selectedId, suggested_article_title: suggTitle, suggested_article_body: suggBody,
      rationale: suggRationale,
    }).then(() => { loadSuggestions(); setSuggTitle(""); setSuggBody(""); setSuggRationale(""); }).catch(() => {});
  }

  function approveSuggestion(id: number) {
    api.post(`/api/oracle/knowledge-suggestions/${id}/approve`, { article_category: suggCategory }).then(() => loadSuggestions()).catch(() => {});
  }

  function rejectSuggestion(id: number) {
    const reason = window.prompt("Reason for rejecting this suggestion?") || "";
    if (!reason.trim()) return;
    api.post(`/api/oracle/knowledge-suggestions/${id}/reject`, { reason }).then(() => loadSuggestions()).catch(() => {});
  }

  useEffect(() => {
    if (activeTab === "Workspace") loadWorkspace();
    if (activeTab === "Hypotheses") loadHypotheses();
    if (activeTab === "Trends") loadTrends();
    if (activeTab === "Digital Twin") loadTwinInsights();
    if (activeTab === "Model Observatory") loadModelObs();
    if (activeTab === "Knowledge") loadSuggestions();
    if (activeTab === "Dashboard") {
      api.get("/api/oracle/dashboard").then(setDashboard).catch(() => setDashboard(null));
      api.get("/api/oracle/registry/summary").then(setRegistrySummary).catch(() => setRegistrySummary(null));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, stageFilter]);

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Oracle — Clinical Intelligence Scientist &amp; Discovery Engine</h1>
        <p className="text-xs text-slate-400">
          Oracle surfaces explainable research hypotheses and discovery signals for scientific review. It never
          changes a production rule, policy, or model automatically, and it never claims causation -- every output
          describes a potential association or possible contributing factor, requiring human scientific and
          clinical review before any production use.
        </p>
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

      {activeTab === "Workspace" && workspace && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Hypotheses by Stage"><CountBadges data={(workspace.hypotheses as Json)?.by_stage as Json} /></Section>
          <Section title="Trend Observations by Direction"><CountBadges data={(workspace.trend_observations as Json)?.by_direction as Json} /></Section>
          <Section title="Digital Twin Insights by Source"><CountBadges data={(workspace.digital_twin_insights as Json)?.by_source_service as Json} /></Section>
          <Section title="Knowledge Suggestions by Status"><CountBadges data={(workspace.knowledge_suggestions as Json)?.by_status as Json} /></Section>
          <div className="md:col-span-2">
            <Section title="Recent Activity">
              {((workspace.recent_activity as Json[]) || []).length ? (
                <ul className="space-y-1">
                  {(workspace.recent_activity as Json[]).map((a, i) => (
                    <li key={i} className="text-xs text-slate-600">
                      <span className="text-slate-400">{(a.created_at as string)?.slice(0, 19).replace("T", " ")}</span>{" "}
                      <span className="font-medium">[{a.type as string}]</span>{" "}
                      {a.type === "stage_transition" ? `#${a.hypothesis_id} ${a.from_stage || "—"} → ${a.to_stage}` : (a.summary as string) || (a.insight_summary as string) || (a.metric_name as string)}
                    </li>
                  ))}
                </ul>
              ) : <p className="text-xs text-slate-400">No activity yet.</p>}
            </Section>
          </div>
        </div>
      )}

      {activeTab === "Hypotheses" && (
        <div className="space-y-4">
          <Section title="Record a New Observation / Hypothesis">
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              <label className="text-xs text-slate-600">
                Discovery category
                <select className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={newCategory} onChange={(e) => setNewCategory(e.target.value)}>
                  {DISCOVERY_CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
                </select>
              </label>
              <label className="text-xs text-slate-600">
                Title
                <input className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
              </label>
              <label className="text-xs text-slate-600 md:col-span-2">
                Observation summary
                <input className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={newObservation} onChange={(e) => setNewObservation(e.target.value)} />
              </label>
              <label className="text-xs text-slate-600 md:col-span-2">
                Hypothesis statement (potential association only -- never causal)
                <input className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={newStatement} onChange={(e) => setNewStatement(e.target.value)} />
              </label>
            </div>
            <button onClick={createHypothesis} className="mt-2 rounded bg-indigo-600 px-3 py-1 text-sm text-white">Record Hypothesis</button>
          </Section>

          <div className="flex flex-wrap gap-1">
            <button onClick={() => setStageFilter("")} className={`rounded px-2 py-1 text-xs ${stageFilter === "" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}>all</button>
            {VALIDATION_STAGES.map((s) => (
              <button key={s} onClick={() => setStageFilter(s)} className={`rounded px-2 py-1 text-xs ${stageFilter === s ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}>{s}</button>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Section title="All Hypotheses"><HypothesisList items={hypotheses} onSelect={selectHypothesis} /></Section>
            {selectedId && detail && (
              <Section title={`${detail.hypothesis_code as string} Detail`}>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-slate-600"><span className="font-medium">Statement:</span> {detail.hypothesis_statement as string}</p>
                    <p className="text-xs text-slate-400">confidence: {detail.confidence_level as string} · stage: {detail.current_stage as string} · outcome: {(detail.outcome as string) || "pending"}</p>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-600">Validation Pipeline History</h4>
                    <StageHistoryView history={stageHistory} />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-600">Evidence</h4>
                    <EvidenceList items={(detail.evidence as Json[]) || []} />
                    <div className="mt-2 flex gap-2">
                      <input className="flex-1 rounded border border-slate-200 p-1 text-xs" placeholder="Add evidence..." value={evidenceText} onChange={(e) => setEvidenceText(e.target.value)} />
                      <button onClick={addEvidence} className="rounded bg-slate-200 px-2 py-1 text-xs text-slate-700">Add</button>
                    </div>
                  </div>
                  {(detail.current_stage as string) !== "PRODUCTION_KNOWLEDGE" && (detail.current_stage as string) !== "REJECTED" && (
                    <div>
                      <h4 className="text-xs font-semibold text-slate-600">Advance Validation Stage</h4>
                      <div className="flex gap-2">
                        <input className="flex-1 rounded border border-slate-200 p-1 text-xs" placeholder="Gate-check notes (required to promote to production knowledge)..." value={gateNotes} onChange={(e) => setGateNotes(e.target.value)} />
                        <button onClick={advanceStage} className="rounded bg-indigo-600 px-2 py-1 text-xs text-white">Advance</button>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <button onClick={() => closeOut("rejected")} className="rounded bg-red-100 px-2 py-1 text-xs text-red-700">Reject</button>
                        <button onClick={() => closeOut("withdrawn")} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">Withdraw</button>
                        <button onClick={() => closeOut("inconclusive")} className="rounded bg-amber-100 px-2 py-1 text-xs text-amber-700">Mark Inconclusive</button>
                      </div>
                    </div>
                  )}
                </div>
              </Section>
            )}
          </div>
        </div>
      )}

      {activeTab === "Trends" && (
        <div className="space-y-4">
          <Section title="Detect a Tenant-Scoped Emerging Trend">
            <div className="flex flex-wrap items-end gap-2">
              <label className="text-xs text-slate-600">
                Category
                <select className="mt-1 block rounded border border-slate-200 p-1 text-sm" value={trendCategory} onChange={(e) => setTrendCategory(e.target.value)}>
                  {DISCOVERY_CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
                </select>
              </label>
              <label className="text-xs text-slate-600">
                Metric name
                <input className="mt-1 block rounded border border-slate-200 p-1 text-sm" value={trendMetric} onChange={(e) => setTrendMetric(e.target.value)} />
              </label>
              <button onClick={detectTrend} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white">Detect Trend</button>
            </div>
          </Section>
          <Section title="Trend Observations">
            {trends.length ? (
              <ul className="space-y-2">
                {trends.map((t) => (
                  <li key={t.id as number} className="rounded border border-slate-100 p-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-slate-700">{t.metric_name as string} — {t.direction as string}</span>
                      <span className="text-slate-400">confidence: {t.statistical_confidence as string}</span>
                    </div>
                    <p className="mt-1 text-slate-500">{t.notes as string}</p>
                    {!t.promoted_to_hypothesis_id ? (
                      <button onClick={() => promoteTrend(t.id as number)} className="mt-1 rounded bg-slate-200 px-2 py-1 text-xs text-slate-700">Promote to Hypothesis</button>
                    ) : <span className="text-emerald-700">promoted → #{t.promoted_to_hypothesis_id as number}</span>}
                  </li>
                ))}
              </ul>
            ) : <p className="text-xs text-slate-400">No trend observations yet.</p>}
          </Section>
        </div>
      )}

      {activeTab === "Digital Twin" && (
        <div className="space-y-4">
          <Section title="Record Digital Twin Research">
            <div className="flex flex-wrap items-end gap-2">
              <button onClick={recordApolloInsight} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white">Record Apollo Governance-Health Insight</button>
              <input className="rounded border border-slate-200 p-1 text-sm" placeholder="instrument identity (e.g. barcode:ABC123)" value={instrumentIdentity} onChange={(e) => setInstrumentIdentity(e.target.value)} />
              <button onClick={recordVulcanInsight} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white">Record Vulcan Progression Insight</button>
            </div>
          </Section>
          <Section title="Digital Twin Insights">
            {twinInsights.length ? (
              <ul className="space-y-2">
                {twinInsights.map((i) => (
                  <li key={i.id as number} className="rounded border border-slate-100 p-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-slate-700">[{i.source_service as string}] {i.source_reference as string}</span>
                      <span className="text-slate-400">{i.confidence_level as string}</span>
                    </div>
                    <p className="mt-1 text-slate-500">{i.insight_summary as string}</p>
                    {!i.promoted_to_hypothesis_id ? (
                      <button onClick={() => promoteTwin(i.id as number)} className="mt-1 rounded bg-slate-200 px-2 py-1 text-xs text-slate-700">Promote to Hypothesis</button>
                    ) : <span className="text-emerald-700">promoted → #{i.promoted_to_hypothesis_id as number}</span>}
                  </li>
                ))}
              </ul>
            ) : <p className="text-xs text-slate-400">No digital twin insights yet.</p>}
          </Section>
        </div>
      )}

      {activeTab === "Model Observatory" && (
        <div className="space-y-4">
          <Section title="AI Model Observatory">
            <button onClick={recordModelObservation} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white">Record Model Health Snapshot</button>
          </Section>
          <Section title="Model Observations">
            {modelObs.length ? (
              <ul className="space-y-2">
                {modelObs.map((m) => (
                  <li key={m.id as number} className="rounded border border-slate-100 p-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-slate-700">{m.observation_type as string}</span>
                      <span className={m.reviewed ? "text-slate-400" : "text-amber-700"}>{m.reviewed ? "reviewed" : "needs review"}</span>
                    </div>
                    <p className="mt-1 text-slate-500">{m.summary as string}</p>
                    {!m.promoted_to_hypothesis_id && (
                      <button onClick={() => promoteModelObs(m.id as number)} className="mt-1 rounded bg-slate-200 px-2 py-1 text-xs text-slate-700">Promote to Hypothesis</button>
                    )}
                  </li>
                ))}
              </ul>
            ) : <p className="text-xs text-slate-400">No model observations yet.</p>}
          </Section>
        </div>
      )}

      {activeTab === "Knowledge" && (
        <div className="space-y-4">
          <Section title="Suggest a Knowledge Article (from selected hypothesis)">
            <p className="text-xs text-slate-400 mb-2">Selected hypothesis: {selectedId ? `#${selectedId}` : "none (select one in the Hypotheses tab first)"}</p>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              <label className="text-xs text-slate-600 md:col-span-2">
                Title
                <input className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={suggTitle} onChange={(e) => setSuggTitle(e.target.value)} />
              </label>
              <label className="text-xs text-slate-600 md:col-span-2">
                Body
                <textarea className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={suggBody} onChange={(e) => setSuggBody(e.target.value)} />
              </label>
              <label className="text-xs text-slate-600 md:col-span-2">
                Rationale
                <input className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={suggRationale} onChange={(e) => setSuggRationale(e.target.value)} />
              </label>
              <label className="text-xs text-slate-600">
                Article category (used on approval)
                <select className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={suggCategory} onChange={(e) => setSuggCategory(e.target.value)}>
                  {ARTICLE_CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
                </select>
              </label>
            </div>
            <button onClick={createSuggestion} className="mt-2 rounded bg-indigo-600 px-3 py-1 text-sm text-white">Submit Suggestion</button>
          </Section>
          <Section title="Knowledge Suggestions (governance-gated)">
            {suggestions.length ? (
              <ul className="space-y-2">
                {suggestions.map((s) => (
                  <li key={s.id as number} className="rounded border border-slate-100 p-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-slate-700">{s.suggested_article_title as string}</span>
                      <span className="text-slate-400">{s.status as string}</span>
                    </div>
                    <p className="mt-1 text-slate-500">{s.rationale as string}</p>
                    {s.status === "pending" && (
                      <div className="mt-1 flex gap-2">
                        <button onClick={() => approveSuggestion(s.id as number)} className="rounded bg-emerald-100 px-2 py-1 text-xs text-emerald-700">Approve</button>
                        <button onClick={() => rejectSuggestion(s.id as number)} className="rounded bg-red-100 px-2 py-1 text-xs text-red-700">Reject</button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            ) : <p className="text-xs text-slate-400">No knowledge suggestions yet.</p>}
          </Section>
        </div>
      )}

      {activeTab === "Dashboard" && dashboard && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Validation Pipeline Funnel"><CountBadges data={dashboard.pipeline_funnel as Json} /></Section>
          <Section title="Category Distribution"><CountBadges data={dashboard.category_distribution as Json} /></Section>
          <Section title="Portfolio Summary">
            <ul className="space-y-1 text-xs">
              <li>Total hypotheses: <span className="font-medium">{dashboard.total_hypotheses as number}</span></li>
              <li>Promoted to production knowledge: <span className="font-medium">{dashboard.promoted_to_production_count as number}</span></li>
              <li>Avg. time to validation: <span className="font-medium">{dashboard.avg_time_to_validation_days != null ? `${dashboard.avg_time_to_validation_days} days` : "n/a"}</span></li>
            </ul>
          </Section>
          <Section title="Top Research Owners">
            {((dashboard.top_research_owners as Json[]) || []).length ? (
              <ul className="space-y-1 text-xs">
                {(dashboard.top_research_owners as Json[]).map((o, i) => (
                  <li key={i} className="flex justify-between"><span>{o.research_owner as string}</span><span className="font-medium">{o.hypothesis_count as number}</span></li>
                ))}
              </ul>
            ) : <p className="text-xs text-slate-400">No research owners recorded yet.</p>}
          </Section>
          {registrySummary && (
            <div className="md:col-span-2">
              <Section title="Research Registry — By Outcome"><CountBadges data={registrySummary.by_outcome as Json} /></Section>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
