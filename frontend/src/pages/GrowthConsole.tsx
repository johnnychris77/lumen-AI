import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid,
} from "recharts";
import { apiFetch } from "@/lib/api";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchJSON(path: string) {
  const res = await apiFetch(`${path}`, { raw: true, headers: authHeaders() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-lg font-semibold text-gray-800">{title}</h2>
      {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
    </div>
  );
}

const STATUS_ORDER = ["prospect", "engaged", "active", "inactive"];
const STAGE_ORDER = ["pilot", "converting", "enterprise", "reference"];

function KpiGauges() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    fetchJSON("/api/growth/kpis").then(setData).catch((e) => setErr(String(e)));
  }, []);
  if (err) return <p className="text-sm text-red-600">{err}</p>;
  if (!data) return <p className="text-sm text-gray-500">Loading…</p>;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {data.kpis.map((k: any) => {
        const pct = k.target ? Math.min(100, (k.value / k.target) * 100) : 0;
        return (
          <div key={k.name} className="border rounded-lg p-3 bg-white">
            <div className="text-2xl font-bold text-gray-900">
              {k.value}{k.unit || ""}
            </div>
            <div className="text-xs text-gray-500 mb-2">{k.name}</div>
            <div className="h-2 bg-gray-100 rounded">
              <div className="h-2 bg-blue-500 rounded" style={{ width: `${pct}%` }} />
            </div>
            <div className="text-xs text-gray-400 mt-1">Target: {k.target}{k.unit || ""}</div>
          </div>
        );
      })}
    </div>
  );
}

function PartnershipPipeline() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  function load() {
    fetchJSON("/api/growth/partnerships").then(setData).catch((e) => setErr(String(e)));
  }
  useEffect(load, []);
  if (err) return <p className="text-sm text-red-600">{err}</p>;
  if (!data) return <p className="text-sm text-gray-500">Loading…</p>;
  const byStatus: Record<string, any[]> = {};
  for (const s of STATUS_ORDER) byStatus[s] = [];
  for (const p of data.partnerships) (byStatus[p.status] ||= []).push(p);
  return (
    <div>
      {data.escalations > 0 && (
        <p className="text-sm text-amber-700 mb-2">
          ⚠ {data.escalations} partnership(s) stalled in “engaged” &gt; 90 days.
        </p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {STATUS_ORDER.map((s) => (
          <div key={s} className="border rounded-lg bg-gray-50 p-2">
            <div className="text-xs font-semibold uppercase text-gray-500 mb-2">
              {s} ({byStatus[s].length})
            </div>
            {byStatus[s].map((p) => (
              <div key={p.id} className="bg-white border rounded p-2 mb-2 text-sm">
                <div className="font-medium">{p.partner_name}</div>
                <div className="text-xs text-gray-500">{p.partner_type} · {p.tier}</div>
                {p.review_overdue && (
                  <div className="text-xs text-red-600 mt-1">review overdue</div>
                )}
                {p.escalation && (
                  <div className="text-xs text-amber-600 mt-1">escalation</div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function ConversionFunnel() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    fetchJSON("/api/growth/conversion-funnel").then(setData).catch((e) => setErr(String(e)));
  }, []);
  if (err) return <p className="text-sm text-red-600">{err}</p>;
  if (!data) return <p className="text-sm text-gray-500">Loading…</p>;
  const chartData = STAGE_ORDER.map((s) => ({ stage: s, count: data.stages[s] || 0 }));
  return (
    <div>
      <p className="text-sm text-gray-600 mb-2">
        Pilot → Enterprise conversion:{" "}
        <span className="font-semibold">{data.pilot_to_enterprise_conversion_pct}%</span>
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData}>
          <XAxis dataKey="stage" />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="count" fill="#3b82f6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function MarketIntelligence() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    fetchJSON("/api/growth/market-intelligence/summary").then(setData).catch((e) => setErr(String(e)));
  }, []);
  if (err) return <p className="text-sm text-red-600">{err}</p>;
  if (!data) return <p className="text-sm text-gray-500">Loading…</p>;
  const net = data.benchmark_network;
  return (
    <div className="text-sm text-gray-700 space-y-2">
      <div>
        Partnerships: <strong>{data.partnerships.active}</strong> active /{" "}
        {data.partnerships.total} total
      </div>
      <div>
        References: <strong>{data.reference_program.public}</strong> public /{" "}
        {data.reference_program.total} total
      </div>
      {net.k_anonymity_met ? (
        <div>Benchmark network: {net.active_participants} active participants</div>
      ) : (
        <div className="text-amber-700">{net.message}</div>
      )}
      <p className="text-xs text-gray-400">{data.disclaimer}</p>
    </div>
  );
}

function BenchmarkTrend() {
  const [metric, setMetric] = useState("");
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  async function load() {
    setErr(null);
    try {
      setData(await fetchJSON(`/api/growth/benchmark-trends?metric=${encodeURIComponent(metric)}`));
    } catch (e) {
      setErr(String(e));
    }
  }
  return (
    <div>
      <div className="flex gap-2 mb-3">
        <input
          className="border rounded px-2 py-1 text-sm flex-1"
          placeholder="metric name (e.g. contamination_rate)"
          value={metric}
          onChange={(e) => setMetric(e.target.value)}
        />
        <button
          className="bg-blue-600 text-white text-sm px-3 py-1 rounded disabled:opacity-50"
          onClick={load}
          disabled={!metric}
        >
          Load
        </button>
      </div>
      {err && <p className="text-sm text-red-600">{err}</p>}
      {data && data.points.length > 0 && (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data.points}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="captured_at" hide />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="p50" stroke="#10b981" name="p50" />
            <Line type="monotone" dataKey="mean" stroke="#6366f1" name="mean" />
          </LineChart>
        </ResponsiveContainer>
      )}
      {data && data.points.length === 0 && (
        <p className="text-sm text-gray-500">
          No points above the k-anonymity floor ({data.suppressed_below_k} suppressed).
        </p>
      )}
    </div>
  );
}

export default function GrowthConsole() {
  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Growth Console</h1>
        <p className="text-sm text-gray-500">
          National expansion, strategic partnerships, and the reference-customer program.
          All network intelligence is anonymized and k-anonymity enforced.
        </p>
      </div>

      <section><SectionHeader title="Growth KPIs" subtitle="Year 1 targets" /><KpiGauges /></section>
      <section><SectionHeader title="Partnership Pipeline" /><PartnershipPipeline /></section>
      <section><SectionHeader title="Reference Conversion Funnel" /><ConversionFunnel /></section>
      <section><SectionHeader title="Market Intelligence" subtitle="Anonymized aggregates" /><MarketIntelligence /></section>
      <section><SectionHeader title="Benchmark Trend" subtitle="Anonymized network metric over time" /><BenchmarkTrend /></section>
    </div>
  );
}
