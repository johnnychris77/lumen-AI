import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";

const API = import.meta.env.VITE_API_BASE_URL || "";
const AUTH = () => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${localStorage.getItem("token") || ""}`,
});

const DISCLAIMER =
  "Global Standards outputs are for planning and governance purposes only. No individual facility, patient, or instrument is identified. Human review required before any operational decisions. Does not constitute regulatory approval or clearance.";

type Rec = Record<string, unknown>;

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

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    published: "bg-green-100 text-green-700",
    active: "bg-green-100 text-green-700",
    approved: "bg-green-100 text-green-700",
    under_review: "bg-orange-100 text-orange-700",
    consortium_review: "bg-orange-100 text-orange-700",
    pending: "bg-yellow-100 text-yellow-700",
    pilot: "bg-blue-100 text-blue-700",
    planning: "bg-gray-100 text-gray-600",
    draft: "bg-gray-100 text-gray-600",
    compliant: "bg-green-100 text-green-700",
    partial: "bg-orange-100 text-orange-700",
    assessing: "bg-blue-100 text-blue-700",
    suspended: "bg-red-100 text-red-700",
    rejected: "bg-red-100 text-red-700",
  };
  const cls = colors[status] ?? "bg-gray-100 text-gray-600";
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-semibold ${cls}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

function DashboardTab() {
  const [data, setData] = useState<Rec | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch(`/api/standards/dashboard`, { raw: true, headers: AUTH() })
      .then((r) => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-gray-500">Loading dashboard…</p>;
  if (!data) return <p className="text-sm text-red-500">Failed to load.</p>;

  const kpis = [
    { label: "Published Standards", value: data.published_standards },
    { label: "Active Regions", value: data.active_regions },
    { label: "Network Participants", value: data.total_network_participants },
    { label: "Consortium Members", value: data.consortium_members },
    { label: "Published Papers", value: data.published_papers },
  ];

  const netMetrics = [
    { label: "Contamination Rate", value: data.network_contamination_rate, fmt: "pct" },
    { label: "Inspection Pass Rate", value: data.network_inspection_pass_rate, fmt: "pct" },
    { label: "Reliability Score", value: data.network_reliability_score, fmt: "pct" },
    { label: "CAPA Closure Rate", value: data.network_capa_closure_rate, fmt: "pct" },
  ];

  return (
    <div>
      <DisclaimerBanner />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {kpis.map((k) => (
          <div key={k.label} className="border rounded p-3 bg-white shadow-sm text-center">
            <div className="text-2xl font-bold text-blue-700">{String(k.value ?? "—")}</div>
            <div className="text-xs text-gray-500 mt-1">{k.label}</div>
          </div>
        ))}
      </div>

      <h3 className="font-semibold text-sm mb-3">Network Quality Metrics</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {netMetrics.map((m) => {
          const val = typeof m.value === "number"
            ? (m.value * 100).toFixed(1) + "%"
            : "—";
          return (
            <div key={m.label} className="border rounded p-3 bg-white shadow-sm text-center">
              <div className="text-xl font-bold text-gray-800">{val}</div>
              <div className="text-xs text-gray-500 mt-1">{m.label}</div>
            </div>
          );
        })}
      </div>
      <HumanReviewBadge />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Quality Standards
// ---------------------------------------------------------------------------

function StandardsTab() {
  const [standards, setStandards] = useState<Rec[]>([]);
  const [loading, setLoading] = useState(true);
  const [type, setType] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const url = type
      ? `${API}/api/standards/quality-standards?standard_type=${encodeURIComponent(type)}`
      : `${API}/api/standards/quality-standards`;
    const r = await apiFetch(url, { raw: true, headers: AUTH() });
    if (r.ok) setStandards((await r.json()).standards ?? []);
    setLoading(false);
  }, [type]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <DisclaimerBanner />
      <div className="flex gap-2 mb-4">
        <select className="border rounded px-2 py-1 text-sm" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">All Types</option>
          <option value="contamination_classification">Contamination Classification</option>
          <option value="instrument_defect">Instrument Defect</option>
          <option value="baseline_variance">Baseline Variance</option>
          <option value="inspection_scoring">Inspection Scoring</option>
        </select>
      </div>
      {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
        <div className="space-y-3">
          {standards.map((s, i) => (
            <div key={i} className="border rounded p-4 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm">{String(s.title ?? "—")}</span>
                <StatusBadge status={String(s.status ?? "")} />
              </div>
              <div className="flex gap-3 text-xs text-gray-500 mb-2">
                <span>v{String(s.version ?? "—")}</span>
                <span>{String(s.standard_type ?? "—").replace(/_/g, " ")}</span>
              </div>
              <p className="text-xs text-gray-700">{String(s.description ?? "")}</p>
              <div className="mt-2"><HumanReviewBadge /></div>
            </div>
          ))}
          {standards.length === 0 && <p className="text-sm text-gray-500">No standards found.</p>}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Benchmarks
// ---------------------------------------------------------------------------

function BenchmarksTab() {
  const [reports, setReports] = useState<Rec[]>([]);
  const [loading, setLoading] = useState(true);
  const [reportType, setReportType] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const url = reportType
      ? `${API}/api/standards/benchmarks?report_type=${encodeURIComponent(reportType)}`
      : `${API}/api/standards/benchmarks`;
    const r = await apiFetch(url, { raw: true, headers: AUTH() });
    if (r.ok) setReports((await r.json()).reports ?? []);
    setLoading(false);
  }, [reportType]);

  useEffect(() => { load(); }, [load]);

  const typeColor: Record<string, string> = {
    annual: "bg-blue-100 text-blue-700",
    contamination: "bg-orange-100 text-orange-700",
    reliability: "bg-green-100 text-green-700",
    executive_scorecard: "bg-purple-100 text-purple-700",
  };

  return (
    <div>
      <DisclaimerBanner />
      <div className="flex gap-2 mb-4">
        <select className="border rounded px-2 py-1 text-sm" value={reportType} onChange={(e) => setReportType(e.target.value)}>
          <option value="">All Reports</option>
          <option value="annual">Annual</option>
          <option value="contamination">Contamination</option>
          <option value="reliability">Reliability</option>
          <option value="executive_scorecard">Executive Scorecard</option>
        </select>
      </div>
      {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
        <div className="space-y-4">
          {reports.map((r, i) => (
            <div key={i} className="border rounded p-4 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm">{String(r.report_period ?? "—")} — {String(r.region ?? "—")}</span>
                <div className="flex gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded font-semibold ${typeColor[String(r.report_type)] ?? "bg-gray-100 text-gray-700"}`}>
                    {String(r.report_type ?? "").replace(/_/g, " ")}
                  </span>
                  <StatusBadge status={String(r.status ?? "")} />
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
                {r.contamination_rate != null && (
                  <div className="text-center border rounded p-2">
                    <div className="text-sm font-bold">{((r.contamination_rate as number) * 100).toFixed(1)}%</div>
                    <div className="text-xs text-gray-500">Contamination</div>
                  </div>
                )}
                {r.inspection_pass_rate != null && (
                  <div className="text-center border rounded p-2">
                    <div className="text-sm font-bold">{((r.inspection_pass_rate as number) * 100).toFixed(1)}%</div>
                    <div className="text-xs text-gray-500">Inspection Pass</div>
                  </div>
                )}
                {r.reliability_score != null && (
                  <div className="text-center border rounded p-2">
                    <div className="text-sm font-bold">{((r.reliability_score as number) * 100).toFixed(1)}%</div>
                    <div className="text-xs text-gray-500">Reliability</div>
                  </div>
                )}
                {r.network_percentile != null && (
                  <div className="text-center border rounded p-2">
                    <div className="text-sm font-bold">{String(r.network_percentile)}th</div>
                    <div className="text-xs text-gray-500">Network Percentile</div>
                  </div>
                )}
              </div>
              <p className="text-xs text-gray-700 mb-2">{String(r.executive_summary ?? r.benchmark_summary ?? "")}</p>
              <div className="mt-2"><HumanReviewBadge /></div>
            </div>
          ))}
          {reports.length === 0 && <p className="text-sm text-gray-500">No reports found.</p>}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Regional Deployments
