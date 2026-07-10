/**
 * v3.5 — Project Beacon: Collaborative Quality Ecosystem & Industry
 * Intelligence Platform. Industry Collaboration Hub — composes the
 * participant directory (Section 1), Standards Collaboration Center
 * (Section 4), Clinical Evidence Exchange (Section 5), Manufacturer
 * Feedback Loop (Section 6), Repair Intelligence (Section 7), Industry
 * Benchmarking (Section 8), and Industry Advisory Board (Section 10).
 * Every output here is governance-approved, de-identified aggregate
 * intelligence — no organization's raw data or identity is disclosed.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Participant {
  tenant_id: string;
  organization_type: string;
  membership_tier: string;
  region: string;
}

interface HubSummary {
  participants_by_type: Record<string, Participant[]>;
  total_active_participants: number;
  disclaimer: string;
}

interface Publication {
  id: number;
  title: string;
  publication_type: string;
  version: string;
  status: string;
}

interface EvidenceSummaryResp {
  evidence_by_type: Record<string, unknown[]>;
  total_evidence_count: number;
  disclaimer: string;
}

interface FeedbackItem {
  id: number;
  title: string;
  category: string;
  approval_status: string;
}

interface RepairSnapshot {
  id: number;
  failure_category: string;
  facility_count: number;
  total_repairs: number;
  suppressed: boolean;
  quality_improvement_recommendation: string;
}

interface Benchmark {
  metric_name: string;
  n_facilities: number;
  suppressed: boolean;
  p50: number | null;
  p90: number | null;
}

interface AdvisoryMeeting {
  id: number;
  title: string;
  scheduled_at: string;
  status: string;
}

interface AdvisoryRecommendation {
  id: number;
  title: string;
  status: string;
  target_area: string;
}

const TABS = [
  "Collaboration Hub", "Standards Center", "Evidence Exchange",
  "Manufacturer Feedback", "Repair Intelligence", "Industry Benchmarks", "Advisory Board",
] as const;
type Tab = (typeof TABS)[number];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

export default function CollaborationHubDashboard() {
  const [tab, setTab] = useState<Tab>("Collaboration Hub");
  const [busy, setBusy] = useState(false);

  const [hub, setHub] = useState<HubSummary | null>(null);
  const [publications, setPublications] = useState<Publication[]>([]);
  const [evidence, setEvidence] = useState<EvidenceSummaryResp | null>(null);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [snapshots, setSnapshots] = useState<RepairSnapshot[]>([]);
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [meetings, setMeetings] = useState<AdvisoryMeeting[]>([]);
  const [recommendations, setRecommendations] = useState<AdvisoryRecommendation[]>([]);

  async function loadHub() {
    setBusy(true);
    try {
      setHub(await api.get<HubSummary>("/api/beacon/collaboration/hub"));
    } finally {
      setBusy(false);
    }
  }

  async function loadStandards() {
    setBusy(true);
    try {
      const result = await api.get<{ guidance: Publication[]; recommended_practices: Publication[] }>("/api/beacon/standards-center");
      setPublications([...result.guidance, ...result.recommended_practices]);
    } finally {
      setBusy(false);
    }
  }

  async function loadEvidence() {
    setBusy(true);
    try {
      setEvidence(await api.get<EvidenceSummaryResp>("/api/beacon/evidence-exchange"));
    } finally {
      setBusy(false);
    }
  }

  async function loadFeedback() {
    setBusy(true);
    try {
      const result = await api.get<{ feedback: FeedbackItem[] }>("/api/beacon/manufacturer-feedback");
      setFeedback(result.feedback);
    } finally {
      setBusy(false);
    }
  }

  async function loadRepairIntelligence() {
    setBusy(true);
    try {
      const result = await api.get<{ snapshots: RepairSnapshot[] }>("/api/beacon/repair-intelligence");
      setSnapshots(result.snapshots);
    } finally {
      setBusy(false);
    }
  }

  async function loadBenchmarks() {
    setBusy(true);
    try {
      const result = await api.get<{ benchmarks: Benchmark[] }>("/api/beacon/industry-benchmarks");
      setBenchmarks(result.benchmarks);
    } finally {
      setBusy(false);
    }
  }

  async function loadAdvisoryBoard() {
    setBusy(true);
    try {
      const result = await api.get<{ meetings: AdvisoryMeeting[]; recommendations: AdvisoryRecommendation[] }>("/api/beacon/advisory-board");
      setMeetings(result.meetings);
      setRecommendations(result.recommendations);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadHub();
  }, []);

  function selectTab(t: Tab) {
    setTab(t);
    if (t === "Standards Center") loadStandards();
    if (t === "Evidence Exchange") loadEvidence();
    if (t === "Manufacturer Feedback") loadFeedback();
    if (t === "Repair Intelligence") loadRepairIntelligence();
    if (t === "Industry Benchmarks") loadBenchmarks();
    if (t === "Advisory Board") loadAdvisoryBoard();
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Industry Collaboration Hub</h2>
        <p className="text-sm text-slate-500">
          Project Beacon — a collaborative quality ecosystem connecting hospitals, manufacturers, repair vendors,
          academic institutions, standards organizations, regulatory teams, and research partners. Every output is
          governance-approved, de-identified aggregate intelligence — potential associations only, never causation.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => selectTab(t)}
            className={`px-4 py-2 text-sm font-medium rounded-t-md ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {busy && <p className="text-sm text-slate-400">Loading…</p>}

      {tab === "Collaboration Hub" && hub && (
        <Section title={`Active Participants (${hub.total_active_participants})`}>
          <div className="space-y-3 text-sm">
            {Object.entries(hub.participants_by_type).map(([type, members]) => (
              <div key={type}>
                <p className="font-medium capitalize">{type.replace(/_/g, " ")} ({members.length})</p>
                <ul className="ml-4 text-xs text-slate-500 list-disc">
                  {members.map((m) => (
                    <li key={m.tenant_id}>{m.membership_tier} · {m.region || "unspecified region"}</li>
                  ))}
                  {members.length === 0 && <li className="list-none text-slate-400">None yet</li>}
                </ul>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-400 italic mt-3">{hub.disclaimer}</p>
        </Section>
      )}

      {tab === "Standards Center" && (
        <Section title="Standards & Recommended Practices">
          <ul className="space-y-1 text-sm">
            {publications.map((p) => (
              <li key={p.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{p.title}</span>
                <span className="text-xs text-slate-500">{p.publication_type} · v{p.version} · {p.status}</span>
              </li>
            ))}
            {publications.length === 0 && <p className="text-slate-400">No publications yet</p>}
          </ul>
        </Section>
      )}

      {tab === "Evidence Exchange" && evidence && (
        <Section title={`Clinical Evidence (${evidence.total_evidence_count} total)`}>
          <ul className="space-y-1 text-sm">
            {Object.entries(evidence.evidence_by_type).map(([type, items]) => (
              <li key={type} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium capitalize">{type.replace(/_/g, " ")}</span>
                <span className="text-xs text-slate-500">{items.length}</span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-slate-400 italic mt-3">{evidence.disclaimer}</p>
        </Section>
      )}

      {tab === "Manufacturer Feedback" && (
        <Section title="Governance-Approved Manufacturer Feedback">
          <ul className="space-y-1 text-sm">
            {feedback.map((f) => (
              <li key={f.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{f.title}</span>
                <span className="text-xs text-slate-500">{f.category.replace(/_/g, " ")}</span>
              </li>
            ))}
            {feedback.length === 0 && <p className="text-slate-400">No approved feedback yet</p>}
          </ul>
        </Section>
      )}

      {tab === "Repair Intelligence" && (
        <Section title="Repair Cause & Outcome Intelligence">
          <ul className="space-y-2 text-sm">
            {snapshots.map((s) => (
              <li key={s.id} className="border-b border-slate-100 pb-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium capitalize">{s.failure_category.replace(/_/g, " ")}</span>
                  <span className="text-xs text-slate-500">{s.suppressed ? "suppressed (k-anonymity)" : `${s.facility_count} facilities · ${s.total_repairs} repairs`}</span>
                </div>
                {!s.suppressed && <p className="text-slate-700 mt-1">{s.quality_improvement_recommendation}</p>}
              </li>
            ))}
            {snapshots.length === 0 && <p className="text-slate-400">No snapshots generated yet</p>}
          </ul>
        </Section>
      )}

      {tab === "Industry Benchmarks" && (
        <Section title="Industry Benchmarking (percentiles only, never raw org data)">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 uppercase">
                  <th className="pb-2 pr-4">Metric</th>
                  <th className="pb-2 pr-4">Organizations</th>
                  <th className="pb-2 pr-4">p50</th>
                  <th className="pb-2">p90</th>
                </tr>
              </thead>
              <tbody>
                {benchmarks.map((b) => (
                  <tr key={b.metric_name} className="border-t border-slate-100">
                    <td className="py-1.5 pr-4 font-medium capitalize">{b.metric_name.replace(/_/g, " ")}</td>
                    <td className="py-1.5 pr-4">{b.n_facilities}</td>
                    <td className="py-1.5 pr-4">{b.suppressed ? "suppressed" : b.p50}</td>
                    <td className="py-1.5">{b.suppressed ? "—" : b.p90}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {tab === "Advisory Board" && (
        <div className="space-y-4">
          <Section title="Upcoming & Past Meetings">
            <ul className="space-y-1 text-sm">
              {meetings.map((m) => (
                <li key={m.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                  <span className="font-medium">{m.title}</span>
                  <span className="text-xs text-slate-500">{m.scheduled_at} · {m.status}</span>
                </li>
              ))}
              {meetings.length === 0 && <p className="text-slate-400">No meetings scheduled yet</p>}
            </ul>
          </Section>
          <Section title="Roadmap Recommendations">
            <ul className="space-y-1 text-sm">
              {recommendations.map((r) => (
                <li key={r.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                  <span className="font-medium">{r.title}</span>
                  <span className="text-xs text-slate-500">{r.target_area} · {r.status}</span>
                </li>
              ))}
              {recommendations.length === 0 && <p className="text-slate-400">No recommendations yet</p>}
            </ul>
          </Section>
        </div>
      )}
    </div>
  );
}
