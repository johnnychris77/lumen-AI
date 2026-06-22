import React, { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "";
const headers = () => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${localStorage.getItem("token") || ""}`,
});

function DisclaimerBanner() {
  return (
    <div className="rounded border border-amber-300 bg-amber-50 px-4 py-2 text-xs text-amber-800 mb-4">
      <strong>Decision-Support Tool:</strong> All outputs require human review. Scores do not
      constitute clinical assessments, regulatory findings, or safety certifications. Causation is
      never implied — outputs represent quality signals and investigation candidates only.
    </div>
  );
}

function HumanReviewBadge() {
  return (
    <span className="inline-block rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 border border-amber-200">
      Human Review Required
    </span>
  );
}

type ReadinessTier = "green" | "yellow" | "amber" | "red";
const TIER_COLORS: Record<ReadinessTier, string> = {
  green: "bg-green-100 text-green-800 border-green-200",
  yellow: "bg-yellow-100 text-yellow-800 border-yellow-200",
  amber: "bg-orange-100 text-orange-800 border-orange-200",
  red: "bg-red-100 text-red-800 border-red-200",
};

function TierBadge({ tier }: { tier: string }) {
  const cls = TIER_COLORS[tier as ReadinessTier] ?? "bg-slate-100 text-slate-700 border-slate-200";
  return (
    <span className={`inline-block rounded border px-2 py-0.5 text-xs font-semibold capitalize ${cls}`}>
      {tier}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    active: "bg-green-100 text-green-800",
    in_maintenance: "bg-yellow-100 text-yellow-800",
    quarantined: "bg-red-100 text-red-800",
    retired: "bg-slate-100 text-slate-600",
    lost: "bg-red-200 text-red-900",
  };
  const cls = map[status] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium capitalize ${cls}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

type Tab = "dashboard" | "instruments" | "readiness" | "registry" | "forecasts";

export default function GlobalInfrastructureConsole() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const TABS: { id: Tab; label: string }[] = [
    { id: "dashboard", label: "Dashboard" },
    { id: "instruments", label: "Instrument Identities" },
    { id: "readiness", label: "Readiness Index" },
    { id: "registry", label: "Quality Registry" },
    { id: "forecasts", label: "Predictive Forecasts" },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Global Surgical Quality Infrastructure</h1>
        <p className="text-sm text-slate-500 mt-1">
          Instrument digital identity, surgical readiness scoring, lifecycle tracking, and predictive quality intelligence.
        </p>
      </div>
      <DisclaimerBanner />
      <div className="flex gap-1 border-b border-slate-200 mb-6 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors ${
              tab === t.id
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "dashboard" && <DashboardTab />}
      {tab === "instruments" && <InstrumentsTab />}
      {tab === "readiness" && <ReadinessTab />}
      {tab === "registry" && <RegistryTab />}
      {tab === "forecasts" && <ForecastsTab />}
    </div>
  );
}

// --- Dashboard Tab ---
function DashboardTab() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/infrastructure/dashboard`, { headers: headers() })
      .then((r) => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;
  if (!data) return <p className="text-sm text-red-600">Failed to load dashboard.</p>;

  const summary = (data.summary as Record<string, unknown>) ?? {};
  const metrics = (data.network_metrics as Record<string, unknown>) ?? {};

  const kpis = [
    { label: "Total Instruments", value: summary.total_instruments as number ?? 0 },
    { label: "Active", value: summary.active_instruments as number ?? 0 },
    { label: "Quarantined", value: summary.quarantined_instruments as number ?? 0 },
    { label: "In Maintenance", value: summary.in_maintenance_instruments as number ?? 0 },
    { label: "Verified Identities", value: summary.verified_identities as number ?? 0 },
    { label: "Registry Entries", value: summary.registry_entries as number ?? 0 },
    { label: "Active API Credentials", value: summary.active_api_credentials as number ?? 0 },
    { label: "Active Forecasts", value: summary.active_forecasts as number ?? 0 },
  ];

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {kpis.map((k) => (
          <div key={k.label} className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-xs text-slate-500">{k.label}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{k.value}</p>
          </div>
        ))}
      </div>

      <h2 className="text-sm font-semibold text-slate-700 mb-3">Network Quality Metrics</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        {Object.entries(metrics).map(([k, v]) => (
          <div key={k} className="rounded border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-500 capitalize">{k.replace(/_/g, " ")}</p>
            <p className="text-lg font-semibold text-slate-800 mt-0.5">
              {typeof v === "number" ? (v < 1 ? (v * 100).toFixed(1) + "%" : v.toFixed(1)) : String(v)}
            </p>
          </div>
        ))}
      </div>
      <HumanReviewBadge />
    </div>
  );
}

