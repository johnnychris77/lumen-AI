import { useState, useEffect, useCallback } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "";
const token = () => localStorage.getItem("token") || "";
const AUTH = () => ({ "Content-Type": "application/json", Authorization: `Bearer ${token()}` });

const DISCLAIMER =
  "Global Surgical Intelligence Network outputs represent anonymized aggregate patterns across participating facilities. No individual facility, patient, or instrument is identified. All outputs are for planning and awareness purposes only. Does not establish causation. Human review required before operational decisions.";

type Signal = Record<string, unknown>;
type RegistryEntry = Record<string, unknown>;
type Warning = Record<string, unknown>;
type Pkg = Record<string, unknown>;
type Dashboard = Record<string, unknown>;

function DisclaimerBanner() {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-800 mb-4">
      <strong>Governance Notice:</strong> {DISCLAIMER}
    </div>
  );
}

function HumanReviewBadge() {
  return (
    <span className="inline-block bg-orange-100 text-orange-700 text-xs px-2 py-0.5 rounded font-semibold">
      Human Review Required
    </span>
  );
}

function SignalsTab() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [region, setRegion] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const url = region
      ? `${API}/api/global-intelligence/signals?region=${encodeURIComponent(region)}`
      : `${API}/api/global-intelligence/signals`;
    const r = await fetch(url, { headers: AUTH() });
    if (r.ok) {
      const d = await r.json();
      setSignals(d.signals ?? []);
    }
    setLoading(false);
  }, [region]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <DisclaimerBanner />
      <div className="flex gap-2 mb-4">
        <select
          className="border rounded px-2 py-1 text-sm"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
        >
          <option value="">All Regions</option>
          <option value="north_america">North America</option>
          <option value="europe">Europe</option>
          <option value="apac">APAC</option>
          <option value="australia">Australia</option>
          <option value="global">Global</option>
        </select>
      </div>
      {loading ? (
        <p className="text-sm text-gray-500">Loading signals…</p>
      ) : (
        <div className="space-y-3">
          {signals.map((s, i) => (
            <div key={i} className="border rounded p-4 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm">{String(s.signal_type ?? "—")} / {String(s.instrument_category ?? "—")}</span>
                <HumanReviewBadge />
              </div>
              <div className="flex gap-4 text-xs text-gray-600 mb-2">
                <span>Region: {String(s.region ?? "—")}</span>
                <span>Facilities: {String(s.facility_count ?? "—")}</span>
                <span>Strength: {typeof s.signal_strength === "number" ? (s.signal_strength as number).toFixed(2) : "—"}</span>
                <span>Trend: {String(s.trend_direction ?? "—")}</span>
              </div>
              <p className="text-xs text-gray-700 italic">{String(s.association_reason ?? "")}</p>
            </div>
          ))}
          {signals.length === 0 && <p className="text-sm text-gray-500">No published signals.</p>}
        </div>
      )}
    </div>
  );
}

