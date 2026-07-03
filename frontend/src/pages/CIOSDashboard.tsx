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

interface Dashboard {
  system_health: { overall_status: string; degraded_agents: string[]; agent_count: number };
  inspection_throughput: number;
  average_inspection_time_minutes: number | null;
  coverage_rate: number | null;
  supervisor_agreement_rate: number | null;
  ai_confidence: number | null;
  governance_versions: Record<string, string>;
  digital_twin_health: { available: boolean; snapshot_count: number };
  most_common_findings: { key: string; count: number }[];
  most_common_zones: { zone: string; missed_count: number; case_count: number }[];
  enterprise_risk_index: number | null;
  readiness_rate: number | null;
}

function pct(v: number | null): string {
  return v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`;
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}

function KPI({ label, value, tone }: { label: string; value: string | number; tone?: "danger" | "warning" | "ok" }) {
  const toneClass =
    tone === "danger" ? "border-red-300 bg-red-50 text-red-800"
    : tone === "warning" ? "border-amber-300 bg-amber-50 text-amber-800"
    : tone === "ok" ? "border-green-300 bg-green-50 text-green-800"
    : "border-gray-200 bg-white text-gray-900";
  return (
    <div className={`rounded-lg border p-4 ${toneClass}`}>
      <p className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}

export default function CIOSDashboard() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchJSON("/api/cios/dashboard")
      .then(setDashboard)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-gray-500">Loading Clinical Intelligence Operating System dashboard…</div>;
  if (error) return <div className="p-6 text-red-600">Failed to load CIOS dashboard: {error}</div>;
  if (!dashboard) return null;

  const riskTone =
    dashboard.enterprise_risk_index === null ? undefined
    : dashboard.enterprise_risk_index <= 20 ? "ok"
    : dashboard.enterprise_risk_index <= 45 ? "warning"
    : "danger";

  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">LumenAI Clinical Intelligence Operating System</h1>
        <p className="text-sm text-gray-500 mt-1">
          Every inspection follows one governed, explainable, anatomy-aware, knowledge-driven workflow
          before an instrument is approved to proceed to packaging and sterilization.
        </p>
      </div>

      <section>
        <SectionHeader title="System Health" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPI
            label="Overall status"
            value={dashboard.system_health.overall_status.toUpperCase()}
            tone={dashboard.system_health.overall_status === "ok" ? "ok" : "danger"}
          />
          <KPI label="Active agents" value={dashboard.system_health.agent_count} />
          <KPI label="Inspection throughput" value={dashboard.inspection_throughput} />
          <KPI
            label="Avg. inspection time"
            value={dashboard.average_inspection_time_minutes !== null ? `${dashboard.average_inspection_time_minutes} min` : "—"}
          />
        </div>
      </section>

      <section>
        <SectionHeader title="Clinical Quality Indicators" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPI label="Readiness rate" value={pct(dashboard.readiness_rate)} />
          <KPI label="Coverage rate" value={pct(dashboard.coverage_rate)} />
          <KPI label="Supervisor agreement" value={pct(dashboard.supervisor_agreement_rate)} />
          <KPI label="AI confidence" value={dashboard.ai_confidence !== null ? dashboard.ai_confidence.toFixed(1) : "—"} />
          <KPI
            label="Enterprise risk index"
            value={dashboard.enterprise_risk_index !== null ? dashboard.enterprise_risk_index : "—"}
            tone={riskTone}
          />
          <KPI
            label="Digital twin"
            value={dashboard.digital_twin_health.available ? `${dashboard.digital_twin_health.snapshot_count} snapshots` : "Unavailable"}
            tone={dashboard.digital_twin_health.available ? "ok" : undefined}
          />
        </div>
      </section>

      <section>
        <SectionHeader title="Platform Governance" subtitle="Every inspection references these versions." />
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
          {Object.entries(dashboard.governance_versions).map(([key, value]) => (
            <div key={key} className="rounded-lg border bg-white p-3 text-sm">
              <p className="text-xs text-gray-500 uppercase">{key.replace(/_/g, " ")}</p>
              <p className="font-semibold text-gray-900">{value}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <SectionHeader title="Most Common Findings" />
        <div className="rounded-lg border bg-white divide-y">
          {dashboard.most_common_findings.map((f) => (
            <div key={f.key} className="p-3 text-sm flex justify-between">
              <span>{f.key}</span>
              <span className="text-gray-500">{f.count}</span>
            </div>
          ))}
          {dashboard.most_common_findings.length === 0 && (
            <div className="p-6 text-center text-gray-400">No findings yet.</div>
          )}
        </div>
      </section>

      <section>
        <SectionHeader title="Most Missed Anatomy Zones" />
        <div className="rounded-lg border bg-white divide-y">
          {dashboard.most_common_zones.map((z) => (
            <div key={z.zone} className="p-3 text-sm flex justify-between">
              <span>{z.zone}</span>
              <span className="text-gray-500">{z.missed_count}/{z.case_count} missed</span>
            </div>
          ))}
          {dashboard.most_common_zones.length === 0 && (
            <div className="p-6 text-center text-gray-400">No pilot validation ground truth yet.</div>
          )}
        </div>
      </section>

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
        ⚠ The Enterprise Risk Index is a composite indicator (readiness rate, coverage rate, supervisor
        agreement), not a validated clinical risk score. All figures require human review before action.
      </p>
    </div>
  );
}
