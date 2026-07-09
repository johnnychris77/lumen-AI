/**
 * v2.9 — LumenAI Quality: Closed-Loop Quality Intelligence (Project Guardian).
 * Executive Quality Dashboard — connects OR quality events to inspections,
 * technicians, trays, root cause analysis, CAPAs, and competency into one
 * explainable quality intelligence platform. Advisory only.
 */
import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface QualityEvent {
  id: number;
  event_ref: string;
  narrative: string;
  severity: string;
  instrument_type_guess: string | null;
  finding_type: string | null;
  spd_category: string | null;
  classification_confidence: number | null;
  requires_supervisor_classification: boolean;
  confirmed: boolean;
}

interface Correlation {
  id: number;
  target_type: string;
  target_id: string;
  confidence: number;
  tracked: boolean;
  note: string;
  supervisor_confirmed: boolean;
}

interface RcaDraft {
  id: number;
  likely_process_stage: string;
  evidence: string[];
  contributing_factors: string[];
  investigation_questions: string[];
  historical_recurrence_count: number;
  status: string;
  inspection_id: number | null;
}

interface CapaRecommendation {
  id: number;
  recommendation_type: string;
  rationale: string;
  status: string;
}

interface Capa {
  id: string;
  title: string;
  lifecycle_status: string;
  recommendation_type: string | null;
}

interface CompetencyOpportunity {
  id: number;
  scope_type: string;
  scope_value: string;
  opportunity_type: string;
  finding_type: string;
  rationale: string;
  status: string;
}

interface FpySnapshot {
  scope_type: string;
  scope_value: string;
  total_pass_count: number;
  confirmed_miss_count: number;
  true_fpy_pct: number;
  false_pass_pct: number;
}

interface FpyAllScopes {
  overall: FpySnapshot;
  by_department: FpySnapshot[];
  by_instrument: FpySnapshot[];
  by_technician: FpySnapshot[];
  by_facility: FpySnapshot[];
}

interface CommandCenterSummary {
  quality_events: { total: number; by_severity: Record<string, number> };
  recurring_findings: { finding_type: string; count: number }[];
  capas: Record<string, number>;
  root_causes: { overall: Record<string, number> };
  first_pass_yield: FpyAllScopes;
  education_impact_avg_pct: number | null;
  vendor_trends: Record<string, { total: number; received: number }>;
  manufacturer_trends: Record<string, { total: number; approved: number }>;
}

const TABS = ["Quality Events", "RCA & CAPA", "Competency", "First Pass Yield", "Executive Dashboard"] as const;
type Tab = (typeof TABS)[number];

