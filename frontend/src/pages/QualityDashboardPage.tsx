import { useState, useEffect, useCallback } from "react";
import { BarChart3 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Tab =
  | "overview" | "trends" | "anatomy" | "instruments"
  | "technicians" | "supervisors" | "root-cause" | "improvement";

function Stat({ label, value, suffix = "%" }: { label: string; value: number | null; suffix?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-2xl font-bold text-slate-900">{value == null ? "—" : `${value}${suffix}`}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

const CHANGE_STYLE: Record<string, string> = {
  improvement: "text-emerald-700 bg-emerald-50 border-emerald-200",
  regression: "text-red-700 bg-red-50 border-red-200",
  stable: "text-slate-600 bg-slate-50 border-slate-200",
  insufficient_data: "text-slate-400 bg-slate-50 border-slate-200",
};

export default function QualityDashboardPage() {
  const { role } = useAuth();
  const isLeadership = role === "admin" || role === "spd_manager";
  const [tab, setTab] = useState<Tab>("overview");

  const TABS: { id: Tab; label: string; leadershipOnly?: boolean }[] = [
    { id: "overview", label: "Overview" },
    { id: "trends", label: "Finding Trends" },
    { id: "anatomy", label: "Anatomy Risk" },
    { id: "instruments", label: "Instrument Performance" },
    { id: "technicians", label: "Technician Quality", leadershipOnly: true },
    { id: "supervisors", label: "Supervisor Quality", leadershipOnly: true },
    { id: "root-cause", label: "Root Cause & CAPA" },
    { id: "improvement", label: "Improvement Tracker", leadershipOnly: true },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="mb-6 flex items-center gap-2">
        <BarChart3 className="h-6 w-6 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Quality Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            Operational quality intelligence and continuous improvement — every inspection, aggregated.
          </p>
        </div>
      </div>

      <div className="flex gap-1 border-b border-slate-200 mb-6 overflow-x-auto">
        {TABS.filter((t) => !t.leadershipOnly || isLeadership).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors ${
              tab === t.id ? "border-b-2 border-blue-600 text-blue-600" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && <OverviewTab />}
      {tab === "trends" && <TrendsTab />}
      {tab === "anatomy" && <AnatomyTab />}
      {tab === "instruments" && <InstrumentsTab />}
      {tab === "technicians" && isLeadership && <TechniciansTab />}
      {tab === "supervisors" && isLeadership && <SupervisorsTab />}
      {tab === "root-cause" && <RootCauseTab isLeadership={isLeadership} />}
      {tab === "improvement" && isLeadership && <ImprovementTab />}
    </div>
  );
}

// ── Overview: KPIs + benchmark + executive score ─────────────────────────────
function OverviewTab() {
  const { role } = useAuth();
  const isLeadership = role === "admin" || role === "spd_manager";
  const [summary, setSummary] = useState<Record<string, number | null> | null>(null);
  const [benchmark, setBenchmark] = useState<{
    comparison_current_vs_previous_month: Record<string, string>;
  } | null>(null);
  const [score, setScore] = useState<{ score: number | null; note: string } | null>(null);

  useEffect(() => {
    apiFetch<Record<string, number | null>>("/api/quality/dashboard").then(setSummary);
    apiFetch<typeof benchmark>("/api/quality/benchmark").then(setBenchmark);
    if (isLeadership) {
      apiFetch<typeof score>("/api/quality/executive-score").then(setScore);
    }
  }, [isLeadership]);

  if (!summary) return <p className="text-sm text-slate-400">Loading…</p>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <Stat label="Inspection Volume" value={summary.inspection_volume} suffix="" />
        <Stat label="Pass Rate" value={summary.pass_rate_pct} />
        <Stat label="Reclean Rate" value={summary.reclean_rate_pct} />
        <Stat label="Repair Rate" value={summary.repair_rate_pct} />
        <Stat label="Remove From Service" value={summary.remove_from_service_rate_pct} />
        <Stat label="Supervisor Override" value={summary.supervisor_override_rate_pct} />
        <Stat label="Baseline Compliance" value={summary.baseline_compliance_pct} />
        <Stat label="Coverage Compliance" value={summary.coverage_compliance_pct} />
        <Stat label="AI Confidence" value={summary.ai_confidence_trend_pct} />
      </div>

      {isLeadership && score && (
        <Section title="Executive Quality Score">
          <div className="text-4xl font-extrabold text-indigo-700">{score.score ?? "—"}<span className="text-lg text-slate-400">/100</span></div>
          <p className="text-xs text-slate-500 mt-1">{score.note}</p>
        </Section>
      )}

      {benchmark && (
        <Section title="Benchmark: Current Month vs Previous Month">
          <div className="flex flex-wrap gap-2">
            {Object.entries(benchmark.comparison_current_vs_previous_month).map(([metric, change]) => (
              <span
                key={metric}
                className={`text-xs font-medium px-2 py-1 rounded border ${CHANGE_STYLE[change] ?? CHANGE_STYLE.stable}`}
              >
                {metric.replace(/_pct$/, "").replace(/_/g, " ")}: {change.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

// ── Finding Trends ────────────────────────────────────────────────────────────
function TrendsTab() {
  const [granularity, setGranularity] = useState("monthly");
  const [data, setData] = useState<{ totals: Record<string, number> } | null>(null);

  const load = useCallback(() => {
    apiFetch<typeof data>(`/api/quality/finding-trends?granularity=${granularity}`).then(setData);
  }, [granularity]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {["daily", "weekly", "monthly", "quarterly", "yearly"].map((g) => (
          <button
            key={g}
            onClick={() => setGranularity(g)}
            className={`text-xs px-3 py-1.5 rounded-full border ${granularity === g ? "bg-blue-600 text-white border-blue-600" : "border-slate-300 text-slate-600"}`}
          >
            {g}
          </button>
        ))}
      </div>
      {data && (
        <Section title={`Finding Totals (${granularity})`}>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {Object.entries(data.totals).map(([type, count]) => (
              <div key={type} className="rounded border border-slate-200 px-3 py-2">
                <div className="text-xs text-slate-500 capitalize">{type.replace(/_/g, " ")}</div>
                <div className="text-lg font-bold text-slate-900">{count}</div>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

// ── Anatomy Risk ──────────────────────────────────────────────────────────────
function AnatomyTab() {
  const [data, setData] = useState<{
    highest_risk_anatomy_zones: { zone: string; count: number }[];
    most_frequent_contamination_zones: { zone: string; count: number }[];
    most_frequent_damage_zones: { zone: string; count: number }[];
    coverage_incomplete_pct: number | null;
  } | null>(null);

  useEffect(() => { apiFetch<typeof data>("/api/quality/anatomy-risk").then(setData); }, []);
  if (!data) return <p className="text-sm text-slate-400">Loading…</p>;

  const ZoneList = ({ items }: { items: { zone: string; count: number }[] }) => (
    <ul className="space-y-1 text-sm">
      {items.length === 0 && <li className="text-slate-400">No data yet.</li>}
      {items.map((z) => (
        <li key={z.zone} className="flex justify-between">
          <span className="capitalize text-slate-700">{z.zone}</span>
          <span className="font-medium text-slate-900">{z.count}</span>
        </li>
      ))}
    </ul>
  );

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <Section title="Highest-Risk Anatomy Zones"><ZoneList items={data.highest_risk_anatomy_zones} /></Section>
      <Section title="Most Frequent Contamination"><ZoneList items={data.most_frequent_contamination_zones} /></Section>
      <Section title="Most Frequent Damage"><ZoneList items={data.most_frequent_damage_zones} /></Section>
      <Section title="Coverage Incomplete Rate">
        <div className="text-2xl font-bold text-slate-900">{data.coverage_incomplete_pct ?? "—"}%</div>
        <p className="text-xs text-slate-400 mt-1">Share of inspections with incomplete/insufficient zone coverage.</p>
      </Section>
    </div>
  );
}

// ── Instrument Family Performance ─────────────────────────────────────────────
function InstrumentsTab() {
  const [data, setData] = useState<{ families: Record<string, unknown>[] } | null>(null);
  useEffect(() => { apiFetch<typeof data>("/api/quality/instrument-performance").then(setData); }, []);
  if (!data) return <p className="text-sm text-slate-400">Loading…</p>;

  return (
    <Section title="Instrument Family Performance">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400 text-xs">
              <th className="py-1 pr-3">Family</th>
              <th className="py-1 px-2">Inspections</th>
              <th className="py-1 px-2">Pass Rate</th>
              <th className="py-1 px-2">Failure Rate</th>
              <th className="py-1 px-2">Repair Rate</th>
              <th className="py-1 px-2">Supervisor Intervention</th>
            </tr>
          </thead>
          <tbody>
            {data.families.map((f) => (
              <tr key={String(f.family)} className="border-t border-slate-100">
                <td className="py-1 pr-3 font-medium capitalize">{String(f.family).replace(/_/g, " ")}</td>
                <td className="py-1 px-2">{String(f.inspection_count)}</td>
                <td className="py-1 px-2">{f.pass_rate_pct == null ? "—" : `${f.pass_rate_pct}%`}</td>
                <td className="py-1 px-2">{f.failure_rate_pct == null ? "—" : `${f.failure_rate_pct}%`}</td>
                <td className="py-1 px-2">{f.repair_rate_pct == null ? "—" : `${f.repair_rate_pct}%`}</td>
                <td className="py-1 px-2">{f.supervisor_intervention_rate_pct == null ? "—" : `${f.supervisor_intervention_rate_pct}%`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

// ── Technician Quality (leadership only) ──────────────────────────────────────
function TechniciansTab() {
  const [data, setData] = useState<{ technicians: Record<string, unknown>[] } | null>(null);
  useEffect(() => { apiFetch<typeof data>("/api/quality/technician-quality").then(setData); }, []);
  if (!data) return <p className="text-sm text-slate-400">Loading…</p>;

  return (
    <Section title="Technician Quality (Leadership Only)">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400 text-xs">
              <th className="py-1 pr-3">Technician</th>
              <th className="py-1 px-2">Inspections</th>
              <th className="py-1 px-2">Avg Coverage</th>
              <th className="py-1 px-2">Avg AI Confidence</th>
              <th className="py-1 px-2">Supervisor Agreement</th>
              <th className="py-1 px-2">Corrections</th>
              <th className="py-1 px-2">Training Progress</th>
            </tr>
          </thead>
          <tbody>
            {data.technicians.map((t) => (
              <tr key={String(t.technician)} className="border-t border-slate-100">
                <td className="py-1 pr-3 font-medium">{String(t.technician)}</td>
                <td className="py-1 px-2">{String(t.inspection_count)}</td>
                <td className="py-1 px-2">{t.avg_coverage_pct == null ? "—" : `${t.avg_coverage_pct}%`}</td>
                <td className="py-1 px-2">{t.avg_ai_confidence_pct == null ? "—" : `${t.avg_ai_confidence_pct}%`}</td>
                <td className="py-1 px-2">{t.supervisor_agreement_pct == null ? "—" : `${t.supervisor_agreement_pct}%`}</td>
                <td className="py-1 px-2">{String(t.supervisor_corrections)}</td>
                <td className="py-1 px-2">{t.training_progress_pct == null ? "—" : `${t.training_progress_pct}%`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

// ── Supervisor Quality ────────────────────────────────────────────────────────
function SupervisorsTab() {
  const [data, setData] = useState<{
    supervisors: Record<string, unknown>[];
    department_trends: Record<string, unknown>[];
  } | null>(null);
  useEffect(() => { apiFetch<typeof data>("/api/quality/supervisor-quality").then(setData); }, []);
  if (!data) return <p className="text-sm text-slate-400">Loading…</p>;

  return (
    <div className="space-y-4">
      <Section title="Supervisor Quality">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-400 text-xs">
                <th className="py-1 pr-3">Supervisor</th>
                <th className="py-1 px-2">Workload</th>
                <th className="py-1 px-2">Override Frequency</th>
                <th className="py-1 px-2">Education Provided</th>
                <th className="py-1 px-2">Agreement with AI</th>
              </tr>
            </thead>
            <tbody>
              {data.supervisors.map((s) => (
                <tr key={String(s.reviewer)} className="border-t border-slate-100">
                  <td className="py-1 pr-3 font-medium">{String(s.reviewer)}</td>
                  <td className="py-1 px-2">{String(s.review_workload)}</td>
                  <td className="py-1 px-2">{s.override_frequency_pct == null ? "—" : `${s.override_frequency_pct}%`}</td>
                  <td className="py-1 px-2">{String(s.education_provided_count)}</td>
                  <td className="py-1 px-2">{s.agreement_with_ai_pct == null ? "—" : `${s.agreement_with_ai_pct}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
      <Section title="Department Trends">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {data.department_trends.map((d) => (
            <div key={String(d.department)} className="rounded border border-slate-200 px-3 py-2">
              <div className="text-xs text-slate-500">{String(d.department)}</div>
              <div className="text-sm text-slate-900">{String(d.inspection_count)} inspections</div>
              <div className="text-xs text-slate-500">Pass {d.pass_rate_pct == null ? "—" : `${d.pass_rate_pct}%`}</div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

// ── Root Cause & CAPA ─────────────────────────────────────────────────────────
function RootCauseTab({ isLeadership }: { isLeadership: boolean }) {
  const [trends, setTrends] = useState<{ overall: Record<string, number> } | null>(null);
  const [suggestions, setSuggestions] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    apiFetch<typeof trends>("/api/quality/root-cause-trends").then(setTrends);
    if (isLeadership) {
      apiFetch<{ suggestions: Record<string, unknown>[] }>("/api/quality/capa-suggestions")
        .then((d) => setSuggestions(d.suggestions));
    }
  }, [isLeadership]);

  async function createCapa(suggestion: Record<string, unknown>) {
    await apiFetch("/api/quality/capa-suggestions/create", { method: "POST", body: suggestion });
    alert("CAPA created.");
  }

  return (
    <div className="space-y-4">
      {trends && (
        <Section title="Recurring Root Causes">
          <div className="flex flex-wrap gap-2">
            {Object.entries(trends.overall).length === 0 && <p className="text-sm text-slate-400">No root causes assigned yet.</p>}
            {Object.entries(trends.overall).map(([cause, count]) => (
              <span key={cause} className="text-xs font-medium px-2 py-1 rounded-full bg-slate-100 text-slate-700">
                {cause.replace(/_/g, " ")}: {count}
              </span>
            ))}
          </div>
        </Section>
      )}
      {isLeadership && (
        <Section title="CAPA Suggestions">
          {suggestions.length === 0 && <p className="text-sm text-slate-400">No recurring patterns yet.</p>}
          <div className="space-y-2">
            {suggestions.map((s, i) => (
              <div key={i} className="rounded border border-amber-200 bg-amber-50 px-3 py-2">
                <p className="text-sm font-semibold text-amber-900">{String(s.trigger)} ({String(s.occurrences)}x)</p>
                <p className="text-sm text-amber-800">{String(s.recommendation)}</p>
                <button
                  onClick={() => createCapa(s)}
                  className="mt-2 text-xs font-semibold px-3 py-1 rounded bg-amber-600 text-white hover:bg-amber-700"
                >
                  Create CAPA
                </button>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

// ── Continuous Improvement Tracker ───────────────────────────────────────────
function ImprovementTab() {
  const [initiatives, setInitiatives] = useState<Record<string, unknown>[]>([]);
  const [form, setForm] = useState({ initiative: "", owner: "", target_date: "", expected_impact: "" });

  const load = useCallback(() => {
    apiFetch<{ initiatives: Record<string, unknown>[] }>("/api/quality/improvement-initiatives")
      .then((d) => setInitiatives(d.initiatives));
  }, []);
  useEffect(() => { load(); }, [load]);

  async function submit() {
    if (!form.initiative.trim()) return;
    await apiFetch("/api/quality/improvement-initiatives", {
      method: "POST",
      body: { ...form, target_date: form.target_date || null },
    });
    setForm({ initiative: "", owner: "", target_date: "", expected_impact: "" });
    load();
  }

  async function markCompleted(id: number) {
    const actual = prompt("Actual impact observed?") ?? "";
    await apiFetch(`/api/quality/improvement-initiatives/${id}`, {
      method: "PATCH",
      body: { status: "completed", actual_impact: actual },
    });
    load();
  }

  return (
    <div className="space-y-4">
      <Section title="New Initiative">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <input className="rounded border border-slate-300 px-2 py-1.5 text-sm" placeholder="Initiative"
            value={form.initiative} onChange={(e) => setForm((f) => ({ ...f, initiative: e.target.value }))} />
          <input className="rounded border border-slate-300 px-2 py-1.5 text-sm" placeholder="Owner"
            value={form.owner} onChange={(e) => setForm((f) => ({ ...f, owner: e.target.value }))} />
          <input type="date" className="rounded border border-slate-300 px-2 py-1.5 text-sm"
            value={form.target_date} onChange={(e) => setForm((f) => ({ ...f, target_date: e.target.value }))} />
          <input className="rounded border border-slate-300 px-2 py-1.5 text-sm" placeholder="Expected impact"
            value={form.expected_impact} onChange={(e) => setForm((f) => ({ ...f, expected_impact: e.target.value }))} />
        </div>
        <button onClick={submit} className="mt-2 text-xs font-semibold px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700">
          Add Initiative
        </button>
      </Section>
      <Section title="Initiatives">
        <div className="space-y-2">
          {initiatives.length === 0 && <p className="text-sm text-slate-400">No initiatives yet.</p>}
          {initiatives.map((i) => (
            <div key={String(i.id)} className="rounded border border-slate-200 px-3 py-2 flex items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-slate-800">{String(i.initiative)}</p>
                <p className="text-xs text-slate-500">
                  {String(i.owner)} · {String(i.target_date ?? "no target date")} · <span className="capitalize">{String(i.status)}</span>
                </p>
                {!!i.actual_impact && <p className="text-xs text-emerald-700 mt-1">Actual: {String(i.actual_impact)}</p>}
              </div>
              {i.status !== "completed" && (
                <button onClick={() => markCompleted(Number(i.id))} className="text-xs font-semibold px-2 py-1 rounded bg-emerald-600 text-white">
                  Mark Completed
                </button>
              )}
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