// --- Instruments Tab ---
function InstrumentsTab() {
  const [instruments, setInstruments] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    fetch(`${API}/api/infrastructure/instruments`, { headers: headers() })
      .then((r) => r.json())
      .then((d) => setInstruments(d.instruments ?? d ?? []))
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter
    ? instruments.filter(
        (i) =>
          String(i.instrument_type ?? "").toLowerCase().includes(filter.toLowerCase()) ||
          String(i.lifecycle_status ?? "").toLowerCase().includes(filter.toLowerCase()) ||
          String(i.udi ?? "").toLowerCase().includes(filter.toLowerCase())
      )
    : instruments;

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div>
      <div className="flex gap-3 mb-4">
        <input
          type="text"
          placeholder="Filter by type, status, UDI…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm w-64"
        />
        <span className="text-xs text-slate-500 self-center">{filtered.length} instruments</span>
      </div>
      <div className="overflow-x-auto rounded border border-slate-200">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              {["Type", "Lifecycle Status", "Verified", "Cycles", "UDI", "Verification Method"].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-slate-600">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((inst, i) => (
              <tr key={i} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2 capitalize">{String(inst.instrument_type ?? "—")}</td>
                <td className="px-3 py-2">
                  <StatusBadge status={String(inst.lifecycle_status ?? "")} />
                </td>
                <td className="px-3 py-2">
                  {inst.identity_verified ? (
                    <span className="text-green-700 font-medium">Yes</span>
                  ) : (
                    <span className="text-slate-400">No</span>
                  )}
                </td>
                <td className="px-3 py-2">{String(inst.total_cycle_count ?? 0)}</td>
                <td className="px-3 py-2 font-mono text-xs">{String(inst.udi ?? "—")}</td>
                <td className="px-3 py-2 capitalize">{String(inst.verification_method ?? "—")}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="text-sm text-slate-500 text-center py-8">No instruments found.</p>
        )}
      </div>
    </div>
  );
}

