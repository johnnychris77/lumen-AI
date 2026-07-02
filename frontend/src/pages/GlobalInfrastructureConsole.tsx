import React, { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getImagesByInstrument, getImagesByIdentifier, MANIFEST_INSTRUMENTS } from "../data/pilotImageManifest";

const API = import.meta.env.VITE_API_BASE_URL || "";
const headers = () => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${localStorage.getItem("token") || ""}`,
});

// Coerce a fetch response body to an array. When a request fails (e.g. 401/500),
// the body is an error object, not a list — return [] rather than letting an
// object reach a `.map(...)` and crash the page to the error boundary.
function toArray(d: unknown, key?: string): Record<string, unknown>[] {
  if (key && d && typeof d === "object" && Array.isArray((d as Record<string, unknown>)[key])) {
    return (d as Record<string, Record<string, unknown>[]>)[key];
  }
  return Array.isArray(d) ? (d as Record<string, unknown>[]) : [];
}

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

type Tab = "dashboard" | "instruments" | "passport" | "readiness" | "registry" | "spd-registry" | "forecasts" | "credentials";

export default function GlobalInfrastructureConsole() {
  const [searchParams] = useSearchParams();
  const initialTab = (searchParams.get("tab") as Tab | null) ?? "dashboard";
  const deepLinkInstrument = searchParams.get("instrument") ?? "";
  const [tab, setTab] = useState<Tab>(initialTab);
  const TABS: { id: Tab; label: string }[] = [
    { id: "dashboard", label: "Dashboard" },
    { id: "instruments", label: "Instrument Identities" },
    { id: "passport", label: "Instrument Passport" },
    { id: "readiness", label: "Readiness Index" },
    { id: "registry", label: "Quality Registry" },
    { id: "spd-registry", label: "SPD Registry" },
    { id: "forecasts", label: "Predictive Forecasts" },
    { id: "credentials", label: "API Credentials" },
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
      {tab === "passport" && <PassportTab deepLinkInstrument={deepLinkInstrument} />}
      {tab === "readiness" && <ReadinessTab />}
      {tab === "registry" && <RegistryTab />}
      {tab === "spd-registry" && <SPDRegistryTab />}
      {tab === "forecasts" && <ForecastsTab />}
      {tab === "credentials" && <CredentialsTab />}
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
      .then((d) => setInstruments(toArray(d, "instruments")))
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
              {["Type", "Lifecycle Status", "Verified", "Cycles", "UDI", "Verification Method", "Pilot Images"].map((h) => (
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
                <td className="px-3 py-2">
                  {(() => {
                    const itype = String(inst.instrument_type ?? "");
                    const matched = MANIFEST_INSTRUMENTS.find((m) =>
                      itype.toLowerCase().includes(m.toLowerCase()) || m.toLowerCase().includes(itype.toLowerCase())
                    );
                    const imgs = matched ? getImagesByInstrument(matched) : [];
                    return imgs.length > 0 ? (
                      <span className="inline-flex items-center gap-1 rounded bg-blue-50 border border-blue-200 px-2 py-0.5 text-xs text-blue-700 font-medium">
                        {imgs.length} image{imgs.length !== 1 ? "s" : ""}
                      </span>
                    ) : (
                      <span className="text-slate-300 text-xs">—</span>
                    );
                  })()}
                </td>
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
      .then((d) => setEntries(toArray(d, "entries")))
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
      .then((d) => setForecasts(toArray(d, "forecasts")))
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

// --- Instrument Passport Tab ---
function PassportTab({ deepLinkInstrument = "" }: { deepLinkInstrument?: string }) {
  const [instruments, setInstruments] = useState<Record<string, unknown>[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const deepLinked = useRef(false);
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [form, setForm] = useState({ event_type: "inspection", outcome: "pass", finding_severity: "none", notes: "" });
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/api/infrastructure/instruments`, { headers: headers() })
      .then((r) => r.json())
      .then((d) => {
        const list: Record<string, unknown>[] = toArray(d, "instruments");
        setInstruments(list);
        // Auto-select instrument from deep-link query param on first load
        if (deepLinkInstrument && !deepLinked.current) {
          deepLinked.current = true;
          const match = list.find(
            (inst) =>
              String(inst.udi ?? "").toLowerCase().includes(deepLinkInstrument.toLowerCase()) ||
              String(inst.barcode ?? "").toLowerCase() === deepLinkInstrument.toLowerCase() ||
              String(inst.internal_id ?? "").toLowerCase() === deepLinkInstrument.toLowerCase()
          );
          if (match) loadPassport(String(match.id ?? ""));
        }
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadPassport = (id: string) => {
    setSelectedId(id);
    setLoadingEvents(true);
    fetch(`${API}/api/infrastructure/instruments/${id}/passport`, { headers: headers() })
      .then((r) => r.json())
      .then((d) => setEvents(toArray(d, "events")))
      .finally(() => setLoadingEvents(false));
  };

  const addEvent = async () => {
    if (!selectedId) return;
    setSubmitting(true);
    setMsg(null);
    try {
      const r = await fetch(`${API}/api/infrastructure/instruments/${selectedId}/passport`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify(form),
      });
      const d = await r.json();
      if (r.ok) {
        setMsg("Event recorded.");
        loadPassport(selectedId);
      } else {
        setMsg(d.detail ?? "Error recording event.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const EVENT_TYPES = ["inspection", "sterilization", "maintenance", "repair", "transfer", "quarantine", "retirement"];
  const SEV_TYPES = ["none", "minor", "major", "critical"];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div>
        <p className="text-xs font-semibold text-slate-600 mb-2">Select Instrument</p>
        <select
          value={selectedId}
          onChange={(e) => loadPassport(e.target.value)}
          className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm mb-4"
        >
          <option value="">— choose instrument —</option>
          {instruments.map((inst, i) => (
            <option key={i} value={String(inst.id ?? i)}>
              {String(inst.instrument_type ?? "Unknown")} — {String(inst.udi ?? inst.internal_id ?? inst.id ?? i)}
            </option>
          ))}
        </select>

        {selectedId && (
          <div className="border border-slate-200 rounded p-4 bg-slate-50">
            <p className="text-xs font-semibold text-slate-600 mb-3">Log New Event</p>
            <div className="space-y-2">
              <div>
                <label className="text-xs text-slate-500">Event Type</label>
                <select value={form.event_type} onChange={(e) => setForm({ ...form, event_type: e.target.value })}
                  className="w-full border border-slate-300 rounded px-2 py-1 text-sm mt-0.5">
                  {EVENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500">Outcome</label>
                <select value={form.outcome} onChange={(e) => setForm({ ...form, outcome: e.target.value })}
                  className="w-full border border-slate-300 rounded px-2 py-1 text-sm mt-0.5">
                  {["pass", "fail", "conditional", "completed", "escalated"].map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500">Finding Severity</label>
                <select value={form.finding_severity} onChange={(e) => setForm({ ...form, finding_severity: e.target.value })}
                  className="w-full border border-slate-300 rounded px-2 py-1 text-sm mt-0.5">
                  {SEV_TYPES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500">Notes</label>
                <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  className="w-full border border-slate-300 rounded px-2 py-1 text-sm mt-0.5" rows={2} />
              </div>
              <button onClick={addEvent} disabled={submitting}
                className="w-full bg-slate-900 text-white text-sm rounded px-3 py-1.5 hover:bg-slate-700 disabled:opacity-50">
                {submitting ? "Saving…" : "Record Event"}
              </button>
              {msg && <p className="text-xs text-green-700">{msg}</p>}
            </div>
          </div>
        )}
      </div>

      <div className="md:col-span-2">
        <p className="text-xs font-semibold text-slate-600 mb-2">
          Passport History {selectedId ? `— ${events.length} event(s)` : ""}
        </p>
        {loadingEvents && <p className="text-sm text-slate-500">Loading…</p>}
        {!loadingEvents && !selectedId && (
          <p className="text-sm text-slate-400 py-8 text-center">Select an instrument to view its passport.</p>
        )}
        {!loadingEvents && selectedId && (
          <div className="overflow-x-auto rounded border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {["Event Type", "Outcome", "Severity", "Cycle Count", "Timestamp"].map((h) => (
                    <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-slate-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {events.map((ev, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    <td className="px-3 py-2 capitalize">{String(ev.event_type ?? "—")}</td>
                    <td className="px-3 py-2 capitalize">{String(ev.outcome ?? "—")}</td>
                    <td className="px-3 py-2 capitalize">{String(ev.finding_severity ?? "—")}</td>
                    <td className="px-3 py-2">{String(ev.cycle_count_at_event ?? "—")}</td>
                    <td className="px-3 py-2 text-slate-400 text-xs">
                      {ev.created_at ? new Date(String(ev.created_at)).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
                {events.length === 0 && (
                  <tr><td colSpan={5} className="px-3 py-8 text-center text-slate-400 text-sm">No events recorded yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        <div className="mt-3"><HumanReviewBadge /></div>

        {selectedId && <PassportImageGallery instrumentId={selectedId} instruments={instruments} />}
      </div>
    </div>
  );
}

function PassportImageGallery({
  instrumentId,
  instruments,
}: {
  instrumentId: string;
  instruments: Record<string, unknown>[];
}) {
  const inst = instruments.find((i) => String(i.id ?? "") === instrumentId);
  const udi = inst ? String(inst.udi ?? inst.internal_id ?? "") : "";
  const itype = inst ? String(inst.instrument_type ?? "") : "";

  // Match by UDI/barcode identifier first, fall back to instrument type
  const byId = udi ? getImagesByIdentifier(udi) : [];
  const byType = (() => {
    const matched = MANIFEST_INSTRUMENTS.find((m) =>
      itype.toLowerCase().includes(m.toLowerCase()) || m.toLowerCase().includes(itype.toLowerCase())
    );
    return matched ? getImagesByInstrument(matched) : [];
  })();

  const images = byId.length > 0 ? byId : byType;

  if (images.length === 0) return null;

  return (
    <div className="mt-6">
      <p className="text-xs font-semibold text-slate-600 mb-2">
        Pilot Images ({images.length})
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {images.map((img) => (
          <div key={img.id} className="rounded border border-slate-200 overflow-hidden bg-slate-50">
            <img
              src={img.available ? img.imageSrc : img.placeholderSrc}
              alt={`${img.instrumentName} — ${img.imageType}`}
              className="w-full h-28 object-cover"
              onError={(e) => {
                const target = e.currentTarget;
                if (target.src !== img.placeholderSrc) target.src = img.placeholderSrc;
              }}
            />
            <div className="px-2 py-1.5">
              <p className="text-xs font-medium text-slate-700 capitalize">{img.imageType}</p>
              {img.findingCategory && img.findingCategory !== "none" && (
                <p className="text-xs text-slate-500 capitalize">{img.findingCategory.replace(/_/g, " ")}</p>
              )}
              <p className="text-xs text-slate-400 mt-0.5">{img.facilityName}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- SPD Registry Tab ---
function SPDRegistryTab() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [defectHistory, setDefectHistory] = useState<{ udi: string; history: Record<string, unknown>[] } | null>(null);

  useEffect(() => {
    fetch(`${API}/api/network/registry/stats`, { headers: headers() })
      .then((r) => r.json())
      .then(setStats);
    fetch(`${API}/api/network/registry/search?q=`, { headers: headers() })
      .then((r) => r.json())
      .then((d) => setResults(toArray(d, "results")));
  }, []);

  const search = () => {
    setLoading(true);
    fetch(`${API}/api/network/registry/search?q=${encodeURIComponent(query)}`, { headers: headers() })
      .then((r) => r.json())
      .then((d) => setResults(toArray(d, "results")))
      .finally(() => setLoading(false));
  };

  const loadDefectHistory = (udi: string) => {
    fetch(`${API}/api/network/registry/${encodeURIComponent(udi)}/defect-history`, { headers: headers() })
      .then((r) => r.json())
      .then((d) => setDefectHistory({ udi, history: toArray(d, "history") }));
  };

  return (
    <div>
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {Object.entries(stats).filter(([k]) => typeof stats[k] === "number").map(([k, v]) => (
            <div key={k} className="rounded border border-slate-200 bg-white p-3">
              <p className="text-xs text-slate-500 capitalize">{k.replace(/_/g, " ")}</p>
              <p className="text-xl font-bold text-slate-900 mt-0.5">{String(v)}</p>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          placeholder="Search by UDI, manufacturer, instrument type…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm flex-1"
        />
        <button onClick={search} disabled={loading}
          className="bg-slate-900 text-white text-sm rounded px-4 py-1.5 hover:bg-slate-700 disabled:opacity-50">
          {loading ? "Searching…" : "Search"}
        </button>
      </div>

      <div className="overflow-x-auto rounded border border-slate-200 mb-6">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              {["UDI", "Instrument Type", "Manufacturer", "Version", "Defect History"].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-slate-600">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.map((entry, i) => (
              <tr key={i} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2 font-mono text-xs">{String(entry.udi ?? "—")}</td>
                <td className="px-3 py-2 capitalize">{String(entry.instrument_type ?? "—")}</td>
                <td className="px-3 py-2">{String(entry.manufacturer ?? "—")}</td>
                <td className="px-3 py-2">{String(entry.version ?? "—")}</td>
                <td className="px-3 py-2">
                  {entry.udi && (
                    <button onClick={() => loadDefectHistory(String(entry.udi))}
                      className="text-xs text-blue-600 hover:underline">
                      View history
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {results.length === 0 && (
              <tr><td colSpan={5} className="px-3 py-8 text-center text-slate-400 text-sm">No registry entries found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {defectHistory && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-sm font-semibold text-slate-700 mb-3">
            Defect History — <span className="font-mono text-xs">{defectHistory.udi}</span>
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-50">
                <tr>
                  {["Finding Type", "Severity", "Date", "Outcome"].map((h) => (
                    <th key={h} className="px-3 py-1.5 text-left font-semibold text-slate-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {defectHistory.history.map((d, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    <td className="px-3 py-1.5 capitalize">{String(d.finding_type ?? "—")}</td>
                    <td className="px-3 py-1.5 capitalize">{String(d.severity ?? "—")}</td>
                    <td className="px-3 py-1.5 text-slate-400">{d.date ? new Date(String(d.date)).toLocaleDateString() : "—"}</td>
                    <td className="px-3 py-1.5 capitalize">{String(d.outcome ?? "—")}</td>
                  </tr>
                ))}
                {defectHistory.history.length === 0 && (
                  <tr><td colSpan={4} className="px-3 py-4 text-center text-slate-400">No defect history.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <div className="mt-3"><HumanReviewBadge /></div>
    </div>
  );
}

// --- API Credentials Tab ---
function CredentialsTab() {
  const [creds, setCreds] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ consumer_type: "hospital", label: "", scopes: ["readiness"] });
  const [issuedKey, setIssuedKey] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const ALL_SCOPES = ["readiness", "passport", "registry", "lifecycle", "quality_signals", "forecasts", "benchmarks", "all"];
  const CONSUMER_TYPES = ["hospital", "manufacturer", "researcher", "governance"];

  const load = () => {
    setLoading(true);
    fetch(`${API}/api/infrastructure/api-credentials`, { headers: headers() })
      .then((r) => r.json())
      .then((d) => setCreds(toArray(d, "credentials")))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const issue = async () => {
    setSubmitting(true);
    setMsg(null);
    setIssuedKey(null);
    try {
      const r = await fetch(`${API}/api/infrastructure/api-credentials`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ consumer_type: form.consumer_type, label: form.label, scopes: form.scopes }),
      });
      const d = await r.json();
      if (r.ok) {
        setIssuedKey(d.api_key ?? null);
        setMsg("Credential issued. Copy the API key now — it will not be shown again.");
        load();
      } else {
        setMsg(d.detail ?? "Error issuing credential.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const revoke = async (id: unknown) => {
    setMsg(null);
    const r = await fetch(`${API}/api/infrastructure/api-credentials/${id}/revoke`, {
      method: "POST", headers: headers(),
    });
    const d = await r.json();
    setMsg(r.ok ? "Credential revoked." : (d.detail ?? "Error."));
    load();
  };

  const toggleScope = (scope: string) => {
    setForm((f) => ({
      ...f,
      scopes: f.scopes.includes(scope) ? f.scopes.filter((s) => s !== scope) : [...f.scopes, scope],
    }));
  };

  return (
    <div className="grid md:grid-cols-3 gap-6">
      <div className="border border-slate-200 rounded-lg p-4 bg-slate-50">
        <p className="text-sm font-semibold text-slate-700 mb-3">Issue New Credential</p>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-slate-500">Consumer Type</label>
            <select value={form.consumer_type} onChange={(e) => setForm({ ...form, consumer_type: e.target.value })}
              className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm mt-0.5">
              {CONSUMER_TYPES.map((t) => <option key={t} value={t} className="capitalize">{t}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500">Label</label>
            <input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })}
              placeholder="e.g. County Hospital API"
              className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm mt-0.5" />
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">Scopes</label>
            <div className="flex flex-wrap gap-1.5">
              {ALL_SCOPES.map((s) => (
                <button key={s} onClick={() => toggleScope(s)}
                  className={`px-2 py-0.5 rounded text-xs border ${form.scopes.includes(s) ? "bg-blue-600 text-white border-blue-600" : "bg-white text-slate-600 border-slate-300 hover:bg-slate-100"}`}>
                  {s}
                </button>
              ))}
            </div>
          </div>
          <button onClick={issue} disabled={submitting || form.scopes.length === 0}
            className="w-full bg-slate-900 text-white text-sm rounded px-3 py-1.5 hover:bg-slate-700 disabled:opacity-50">
            {submitting ? "Issuing…" : "Issue Credential"}
          </button>
          {msg && <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">{msg}</p>}
          {issuedKey && (
            <div className="rounded bg-green-50 border border-green-200 p-2">
              <p className="text-xs text-green-800 font-semibold mb-1">API Key (copy now — shown once):</p>
              <p className="font-mono text-xs break-all text-green-900 select-all">{issuedKey}</p>
            </div>
          )}
        </div>
      </div>

      <div className="md:col-span-2">
        <p className="text-xs font-semibold text-slate-600 mb-2">Active Credentials</p>
        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        <div className="overflow-x-auto rounded border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {["Consumer Type", "Label", "Scopes", "Status", "Expires", "Action"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-slate-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {creds.map((c, i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="px-3 py-2 capitalize">{String(c.consumer_type ?? "—")}</td>
                  <td className="px-3 py-2">{String(c.label ?? "—")}</td>
                  <td className="px-3 py-2 text-xs">
                    {Array.isArray(c.scopes) ? (c.scopes as string[]).join(", ") : String(c.scopes ?? "—")}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`text-xs font-medium ${c.status === "active" ? "text-green-700" : "text-slate-400"}`}>
                      {String(c.status ?? "—")}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-400">
                    {c.expires_at ? new Date(String(c.expires_at)).toLocaleDateString() : "Never"}
                  </td>
                  <td className="px-3 py-2">
                    {c.status === "active" && (
                      <button onClick={() => revoke(c.id)}
                        className="text-xs text-red-600 hover:underline">
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {creds.length === 0 && (
                <tr><td colSpan={6} className="px-3 py-8 text-center text-slate-400 text-sm">No credentials issued.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-slate-400 mt-2">API keys are hashed on issuance and cannot be retrieved after creation.</p>
      </div>
    </div>
  );
}
