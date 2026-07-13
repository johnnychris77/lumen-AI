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

function ScoreRow({ label, value }: { label: string; value: unknown }) {
  const num = typeof value === "number" ? value : null;
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-slate-500">{label}</span>
      <span className={num === null ? "text-slate-300" : "font-medium text-slate-700"}>{num === null ? "no data" : num}</span>
    </div>
  );
}

function HealthView({ data }: { data: Json | null | undefined }) {
  if (!data) return <p className="text-xs text-slate-400">No operational health snapshot yet.</p>;
  return (
    <div>
      <div className="mb-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-slate-800">{(data.overall_score as number) ?? "—"}</span>
        <span className="text-xs text-slate-400">overall operational health</span>
      </div>
      <div className="space-y-1">
        <ScoreRow label="Quality" value={data.quality_score} />
        <ScoreRow label="Workflow" value={data.workflow_score} />
        <ScoreRow label="Education" value={data.education_score} />
        <ScoreRow label="Equipment" value={data.equipment_score} />
        <ScoreRow label="Digital twins" value={data.digital_twin_score} />
        <ScoreRow label="Knowledge" value={data.knowledge_score} />
        <ScoreRow label="Enterprise" value={data.enterprise_score} />
      </div>
    </div>
  );
}

function RiskHeatRow({ item }: { item: Json }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-slate-600">{item.key as string}</span>
      <span className="text-slate-400">avg {item.average_risk_score as number} · n={item.count as number}</span>
    </div>
  );
}

function OpenRisksView({ data }: { data: Json | null | undefined }) {
  if (!data) return <p className="text-xs text-slate-400">No risk data yet.</p>;
  const enterprise = (data.enterprise_risk as Json) || {};
  const facilities = (data.top_facility_risk as Json[]) || [];
  const anatomy = (data.top_anatomy_risk as Json[]) || [];
  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-2">
        <span className="text-lg font-semibold text-slate-800">{(enterprise.average_risk_score as number) ?? "—"}</span>
        <span className="text-xs text-slate-400">avg enterprise risk score · {(enterprise.high_or_critical_pct as number) ?? "—"}% high/critical</span>
      </div>
      <div>
        <p className="mb-1 text-xs font-medium text-slate-500">Top facility risk</p>
        {facilities.length ? facilities.map((f, i) => <RiskHeatRow key={i} item={f} />) : <p className="text-xs text-slate-300">No facility data.</p>}
      </div>
      <div>
        <p className="mb-1 text-xs font-medium text-slate-500">Top anatomy risk</p>
        {anatomy.length ? anatomy.map((a, i) => <RiskHeatRow key={i} item={a} />) : <p className="text-xs text-slate-300">No anatomy data.</p>}
      </div>
    </div>
  );
}

