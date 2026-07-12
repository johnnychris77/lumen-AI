/**
 * LumenAI AI Leadership Platform — Project Council: Multi-Agent
 * Leadership Teams & Governed Consensus Intelligence.
 *
 * Frontend route `/council`, API prefix `/api/council`. Council convenes
 * LumenAI's specialist agents as a structured leadership team -- it
 * synthesizes evidence, surfaces agreement and disagreement, and
 * evaluates tradeoffs, but never replaces leadership. No recommendation
 * may hide specialist disagreement, and a simple majority never
 * overrides unresolved safety dissent.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Json = Record<string, unknown>;

const TABS = ["Workspace", "Cases", "Teams", "Performance", "Notifications"] as const;
type Tab = (typeof TABS)[number];

const CASE_TYPES = [
  "high_risk_inspection", "recurring_contamination", "recurring_instrument_failure", "repair_recurrence",
  "process_variation", "education_need", "capa_escalation", "workflow_bottleneck", "enterprise_trend",
  "model_performance_issue", "evidence_conflict", "innovation_proposal",
];

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

function CaseList({ cases, onSelect }: { cases: Json[]; onSelect: (id: number) => void }) {
  if (!cases.length) return <p className="text-xs text-slate-400">No cases.</p>;
  return (
    <ul className="space-y-2">
      {cases.map((c) => (
        <li key={c.id as number} className="cursor-pointer rounded border border-slate-100 p-2 hover:bg-slate-50" onClick={() => onSelect(c.id as number)}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-800">Case #{c.id as number} — {c.case_type as string}</span>
            <span className="text-xs text-slate-400">{c.consensus_status as string || "pending"}</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">{c.recommended_action as string}</p>
          <p className="mt-1 text-xs text-slate-400">team: {c.team_key as string} · status: {c.status as string}</p>
        </li>
      ))}
    </ul>
  );
}

export default function CouncilWorkspace() {
  const [activeTab, setActiveTab] = useState<Tab>("Workspace");

  const [workspace, setWorkspace] = useState<Json | null>(null);
  const [cases, setCases] = useState<Json[]>([]);
  const [teams, setTeams] = useState<Json[]>([]);
  const [performance, setPerformance] = useState<Json | null>(null);
  const [notifications, setNotifications] = useState<Json[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);
  const [caseDetail, setCaseDetail] = useState<Json | null>(null);

  const [newCaseType, setNewCaseType] = useState(CASE_TYPES[0]);
  const [newSourceEvent, setNewSourceEvent] = useState("");
  const [newInstrumentIdentity, setNewInstrumentIdentity] = useState("");

  function loadWorkspace() {
    api.get("/api/council/workspace").then(setWorkspace).catch(() => {});
  }

  useEffect(() => {
    if (activeTab === "Workspace") loadWorkspace();
    if (activeTab === "Cases") api.get("/api/council/cases").then((r: Json) => setCases((r.cases as Json[]) || [])).catch(() => {});
    if (activeTab === "Teams") api.get("/api/council/teams").then((r: Json) => setTeams((r.teams as Json[]) || [])).catch(() => {});
    if (activeTab === "Performance") api.get("/api/council/performance").then(setPerformance).catch(() => {});
    if (activeTab === "Notifications") api.get("/api/council/notifications").then((r: Json) => setNotifications((r.notifications as Json[]) || [])).catch(() => {});
  }, [activeTab]);

  function openAndConvene() {
    api.post("/api/council/cases", {
      case_type: newCaseType,
      source_event: newSourceEvent,
      instrument_ids: newInstrumentIdentity ? [newInstrumentIdentity] : [],
    }).then((created: Json) => {
      const id = created.id as number;
      return api.post(`/api/council/cases/${id}/convene`, {}).then(() => id);
    }).then((id: number) => {
      setSelectedCaseId(id);
      loadCaseDetail(id);
      setActiveTab("Cases");
      api.get("/api/council/cases").then((r: Json) => setCases((r.cases as Json[]) || [])).catch(() => {});
    }).catch(() => {});
  }

  function loadCaseDetail(id: number) {
    api.get(`/api/council/cases/${id}`).then(setCaseDetail).catch(() => {});
  }

  function selectCase(id: number) {
    setSelectedCaseId(id);
    loadCaseDetail(id);
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Council — Multi-Agent Leadership Teams</h1>
        <p className="text-xs text-slate-400">
          Council convenes LumenAI's specialist agents as a structured leadership team to synthesize evidence,
          surface agreement and disagreement, and evaluate tradeoffs. Council does not replace leadership -- no
          recommendation may hide specialist disagreement, and a simple majority never overrides unresolved
          safety dissent.
        </p>
      </div>

      <Section title="Open a new Council Case">
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs text-slate-600">
            Case type
            <select className="mt-1 block rounded border border-slate-200 p-1 text-sm" value={newCaseType} onChange={(e) => setNewCaseType(e.target.value)}>
              {CASE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label className="text-xs text-slate-600">
            Source event
            <input className="mt-1 block rounded border border-slate-200 p-1 text-sm" value={newSourceEvent} onChange={(e) => setNewSourceEvent(e.target.value)} />
          </label>
          <label className="text-xs text-slate-600">
            Instrument identity
            <input className="mt-1 block rounded border border-slate-200 p-1 text-sm" value={newInstrumentIdentity} onChange={(e) => setNewInstrumentIdentity(e.target.value)} />
          </label>
          <button onClick={openAndConvene} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white">
            Open &amp; Convene
          </button>
        </div>
      </Section>

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
          <Section title="Urgent Cases">
            <CaseList cases={(workspace.urgent_cases as Json[]) || []} onSelect={selectCase} />
          </Section>
          <Section title="Safety Dissent">
            <CaseList cases={(workspace.safety_dissent_cases as Json[]) || []} onSelect={selectCase} />
          </Section>
          <Section title="Split Decisions">
            <CaseList cases={(workspace.split_decision_cases as Json[]) || []} onSelect={selectCase} />
          </Section>
          <Section title="Awaiting Evidence">
            <CaseList cases={(workspace.awaiting_evidence as Json[]) || []} onSelect={selectCase} />
          </Section>
          <Section title="Awaiting Human Decision">
            <CaseList cases={(workspace.awaiting_decision as Json[]) || []} onSelect={selectCase} />
          </Section>
          <Section title="Recently Resolved">
            <CaseList cases={(workspace.recently_resolved as Json[]) || []} onSelect={selectCase} />
          </Section>
          <Section title="Outcome Effectiveness">
            <JsonView data={workspace.outcome_effectiveness} />
          </Section>
          <Section title="Specialist Participation">
            <JsonView data={workspace.specialist_participation} />
          </Section>
          <Section title="Recurring Decision Themes">
            <JsonView data={workspace.recurring_decision_themes} />
          </Section>
        </div>
      )}

      {activeTab === "Cases" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="All Cases">
            <CaseList cases={cases} onSelect={selectCase} />
          </Section>
          {selectedCaseId && caseDetail && (
            <Section title={`Case #${selectedCaseId} Detail`}>
              <div className="space-y-3">
                <div>
                  <h4 className="text-xs font-semibold text-slate-600">1. Issue Summary</h4>
                  <JsonView data={caseDetail.case} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-600">3. Specialist Assessments</h4>
                  <JsonView data={caseDetail.assessments} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-600">4. Agreement Map</h4>
                  <JsonView data={caseDetail.agreement_map} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-600">5. Dissent</h4>
                  <JsonView data={caseDetail.dissent} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-600">6. Decision Options</h4>
                  <JsonView data={caseDetail.decision_options} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-600">9. Final Human Decision(s)</h4>
                  <JsonView data={caseDetail.human_decisions} />
                </div>
              </div>
            </Section>
          )}
        </div>
      )}

      {activeTab === "Teams" && (
        <Section title="Leadership Team Registry">
          <JsonView data={teams} />
        </Section>
      )}

      {activeTab === "Performance" && performance && (
        <Section title="Specialist Performance Review (aggregate, non-punitive)">
          <JsonView data={performance} />
        </Section>
      )}

      {activeTab === "Notifications" && (
        <Section title="Notifications and Escalations">
          <JsonView data={notifications} />
        </Section>
      )}
    </div>
  );
}
