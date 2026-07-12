/**
 * LumenAI AI Leadership Platform — Project Steward: Governed Action
 * Execution, Change Management & Benefits Realization.
 *
 * Frontend route `/steward`, API prefix `/api/steward`. Steward converts
 * approved decisions (Council, CAPA, Sentinel-X, Maestro, Aegis, Vulcan,
 * Sage, Veritas, Phoenix, audits, policy changes, leadership directives)
 * into governed implementation plans -- it never approves clinical or
 * operational decisions itself, only executes and monitors what an
 * appropriate human role already authorized.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Json = Record<string, unknown>;

const TABS = ["Workspace", "Actions", "Boards", "Notifications"] as const;
type Tab = (typeof TABS)[number];

const BOARD_ROLES = ["supervisor", "manager", "director", "executive"] as const;

const CATEGORY_ACTION_TYPES: Record<string, string[]> = {
  clinical_quality: [
    "recleaning_workflow_revision", "enhanced_inspection_requirement", "supervisor_review_threshold_change",
    "baseline_remediation", "anatomy_profile_update",
  ],
  operational: ["workload_reassignment", "queue_priority_change", "staffing_adjustment_recommendation", "workflow_redesign", "equipment_use_change"],
  education: ["targeted_microlearning", "competency_reassessment", "supervised_return_demonstration", "shift_based_education", "instrument_family_training"],
  reliability: ["repair_evaluation", "manufacturer_review", "increased_inspection_frequency", "quarantine", "retirement_review"],
  governance: ["policy_revision", "rule_revision", "workflow_approval", "knowledge_update", "model_review", "evidence_remediation"],
};

const SOURCE_TYPES = [
  "council_case", "capa", "sentinelx_risk_alert", "maestro_recommendation", "aegis_process_recommendation",
  "vulcan_reliability_recommendation", "sage_education_recommendation", "veritas_evidence_remediation",
  "phoenix_improvement_recommendation", "audit_finding", "policy_change", "leadership_directive",
];

const STATUSES = [
  "DRAFT", "PENDING_APPROVAL", "APPROVED", "READY_TO_START", "IN_PROGRESS", "BLOCKED", "AT_RISK",
  "AWAITING_EVIDENCE", "AWAITING_VERIFICATION", "COMPLETED_PENDING_REVIEW", "SUSTAIN", "REVISE", "ESCALATE",
  "CLOSED", "CANCELLED",
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {children}
    </div>
  );
}

function riskColor(risk: string): string {
  if (risk === "critical") return "text-red-700";
  if (risk === "high") return "text-amber-700";
  return "text-slate-500";
}

function ActionCard({ action, onSelect }: { action: Json; onSelect: (id: number) => void }) {
  return (
    <li className="cursor-pointer rounded border border-slate-100 p-2 hover:bg-slate-50" onClick={() => onSelect(action.id as number)}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-800">#{action.id as number} — {action.action_title as string}</span>
        <span className={`text-xs font-medium ${riskColor(action.risk_level as string)}`}>{action.risk_level as string}</span>
      </div>
      <p className="mt-1 text-xs text-slate-500">{action.action_type as string} · {action.status as string}</p>
      <p className="mt-1 text-xs text-slate-400">owner: {(action.owner as string) || "unassigned"} · due: {(action.due_date as string)?.slice(0, 10) || "none"}</p>
    </li>
  );
}

function ActionList({ actions, onSelect }: { actions: Json[]; onSelect: (id: number) => void }) {
  if (!actions.length) return <p className="text-xs text-slate-400">None.</p>;
  return <ul className="space-y-2">{actions.map((a) => <ActionCard key={a.id as number} action={a} onSelect={onSelect} />)}</ul>;
}

function KeyValueCounts({ data }: { data: Json | null | undefined }) {
  const entries = data ? Object.entries(data) : [];
  if (!entries.length) return <p className="text-xs text-slate-400">No data yet.</p>;
  return (
    <ul className="space-y-1">
      {entries.map(([key, value]) => (
        <li key={key} className="flex items-center justify-between text-xs">
          <span className="text-slate-600">{key}</span>
          <span className="font-medium text-slate-700">{value as number}</span>
        </li>
      ))}
    </ul>
  );
}

function PlanView({ plan }: { plan: Json | null }) {
  if (!plan) return <p className="text-xs text-slate-400">No plan generated yet.</p>;
  return (
    <div className="space-y-1 text-xs">
      <p><span className="font-medium text-slate-600">Objective:</span> {plan.objective as string}</p>
      <p><span className="font-medium text-slate-600">Rationale:</span> {plan.rationale as string}</p>
      <p><span className="font-medium text-slate-600">Owner:</span> {(plan.owner as string) || "unassigned"} · <span className="font-medium text-slate-600">Accountable leader:</span> {(plan.accountable_leader as string) || "unassigned"}</p>
      <p><span className="font-medium text-slate-600">Affected roles:</span> {((plan.affected_roles as string[]) || []).join(", ")}</p>
      <p><span className="font-medium text-slate-600">Communication plan:</span></p>
      <ul className="ml-3 list-disc text-slate-500">{((plan.communication_plan as string[]) || []).map((c, i) => <li key={i}>{c}</li>)}</ul>
      <p><span className="font-medium text-slate-600">Training required:</span> {plan.training_requirements ? "yes" : "no"}</p>
      <p><span className="font-medium text-slate-600">Rollback plan:</span> {plan.rollback_plan as string}</p>
      <p className="italic text-slate-400">{plan.activation_note as string}</p>
    </div>
  );
}

function DependenciesView({ data }: { data: Json | null }) {
  if (!data) return <p className="text-xs text-slate-400">No dependency analysis yet.</p>;
  return (
    <div className="space-y-1 text-xs">
      <p><span className="font-medium text-slate-600">Operational risk:</span> {data.operational_risk as string}</p>
      <p><span className="font-medium text-slate-600">Affected workflows:</span> {((data.affected_workflows as string[]) || []).join(", ") || "none"}</p>
      <p><span className="font-medium text-slate-600">Affected policies:</span> {((data.affected_policies as string[]) || []).join(", ") || "none"}</p>
      <p><span className="font-medium text-slate-600">Staffing impact:</span> {data.staffing_impact ? "yes" : "no"}</p>
      <p><span className="font-medium text-slate-600">Possible service disruption:</span> {data.possible_service_disruption ? "yes" : "no"}</p>
      <p><span className="font-medium text-slate-600">Requires dependency review before publication:</span> {data.requires_dependency_review_before_publication ? "yes" : "no"}</p>
    </div>
  );
}

function VerificationList({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">No verifications recorded.</p>;
  return (
    <ul className="space-y-1">
      {items.map((v) => (
        <li key={v.id as number} className="text-xs">
          <span className={v.sufficient ? "text-emerald-700" : "text-red-700"}>{v.sufficient ? "sufficient" : "insufficient"}</span>
          {" — "}{v.evidence_type as string}{v.insufficiency_reason ? `: ${v.insufficiency_reason as string}` : ""}
        </li>
      ))}
    </ul>
  );
}

function OutcomeReviewList({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">No outcome reviews recorded.</p>;
  return (
    <ul className="space-y-1">
      {items.map((o) => (
        <li key={o.id as number} className="text-xs text-slate-600">
          {o.metric_name as string}: baseline {String(o.baseline_value ?? "—")} → expected {String(o.expected_value ?? "—")} → actual {String(o.actual_value ?? "—")}
          {" — "}<span className="font-medium">{o.classification as string}</span>
        </li>
      ))}
    </ul>
  );
}

function ConsequenceList({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">None flagged.</p>;
  return (
    <ul className="space-y-1">
      {items.map((c) => (
        <li key={c.id as number} className={`text-xs ${c.reviewed ? "text-slate-500" : "text-amber-700"}`}>
          {c.consequence_type as string}: {c.description as string} {c.reviewed ? "(reviewed)" : "(needs review)"}
        </li>
      ))}
    </ul>
  );
}

function ResidualRiskList({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">No residual-risk review recorded.</p>;
  return (
    <ul className="space-y-1">
      {items.map((r) => (
        <li key={r.id as number} className="text-xs text-slate-600">
          before {String(r.risk_before ?? "—")} · during {String(r.risk_during ?? "—")} · after {String(r.risk_after ?? "—")} — reviewed by {(r.reviewed_by as string) || "pending"}
        </li>
      ))}
    </ul>
  );
}

function TimelineView({ timeline }: { timeline: Json | null }) {
  const events = (timeline?.events as Json[]) || [];
  if (!events.length) return <p className="text-xs text-slate-400">No timeline events yet.</p>;
  return (
    <ol className="space-y-1 border-l border-slate-200 pl-3">
      {events.map((e, i) => (
        <li key={i} className="text-xs">
          <span className="text-slate-400">{(e.timestamp as string)?.slice(0, 19).replace("T", " ")}</span>{" "}
          <span className="font-medium text-slate-600">[{(e.stage as string).replace(/_/g, " ")}]</span>{" "}
          <span className="text-slate-600">{e.detail as string}</span>
        </li>
      ))}
    </ol>
  );
}

export default function StewardWorkspace() {
  const [activeTab, setActiveTab] = useState<Tab>("Workspace");
  const [workspace, setWorkspace] = useState<Json | null>(null);

  const [actions, setActions] = useState<Json[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedActionId, setSelectedActionId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Json | null>(null);
  const [plan, setPlan] = useState<Json | null>(null);
  const [dependencies, setDependencies] = useState<Json | null>(null);
  const [timeline, setTimeline] = useState<Json | null>(null);

  const [boardRole, setBoardRole] = useState<(typeof BOARD_ROLES)[number]>("supervisor");
  const [board, setBoard] = useState<Json | null>(null);

  const [notifications, setNotifications] = useState<Json[]>([]);
  const [escalations, setEscalations] = useState<Json[]>([]);

  const [newCategory, setNewCategory] = useState("operational");
  const [newActionType, setNewActionType] = useState(CATEGORY_ACTION_TYPES.operational[0]);
  const [newSourceType, setNewSourceType] = useState(SOURCE_TYPES[0]);
  const [newSourceId, setNewSourceId] = useState("");
  const [newSourceDecision, setNewSourceDecision] = useState("");
  const [newApprovedBy, setNewApprovedBy] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newRiskLevel, setNewRiskLevel] = useState("medium");

  function loadWorkspace() {
    api.get("/api/steward/workspace").then(setWorkspace).catch(() => {});
  }

  function loadActions() {
    const q = statusFilter ? `?status=${statusFilter}` : "";
    api.get(`/api/steward/actions${q}`).then((r: Json) => setActions((r.actions as Json[]) || [])).catch(() => {});
  }

  function loadDetail(id: number) {
    api.get(`/api/steward/actions/${id}`).then(setDetail).catch(() => {});
    api.get(`/api/steward/actions/${id}/plan`).then(setPlan).catch(() => setPlan(null));
    api.get(`/api/steward/actions/${id}/dependencies`).then(setDependencies).catch(() => setDependencies(null));
    api.get(`/api/steward/actions/${id}/timeline`).then(setTimeline).catch(() => setTimeline(null));
  }

  function selectAction(id: number) {
    setSelectedActionId(id);
    loadDetail(id);
  }

  function createAction() {
    api.post("/api/steward/actions", {
      source_type: newSourceType, source_id: newSourceId, source_decision: newSourceDecision,
      approved_by: newApprovedBy, approval_timestamp: new Date().toISOString(), action_title: newTitle,
      category: newCategory, action_type: newActionType, risk_level: newRiskLevel,
    }).then(() => {
      loadActions();
      setNewSourceId(""); setNewSourceDecision(""); setNewApprovedBy(""); setNewTitle("");
    }).catch(() => {});
  }

  useEffect(() => {
    if (activeTab === "Workspace") loadWorkspace();
    if (activeTab === "Actions") loadActions();
    if (activeTab === "Notifications") {
      api.get("/api/steward/notifications").then((r: Json) => setNotifications((r.notifications as Json[]) || [])).catch(() => {});
      api.get("/api/steward/escalations").then((r: Json) => setEscalations((r.escalations as Json[]) || [])).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, statusFilter]);

  useEffect(() => {
    if (activeTab === "Boards") api.get(`/api/steward/boards/${boardRole}`).then(setBoard).catch(() => setBoard(null));
  }, [activeTab, boardRole]);

  return (
    <div className="space-y-4 p-4">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Steward — Governed Action Execution</h1>
        <p className="text-xs text-slate-400">
          Steward converts approved decisions into governed implementation plans and tracks execution,
          verification, and measured outcomes. It does not approve clinical or operational decisions -- it
          executes and monitors only actions authorized by the appropriate human role.
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
          <Section title="Approved Actions"><ActionList actions={(workspace.approved_actions as Json[]) || []} onSelect={() => {}} /></Section>
          <Section title="Actions Awaiting Owner"><ActionList actions={(workspace.actions_awaiting_owner as Json[]) || []} onSelect={() => {}} /></Section>
          <Section title="Actions Due Soon"><ActionList actions={(workspace.actions_due_soon as Json[]) || []} onSelect={() => {}} /></Section>
          <Section title="Blocked Actions"><ActionList actions={(workspace.blocked_actions as Json[]) || []} onSelect={() => {}} /></Section>
          <Section title="Actions At Risk"><ActionList actions={(workspace.actions_at_risk as Json[]) || []} onSelect={() => {}} /></Section>
          <Section title="Evidence Missing"><ActionList actions={(workspace.evidence_missing as Json[]) || []} onSelect={() => {}} /></Section>
          <Section title="Verification Pending"><ActionList actions={(workspace.verification_pending as Json[]) || []} onSelect={() => {}} /></Section>
          <Section title="Benefits Not Achieved"><ActionList actions={(workspace.benefits_not_achieved as Json[]) || []} onSelect={() => {}} /></Section>
          <Section title="Unintended Consequences"><ActionList actions={(workspace.unintended_consequences as Json[]) || []} onSelect={() => {}} /></Section>
          <Section title="Ready For Closure"><ActionList actions={(workspace.actions_ready_for_closure as Json[]) || []} onSelect={() => {}} /></Section>
          <Section title="Recently Closed"><ActionList actions={(workspace.recently_closed_actions as Json[]) || []} onSelect={() => {}} /></Section>
        </div>
      )}

      {activeTab === "Actions" && (
        <div className="space-y-4">
          <Section title="Create Governed Action (from an already-approved decision)">
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
              <label className="text-xs text-slate-600">
                Source type
                <select className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={newSourceType} onChange={(e) => setNewSourceType(e.target.value)}>
                  {SOURCE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </label>
              <label className="text-xs text-slate-600">
                Source id
                <input className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={newSourceId} onChange={(e) => setNewSourceId(e.target.value)} />
              </label>
              <label className="text-xs text-slate-600 md:col-span-2">
                Source decision (approved text)
                <input className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={newSourceDecision} onChange={(e) => setNewSourceDecision(e.target.value)} />
              </label>
              <label className="text-xs text-slate-600">
                Approved by
                <input className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={newApprovedBy} onChange={(e) => setNewApprovedBy(e.target.value)} />
              </label>
              <label className="text-xs text-slate-600 md:col-span-2">
                Action title
                <input className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
              </label>
              <label className="text-xs text-slate-600">
                Category
                <select
                  className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={newCategory}
                  onChange={(e) => { setNewCategory(e.target.value); setNewActionType(CATEGORY_ACTION_TYPES[e.target.value][0]); }}
                >
                  {Object.keys(CATEGORY_ACTION_TYPES).map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </label>
              <label className="text-xs text-slate-600">
                Action type
                <select className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={newActionType} onChange={(e) => setNewActionType(e.target.value)}>
                  {CATEGORY_ACTION_TYPES[newCategory].map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </label>
              <label className="text-xs text-slate-600">
                Risk level
                <select className="mt-1 block w-full rounded border border-slate-200 p-1 text-sm" value={newRiskLevel} onChange={(e) => setNewRiskLevel(e.target.value)}>
                  {["low", "medium", "high", "critical"].map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </label>
            </div>
            <button onClick={createAction} className="mt-2 rounded bg-indigo-600 px-3 py-1 text-sm text-white">Create Governed Action</button>
          </Section>

          <div className="flex flex-wrap gap-1">
            <button onClick={() => setStatusFilter("")} className={`rounded px-2 py-1 text-xs ${statusFilter === "" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}>all</button>
            {STATUSES.map((s) => (
              <button key={s} onClick={() => setStatusFilter(s)} className={`rounded px-2 py-1 text-xs ${statusFilter === s ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}>{s}</button>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Section title="All Actions"><ActionList actions={actions} onSelect={selectAction} /></Section>
            {selectedActionId && detail && (
              <Section title={`Action #${selectedActionId} Detail`}>
                <div className="space-y-3">
                  <div>
                    <h4 className="text-xs font-semibold text-slate-600">1. Approved Decision & Source Evidence</h4>
                    <p className="text-xs text-slate-600">{(detail.action as Json).source_decision as string}</p>
                    <p className="text-xs text-slate-400">approved by {(detail.action as Json).approved_by as string} · source: {(detail.action as Json).source_type as string} #{(detail.action as Json).source_id as string}</p>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-600">3. Implementation Plan</h4>
                    <PlanView plan={plan} />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-600">5. Dependencies</h4>
                    <DependenciesView data={dependencies} />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-600">9. Completion Evidence</h4>
                    <VerificationList items={(detail.verifications as Json[]) || []} />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-600">10. Outcome Metrics & Benefits Realization</h4>
                    <OutcomeReviewList items={(detail.outcome_reviews as Json[]) || []} />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-600">12. Unintended Consequences</h4>
                    <ConsequenceList items={(detail.unintended_consequences as Json[]) || []} />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-600">Residual Risk Review</h4>
                    <ResidualRiskList items={(detail.residual_risk_reviews as Json[]) || []} />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-600">14. Decision-to-Outcome Timeline / Audit History</h4>
                    <TimelineView timeline={timeline} />
                  </div>
                </div>
              </Section>
            )}
          </div>
        </div>
      )}

      {activeTab === "Boards" && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-1">
            {BOARD_ROLES.map((r) => (
              <button key={r} onClick={() => setBoardRole(r)} className={`rounded px-3 py-1 text-sm capitalize ${boardRole === r ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}>{r}</button>
            ))}
          </div>
          {board && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {Object.entries(board).map(([key, value]) => (
                <Section key={key} title={key.replace(/_/g, " ")}>
                  {Array.isArray(value) ? <ActionList actions={value as Json[]} onSelect={selectAction} /> : <KeyValueCounts data={value as Json} />}
                </Section>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "Notifications" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Notifications">
            {notifications.length ? (
              <ul className="space-y-1">{notifications.map((n, i) => <li key={i} className="text-xs text-slate-600">{n.message as string} <span className="text-slate-400">({n.recipient_role as string})</span></li>)}</ul>
            ) : <p className="text-xs text-slate-400">No notifications.</p>}
          </Section>
          <Section title="Escalations">
            {escalations.length ? (
              <ul className="space-y-1">{escalations.map((e, i) => <li key={i} className="text-xs text-amber-700">{e.message as string} <span className="text-slate-400">→ {e.next_accountable_role as string}</span></li>)}</ul>
            ) : <p className="text-xs text-slate-400">No escalations.</p>}
          </Section>
        </div>
      )}
    </div>
  );
}
