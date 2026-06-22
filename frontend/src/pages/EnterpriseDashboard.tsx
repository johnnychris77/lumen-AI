import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
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

const STATUS_COLOR: Record<string, string> = {
  green: "bg-green-100 text-green-800 border-green-300",
  amber: "bg-yellow-100 text-yellow-800 border-yellow-300",
  red: "bg-red-100 text-red-800 border-red-300",
  ready: "bg-green-100 text-green-800 border-green-300",
  conditional: "bg-yellow-100 text-yellow-800 border-yellow-300",
  not_ready: "bg-red-100 text-red-800 border-red-300",
};

const RAG_BAR: Record<string, string> = {
  green: "#16a34a",
  amber: "#eab308",
  red: "#dc2626",
};

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-lg font-semibold text-gray-800">{title}</h2>
      {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
    </div>
  );
}

function Disclaimer() {
  return (
    <p className="text-xs text-gray-400 italic mt-2">
      All quality signals are candidate indicators requiring human review. LumenAI
      does not claim FDA clearance or regulatory approval.
    </p>
  );
}

interface KPI {
  name: string;
  value: number | string;
  target: number | null;
  unit?: string;
  status: string;
}

export default function EnterpriseDashboard() {
  const [scorecard, setScorecard] = useState<any>(null);
  const [quality, setQuality] = useState<any>(null);
  const [readiness, setReadiness] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [sc, q, r] = await Promise.all([
          fetchJSON("/api/enterprise/dashboards/executive-scorecard").catch(() => null),
          fetchJSON("/api/enterprise/dashboards/system-quality").catch(() => null),
          fetchJSON("/api/enterprise/dashboards/readiness").catch(() => null),
        ]);
        setScorecard(sc);
        setQuality(q);
        setReadiness(r);
      } catch (e: any) {
        setError(e.message || "Failed to load");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div className="p-6 text-gray-500">Loading enterprise dashboards…</div>;
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>;

  const kpis: KPI[] = scorecard?.kpis || [];
  const facilities: any[] = readiness?.facilities || readiness?.scores || [];
  const outliers: any[] = quality?.outlier_facilities || [];
  const perFacility: any[] = quality?.per_facility || [];

  const readinessChart = facilities.map((f: any) => ({
    name: f.facility_id || f.facility_name || "facility",
    score: f.overall_score ?? f.composite_score ?? 0,
    status: f.readiness_status || f.status || "not_ready",
  }));

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Enterprise Dashboard</h1>
        <p className="text-sm text-gray-500">
          System-wide quality, executive scorecard, and facility readiness.
        </p>
      </div>

      {/* Executive scorecard */}
      <section>
        <SectionHeader
          title="Executive Scorecard"
          subtitle={scorecard?.overall_status ? `Overall status: ${scorecard.overall_status}` : undefined}
        />
        {kpis.length === 0 ? (
          <p className="text-sm text-gray-400">No scorecard data available.</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {kpis.map((k) => (
              <div
                key={k.name}
                className={`border rounded-lg p-3 ${STATUS_COLOR[k.status] || "bg-gray-50 border-gray-200"}`}
              >
                <div className="text-xs uppercase tracking-wide opacity-70">{k.name}</div>
                <div className="text-xl font-bold">
                  {k.value}
                  {k.unit && <span className="text-sm font-normal"> {k.unit}</span>}
                </div>
                {k.target != null && (
                  <div className="text-xs opacity-60">target: {k.target}</div>
                )}
              </div>
            ))}
          </div>
        )}
        <Disclaimer />
      </section>

      {/* Facility readiness */}
      <section>
        <SectionHeader
          title="Facility Readiness"
          subtitle="Composite score (0–100): ready ≥ 80, conditional ≥ 60."
        />
        {readinessChart.length === 0 ? (
          <p className="text-sm text-gray-400">No readiness scores computed yet.</p>
        ) : (
          <div className="h-72 w-full">
            <ResponsiveContainer>
              <BarChart data={readinessChart}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Bar dataKey="score">
                  {readinessChart.map((d, i) => (
                    <Cell
                      key={i}
                      fill={
                        d.score >= 80 ? RAG_BAR.green : d.score >= 60 ? RAG_BAR.amber : RAG_BAR.red
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      {/* System quality + outliers */}
      <section>
        <SectionHeader
          title="System Quality"
          subtitle={
            quality
              ? `Contamination rate: ${quality.contamination_rate_pct ?? quality.system_contamination_rate_pct ?? "—"}% (candidate signal)`
              : undefined
          }
        />
        {outliers.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-red-700 mb-1">
              Outlier facilities (contamination &gt; 2× system avg)
            </h3>
            <table className="w-full text-sm border">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-2">Facility</th>
                  <th className="text-right p-2">Inspections</th>
                  <th className="text-right p-2">Contamination %</th>
                </tr>
              </thead>
              <tbody>
                {outliers.map((o: any, i: number) => (
                  <tr key={i} className="border-t">
                    <td className="p-2">{o.facility_id || o.tenant_id}</td>
                    <td className="text-right p-2">{o.inspections ?? "—"}</td>
                    <td className="text-right p-2">{o.contamination_rate_pct ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {perFacility.length > 0 && (
          <p className="text-xs text-gray-500">
            {perFacility.length} facilities tracked across the system.
          </p>
        )}
        <Disclaimer />
      </section>
    </div>
  );
}