// --- Readiness Tab ---
function ReadinessTab() {
  const [scope, setScope] = useState<"facility" | "tray" | "enterprise">("facility");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const compute = () => {
    setLoading(true);
    fetch(`${API}/api/infrastructure/readiness`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ scope }),
    })
      .then((r) => r.json())
      .then(setResult)
      .finally(() => setLoading(false));
  };

  const tier = result?.readiness_tier as ReadinessTier | undefined;

  return (
    <div className="max-w-2xl">
      <div className="flex gap-3 mb-6">
        {(["facility", "tray", "enterprise"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setScope(s)}
            className={`px-3 py-1.5 rounded text-sm capitalize ${
              scope === s
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {s}
          </button>
        ))}
        <button
          onClick={compute}
          disabled={loading}
          className="ml-2 px-4 py-1.5 rounded bg-slate-900 text-white text-sm hover:bg-slate-700 disabled:opacity-50"
        >
          {loading ? "Computing…" : "Compute Readiness"}
        </button>
      </div>

      {result && (
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <div className="flex items-center gap-4 mb-4">
            <div>
              <p className="text-xs text-slate-500 mb-1">Readiness Score</p>
              <p className="text-4xl font-bold text-slate-900">{String(result.readiness_score ?? "—")}</p>
            </div>
            {tier && <TierBadge tier={tier} />}
            <HumanReviewBadge />
          </div>

          {result.component_scores && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-slate-600 mb-2">Component Scores</p>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(result.component_scores as Record<string, number>).map(([k, v]) => (
                  <div key={k} className="flex justify-between rounded bg-slate-50 px-3 py-1.5 text-xs">
                    <span className="text-slate-600 capitalize">{k.replace(/_/g, " ")}</span>
                    <span className="font-semibold">{typeof v === "number" ? v.toFixed(1) : String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {Array.isArray(result.blocking_issues) && result.blocking_issues.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-semibold text-red-700 mb-1">Blocking Issues</p>
              <ul className="list-disc list-inside text-xs text-red-700">
                {(result.blocking_issues as string[]).map((issue, i) => (
                  <li key={i}>{issue}</li>
                ))}
              </ul>
            </div>
          )}

          {Array.isArray(result.warnings) && result.warnings.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-amber-700 mb-1">Warnings</p>
              <ul className="list-disc list-inside text-xs text-amber-700">
                {(result.warnings as string[]).map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// --- Registry Tab ---
function RegistryTab() {
  const [entries, setEntries] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("");

  useEffect(() => {
    fetch(`${API}/api/infrastructure/quality-registry`, { headers: headers() })
      .then((r) => r.json())
      .then((d) => setEntries(d.entries ?? d ?? []))
      .finally(() => setLoading(false));
  }, []);

  const filtered = typeFilter
    ? entries.filter((e) => String(e.registry_type ?? "").includes(typeFilter))
    : entries;

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="border border-slate-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">All types</option>
          <option value="contamination">Contamination</option>
          <option value="defect">Defect</option>
          <option value="baseline">Baseline</option>
          <option value="reliability">Reliability</option>
        </select>
        <span className="text-xs text-slate-500">{filtered.length} entries</span>
        <span className="ml-auto rounded bg-blue-50 border border-blue-200 px-2 py-0.5 text-xs text-blue-800">
          Anonymized · K-Anonymity Verified
        </span>
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        {filtered.map((entry, i) => (
          <div key={i} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-semibold text-slate-700 capitalize">
                {String(entry.registry_type ?? "").replace(/_/g, " ")}
              </span>
              <span className="text-xs text-slate-500">
                {entry.k_anonymity_verified ? "✓ k-anon" : "⚠ pending"}
              </span>
            </div>
            <p className="text-2xl font-bold text-slate-900">
              {typeof entry.rate === "number" ? (entry.rate * 100).toFixed(2) + "%" : String(entry.rate ?? "—")}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              {entry.contributing_facilities as number} contributing facilities
            </p>
            <p className="text-xs text-slate-400 mt-2 italic">{String(entry.disclaimer ?? "")}</p>
            <div className="mt-2">
              <HumanReviewBadge />
            </div>
          </div>
        ))}
      </div>
      {filtered.length === 0 && (
        <p className="text-sm text-slate-500 text-center py-8">No registry entries found.</p>
      )}
    </div>
  );
}

// --- Forecasts Tab ---
function ForecastsTab() {
  const [forecasts, setForecasts] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/infrastructure/forecasts`, { headers: headers() })
      .then((r) => r.json())
      .then((d) => setForecasts(d.forecasts ?? d ?? []))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;

  const RISK_COLORS: Record<string, string> = {
    low: "text-green-700",
    moderate: "text-yellow-700",
    high: "text-orange-700",
    critical: "text-red-700",
  };

  return (
    <div>
      <p className="text-xs text-slate-500 mb-4">
        All forecasts include confidence intervals. Outputs represent potential signals only — not clinical
        predictions or regulatory findings.
      </p>
      <div className="grid md:grid-cols-2 gap-4">
        {forecasts.map((fc, i) => (
          <div key={i} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex justify-between items-start mb-3">
              <p className="text-sm font-semibold text-slate-800 capitalize">
                {String(fc.forecast_type ?? "").replace(/_/g, " ")}
              </p>
              <span className={`text-xs font-semibold capitalize ${RISK_COLORS[String(fc.risk_level ?? "low")] ?? ""}`}>
                {String(fc.risk_level ?? "")} risk
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 mb-3 text-center">
              <div className="bg-slate-50 rounded p-2">
                <p className="text-xs text-slate-500">Predicted Rate</p>
                <p className="text-lg font-bold text-slate-900">
                  {typeof fc.predicted_rate === "number" ? (fc.predicted_rate * 100).toFixed(1) + "%" : "—"}
                </p>
              </div>
              <div className="bg-slate-50 rounded p-2">
                <p className="text-xs text-slate-500">CI Low</p>
                <p className="text-lg font-semibold text-slate-700">
                  {typeof fc.confidence_interval_low === "number"
                    ? (fc.confidence_interval_low * 100).toFixed(1) + "%"
                    : "—"}
                </p>
              </div>
              <div className="bg-slate-50 rounded p-2">
                <p className="text-xs text-slate-500">CI High</p>
                <p className="text-lg font-semibold text-slate-700">
                  {typeof fc.confidence_interval_high === "number"
                    ? (fc.confidence_interval_high * 100).toFixed(1) + "%"
                    : "—"}
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-500 mb-1">
              Confidence Score: {typeof fc.confidence_score === "number" ? (fc.confidence_score * 100).toFixed(0) + "%" : "—"}
            </p>

            {Array.isArray(fc.recommended_actions) && fc.recommended_actions.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-semibold text-slate-600 mb-1">Recommended Actions</p>
                <ul className="list-disc list-inside text-xs text-slate-600 space-y-0.5">
                  {(fc.recommended_actions as string[]).map((a, j) => (
                    <li key={j}>{a}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-3">
              <HumanReviewBadge />
            </div>
          </div>
        ))}
      </div>
      {forecasts.length === 0 && (
        <p className="text-sm text-slate-500 text-center py-8">No forecasts available.</p>
      )}
    </div>
  );
}