function RiskRegistryTab() {
  const [entries, setEntries] = useState<RegistryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/global-intelligence/risk-registry`, { headers: AUTH() })
      .then((r) => r.json())
      .then((d) => setEntries(d.entries ?? []))
      .finally(() => setLoading(false));
  }, []);

  const statusColor: Record<string, string> = {
    active_signal: "bg-red-100 text-red-700",
    elevated: "bg-orange-100 text-orange-700",
    monitoring: "bg-blue-100 text-blue-700",
    resolved: "bg-green-100 text-green-700",
  };

  return (
    <div>
      <DisclaimerBanner />
      {loading ? (
        <p className="text-sm text-gray-500">Loading registry…</p>
      ) : (
        <div className="space-y-3">
          {entries.map((e, i) => (
            <div key={i} className="border rounded p-4 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm">{String(e.instrument_category ?? "—")} — {String(e.risk_pattern ?? "—")}</span>
                <span className={`text-xs px-2 py-0.5 rounded font-semibold ${statusColor[String(e.registry_status)] ?? "bg-gray-100 text-gray-700"}`}>
                  {String(e.registry_status ?? "—")}
                </span>
              </div>
              <div className="flex gap-4 text-xs text-gray-600 mb-2">
                <span>Risk Score: {typeof e.risk_score === "number" ? (e.risk_score as number).toFixed(2) : "—"}</span>
                <span>Facilities: {String(e.facilities_reporting ?? "—")}</span>
                <span>Findings: {String(e.finding_count ?? "—")}</span>
                <span>Trend: {String(e.trend_direction ?? "—")}</span>
              </div>
              <p className="text-xs text-gray-700 italic">{String(e.association_reason ?? "")}</p>
              <div className="mt-2"><HumanReviewBadge /></div>
            </div>
          ))}
          {entries.length === 0 && <p className="text-sm text-gray-500">No registry entries.</p>}
        </div>
      )}
    </div>
  );
}

function RecallWarningsTab() {
  const [warnings, setWarnings] = useState<Warning[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/global-intelligence/recall-warnings`, { headers: AUTH() })
      .then((r) => r.json())
      .then((d) => setWarnings(d.warnings ?? []))
      .finally(() => setLoading(false));
  }, []);

  const statusColor: Record<string, string> = {
    escalated: "bg-red-100 text-red-700",
    under_review: "bg-orange-100 text-orange-700",
    active: "bg-yellow-100 text-yellow-700",
    resolved: "bg-green-100 text-green-700",
  };

  return (
    <div>
      <DisclaimerBanner />
      <div className="bg-red-50 border border-red-200 rounded p-3 text-xs text-red-800 mb-4">
        <strong>Important:</strong> These are early warning signals only — not regulatory recall notices. Human review and regulatory consultation required before any action.
      </div>
      {loading ? (
        <p className="text-sm text-gray-500">Loading warnings…</p>
      ) : (
        <div className="space-y-3">
          {warnings.map((w, i) => (
            <div key={i} className="border rounded p-4 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm">{String(w.instrument_category ?? "—")} — {String(w.finding_type ?? "—")}</span>
                <span className={`text-xs px-2 py-0.5 rounded font-semibold ${statusColor[String(w.status)] ?? "bg-gray-100 text-gray-700"}`}>
                  {String(w.status ?? "—")}
                </span>
              </div>
              <div className="flex gap-4 text-xs text-gray-600 mb-2">
                <span>Region: {String(w.region ?? "—")}</span>
                <span>Facilities: {String(w.facilities_count ?? "—")}</span>
                <span>Strength: {typeof w.signal_strength_score === "number" ? (w.signal_strength_score as number).toFixed(2) : "—"}</span>
                <span>Recency: {String(w.recency_days ?? "—")}d</span>
              </div>
              <div className="flex gap-3 text-xs mb-2">
                <span className={w.manufacturer_notified ? "text-green-700" : "text-gray-400"}>
                  {w.manufacturer_notified ? "✓ Manufacturer Notified" : "○ Manufacturer Pending"}
                </span>
                <span className={w.regulatory_notified ? "text-green-700" : "text-gray-400"}>
                  {w.regulatory_notified ? "✓ Regulatory Notified" : "○ Regulatory Pending"}
                </span>
              </div>
              <p className="text-xs text-gray-700 italic">{String(w.association_reason ?? "")}</p>
              <div className="mt-2"><HumanReviewBadge /></div>
            </div>
          ))}
          {warnings.length === 0 && <p className="text-sm text-gray-500">No active warnings.</p>}
        </div>
      )}
    </div>
  );
}