function ShiftReadinessView({ data }: { data: Json | null | undefined }) {
  if (!data) return <p className="text-xs text-slate-400">No shift readiness data yet.</p>;
  const trends = (data.escalating_trends as Json[]) || [];
  return (
    <div className="space-y-2">
      <ScoreRow label="Pending reviews" value={data.pending_reviews} />
      <ScoreRow label="Open patient safety alerts" value={data.open_patient_safety_alerts} />
      <div>
        <p className="mb-1 text-xs font-medium text-slate-500">Escalating trends</p>
        {trends.length ? (
          <ul className="space-y-1">
            {trends.map((t, i) => (
              <li key={i} className="text-xs text-slate-600">{t.instrument_identity as string} — {t.declining_count as number} declining assessment(s)</li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-slate-300">No escalating trends.</p>
        )}
      </div>
    </div>
  );
}

function EnterpriseStatusView({ data }: { data: Json | null | undefined }) {
  if (!data) return <p className="text-xs text-slate-400">No enterprise status yet.</p>;
  return (
    <div className="space-y-1">
      <ScoreRow label="Overall operational health" value={data.overall_operational_health} />
      <ScoreRow label="Average risk score" value={data.average_risk_score} />
      <ScoreRow label="High/critical risk %" value={data.high_or_critical_risk_pct} />
    </div>
  );
}

function TimelineView({ horizons }: { horizons: Json | null | undefined }) {
  if (!horizons) return <p className="text-xs text-slate-400">No timeline data yet.</p>;
  const entries = Object.entries(horizons);
  return (
    <div className="space-y-4">
      {entries.map(([horizon, items]) => (
        <div key={horizon}>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{horizon.replace(/_/g, " ")}</p>
          <RecommendationList items={(items as Json[]) || []} />
        </div>
      ))}
    </div>
  );
}

function JournalView({ items }: { items: Json[] }) {
  if (!items.length) return <p className="text-xs text-slate-400">No decision journal entries yet.</p>;
  return (
    <ol className="space-y-2">
      {items.map((entry) => (
        <li key={entry.id as number} className="rounded border border-slate-100 p-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-800">Recommendation #{entry.recommendation_id as number}</span>
            <span className="text-xs text-slate-400">{entry.decided_by as string} ({entry.decided_role as string})</span>
          </div>
          <p className="mt-1 text-xs text-slate-600">{entry.leader_decision as string}</p>
          {(entry.outcome as string) ? <p className="mt-1 text-xs text-slate-500">Outcome: {entry.outcome as string}</p> : null}
          {(entry.lessons_learned as string) ? <p className="mt-1 text-xs text-slate-400">Lessons: {entry.lessons_learned as string}</p> : null}
          <p className="mt-1 text-xs text-slate-400">confidence: {entry.confidence as string} · specialists: {((entry.specialists_consulted as string[]) || []).join(", ") || "none"}</p>
        </li>
      ))}
    </ol>
  );
}

function BriefContentView({ content }: { content: Json | null | undefined }) {
  if (!content) return null;
  const priorities = (content.top_priorities as Json[]) || [];
  const pending = (content.pending_recommendations as Json[]) || [];
  const alerts = (content.open_patient_safety_alerts as Json[]) || [];
  const health = content.operational_health as Json | undefined;
  return (
    <div className="space-y-3">
      <div>
        <p className="mb-1 text-xs font-medium text-slate-500">Top priorities</p>
        <PriorityList items={priorities} />
      </div>
      <div>
        <p className="mb-1 text-xs font-medium text-slate-500">Pending recommendations</p>
        <RecommendationList items={pending} />
      </div>
      <div>
        <p className="mb-1 text-xs font-medium text-slate-500">Operational health</p>
        <HealthView data={health} />
      </div>
      <div>
        <p className="mb-1 text-xs font-medium text-slate-500">Open patient safety alerts ({alerts.length})</p>
        {alerts.length ? (
          <ul className="space-y-1">
            {alerts.map((a) => (
              <li key={a.id as number} className="text-xs text-slate-600">{a.alert_type as string} — {a.instrument_identity as string} ({a.severity as string})</li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-slate-300">No open alerts.</p>
        )}
      </div>
    </div>
  );
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
            <HealthView data={workspace.operational_health as Json} />
          </Section>
          <Section title="Open Risks">
            <OpenRisksView data={workspace.open_risks as Json} />
          </Section>
          <Section title="Today's Recommendations">
            <RecommendationList items={(workspace.todays_recommendations as Json[]) || []} />
          </Section>
          <Section title="Pending Executive Decisions">
            <RecommendationList items={(workspace.pending_executive_decisions as Json[]) || []} />
          </Section>
          <Section title="Shift Readiness">
            <ShiftReadinessView data={workspace.shift_readiness as Json} />
          </Section>
          <Section title="Enterprise Status">
            <EnterpriseStatusView data={workspace.enterprise_status as Json} />
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
          <TimelineView horizons={timeline.horizons as Json} />
        </Section>
      )}

      {activeTab === "Decision Journal" && (
        <Section title="Decision Journal">
          <JournalView items={journal} />
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
              <BriefContentView content={brief.content as Json} />
            </div>
          ) : (
            <p className="text-xs text-slate-400">No brief generated yet.</p>
          )}
        </Section>
      )}
    </div>
  );
}