// ---------------------------------------------------------------------------

function RegionsTab() {
  const [deployments, setDeployments] = useState<Rec[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch(`/api/standards/regional-deployments`, { raw: true, headers: AUTH() })
      .then((r) => r.json())
      .then((d) => setDeployments(d.deployments ?? []))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <DisclaimerBanner />
      {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
        <div className="space-y-3">
          {deployments.map((d, i) => (
            <div key={i} className="border rounded p-4 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm capitalize">{String(d.region ?? "—").replace(/_/g, " ")}</span>
                <div className="flex gap-2">
                  <StatusBadge status={String(d.deployment_status ?? "")} />
                  <StatusBadge status={String(d.compliance_status ?? "")} />
                </div>
              </div>
              <div className="flex gap-4 text-xs text-gray-600 mb-2">
                <span>Privacy: {String(d.privacy_framework ?? "—")}</span>
                <span>Residency: {String(d.data_residency_country ?? "—")}</span>
                <span>Participants: {String(d.active_participants ?? 0)}</span>
              </div>
              <div className="flex gap-3 text-xs mb-2">
                <span className={d.data_residency_verified ? "text-green-700" : "text-gray-400"}>
                  {d.data_residency_verified ? "✓ Data Residency Verified" : "○ Residency Pending"}
                </span>
                <span className={d.cross_border_transfer_approved ? "text-green-700" : "text-gray-400"}>
                  {d.cross_border_transfer_approved ? "✓ Cross-Border Approved" : "○ Cross-Border Pending"}
                </span>
              </div>
              {d.notes && <p className="text-xs text-gray-600 italic">{String(d.notes)}</p>}
              <div className="mt-2"><HumanReviewBadge /></div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Consortium & Publications
// ---------------------------------------------------------------------------

function ConsortiumTab() {
  const [members, setMembers] = useState<Rec[]>([]);
  const [pubs, setPubs] = useState<Rec[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiFetch(`/api/standards/consortium`, { raw: true, headers: AUTH() }).then((r) => r.json()),
      apiFetch(`/api/standards/publications`, { raw: true, headers: AUTH() }).then((r) => r.json()),
    ]).then(([c, p]) => {
      setMembers(c.members ?? []);
      setPubs(p.publications ?? []);
    }).finally(() => setLoading(false));
  }, []);

  const tierColor: Record<string, string> = {
    steering: "bg-purple-100 text-purple-700",
    voting: "bg-blue-100 text-blue-700",
    contributor: "bg-green-100 text-green-700",
    observer: "bg-gray-100 text-gray-600",
  };

  return (
    <div>
      <DisclaimerBanner />
      {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
        <>
          <h3 className="font-semibold text-sm mb-3">Members ({members.length})</h3>
          <div className="space-y-2 mb-6">
            {members.map((m, i) => (
              <div key={i} className="border rounded p-3 bg-white shadow-sm flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium">{String(m.organization_type ?? "—").replace(/_/g, " ")} — {String(m.region ?? "—")}</span>
                  {m.voting_rights && (
                    <span className="ml-2 text-xs text-blue-700 font-semibold">✓ Voting</span>
                  )}
                </div>
                <span className={`text-xs px-2 py-0.5 rounded font-semibold ${tierColor[String(m.membership_tier)] ?? "bg-gray-100 text-gray-700"}`}>
                  {String(m.membership_tier ?? "—")}
                </span>
              </div>
            ))}
          </div>

          <h3 className="font-semibold text-sm mb-3">Publications ({pubs.length})</h3>
          <div className="space-y-3">
            {pubs.map((p, i) => (
              <div key={i} className="border rounded p-4 bg-white shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-sm">{String(p.title ?? "—")}</span>
                  <StatusBadge status={String(p.status ?? "")} />
                </div>
                <div className="text-xs text-gray-500 mb-2">v{String(p.version ?? "—")} · {String(p.publication_type ?? "").replace(/_/g, " ")}</div>
                <p className="text-xs text-gray-700">{String(p.abstract ?? "")}</p>
                <div className="mt-2"><HumanReviewBadge /></div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Console
// ---------------------------------------------------------------------------

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "standards", label: "Quality Standards" },
  { id: "benchmarks", label: "Benchmarks" },
  { id: "regions", label: "International" },
  { id: "consortium", label: "Consortium & Publications" },
];

export default function GlobalStandardsConsole() {
  const [tab, setTab] = useState("dashboard");

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Global Healthcare Intelligence Ecosystem
        </h1>
        <p className="text-sm text-gray-600 mt-1">
          Quality standards framework · Benchmark program · International deployment · Advisory consortium
        </p>
      </div>

      <div className="flex gap-2 border-b mb-6 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
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
      {tab === "standards" && <StandardsTab />}
      {tab === "benchmarks" && <BenchmarksTab />}
      {tab === "regions" && <RegionsTab />}
      {tab === "consortium" && <ConsortiumTab />}
    </div>
  );
}
