import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
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

interface ZonePerf {
  zone: string;
  is_high_risk_zone: boolean;
  case_count: number;
  missed_count: number;
  false_positive_count: number;
  miss_rate: number | null;
  accuracy: number | null;
  mean_confidence: number | null;
  override_count: number;
  override_rate: number | null;
}

interface FamilyPerf {
  instrument_family: string;
  case_count: number;
  missed_count: number;
  accuracy: number | null;
}

interface Dashboard {
  total_inspections_reviewed: number;
  ai_supervisor_agreement_rate: number | null;
  false_positives: number;
  false_negatives: number;
  high_risk_findings_detected: number;
  inconclusive_cases: number;
  model_confidence_trend: { created_at: string | null; ai_confidence: number }[];
  zone_performance: ZonePerf[];
  instrument_family_performance: FamilyPerf[];
}

interface SafetyQueue {
  false_negatives: { count: number };
  high_confidence_disagreement: { count: number };
  low_confidence_critical_findings: { count: number };
  missing_baseline_cases: { count: number };
  missing_required_zones: { count: number };
  critical_missed_findings: { count: number; cases: { id: number; finding_type: string; anatomy_zone: string }[] };
}

interface GoNoGo {
  decision: "GO" | "NO-GO";
  reasons: string[];
  criteria: Record<string, unknown>;
}