function severityColor(sev: string): string {
  switch (sev) {
    case "critical": return "bg-red-100 text-red-800";
    case "high": return "bg-orange-100 text-orange-800";
    case "medium": return "bg-amber-100 text-amber-800";
    default: return "bg-slate-100 text-slate-700";
  }
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

export default function QualityCommandCenterDashboard() {
  const { role } = useAuth();
  const canApprove = role === "admin" || role === "spd_manager";

  const [tab, setTab] = useState<Tab>("Quality Events");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [narrative, setNarrative] = useState("");
  const [eventDate, setEventDate] = useState(() => new Date().toISOString().slice(0, 16));
  const [events, setEvents] = useState<QualityEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<QualityEvent | null>(null);
  const [correlations, setCorrelations] = useState<Correlation[]>([]);
  const [rcaDraft, setRcaDraft] = useState<RcaDraft | null>(null);
  const [rootCause, setRootCause] = useState("unknown");
  const [recommendations, setRecommendations] = useState<CapaRecommendation[]>([]);
  const [capas, setCapas] = useState<Capa[]>([]);

  const [opportunities, setOpportunities] = useState<CompetencyOpportunity[]>([]);
  const [fpy, setFpy] = useState<FpyAllScopes | null>(null);
  const [summary, setSummary] = useState<CommandCenterSummary | null>(null);

  async function createEvent() {
    if (!narrative.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.post<QualityEvent>("/api/quality-guardian/events", {
        event_date: new Date(eventDate).toISOString(),
        narrative,
        source_system: "manual",
        severity: "medium",
      });
      setEvents((prev) => [created, ...prev]);
      setNarrative("");
    } catch {
      setError("Could not create quality event.");
    } finally {
      setBusy(false);
    }
  }

  async function loadEvents() {
    setBusy(true);
    try {
      const result = await api.get<{ events: QualityEvent[] }>("/api/quality-guardian/events");
      setEvents(result.events);
    } finally {
      setBusy(false);
    }
  }

  async function selectEvent(event: QualityEvent) {
    setSelectedEvent(event);
    setRcaDraft(null);
    setBusy(true);
    try {
      const result = await api.post<{ correlations: Correlation[] }>(`/api/quality-guardian/events/${event.id}/correlate`);
      setCorrelations(result.correlations);
    } finally {
      setBusy(false);
    }
  }

  async function generateRcaDraft() {
    if (!selectedEvent) return;
    setBusy(true);
    try {
      const draft = await api.post<RcaDraft>(`/api/quality-guardian/events/${selectedEvent.id}/rca-draft`);
      setRcaDraft(draft);
    } finally {
      setBusy(false);
    }
  }

  async function approveRcaDraft() {
    if (!rcaDraft) return;
    setBusy(true);
    try {
      const updated = await api.post<RcaDraft>(`/api/quality-guardian/rca-drafts/${rcaDraft.id}/approve`, { root_cause: rootCause });
      setRcaDraft(updated);
    } finally {
      setBusy(false);
    }
  }

  async function generateRecommendations() {
    if (!selectedEvent) return;
    setBusy(true);
    try {
      const result = await api.post<{ recommendations: CapaRecommendation[] }>(
        "/api/quality-guardian/capa-recommendations/generate",
        { event_id: selectedEvent.id },
      );
      setRecommendations(result.recommendations);
    } finally {
      setBusy(false);
    }
  }

  async function acceptRecommendation(id: number) {
    setBusy(true);
    try {
      await api.post(`/api/quality-guardian/capa-recommendations/${id}/accept`, {
        title: `CAPA for event ${selectedEvent?.event_ref ?? ""}`,
        owner: "spd_manager",
      });
      const result = await api.get<{ capas: Capa[] }>("/api/quality-guardian/capas");
      setCapas(result.capas);
    } finally {
      setBusy(false);
    }
  }

  async function loadCapas() {
    setBusy(true);
    try {
      const result = await api.get<{ capas: Capa[] }>("/api/quality-guardian/capas");
      setCapas(result.capas);
    } finally {
      setBusy(false);
    }
  }

  async function advanceCapa(capaId: string, newStatus: string) {
    setBusy(true);
    try {
      await api.post(`/api/quality-guardian/capas/${capaId}/advance`, { new_status: newStatus });
      await loadCapas();
    } finally {
      setBusy(false);
    }
  }

  async function detectOpportunities() {
    setBusy(true);
    try {
      const result = await api.post<{ opportunities: CompetencyOpportunity[] }>("/api/quality-guardian/competency-opportunities/detect");
      setOpportunities(result.opportunities);
    } finally {
      setBusy(false);
    }
  }

  async function loadOpportunities() {
    setBusy(true);
    try {
      const result = await api.get<{ opportunities: CompetencyOpportunity[] }>("/api/quality-guardian/competency-opportunities");
      setOpportunities(result.opportunities);
    } finally {
      setBusy(false);
    }
  }

  async function loadFpy() {
    setBusy(true);
    try {
      const result = await api.get<FpyAllScopes>("/api/quality-guardian/first-pass-yield/all-scopes");
      setFpy(result);
    } finally {
      setBusy(false);
    }
  }

  async function loadSummary() {
    setBusy(true);
    try {
      const result = await api.get<CommandCenterSummary>("/api/quality-guardian/command-center");
      setSummary(result);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">LumenAI Quality — Command Center</h2>
        <p className="text-sm text-slate-500">
          Transforms perioperative quality events into structured SPD intelligence — connecting OR feedback to
          inspections, technicians, trays, root causes, CAPAs, and competency. Advisory only.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              if (t === "Quality Events") loadEvents();
              if (t === "Competency") loadOpportunities();
              if (t === "First Pass Yield") loadFpy();
              if (t === "Executive Dashboard") loadSummary();
              if (t === "RCA & CAPA") loadCapas();
            }}
            className={`px-4 py-2 text-sm font-medium rounded-t-md ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {error && <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>}

      {tab === "Quality Events" && (
        <div className="space-y-3">
          <Section title="Report a Quality Event">
            <div className="flex flex-col gap-2">
              <input
                type="datetime-local" value={eventDate} onChange={(e) => setEventDate(e.target.value)}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm w-64"
              />
              <textarea
                value={narrative} onChange={(e) => setNarrative(e.target.value)}
                placeholder='e.g. "Dirty suction found in OR, visible blood residue on Yankauer tip."'
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm" rows={2}
              />
              <button onClick={createEvent} disabled={busy} className="self-start rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
                {busy ? "Submitting…" : "Submit & Classify"}
              </button>
            </div>
          </Section>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Section title="Recent Events">
              <ul className="space-y-1 text-sm">
                {events.map((e) => (
                  <li key={e.id}>
                    <button onClick={() => selectEvent(e)} className="text-left w-full rounded p-2 hover:bg-slate-50">
                      <div className="flex items-center gap-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${severityColor(e.severity)}`}>{e.severity}</span>
                        <span className="font-medium">{e.event_ref}</span>
                        {e.requires_supervisor_classification && <span className="text-xs text-amber-600">needs classification</span>}
                      </div>
                      <div className="text-slate-500 text-xs mt-1">{e.narrative}</div>
                      {e.finding_type && (
                        <div className="text-xs text-slate-400 mt-0.5">
                          {e.finding_type} ({e.spd_category}) — {Math.round((e.classification_confidence ?? 0) * 100)}% confidence
                        </div>
                      )}
                    </button>
                  </li>
                ))}
                {events.length === 0 && <p className="text-slate-400">No events yet</p>}
              </ul>
            </Section>

            {selectedEvent && (
              <Section title={`Correlations — ${selectedEvent.event_ref}`}>
                <ul className="space-y-1 text-sm">
                  {correlations.map((c) => (
                    <li key={c.id} className="flex items-center justify-between">
                      <span className={c.tracked ? "" : "text-slate-400 italic"}>
                        {c.target_type}: {c.tracked ? (c.target_id || "—") : "not tracked"}
                      </span>
                      {c.tracked && <span className="text-xs text-slate-500">{Math.round(c.confidence * 100)}%</span>}
                    </li>
                  ))}
                </ul>
                <div className="mt-3 flex gap-2">
                  <button onClick={generateRcaDraft} disabled={busy} className="rounded-md bg-slate-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">
                    Generate RCA Draft
                  </button>
                  <button onClick={generateRecommendations} disabled={busy} className="rounded-md bg-slate-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">
                    Suggest CAPA
                  </button>
                </div>
              </Section>
            )}
          </div>
        </div>
      )}

      {tab === "RCA & CAPA" && (
        <div className="space-y-3">
          {rcaDraft && (
            <Section title={`RCA Draft — ${rcaDraft.likely_process_stage}`}>
              <p className="text-xs text-slate-500 mb-1">Historical recurrence: {rcaDraft.historical_recurrence_count} similar events</p>
              <p className="text-xs font-semibold text-slate-600 mt-2">Evidence</p>
              <ul className="text-sm text-slate-700 mb-2">{rcaDraft.evidence.map((e, i) => <li key={i}>• {e}</li>)}</ul>
              <p className="text-xs font-semibold text-slate-600">Contributing Factors</p>
              <ul className="text-sm text-slate-700 mb-2">{rcaDraft.contributing_factors.map((f, i) => <li key={i}>• {f}</li>)}</ul>
              <p className="text-xs font-semibold text-slate-600">Investigation Questions</p>
              <ul className="text-sm text-slate-700 mb-2">{rcaDraft.investigation_questions.map((q, i) => <li key={i}>• {q}</li>)}</ul>
              {canApprove && rcaDraft.status === "draft" && (
                <div className="flex gap-2 items-center mt-2">
                  <select value={rootCause} onChange={(e) => setRootCause(e.target.value)} className="rounded-md border border-slate-300 px-2 py-1 text-sm">
                    {["incomplete_manual_cleaning", "improper_brushing", "improper_flushing", "missed_inspection_zone",
                      "poor_lighting", "image_quality", "instrument_damage", "manufacturer_wear", "unknown"].map((rc) => (
                      <option key={rc} value={rc}>{rc.replace(/_/g, " ")}</option>
                    ))}
                  </select>
                  <button onClick={approveRcaDraft} disabled={busy || !rcaDraft.inspection_id} className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">
                    Approve Root Cause
                  </button>
                  {!rcaDraft.inspection_id && <span className="text-xs text-slate-400">No correlated inspection — cannot approve.</span>}
                </div>
              )}
              {rcaDraft.status !== "draft" && <p className="text-sm font-medium text-emerald-700 mt-2">Status: {rcaDraft.status}</p>}
            </Section>
          )}

          {recommendations.length > 0 && (
            <Section title="CAPA Recommendations">
              <ul className="space-y-2">
                {recommendations.map((r) => (
                  <li key={r.id} className="flex items-center justify-between text-sm">
                    <div>
                      <span className="font-medium capitalize">{r.recommendation_type.replace(/_/g, " ")}</span>
                      <span className="text-slate-500"> — {r.rationale}</span>
                    </div>
                    {canApprove && r.status === "suggested" && (
                      <button onClick={() => acceptRecommendation(r.id)} disabled={busy} className="rounded-md bg-slate-700 px-3 py-1 text-xs font-semibold text-white disabled:opacity-50">
                        Accept
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          <Section title="CAPA Lifecycle">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-slate-400"><th className="py-1 pr-3">Title</th><th className="py-1 pr-3">Status</th><th className="py-1 pr-3">Action</th></tr></thead>
              <tbody>
                {capas.map((c) => (
                  <tr key={c.id} className="border-t border-slate-100">
                    <td className="py-1 pr-3">{c.title}</td>
                    <td className="py-1 pr-3 capitalize">{c.lifecycle_status.replace(/_/g, " ")}</td>
                    <td className="py-1 pr-3">
                      {canApprove && c.lifecycle_status !== "closed" && (
                        <select
                          onChange={(e) => e.target.value && advanceCapa(c.id, e.target.value)}
                          defaultValue=""
                          className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                        >
                          <option value="">Advance…</option>
                          {["assigned", "in_progress", "verified", "closed"].map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                      )}
                    </td>
                  </tr>
                ))}
                {capas.length === 0 && <tr><td colSpan={3} className="py-4 text-center text-slate-400">No CAPAs yet</td></tr>}
              </tbody>
            </table>
          </Section>
        </div>
      )}

      {tab === "Competency" && (
        <div className="space-y-3">
          <Section title="Competency Opportunities">
            {canApprove && (
              <button onClick={detectOpportunities} disabled={busy} className="mb-3 rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
                Detect Opportunities
              </button>
            )}
            <ul className="space-y-2">
              {opportunities.map((o) => (
                <li key={o.id} className="text-sm">
                  <span className="font-medium capitalize">{o.opportunity_type.replace(/_/g, " ")}</span>
                  {" — "}<span className="text-slate-700">{o.rationale}</span>
                  {" "}<span className="text-xs text-slate-400">({o.status})</span>
                </li>
              ))}
              {opportunities.length === 0 && <p className="text-slate-400 text-sm">No opportunities detected yet</p>}
            </ul>
          </Section>
        </div>
      )}

      {tab === "First Pass Yield" && fpy && (
        <div className="space-y-3">
          <Section title="Overall First Pass Yield">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <div><div className="text-xs text-slate-500">True FPY</div><div className="text-xl font-bold text-emerald-600">{fpy.overall.true_fpy_pct}%</div></div>
              <div><div className="text-xs text-slate-500">False Pass</div><div className="text-xl font-bold text-red-600">{fpy.overall.false_pass_pct}%</div></div>
              <div><div className="text-xs text-slate-500">Total Pass</div><div className="text-xl font-bold text-slate-900">{fpy.overall.total_pass_count}</div></div>
              <div><div className="text-xs text-slate-500">Confirmed Miss</div><div className="text-xl font-bold text-slate-900">{fpy.overall.confirmed_miss_count}</div></div>
            </div>
          </Section>
          {([["By Department", fpy.by_department], ["By Instrument", fpy.by_instrument], ["By Technician", fpy.by_technician], ["By Facility", fpy.by_facility]] as [string, FpySnapshot[]][]).map(([label, rows]) => (
            <Section key={label} title={label}>
              <ul className="text-sm text-slate-700">
                {rows.map((r) => <li key={r.scope_value}>{r.scope_value}: {r.true_fpy_pct}% true FPY ({r.total_pass_count} pass)</li>)}
                {rows.length === 0 && <p className="text-slate-400">No data yet</p>}
              </ul>
            </Section>
          ))}
        </div>
      )}

      {tab === "Executive Dashboard" && summary && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Section title="Quality Events (30d)"><p className="text-2xl font-bold text-slate-900">{summary.quality_events.total}</p></Section>
            <Section title="Education Impact"><p className="text-2xl font-bold text-slate-900">{summary.education_impact_avg_pct ?? "—"}%</p></Section>
            <Section title="True FPY"><p className="text-2xl font-bold text-emerald-600">{summary.first_pass_yield.overall.true_fpy_pct}%</p></Section>
            <Section title="CAPAs Open"><p className="text-2xl font-bold text-slate-900">{summary.capas.open ?? 0}</p></Section>
          </div>
          <Section title="Recurring Findings">
            <ul className="text-sm text-slate-700">{summary.recurring_findings.map((f) => <li key={f.finding_type}>{f.finding_type}: {f.count}</li>)}</ul>
          </Section>
          <Section title="Root Causes">
            <ul className="text-sm text-slate-700">{Object.entries(summary.root_causes.overall).map(([k, v]) => <li key={k}>{k.replace(/_/g, " ")}: {v}</li>)}</ul>
          </Section>
          <Section title="Vendor Trends">
            <ul className="text-sm text-slate-700">{Object.entries(summary.vendor_trends).map(([v, t]) => <li key={v}>{v}: {t.received}/{t.total} received</li>)}</ul>
          </Section>
          <Section title="Manufacturer Trends">
            <ul className="text-sm text-slate-700">{Object.entries(summary.manufacturer_trends).map(([m, t]) => <li key={m}>{m}: {t.approved}/{t.total} approved baselines</li>)}</ul>
          </Section>
        </div>
      )}

      <p className="text-xs text-slate-400 italic">
        LumenAI Quality transforms perioperative quality feedback into structured SPD intelligence for decision
        support only. Classifications, correlations, draft root causes, and CAPA recommendations are potential
        associations, not causal determinations — human review and approval are required before finalizing any
        classification, root cause, or corrective action.
      </p>
    </div>
  );
}