function DashboardTab() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/global-intelligence/dashboard`, { headers: AUTH() })
      .then((r) => r.json())
      .then((d) => setData(d))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-gray-500">Loading dashboard…</p>;
  if (!data) return <p className="text-sm text-red-500">Failed to load dashboard.</p>;

  const kpis = [
    { label: "Active Global Signals", value: data.active_global_signals },
    { label: "Recall Early Warnings", value: data.recall_early_warnings },
    { label: "Risk Registry Entries", value: data.risk_registry_entries },
    { label: "Network Participants", value: data.network_participants },
    { label: "Pending Human Reviews", value: data.human_review_required_count },
  ];

  return (
    <div>
      <DisclaimerBanner />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {kpis.map((k) => (
          <div key={k.label} className="border rounded p-3 bg-white shadow-sm text-center">
            <div className="text-2xl font-bold text-blue-700">{String(k.value ?? 0)}</div>
            <div className="text-xs text-gray-500 mt-1">{k.label}</div>
          </div>
        ))}
      </div>
      <div className="text-xs text-gray-500 mb-2">
        Participant Status: <span className="font-semibold">{String(data.participant_status ?? "—")}</span>
      </div>
      <HumanReviewBadge />
    </div>
  );
}

function RegulatoryEvidenceTab() {
  const [packages, setPackages] = useState<Pkg[]>([]);
  const [loading, setLoading] = useState(true);
  const [authority, setAuthority] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const url = authority
      ? `${API}/api/global-intelligence/regulatory-evidence?authority=${encodeURIComponent(authority)}`
      : `${API}/api/global-intelligence/regulatory-evidence`;
    const r = await fetch(url, { headers: AUTH() });
    if (r.ok) {
      const d = await r.json();
      setPackages(d.packages ?? []);
    }
    setLoading(false);
  }, [authority]);

  useEffect(() => { load(); }, [load]);

  const statusColor: Record<string, string> = {
    published: "bg-green-100 text-green-700",
    under_review: "bg-orange-100 text-orange-700",
    draft: "bg-gray-100 text-gray-700",
    archived: "bg-blue-100 text-blue-700",
  };

  return (
    <div>
      <DisclaimerBanner />
      <div className="flex gap-2 mb-4">
        <select
          className="border rounded px-2 py-1 text-sm"
          value={authority}
          onChange={(e) => setAuthority(e.target.value)}
        >
          <option value="">All Authorities</option>
          <option value="FDA">FDA</option>
          <option value="EUMDR">EUMDR</option>
          <option value="TGA">TGA</option>
          <option value="HealthCanada">HealthCanada</option>
          <option value="PMDA">PMDA</option>
          <option value="MFDS">MFDS</option>
        </select>
      </div>
      {loading ? (
        <p className="text-sm text-gray-500">Loading packages…</p>
      ) : (
        <div className="space-y-3">
          {packages.map((pkg, i) => (
            <div key={i} className="border rounded p-4 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm">{String(pkg.target_authority ?? "—")} — {String(pkg.evidence_type ?? "—")}</span>
                <span className={`text-xs px-2 py-0.5 rounded font-semibold ${statusColor[String(pkg.status)] ?? "bg-gray-100 text-gray-700"}`}>
                  {String(pkg.status ?? "—")}
                </span>
              </div>
              <div className="text-xs text-gray-600 mb-2">Facilities: {String(pkg.facility_count ?? "—")} (k-anonymity verified)</div>
              <p className="text-xs text-gray-700 mb-2">{String(pkg.summary ?? "")}</p>
              <p className="text-xs text-gray-500 italic">{String(pkg.disclaimer ?? "")}</p>
              <div className="mt-2"><HumanReviewBadge /></div>
            </div>
          ))}
          {packages.length === 0 && <p className="text-sm text-gray-500">No evidence packages.</p>}
        </div>
      )}
    </div>
  );
}

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "signals", label: "Global Signals" },
  { id: "registry", label: "Risk Registry" },
  { id: "warnings", label: "Recall Warnings" },
  { id: "evidence", label: "Regulatory Evidence" },
];

export default function GlobalIntelligenceConsole() {
  const [tab, setTab] = useState("dashboard");

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Global Surgical Intelligence Network
        </h1>
        <p className="text-sm text-gray-600 mt-1">
          Anonymized cross-network quality intelligence • Instrument risk registry • Recall early warning system
        </p>
      </div>

      <div className="flex gap-2 border-b mb-6">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? "border-blue-600 text-blue-700"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "dashboard" && <DashboardTab />}
      {tab === "signals" && <SignalsTab />}
      {tab === "registry" && <RiskRegistryTab />}
      {tab === "warnings" && <RecallWarningsTab />}
      {tab === "evidence" && <RegulatoryEvidenceTab />}
    </div>
  );
}
