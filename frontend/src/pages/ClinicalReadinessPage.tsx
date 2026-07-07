import { useState, useEffect } from "react";
import { ShieldCheck } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface Dashboard {
  ready_for_packaging: number;
  requires_recleaning: number;
  requires_repair: number;
  remove_from_service: number;
  supervisor_pending: number;
  average_readiness_score: number | null;
  disposition_trends: Record<string, number>;
  total_inspections: number;
}

interface EnterpriseAnalytics {
  readiness_trends: { total_inspections: number; average_readiness_score: number | null };
  disposition_distribution: Record<string, number>;
  supervisor_overrides: Record<string, number>;
  repair_referrals: number;
  high_risk_instrument_families: { family: string; total: number; high_risk_count: number; high_risk_rate_pct: number | null }[];
  most_common_disposition_reasons: Record<string, string>;
}

function Stat({ label, value }: { label: string; value: number | string | null }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-2xl font-bold text-slate-900">{value ?? "—"}</div>
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

export default function ClinicalReadinessPage() {
  const { role } = useAuth();
  const isLeadership = role === "admin" || role === "spd_manager";
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [analytics, setAnalytics] = useState<EnterpriseAnalytics | null>(null);
  const [instrumentIdentity, setInstrumentIdentity] = useState("");
  const [conditionResult, setConditionResult] = useState<Record<string, unknown> | null>(null);
  const [conditionError, setConditionError] = useState("");

  useEffect(() => {
    apiFetch<Dashboard>("/api/clinical-readiness/dashboard").then(setDashboard);
    if (isLeadership) {
      apiFetch<EnterpriseAnalytics>("/api/clinical-readiness/enterprise-analytics").then(setAnalytics);
    }
  }, [isLeadership]);

  async function lookupInstrument() {
    setConditionError("");
    setConditionResult(null);
    try {
      const data = await apiFetch<Record<string, unknown>>(
        `/api/clinical-readiness/instrument-condition?instrument_identity=${encodeURIComponent(instrumentIdentity)}`
      );
      setConditionResult(data);
    } catch {
      setConditionError("No inspection history found for this instrument identity.");
    }
  }

  if (!dashboard) return <div className="p-6 text-sm text-slate-500">Loading…</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-6 w-6 text-teal-600" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Clinical Service Readiness</h1>
          <p className="text-sm text-slate-500 mt-1">
            Evidence-based disposition recommendations for the remainder of the reprocessing workflow.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Stat label="Ready for Packaging" value={dashboard.ready_for_packaging} />
        <Stat label="Requires Recleaning" value={dashboard.requires_recleaning} />
        <Stat label="Requires Repair" value={dashboard.requires_repair} />
        <Stat label="Remove From Service" value={dashboard.remove_from_service} />
        <Stat label="Supervisor Pending" value={dashboard.supervisor_pending} />
        <Stat label="Avg Readiness Score" value={dashboard.average_readiness_score} />
      </div>

      <Section title="Disposition Trends">
        <div className="flex flex-wrap gap-2">
          {Object.entries(dashboard.disposition_trends).map(([disp, count]) => (
            <span key={disp} className="text-xs font-medium px-2 py-1 rounded-full bg-slate-100 text-slate-700">
              {disp}: {count}
            </span>
          ))}
          {Object.keys(dashboard.disposition_trends).length === 0 && (
            <p className="text-sm text-slate-400">No dispositions recorded yet.</p>
          )}
        </div>
      </Section>

      <Section title="Instrument Condition Lookup">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="barcode:XXXX or udi:XXXX"
            value={instrumentIdentity}
            onChange={(e) => setInstrumentIdentity(e.target.value)}
            className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
          <button onClick={lookupInstrument} className="text-xs font-semibold px-3 py-1.5 rounded bg-teal-600 text-white">
            Look Up
          </button>
        </div>
        {conditionError && <p className="text-sm text-red-600 mt-2">{conditionError}</p>}
        {conditionResult && (
          <div className="mt-2 text-sm space-y-1">
            <p><span className="text-slate-500">Instrument:</span> {String(conditionResult.instrument_type)}</p>
            <p><span className="text-slate-500">Inspections:</span> {String(conditionResult.inspection_count)}</p>
            <p><span className="text-slate-500">Repair count:</span> {String(conditionResult.repair_count)}</p>
            <p><span className="text-slate-500">Corrosion history:</span> {String(conditionResult.corrosion_history_count)}</p>
            <p><span className="text-slate-500">Condition trend:</span> {String(conditionResult.condition_trend)}</p>
          </div>
        )}
      </Section>

      {isLeadership && analytics && (
        <>
          <Section title="Enterprise Readiness Analytics">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <Stat label="Total Inspections (180d)" value={analytics.readiness_trends.total_inspections} />
              <Stat label="Avg Readiness Score" value={analytics.readiness_trends.average_readiness_score} />
              <Stat label="Repair Referrals" value={analytics.repair_referrals} />
            </div>
          </Section>

          <Section title="Disposition Distribution">
            <div className="flex flex-wrap gap-2">
              {Object.entries(analytics.disposition_distribution).map(([disp, count]) => (
                <span key={disp} className="text-xs font-medium px-2 py-1 rounded-full bg-slate-100 text-slate-700">
                  {disp}: {count}
                </span>
              ))}
            </div>
          </Section>

          <Section title="Supervisor Overrides">
            <div className="flex flex-wrap gap-2">
              {Object.entries(analytics.supervisor_overrides).map(([action, count]) => (
                <span key={action} className="text-xs font-medium px-2 py-1 rounded-full bg-amber-100 text-amber-800">
                  {action.replace(/_/g, " ")}: {count}
                </span>
              ))}
              {Object.keys(analytics.supervisor_overrides).length === 0 && (
                <p className="text-sm text-slate-400">No supervisor overrides recorded yet.</p>
              )}
            </div>
          </Section>

          <Section title="High-Risk Instrument Families">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-400 text-xs">
                  <th className="py-1 pr-3">Family</th>
                  <th className="py-1 px-2">Total</th>
                  <th className="py-1 px-2">High-Risk Count</th>
                  <th className="py-1 px-2">High-Risk Rate</th>
                </tr>
              </thead>
              <tbody>
                {analytics.high_risk_instrument_families.map((f) => (
                  <tr key={f.family} className="border-t border-slate-100">
                    <td className="py-1 pr-3 font-medium capitalize">{f.family.replace(/_/g, " ")}</td>
                    <td className="py-1 px-2">{f.total}</td>
                    <td className="py-1 px-2">{f.high_risk_count}</td>
                    <td className="py-1 px-2">{f.high_risk_rate_pct == null ? "—" : `${f.high_risk_rate_pct}%`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          <Section title="Most Common Disposition Reasons">
            <div className="space-y-1.5 text-sm">
              {Object.entries(analytics.most_common_disposition_reasons).map(([disp, reason]) => (
                <p key={disp}><span className="font-medium">{disp}:</span> {reason}</p>
              ))}
            </div>
          </Section>
        </>
      )}
    </div>
  );
}
