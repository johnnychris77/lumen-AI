import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchJSON(path: string) {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function postJSON(path: string, body?: object) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

interface KPI {
  name: string;
  value: number | string;
  target: number | null;
  unit: string;
  status: string;
}

const STATUS_COLOR: Record<string, string> = {
  green: "bg-green-100 text-green-800 border-green-300",
  amber: "bg-yellow-100 text-yellow-800 border-yellow-300",
  red: "bg-red-100 text-red-800 border-red-300",
  tracked: "bg-gray-100 text-gray-700 border-gray-300",
  estimated: "bg-blue-100 text-blue-700 border-blue-300",
};

const CONTAMINATION_COLORS: Record<string, string> = {
  blood: "#ef4444",
  bone: "#f97316",
  tissue: "#eab308",
  debris: "#84cc16",
  corrosion: "#06b6d4",
  crack: "#8b5cf6",
  insulation_damage: "#ec4899",
  other: "#94a3b8",
};

function KPICard({ kpi }: { kpi: KPI }) {
  const color = STATUS_COLOR[kpi.status] ?? STATUS_COLOR.tracked;
  return (
    <div className={`rounded-lg border p-4 ${color}`}>
      <p className="text-sm font-medium">{kpi.name}</p>
      <p className="text-2xl font-bold mt-1">
        {typeof kpi.value === "number" ? kpi.value.toLocaleString() : kpi.value}
        <span className="text-sm font-normal ml-1">{kpi.unit}</span>
      </p>
      {kpi.target !== null && (
        <p className="text-xs mt-1 opacity-70">Target: {kpi.target} {kpi.unit}</p>
      )}
      <span className="inline-block text-xs font-semibold uppercase mt-2 px-2 py-0.5 rounded">
        {kpi.status}
      </span>
    </div>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}

function Disclaimer({ text }: { text: string }) {
  return (
    <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2 mt-2">
      ⚠ {text}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Site filter selector
// ---------------------------------------------------------------------------

function SiteFilter({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [sites, setSites] = useState<string[]>([]);

  useEffect(() => {
    fetchJSON("/api/pilot-analytics/site-breakdown?days=90")
      .then((d) => setSites((d.sites as { site_name: string }[]).map((s) => s.site_name)))
      .catch(() => {});
  }, []);

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="text-sm border rounded px-2 py-1 bg-white"
    >
      <option value="">All sites</option>
      {sites.map((s) => (
        <option key={s} value={s}>{s}</option>
      ))}
    </select>
  );
}

// ---------------------------------------------------------------------------
// Contamination trends panel — with chart
// ---------------------------------------------------------------------------

function ContaminationPanel() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [site, setSite] = useState("");
  const [days, setDays] = useState(30);

  useEffect(() => {
    const params = new URLSearchParams({ days: String(days) });
    if (site) params.set("site_name", site);
    fetchJSON(`/api/pilot-analytics/contamination-trends?${params}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [days, site]);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;

  const breakdownData = data
    ? Object.entries(data.breakdown as Record<string, number>)
        .map(([type, count]) => ({ type: type.replace(/_/g, " "), count, fill: CONTAMINATION_COLORS[type] ?? "#94a3b8" }))
        .sort((a, b) => b.count - a.count)
    : [];

  const weeklyData = data?.weekly_trend ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <SectionHeader
          title="Contamination Trends"
          subtitle={data ? `${data.total_inspections} inspections · ${data.contamination_rate_pct}% contamination rate` : "Loading..."}
        />
        <div className="flex gap-2 items-center">
          <SiteFilter value={site} onChange={setSite} />
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="text-sm border rounded px-2 py-1 bg-white">
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
        </div>
      </div>

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wide">By type</p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={breakdownData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="type" type="category" tick={{ fontSize: 11 }} width={110} />
                <Tooltip />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {breakdownData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wide">Weekly stain events</p>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={weeklyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="week_ending" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="stain_count" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
      {data && <Disclaimer text={data.note} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Executive scorecard
// ---------------------------------------------------------------------------

function ScorecardPanel() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    fetchJSON("/api/pilot-analytics/executive-scorecard")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  async function downloadPDF() {
    setDownloading(true);
    try {
      const res = await fetch(`${API_BASE}/api/pilot-analytics/export/scorecard.pdf`, { headers: authHeaders() });
      if (!res.ok) throw new Error(`${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "pilot-scorecard.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`PDF export failed: ${e}`);
    } finally {
      setDownloading(false);
    }
  }

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <p className="text-sm text-gray-400">Loading...</p>;

  const overallColor =
    data.overall_status === "green"
      ? "text-green-700 bg-green-50 border-green-200"
      : data.overall_status === "amber"
      ? "text-yellow-700 bg-yellow-50 border-yellow-200"
      : "text-red-700 bg-red-50 border-red-200";

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <SectionHeader title="Executive Scorecard" subtitle={`${data.period_days}-day window`} />
        <button
          onClick={downloadPDF}
          disabled={downloading}
          className="px-3 py-1.5 bg-gray-800 text-white rounded text-sm hover:bg-gray-900 disabled:opacity-50"
        >
          Export PDF
        </button>
      </div>
      <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border font-semibold text-sm mb-4 ${overallColor}`}>
        Overall: {data.overall_status.toUpperCase()}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {(data.kpis as KPI[]).map((kpi) => (
          <KPICard key={kpi.name} kpi={kpi} />
        ))}
      </div>
      <Disclaimer text={data.disclaimer} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// ROI framework
// ---------------------------------------------------------------------------

function ROIPanel() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [baselineDays, setBaselineDays] = useState("");

  function load() {
    const params = new URLSearchParams({ days: "90" });
    if (baselineDays) params.set("baseline_period_days", baselineDays);
    fetchJSON(`/api/pilot-analytics/roi?${params}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <p className="text-sm text-gray-400">Loading...</p>;

  const ve = data.value_estimates;
  const bc = data.baseline_comparison;

  const chartData = [
    { name: "Labor savings", value: ve.labor_savings_usd, fill: "#3b82f6" },
    { name: "Reprocessing", value: ve.reprocessing_avoidance_usd, fill: "#10b981" },
    { name: "Cancellation", value: ve.surgical_cancellation_avoidance_usd, fill: "#f59e0b" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <SectionHeader title="ROI Framework (90d)" subtitle="Estimated value — requires site validation" />
        <div className="flex gap-2 items-center">
          <select
            value={baselineDays}
            onChange={(e) => setBaselineDays(e.target.value)}
            className="text-sm border rounded px-2 py-1 bg-white"
          >
            <option value="">No baseline comparison</option>
            <option value="90">vs. prior 90 days</option>
            <option value="30">vs. prior 30 days</option>
          </select>
          <button onClick={load} className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
            Apply
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v: number) => `$${v.toLocaleString()}`} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-3">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
            <p className="text-sm text-blue-700">Total estimated value</p>
            <p className="text-2xl font-bold text-blue-900">${ve.total_estimated_value_usd.toLocaleString()}</p>
            <p className="text-xs text-blue-600">Annualised: ${ve && data.annualised_estimate_usd.toLocaleString()}</p>
          </div>
          {bc && (
            <div className="bg-gray-50 border rounded-lg p-3 text-sm">
              <p className="font-medium text-gray-700">vs. prior {bc.baseline_period_days} days</p>
              <p className="text-gray-600">Volume change: <strong>{bc.volume_change_pct !== null ? `${bc.volume_change_pct > 0 ? "+" : ""}${bc.volume_change_pct}%` : "N/A"}</strong></p>
              <p className="text-gray-600">Baseline inspections: <strong>{bc.baseline_inspections}</strong></p>
            </div>
          )}
        </div>
      </div>

      {(data.disclaimers as string[]).map((d: string, i: number) => (
        <Disclaimer key={i} text={d} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Site breakdown drill-down
// ---------------------------------------------------------------------------

function SiteBreakdownPanel() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJSON("/api/pilot-analytics/site-breakdown?days=30")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <p className="text-sm text-gray-400">Loading...</p>;

  const chartData = (data.sites as any[]).slice(0, 8).map((s: any) => ({
    name: s.site_name.length > 16 ? s.site_name.slice(0, 14) + "…" : s.site_name,
    total: s.total_inspections,
    contamination: s.contamination_events,
  }));

  return (
    <div>
      <SectionHeader title="Site Breakdown (30d)" subtitle={`${data.site_count} sites reporting`} />
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="total" fill="#93c5fd" name="Total" radius={[4, 4, 0, 0]} />
          <Bar dataKey="contamination" fill="#ef4444" name="Contamination" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <Disclaimer text={data.note} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Alert thresholds panel
// ---------------------------------------------------------------------------

function AlertsPanel() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(5.0);
  const [volMin, setVolMin] = useState(15);

  function load() {
    fetchJSON(`/api/pilot-analytics/alerts?days=7&contamination_threshold_pct=${threshold}&weekly_volume_min=${volMin}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <p className="text-sm text-gray-400">Loading...</p>;

  const severityColor: Record<string, string> = {
    high: "bg-red-50 border-red-300 text-red-800",
    medium: "bg-yellow-50 border-yellow-300 text-yellow-800",
    low: "bg-blue-50 border-blue-300 text-blue-700",
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <SectionHeader title="Alert Thresholds (7d)" subtitle="Configurable quality tripwires" />
        <div className="flex gap-2 items-center flex-wrap">
          <label className="text-xs text-gray-600">
            Contamination %&nbsp;
            <input type="number" min={0.1} max={100} step={0.5} value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-16 text-sm border rounded px-1 py-0.5" />
          </label>
          <label className="text-xs text-gray-600">
            Vol min&nbsp;
            <input type="number" min={1} value={volMin}
              onChange={(e) => setVolMin(Number(e.target.value))}
              className="w-14 text-sm border rounded px-1 py-0.5" />
          </label>
          <button onClick={load} className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
            Check
          </button>
        </div>
      </div>

      {data.alert_count === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-green-800 text-sm font-medium">
          ✓ No alerts — all metrics within thresholds
        </div>
      ) : (
        <div className="space-y-2">
          {(data.alerts as any[]).map((a: any, i: number) => (
            <div key={i} className={`border rounded-lg p-3 ${severityColor[a.severity] ?? ""}`}>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase px-1.5 py-0.5 rounded bg-white bg-opacity-50">
                  {a.severity}
                </span>
                <span className="text-sm font-medium">{a.message}</span>
              </div>
              <p className="text-xs mt-1 opacity-80">{a.recommendation}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pulse survey widget
// ---------------------------------------------------------------------------

function PulseSurveyPanel() {
  const [ease, setEase] = useState(0);
  const [useful, setUseful] = useState(0);
  const [recommend, setRecommend] = useState(0);
  const [submitted, setSubmitted] = useState(false);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    fetchJSON("/api/pilot-analytics/survey/summary").then(setSummary).catch(() => {});
  }, [submitted]);

  async function submit() {
    if (!ease || !useful || !recommend) return;
    try {
      await fetchJSON(`/api/pilot-analytics/survey/submit?ease=${ease}&useful=${useful}&recommend=${recommend}`);
      setSubmitted(true);
    } catch (e) {
      alert(`Submit failed: ${e}`);
    }
  }

  const RatingRow = ({ label, value, onChange }: { label: string; value: number; onChange: (n: number) => void }) => (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-600 w-40">{label}</span>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            onClick={() => onChange(n)}
            className={`w-8 h-8 rounded text-sm font-medium border transition-colors ${
              value >= n ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-500 border-gray-300 hover:border-blue-400"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div>
      <SectionHeader title="Weekly Pulse Survey" subtitle="Takes 30 seconds — helps improve the pilot" />
      {submitted ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-800 text-sm">
          ✓ Response recorded. Thank you!
        </div>
      ) : (
        <div className="space-y-3">
          <RatingRow label="Ease of use" value={ease} onChange={setEase} />
          <RatingRow label="Useful for my work" value={useful} onChange={setUseful} />
          <RatingRow label="Likelihood to recommend" value={recommend} onChange={setRecommend} />
          <button
            onClick={submit}
            disabled={!ease || !useful || !recommend}
            className="mt-2 px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-40"
          >
            Submit feedback
          </button>
        </div>
      )}
      {summary && summary.response_count > 0 && (
        <div className="mt-4 flex gap-4 text-sm text-gray-600">
          <span>Responses: <strong>{summary.response_count}</strong></span>
          <span>Mean score: <strong>{summary.mean_satisfaction_score} / 5</strong></span>
          <span className={summary.on_track ? "text-green-600" : "text-amber-600"}>
            {summary.on_track ? "✓ On track" : "⚠ Below target (3.5)"}
          </span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Clinical outcomes panel
// ---------------------------------------------------------------------------

function ClinicalOutcomesPanel() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [site, setSite] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ days: "90" });
    if (site) params.set("site_name", site);
    fetchJSON(`/api/pilot-analytics/clinical-outcomes?${params}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [site]);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <p className="text-sm text-gray-400">Loading...</p>;

  const qi = data.quality_indicators;
  const trend = data.trend_vs_prior_period;
  const qf = data.quality_framework;

  const severityData = Object.entries(qi.severity_distribution as Record<string, number>).map(
    ([k, v]) => ({ name: k, value: v, fill: { critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#22c55e" }[k] ?? "#94a3b8" })
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <SectionHeader title="Clinical Quality Indicators (90d)" subtitle="Sterile processing metrics — not clinical diagnoses" />
        <SiteFilter value={site} onChange={setSite} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: "Total Inspections", value: qi.total_inspections },
            { label: "Contamination Events", value: qi.contamination_events },
            { label: "Contamination Rate", value: `${qi.contamination_rate_pct}%` },
            { label: "High-Risk Instruments", value: qi.high_risk_instruments },
          ].map(({ label, value }) => (
            <div key={label} className="bg-white border rounded-lg p-3 text-center">
              <p className="text-xl font-bold text-gray-800">{value}</p>
              <p className="text-xs text-gray-500 mt-1">{label}</p>
            </div>
          ))}
          <div className="col-span-2 flex gap-2 text-xs flex-wrap">
            <span className="bg-gray-100 text-gray-700 rounded px-2 py-1">
              Trend: <strong>{trend.trend.replace(/_/g, " ")}</strong>
            </span>
            <span className="bg-gray-100 text-gray-700 rounded px-2 py-1">
              Benchmark: <strong>{qf.status.replace(/_/g, " ")}</strong>
            </span>
          </div>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wide">Severity distribution</p>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={severityData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {severityData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      {(data.disclaimers as string[]).map((d: string, i: number) => (
        <Disclaimer key={i} text={d} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Export panel
// ---------------------------------------------------------------------------

function ExportPanel() {
  const [downloading, setDownloading] = useState(false);

  async function download(path: string, filename: string) {
    setDownloading(true);
    try {
      const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
      if (!res.ok) throw new Error(`${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`Export failed: ${e}`);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div>
      <SectionHeader title="Export Pilot Reports" subtitle="All exports are audit-logged" />
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={() => download("/api/pilot-analytics/export/inspections.csv", "pilot-inspections.csv")}
          disabled={downloading}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
        >
          Inspections CSV
        </button>
        <button
          onClick={() => download("/api/pilot-analytics/export/report.json", "pilot-report.json")}
          disabled={downloading}
          className="px-4 py-2 bg-gray-700 text-white rounded hover:bg-gray-800 disabled:opacity-50 text-sm font-medium"
        >
          Full Report (JSON)
        </button>
        <button
          onClick={() => download("/api/pilot-analytics/export/scorecard.pdf", "pilot-scorecard.pdf")}
          disabled={downloading}
          className="px-4 py-2 bg-red-700 text-white rounded hover:bg-red-800 disabled:opacity-50 text-sm font-medium"
        >
          Scorecard PDF
        </button>
      </div>
      <Disclaimer text="No PHI is included in exports. Human review required before use in financial or clinical reporting." />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root page
// ---------------------------------------------------------------------------

export default function PilotAnalyticsDashboard() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pilot Analytics & Outcomes</h1>
          <p className="text-sm text-gray-500 mt-1">
            ROI framework · clinical quality indicators · executive scorecard · site drill-down.
            All outputs require human review. Association does not imply causation.
          </p>
        </div>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <AlertsPanel />
        </section>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <ScorecardPanel />
        </section>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <ContaminationPanel />
        </section>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <SiteBreakdownPanel />
        </section>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <ROIPanel />
        </section>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <ClinicalOutcomesPanel />
        </section>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <PulseSurveyPanel />
        </section>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <ExportPanel />
        </section>
      </div>
    </div>
  );
}
