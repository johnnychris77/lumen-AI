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

function KeyValueCounts({ data }: { data: Json | null | undefined }) {
  const entries = data ? Object.entries(data) : [];
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

function CaseSummaryView({ data }: { data: Json | null | undefined }) {
  if (!data) return null;
  return (
    <div className="space-y-1 text-xs">
      <p className="text-sm font-medium text-slate-800">{data.case_type as string}</p>
      <p className="text-slate-600">{data.source_event as string}</p>
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-slate-400">
        <span>team: {data.team_key as string}</span>
        <span>risk: {data.risk_level as string}</span>
        <span>urgency: {data.urgency as string}</span>
        <span>status: {data.status as string}</span>
        <span>consensus: {(data.consensus_status as string) || "pending"}</span>
      </div>
      {(data.recommended_action as string) ? <p className="text-slate-600">recommended: {data.recommended_action as string}</p> : null}
      <p className="text-slate-400">specialists: {((data.participating_specialists as string[]) || []).join(", ")}</p>
    </div>
  );
}

function AssessmentList({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">No specialist assessments yet.</p>;
  return (
    <ol className="space-y-2">
      {items.map((a) => (
        <li key={a.id as number} className="rounded border border-slate-100 p-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-800">{a.specialist_key as string}</span>
            <span className="text-xs text-slate-400">confidence: {a.confidence as string}</span>
          </div>
          <p className="mt-1 text-xs text-slate-600">{a.conclusion as string}</p>
          {(a.significance as string) ? <p className="mt-1 text-xs text-slate-500">{a.significance as string}</p> : null}
          {(a.recommended_action as string) ? <p className="mt-1 text-xs text-slate-500">Recommends: {a.recommended_action as string}</p> : null}
          {(a.evidence_limitations as string) ? <p className="mt-1 text-xs text-warning">Limitations: {a.evidence_limitations as string}</p> : null}
          <p className="mt-1 text-xs text-slate-400">urgency: {a.urgency as string} · approver: {a.human_role_required as string}</p>
        </li>
      ))}
    </ol>
  );
}

function AgreementMapView({ data }: { data: Json | null | undefined }) {
  if (!data) return <p className="text-xs text-slate-400">No agreement map yet.</p>;
  const matrix = (data.matrix as Json) || {};
  const dissenting = new Set((data.dissenting_specialists as string[]) || []);
  return (
    <div className="space-y-2">
      {(data.consensus_position as string) ? (
        <p className="text-xs text-slate-700"><span className="font-medium">Consensus:</span> {data.consensus_position as string}</p>
      ) : null}
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-slate-400">
            <th className="pr-2 font-medium">Specialist</th>
            <th className="pr-2 font-medium">Position</th>
            <th className="font-medium">Confidence</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(matrix).map(([specialist, row]) => (
            <tr key={specialist} className={dissenting.has(specialist) ? "text-warning" : "text-slate-600"}>
              <td className="pr-2 py-1">{specialist}{dissenting.has(specialist) ? " (dissenting)" : ""}</td>
              <td className="pr-2 py-1">{(row as Json).position as string}</td>
              <td className="py-1">{(row as Json).confidence as string}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DissentList({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">No dissent recorded.</p>;
  return (
    <ol className="space-y-2">
      {items.map((d) => (
        <li key={d.id as number} className="rounded border border-warning/30 bg-warning-subtle p-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-warning-hover">{d.dissenting_specialist as string}</span>
            <span className="text-xs text-warning">{d.escalation_level as string}</span>
          </div>
          <p className="mt-1 text-xs text-warning-hover">Disputes: {d.disputed_conclusion as string}</p>
          {(d.risk_if_ignored as string) ? <p className="mt-1 text-xs text-warning">Risk if ignored: {d.risk_if_ignored as string}</p> : null}
          {(d.proposed_alternative_action as string) ? <p className="mt-1 text-xs text-warning">Proposed alternative: {d.proposed_alternative_action as string}</p> : null}
          {(d.additional_evidence_required as string) ? <p className="mt-1 text-xs text-warning">Evidence required: {d.additional_evidence_required as string}</p> : null}
        </li>
      ))}
    </ol>
  );
}

function DecisionOptionList({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">No decision options yet.</p>;
  return (
    <ol className="space-y-2">
      {items.map((o) => (
        <li key={o.id as number} className="rounded border border-slate-100 p-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-800">Option {o.option_label as string} — {o.option_title as string}</span>
            <span className="text-xs text-slate-400">{o.required_authority as string}</span>
          </div>
          <p className="mt-1 text-xs text-success">Benefits: {o.benefits as string}</p>
          <p className="mt-1 text-xs text-danger">Risks: {o.risks as string}</p>
          <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-slate-400">
            <span>clinical risk: {o.clinical_risk as string}</span>
            <span>reversibility: {o.reversibility as string}</span>
            <span>evidence strength: {o.evidence_strength as string}</span>
            <span>time to resolution: {o.expected_time_to_resolution as string}</span>
          </div>
        </li>
      ))}
    </ol>
  );
}

function HumanDecisionList({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">No human decision recorded yet.</p>;
  return (
    <ol className="space-y-2">
      {items.map((d) => (
        <li key={d.id as number} className="rounded border border-primary/20 bg-primary-subtle p-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-primary-active">{d.decision as string}</span>
            <span className="text-xs text-primary">{d.approver as string} ({d.approver_role as string})</span>
          </div>
          {(d.rationale as string) ? <p className="mt-1 text-xs text-primary-active">{d.rationale as string}</p> : null}
          {(d.conditions as string) ? <p className="mt-1 text-xs text-primary">Conditions: {d.conditions as string}</p> : null}
        </li>
      ))}
    </ol>
  );
}

function TeamList({ teams }: { teams: Json[] }) {
  if (!teams.length) return <p className="text-xs text-slate-400">No teams configured.</p>;
  return (
    <ol className="space-y-2">
      {teams.map((t) => (
        <li key={t.id as number} className="rounded border border-slate-100 p-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-800">{t.team_name as string}</span>
            <span className="text-xs text-slate-400">v{t.version as number} · {t.approval_status as string}</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Required: {((t.required_specialists as string[]) || []).join(", ") || "none"}</p>
          <p className="mt-1 text-xs text-slate-400">Optional: {((t.optional_specialists as string[]) || []).join(", ") || "none"}</p>
          <p className="mt-1 text-xs text-slate-400">
            quorum: {t.quorum_requirement as number} · safety veto: {t.safety_veto_enabled ? "enabled" : "disabled"} · owner: {(t.owner as string) || "unassigned"}
          </p>
        </li>
      ))}
    </ol>
  );
}

function PerformanceView({ data }: { data: Json | null | undefined }) {
  if (!data) return <p className="text-xs text-slate-400">No performance data yet.</p>;
  const bySpecialist = (data.by_specialist as Json) || {};
  const entries = Object.entries(bySpecialist);
  return (
    <div>
      {(data.note as string) ? <p className="mb-2 text-xs italic text-slate-400">{data.note as string}</p> : null}
      {entries.length ? (
        <ol className="space-y-2">
          {entries.map(([specialist, stats]) => {
            const s = stats as Json;
            return (
              <li key={specialist} className="rounded border border-slate-100 p-2">
                <p className="text-sm font-medium text-slate-800">{specialist}</p>
                <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-slate-500">
                  <span>assessments: {s.total_assessments as number}</span>
                  <span>abstentions: {s.abstention_count as number}</span>
                  <span>dissents: {s.dissent_count as number}</span>
                  <span>dissent validated: {s.dissent_validated_count as number}/{s.dissent_evaluated_count as number}</span>
                  <span>resolved cases: {s.resolved_case_count as number}</span>
                </div>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="text-xs text-slate-400">No specialist activity recorded yet.</p>
      )}
    </div>
  );
}

function NotificationList({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">No notifications.</p>;
  return (
    <ul className="space-y-2">
      {items.map((n) => (
        <li key={`${n.source as string}-${n.id as number}`} className="rounded border border-slate-100 p-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-700">{n.message as string}</span>
            <span className="text-xs text-slate-400">{n.recipient_role as string}</span>
          </div>
        </li>
      ))}
    </ul>
  );
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
          <button onClick={openAndConvene} className="rounded bg-primary px-3 py-1 text-sm text-white">
            Open &amp; Convene
          </button>
        </div>
      </Section>

      <div className="flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`rounded px-3 py-1 text-sm ${activeTab === t ? "bg-primary text-white" : "bg-slate-100 text-slate-600"}`}
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
            <KeyValueCounts data={workspace.outcome_effectiveness as Json} />
          </Section>
          <Section title="Specialist Participation">
            <KeyValueCounts data={workspace.specialist_participation as Json} />
          </Section>
          <Section title="Recurring Decision Themes">
            <KeyValueCounts data={workspace.recurring_decision_themes as Json} />
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
                  <CaseSummaryView data={caseDetail.case as Json} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-600">3. Specialist Assessments</h4>
                  <AssessmentList items={(caseDetail.assessments as Json[]) || []} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-600">4. Agreement Map</h4>
                  <AgreementMapView data={caseDetail.agreement_map as Json} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-600">5. Dissent</h4>
                  <DissentList items={(caseDetail.dissent as Json[]) || []} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-600">6. Decision Options</h4>
                  <DecisionOptionList items={(caseDetail.decision_options as Json[]) || []} />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-600">9. Final Human Decision(s)</h4>
                  <HumanDecisionList items={(caseDetail.human_decisions as Json[]) || []} />
                </div>
              </div>
            </Section>
          )}
        </div>
      )}

      {activeTab === "Teams" && (
        <Section title="Leadership Team Registry">
          <TeamList teams={teams} />
        </Section>
      )}

      {activeTab === "Performance" && performance && (
        <Section title="Specialist Performance Review (aggregate, non-punitive)">
          <PerformanceView data={performance} />
        </Section>
      )}

      {activeTab === "Notifications" && (
        <Section title="Notifications and Escalations">
          <NotificationList items={notifications} />
        </Section>
      )}
    </div>
  );
}