function pct(v: number | null): string {
  return v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`;
}

function KPI({ label, value, tone }: { label: string; value: string | number; tone?: "danger" | "warning" | "ok" }) {
  const toneClass =
    tone === "danger"
      ? "border-red-300 bg-red-50 text-red-800"
      : tone === "warning"
      ? "border-amber-300 bg-amber-50 text-amber-800"
      : tone === "ok"
      ? "border-green-300 bg-green-50 text-green-800"
      : "border-gray-200 bg-white text-gray-900";
  return (
    <div className={`rounded-lg border p-4 ${toneClass}`}>
      <p className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}

export default function PilotValidationDashboard() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [safety, setSafety] = useState<SafetyQueue | null>(null);
  const [goNoGo, setGoNoGo] = useState<GoNoGo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchJSON("/api/pilot-validation/dashboard"),
      fetchJSON("/api/pilot-validation/safety-queue"),
      fetchJSON("/api/pilot-validation/go-no-go"),
    ])
      .then(([d, s, g]) => {
        setDashboard(d);
        setSafety(s);
        setGoNoGo(g);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-gray-500">Loading pilot validation data…</div>;
  if (error) return <div className="p-6 text-red-600">Failed to load pilot validation data: {error}</div>;
  if (!dashboard) return null;

  const agreementTone =
    dashboard.ai_supervisor_agreement_rate === null
      ? undefined
      : dashboard.ai_supervisor_agreement_rate >= 0.85
      ? "ok"
      : dashboard.ai_supervisor_agreement_rate >= 0.7
      ? "warning"
      : "danger";

  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pilot Validation Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Real-world pilot validation of AI-assisted inspection against trained SPD supervisor review.
        </p>
      </div>

      {goNoGo && (
        <div
          className={`rounded-lg border p-4 ${
            goNoGo.decision === "GO"
              ? "border-green-300 bg-green-50"
              : "border-red-300 bg-red-50"
          }`}
        >
          <p className="text-sm font-semibold uppercase tracking-wide">
            Expansion readiness: <span className={goNoGo.decision === "GO" ? "text-green-700" : "text-red-700"}>{goNoGo.decision}</span>
          </p>
          {goNoGo.reasons.length > 0 && (
            <ul className="text-sm mt-2 list-disc list-inside text-gray-700">
              {goNoGo.reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <section>
        <SectionHeader title="Pilot Performance Summary" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPI label="Inspections reviewed" value={dashboard.total_inspections_reviewed} />
          <KPI label="AI/supervisor agreement" value={pct(dashboard.ai_supervisor_agreement_rate)} tone={agreementTone} />
          <KPI label="False positives" value={dashboard.false_positives} />
          <KPI label="False negatives" value={dashboard.false_negatives} tone={dashboard.false_negatives > 0 ? "warning" : "ok"} />
          <KPI label="High-risk findings detected" value={dashboard.high_risk_findings_detected} />
          <KPI label="Inconclusive cases" value={dashboard.inconclusive_cases} />
        </div>
      </section>

      <section>
        <SectionHeader title="Model Confidence Trend" subtitle="AI confidence across reviewed cases, oldest to newest." />
        <div className="h-64 bg-white border rounded-lg p-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dashboard.model_confidence_trend.map((p, i) => ({ ...p, idx: i }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="idx" tick={false} label={{ value: "Case sequence", position: "insideBottom", offset: -2 }} />
              <YAxis domain={[0, 1]} />
              <Tooltip formatter={(v: number) => v.toFixed(2)} />
              <Line type="monotone" dataKey="ai_confidence" stroke="#2563eb" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section>
        <SectionHeader
          title="Zone Performance"
          subtitle="Missed findings, override rate, and confidence by high-retention instrument zone."
        />
        <div className="overflow-x-auto bg-white border rounded-lg">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="text-left px-3 py-2">Zone</th>
                <th className="text-right px-3 py-2">Cases</th>
                <th className="text-right px-3 py-2">Missed</th>
                <th className="text-right px-3 py-2">Miss rate</th>
                <th className="text-right px-3 py-2">Accuracy</th>
                <th className="text-right px-3 py-2">Mean confidence</th>
                <th className="text-right px-3 py-2">Overrides</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.zone_performance.map((z) => (
                <tr key={z.zone} className="border-t">
                  <td className="px-3 py-2 font-medium text-gray-900">
                    {z.zone}
                    {z.is_high_risk_zone && (
                      <span className="ml-2 text-xs text-red-600 font-semibold">HIGH-RISK</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right">{z.case_count}</td>
                  <td className="px-3 py-2 text-right">{z.missed_count}</td>
                  <td className="px-3 py-2 text-right">{pct(z.miss_rate)}</td>
                  <td className="px-3 py-2 text-right">{pct(z.accuracy)}</td>
                  <td className="px-3 py-2 text-right">
                    {z.mean_confidence === null ? "—" : z.mean_confidence.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right">{z.override_count}</td>
                </tr>
              ))}
              {dashboard.zone_performance.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-6 text-center text-gray-400">
                    No zone-tagged pilot cases yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <SectionHeader title="Instrument-Family Performance" />
        <div className="overflow-x-auto bg-white border rounded-lg">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="text-left px-3 py-2">Instrument family</th>
                <th className="text-right px-3 py-2">Cases</th>
                <th className="text-right px-3 py-2">Missed</th>
                <th className="text-right px-3 py-2">Accuracy</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.instrument_family_performance.map((f) => (
                <tr key={f.instrument_family} className="border-t">
                  <td className="px-3 py-2 font-medium text-gray-900">{f.instrument_family}</td>
                  <td className="px-3 py-2 text-right">{f.case_count}</td>
                  <td className="px-3 py-2 text-right">{f.missed_count}</td>
                  <td className="px-3 py-2 text-right">{pct(f.accuracy)}</td>
                </tr>
              ))}
              {dashboard.instrument_family_performance.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-gray-400">
                    No instrument-family data yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {safety && (
        <section>
          <SectionHeader title="Safety Review Queue" subtitle="Cases requiring supervisor or QA follow-up." />
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <KPI label="False negatives" value={safety.false_negatives.count} tone={safety.false_negatives.count > 0 ? "danger" : "ok"} />
            <KPI label="High-conf. disagreement" value={safety.high_confidence_disagreement.count} tone="warning" />
            <KPI label="Low-conf. critical findings" value={safety.low_confidence_critical_findings.count} tone="warning" />
            <KPI label="Missing baseline" value={safety.missing_baseline_cases.count} />
            <KPI label="Missing required zone" value={safety.missing_required_zones.count} />
          </div>
          {safety.critical_missed_findings.count > 0 && (
            <div className="mt-4 rounded-lg border border-red-300 bg-red-50 p-4">
              <p className="text-sm font-semibold text-red-800 mb-2">
                Critical missed findings ({safety.critical_missed_findings.count})
              </p>
              <ul className="text-sm text-red-700 list-disc list-inside">
                {safety.critical_missed_findings.cases.map((c) => (
                  <li key={c.id}>
                    Case #{c.id} — {c.finding_type} in {c.anatomy_zone || "unspecified zone"}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
        ⚠ All metrics on this page are quality indicators computed from supervisor-adjudicated pilot cases.
        They require human review and do not constitute FDA clearance, regulatory approval, or a clinical diagnosis.
      </p>
    </div>
  );
}
