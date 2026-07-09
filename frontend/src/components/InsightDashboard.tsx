/**
 * v3.3 — Project Insight: Predictive Clinical Intelligence & Quality
 * Forecasting. Enterprise Forecast Dashboard (Section 7) — every forecast
 * is a modeled projection from real historical data, never fabricated;
 * confidence indicators accompany every number. Advisory only — forecasts
 * assist proactive decision-making but do not replace human operational
 * or clinical judgment.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface QualityTrendForecast {
  metric: string;
  horizon: string;
  forecast_value: number | null;
  confidence_low: number | null;
  confidence_high: number | null;
  confidence_level: number;
  trend_direction: string;
  known_limitations: string[];
}

interface InstrumentLifecycleForecast {
  instrument_type: string;
  lifecycle_risk_tier: string;
  retirement_likelihood: number | null;
  repair_likelihood: number | null;
  health_score_trajectory: { horizon_days: number; projected_quality_score: number }[];
}

interface Recommendation {
  id: number;
  recommendation_type: string;
  title: string;
  reasoning: string;
  suggested_action: string;
  confidence_level: number;
  status: string;
}

interface ForecastDashboard {
  tenant_id: string;
  horizon: string;
  enterprise_quality_forecast: { metrics: QualityTrendForecast[]; confidence: number | null };
  risk_forecast: { instrument_lifecycle: InstrumentLifecycleForecast[]; elevated_risk_count: number; confidence: number | null };
  repair_forecast: { instrument_repair_likelihoods: { instrument_type: string; repair_likelihood: number | null }[]; confidence: number | null };
  instrument_health_forecast: { health_score_trajectories: InstrumentLifecycleForecast[]; confidence: number | null };
  inspection_volume_forecast: { inspection_workload: { forecast_value: number | null } | null; confidence: number | null };
  education_forecast: { new_signals: unknown[]; existing_competency_opportunities: unknown[] };
  disclaimer: string;
}

const TABS = ["Overview", "Quality Trends", "Instrument Health", "Recommendations"] as const;
type Tab = (typeof TABS)[number];
const HORIZONS = ["7_day", "30_day", "90_day", "rolling_annual"] as const;

function riskColor(tier: string): string {
  switch (tier) {
    case "critical": return "bg-red-100 text-red-800";
    case "high": return "bg-orange-100 text-orange-800";
    case "moderate": return "bg-amber-100 text-amber-800";
    default: return "bg-emerald-100 text-emerald-800";
  }
}

function directionColor(direction: string): string {
  if (direction === "increasing") return "text-red-600";
  if (direction === "decreasing") return "text-emerald-600";
  return "text-slate-500";
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

function ConfidenceBadge({ confidence }: { confidence: number | null | undefined }) {
  if (confidence === null || confidence === undefined) return <span className="text-xs text-slate-400">confidence: n/a</span>;
  return <span className="text-xs text-slate-500">confidence: {Math.round(confidence * 100)}%</span>;
}

export default function InsightDashboard() {
  const [tab, setTab] = useState<Tab>("Overview");
  const [horizon, setHorizon] = useState<(typeof HORIZONS)[number]>("30_day");
  const [busy, setBusy] = useState(false);
  const [dashboard, setDashboard] = useState<ForecastDashboard | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  async function loadDashboard() {
    setBusy(true);
    try {
      const result = await api.get<ForecastDashboard>(`/api/insight/dashboard?horizon=${horizon}`);
      setDashboard(result);
    } finally {
      setBusy(false);
    }
  }

  async function loadRecommendations() {
    setBusy(true);
    try {
      const result = await api.get<{ recommendations: Recommendation[] }>("/api/insight/recommendations");
      setRecommendations(result.recommendations);
    } finally {
      setBusy(false);
    }
  }

  async function generateRecommendations() {
    setBusy(true);
    try {
      const result = await api.post<{ recommendations: Recommendation[] }>("/api/insight/recommendations/generate");
      setRecommendations(result.recommendations);
    } finally {
      setBusy(false);
    }
  }

  async function actionRecommendation(id: number) {
    setBusy(true);
    try {
      await api.post(`/api/insight/recommendations/${id}/action`);
      await loadRecommendations();
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [horizon]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Project Insight</h2>
          <p className="text-sm text-slate-500">
            Predictive clinical intelligence and quality forecasting — evidence-based forecasts to help SPD
            leaders anticipate quality risks, operational demand, and instrument health before issues become
            significant. Advisory only; forecasts do not replace human operational or clinical decision-making.
          </p>
        </div>
        <select
          value={horizon}
          onChange={(e) => setHorizon(e.target.value as (typeof HORIZONS)[number])}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        >
          {HORIZONS.map((h) => <option key={h} value={h}>{h.replace(/_/g, " ")}</option>)}
        </select>
      </div>

      <div className="flex gap-1 border-b border-slate-200 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              if (t === "Recommendations") loadRecommendations();
            }}
            className={`px-4 py-2 text-sm font-medium rounded-t-md ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {busy && !dashboard && <p className="text-sm text-slate-400">Loading forecasts…</p>}

      {tab === "Overview" && dashboard && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Section title="Enterprise Quality Forecast">
              <p className="text-2xl font-bold text-slate-900">{dashboard.enterprise_quality_forecast.metrics.length} metrics</p>
              <ConfidenceBadge confidence={dashboard.enterprise_quality_forecast.confidence} />
            </Section>
            <Section title="Risk Forecast">
              <p className="text-2xl font-bold text-red-600">{dashboard.risk_forecast.elevated_risk_count}</p>
              <ConfidenceBadge confidence={dashboard.risk_forecast.confidence} />
            </Section>
            <Section title="Repair Forecast">
              <p className="text-2xl font-bold text-slate-900">{dashboard.repair_forecast.instrument_repair_likelihoods.length} types</p>
              <ConfidenceBadge confidence={dashboard.repair_forecast.confidence} />
            </Section>
            <Section title="Inspection Volume Forecast">
              <p className="text-2xl font-bold text-slate-900">{dashboard.inspection_volume_forecast.inspection_workload?.forecast_value ?? "—"}</p>
              <ConfidenceBadge confidence={dashboard.inspection_volume_forecast.confidence} />
            </Section>
          </div>

          <Section title="Instrument Health Forecast">
            <ul className="space-y-1 text-sm">
              {dashboard.instrument_health_forecast.health_score_trajectories.map((f) => (
                <li key={f.instrument_type} className="flex items-center justify-between border-b border-slate-100 pb-1">
                  <span className="font-medium">{f.instrument_type}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${riskColor(f.lifecycle_risk_tier)}`}>{f.lifecycle_risk_tier}</span>
                </li>
              ))}
              {dashboard.instrument_health_forecast.health_score_trajectories.length === 0 && <p className="text-slate-400">No instrument lifecycle forecasts yet</p>}
            </ul>
          </Section>

          <Section title="Education Forecast">
            <p className="text-sm text-slate-700">
              {dashboard.education_forecast.new_signals.length} new predictive signals ·{" "}
              {dashboard.education_forecast.existing_competency_opportunities.length} competency opportunities
            </p>
          </Section>
        </div>
      )}

      {tab === "Quality Trends" && dashboard && (
        <Section title="Quality Trend Forecasts">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 uppercase">
                  <th className="pb-2 pr-4">Metric</th>
                  <th className="pb-2 pr-4">Trend</th>
                  <th className="pb-2 pr-4">Forecast</th>
                  <th className="pb-2 pr-4">Confidence Interval</th>
                  <th className="pb-2">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.enterprise_quality_forecast.metrics.map((m) => (
                  <tr key={m.metric} className="border-t border-slate-100">
                    <td className="py-1.5 pr-4 font-medium capitalize">{m.metric.replace(/_/g, " ")}</td>
                    <td className={`py-1.5 pr-4 font-semibold ${directionColor(m.trend_direction)}`}>{m.trend_direction}</td>
                    <td className="py-1.5 pr-4">{m.forecast_value ?? "—"}</td>
                    <td className="py-1.5 pr-4">{m.confidence_low ?? "—"} – {m.confidence_high ?? "—"}</td>
                    <td className="py-1.5">{Math.round(m.confidence_level * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {tab === "Instrument Health" && dashboard && (
        <Section title="Instrument Lifecycle Forecasts">
          <ul className="space-y-2 text-sm">
            {dashboard.risk_forecast.instrument_lifecycle.map((f) => (
              <li key={f.instrument_type} className="border-b border-slate-100 pb-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{f.instrument_type}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${riskColor(f.lifecycle_risk_tier)}`}>{f.lifecycle_risk_tier}</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Retirement likelihood: {f.retirement_likelihood ?? "—"} · Repair likelihood: {f.repair_likelihood ?? "—"}
                </p>
              </li>
            ))}
            {dashboard.risk_forecast.instrument_lifecycle.length === 0 && <p className="text-slate-400">No instrument lifecycle forecasts yet</p>}
          </ul>
        </Section>
      )}

      {tab === "Recommendations" && (
        <div className="space-y-3">
          <button onClick={generateRecommendations} disabled={busy} className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
            Generate Recommendations
          </button>
          <Section title="Predictive Recommendations">
            <ul className="space-y-2 text-sm">
              {recommendations.map((r) => (
                <li key={r.id} className="border-b border-slate-100 pb-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{r.title}</span>
                    {r.status === "open" && (
                      <button onClick={() => actionRecommendation(r.id)} disabled={busy} className="rounded-md bg-slate-700 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50">
                        Mark Actioned
                      </button>
                    )}
                  </div>
                  <p className="text-slate-700 mt-1">{r.reasoning}</p>
                  <p className="text-slate-500 text-xs mt-1">Suggested action: {r.suggested_action}</p>
                  <p className="text-slate-400 text-xs mt-1">Confidence: {Math.round(r.confidence_level * 100)}%</p>
                </li>
              ))}
              {recommendations.length === 0 && <p className="text-slate-400">No recommendations yet</p>}
            </ul>
          </Section>
        </div>
      )}

      {dashboard && <p className="text-xs text-slate-400 italic">{dashboard.disclaimer}</p>}
    </div>
  );
}
