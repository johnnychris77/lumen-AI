import { useEffect, useState } from "react";

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

function ContaminationPanel() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJSON("/api/pilot-analytics/contamination-trends?days=30")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <p className="text-sm text-gray-400">Loading...</p>;

  const breakdown = data.breakdown as Record<string, number>;
  const sorted = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);

  return (
    <div>
      <SectionHeader
        title="Contamination Trends (30d)"
        subtitle={`${data.total_inspections} inspections · ${data.contamination_rate_pct}% contamination rate`}
      />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {sorted.map(([type, count]) => (
          <div key={type} className="bg-white border rounded-lg p-3 text-center">
            <p className="text-xl font-bold text-gray-800">{count}</p>
            <p className="text-xs text-gray-500 mt-1 capitalize">{type.replace(/_/g, " ")}</p>
          </div>
        ))}
      </div>
      <Disclaimer text={data.note} />
    </div>
  );
}

function ScorecardPanel() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJSON("/api/pilot-analytics/executive-scorecard")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

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
      <SectionHeader
        title="Executive Scorecard"
        subtitle={`Overall status · ${data.period_days}-day window`}
      />
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

function ROIPanel() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJSON("/api/pilot-analytics/roi?days=90")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <p className="text-sm text-gray-400">Loading...</p>;

  const ve = data.value_estimates;

  return (
    <div>
      <SectionHeader
        title="ROI Framework (90d)"
        subtitle="Estimated value — requires site validation before financial reporting"
      />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: "Labor Savings", value: ve.labor_savings_usd },
          { label: "Reprocessing Avoidance", value: ve.reprocessing_avoidance_usd },
          { label: "Cancellation Avoidance", value: ve.surgical_cancellation_avoidance_usd },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white border rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-gray-900">
              ${value.toLocaleString("en-US", { minimumFractionDigits: 0 })}
            </p>
            <p className="text-sm text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>
      <div className="mt-3 bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
        <p className="text-sm text-blue-700">
          Total Estimated Value:{" "}
          <span className="font-bold text-blue-900">
            ${ve.total_estimated_value_usd.toLocaleString()}
          </span>
          {" "}· Annualised: ${data.annualised_estimate_usd.toLocaleString()}
        </p>
      </div>
      {(data.disclaimers as string[]).map((d, i) => (
        <Disclaimer key={i} text={d} />
      ))}
    </div>
  );
}

function ClinicalOutcomesPanel() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJSON("/api/pilot-analytics/clinical-outcomes?days=90")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <p className="text-sm text-gray-400">Loading...</p>;

  const qi = data.quality_indicators;
  const trend = data.trend_vs_prior_period;
  const qf = data.quality_framework;

  return (
    <div>
      <SectionHeader
        title="Clinical Quality Indicators (90d)"
        subtitle="Sterile processing quality metrics — not clinical diagnoses"
      />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
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
      </div>
      <div className="flex gap-3 text-sm">
        <span className="bg-gray-100 text-gray-700 rounded px-2 py-1">
          Trend vs prior period: <strong>{trend.trend.replace(/_/g, " ")}</strong>
        </span>
        <span className="bg-gray-100 text-gray-700 rounded px-2 py-1">
          Benchmark ({qf.benchmark_contamination_rate_pct}%): <strong>{qf.status.replace(/_/g, " ")}</strong>
        </span>
      </div>
      {(data.disclaimers as string[]).map((d, i) => (
        <Disclaimer key={i} text={d} />
      ))}
    </div>
  );
}

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
          Download Inspections CSV
        </button>
        <button
          onClick={() => download("/api/pilot-analytics/export/report.json", "pilot-report.json")}
          disabled={downloading}
          className="px-4 py-2 bg-gray-700 text-white rounded hover:bg-gray-800 disabled:opacity-50 text-sm font-medium"
        >
          Download Full Report (JSON)
        </button>
      </div>
      <Disclaimer text="No PHI is included in exports. Human review is required before use in financial or clinical reporting." />
    </div>
  );
}

export default function PilotAnalyticsDashboard() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pilot Analytics & Outcomes</h1>
          <p className="text-sm text-gray-500 mt-1">
            P15 — ROI framework, clinical quality indicators, executive scorecard.
            All outputs require human review. Association does not imply causation.
          </p>
        </div>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <ScorecardPanel />
        </section>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <ContaminationPanel />
        </section>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <ROIPanel />
        </section>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <ClinicalOutcomesPanel />
        </section>

        <section className="bg-white rounded-xl border p-6 shadow-sm">
          <ExportPanel />
        </section>
      </div>
    </div>
  );
}
