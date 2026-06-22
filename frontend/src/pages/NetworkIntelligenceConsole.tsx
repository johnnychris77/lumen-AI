import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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

async function postJSON(path: string, body: object = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

const WARNING_VARIANT: Record<string, "destructive" | "warning" | "secondary"> = {
  alert: "destructive",
  advisory: "warning",
  watch: "secondary",
};

const STATUS_VARIANT: Record<string, "success" | "warning" | "destructive" | "secondary"> = {
  candidate: "warning",
  under_review: "secondary",
  escalated: "destructive",
  closed: "success",
  suppressed: "secondary",
};

interface NetworkSummary {
  total_active_facilities?: number;
  suppressed?: boolean;
  by_facility_type?: Record<string, number>;
  by_region?: Record<string, number | string>;
}

interface EarlyWarning {
  id: number;
  signal_ref: string;
  instrument_category: string;
  finding_type: string;
  anomaly_score: number;
  n_facilities_reporting: number;
  warning_level: string;
  trend: string;
  status: string;
  last_observed: string;
}

interface ExecSnapshot {
  captured_at: string;
  network_pass_rate_p50: number | null;
  tenant_pass_rate: number | null;
  tenant_defect_rate: number | null;
  network_defect_rate_p50: number | null;
  open_early_warnings_network: number;
  tenant_recall_exposure_score: number;
  network_percentile: number | null;
}

type Tab = "overview" | "lifecycle" | "recall" | "research" | "executive";

export default function NetworkIntelligenceConsole() {
  const [tab, setTab] = useState<Tab>("overview");
  const [tenantId, setTenantId] = useState(localStorage.getItem("tenant_id") || "default-tenant");
  const [summary, setSummary] = useState<NetworkSummary | null>(null);
  const [warnings, setWarnings] = useState<EarlyWarning[]>([]);
  const [snapshots, setSnapshots] = useState<ExecSnapshot[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Lifecycle form state
  const [lcUid, setLcUid] = useState("");
  const [lcMfr, setLcMfr] = useState("");
  const [lcModel, setLcModel] = useState("");
  const [lcCategory, setLcCategory] = useState("laparoscope");

  async function loadOverview() {
    try {
      const [s, w, sn] = await Promise.all([
        fetchJSON("/api/network-intelligence/registry/network-summary"),
        fetchJSON("/api/network-intelligence/recall-early-warning"),
        fetchJSON(`/api/network-intelligence/executive/snapshots?tenant_id=${encodeURIComponent(tenantId)}`),
      ]);
      setSummary(s);
      setWarnings(w.early_warnings || []);
      setSnapshots(sn.snapshots || []);
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => { loadOverview(); /* eslint-disable-next-line */ }, []);

  async function act(fn: () => Promise<string>) {
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const m = await fn();
      setMsg(m);
      await loadOverview();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  const registerFacility = () => act(async () => {
    const r = await postJSON("/api/network-intelligence/registry", {
      tenant_id: tenantId, facility_type: "hospital", participation_tier: "contributor",
    });
    return `Registered as ${r.facility_pseudonym}`;
  });

  const createLifecycleRecord = () => act(async () => {
    await postJSON("/api/network-intelligence/lifecycle/instruments", {
      tenant_id: tenantId, facility_id: "F1",
      instrument_uid: lcUid || `INST-${Date.now()}`,
      manufacturer_name: lcMfr || "Unknown Manufacturer",
      model_name: lcModel || "Unknown Model",
      instrument_category: lcCategory,
    });
    return "Lifecycle record created.";
  });

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Network Overview" },
    { key: "lifecycle", label: "Lifecycle" },
    { key: "recall", label: "Recall Watch" },
    { key: "research", label: "Research" },
    { key: "executive", label: "Executive" },
  ];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-800">Network Intelligence Platform</h1>
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500">Tenant</label>
          <Input value={tenantId} onChange={e => setTenantId(e.target.value)} className="w-44 h-8 text-sm" />
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-slate-200">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-slate-700 text-slate-800"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {err && <p className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">{err}</p>}
      {msg && <p className="text-sm text-emerald-700 bg-emerald-50 rounded px-3 py-2">{msg}</p>}

      {/* ── Overview ── */}
      {tab === "overview" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader><CardTitle className="text-sm">Network Facilities</CardTitle></CardHeader>
              <CardContent>
                {summary?.suppressed ? (
                  <p className="text-xs text-slate-400">Below k-anonymity floor — suppressed</p>
                ) : (
                  <div className="text-3xl font-bold text-slate-800">
                    {summary?.total_active_facilities ?? "—"}
                  </div>
                )}
                <p className="text-xs text-slate-400 mt-1">Active contributors</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-sm">Open Early Warnings</CardTitle></CardHeader>
              <CardContent>
                <div className={`text-3xl font-bold ${
                  warnings.filter(w => ["candidate","under_review","escalated"].includes(w.status)).length > 0
                    ? "text-amber-600" : "text-slate-800"
                }`}>
                  {warnings.filter(w => ["candidate","under_review","escalated"].includes(w.status)).length}
                </div>
                <p className="text-xs text-slate-400 mt-1">Requiring review</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-sm">Network Percentile</CardTitle></CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-slate-800">
                  {snapshots[0]?.network_percentile != null
                    ? `${snapshots[0].network_percentile}%`
                    : "—"}
                </div>
                <p className="text-xs text-slate-400 mt-1">vs. network (latest snapshot)</p>
              </CardContent>
            </Card>
          </div>

          {summary && !summary.suppressed && summary.by_region && (
            <Card>
              <CardHeader><CardTitle className="text-sm">Regional Distribution</CardTitle></CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(summary.by_region).map(([region, count]) => (
                    <Badge key={region} variant="secondary">
                      {region}: {typeof count === "number" ? count : count}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent className="pt-5">
              <Button onClick={registerFacility} disabled={busy} variant="outline" size="sm">
                Register This Facility
              </Button>
              <p className="text-xs text-slate-400 mt-3">
                All network intelligence outputs are anonymized aggregates. Signals are candidate indicators
                requiring human review. LumenAI does not claim FDA clearance or regulatory approval.
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── Lifecycle ── */}
      {tab === "lifecycle" && (
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-sm">Add Instrument Lifecycle Record</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <label className="text-xs text-slate-500">Instrument UID</label>
                  <Input value={lcUid} onChange={e => setLcUid(e.target.value)} placeholder="INST-001" className="h-8 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Manufacturer</label>
                  <Input value={lcMfr} onChange={e => setLcMfr(e.target.value)} placeholder="AcmeSurg" className="h-8 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Model</label>
                  <Input value={lcModel} onChange={e => setLcModel(e.target.value)} placeholder="Trocar-X" className="h-8 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Category</label>
                  <select
                    className="h-8 w-full rounded border border-slate-300 px-2 text-sm"
                    value={lcCategory}
                    onChange={e => setLcCategory(e.target.value)}
                  >
                    {["laparoscope","trocar","forceps","retractor","scissors","clamp","grasper","needle"].map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>
              <Button onClick={createLifecycleRecord} disabled={busy} size="sm">
                Create Record
              </Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-sm">Network Lifecycle Benchmarks</CardTitle></CardHeader>
            <CardContent>
              <NetworkBenchmarkTable />
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── Recall Watch ── */}
      {tab === "recall" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Recall Early Warnings</CardTitle>
          </CardHeader>
          <CardContent>
            {warnings.length === 0 ? (
              <p className="text-sm text-slate-500">No active signals.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-xs uppercase text-slate-400">
                      <th className="py-2 pr-3 text-left">Ref</th>
                      <th className="py-2 pr-3 text-left">Category</th>
                      <th className="py-2 pr-3 text-left">Finding</th>
                      <th className="py-2 pr-3 text-left">Score</th>
                      <th className="py-2 pr-3 text-left">Facilities</th>
                      <th className="py-2 pr-3 text-left">Level</th>
                      <th className="py-2 pr-3 text-left">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {warnings.map(w => (
                      <tr key={w.id} className="border-b last:border-0">
                        <td className="py-2 pr-3 font-mono text-xs">{w.signal_ref}</td>
                        <td className="py-2 pr-3">{w.instrument_category}</td>
                        <td className="py-2 pr-3">{w.finding_type}</td>
                        <td className="py-2 pr-3">{w.anomaly_score.toFixed(2)}</td>
                        <td className="py-2 pr-3">{w.n_facilities_reporting}</td>
                        <td className="py-2 pr-3">
                          <Badge variant={WARNING_VARIANT[w.warning_level] ?? "secondary"}>
                            {w.warning_level}
                          </Badge>
                        </td>
                        <td className="py-2 pr-3">
                          <Badge variant={STATUS_VARIANT[w.status] ?? "secondary"}>
                            {w.status.replace("_", " ")}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="mt-3 text-xs text-slate-400">
              Signals are candidate indicators requiring human review by the network steward.
              Not causation findings. No FDA reporting implied.
            </p>
          </CardContent>
        </Card>
      )}

      {/* ── Research ── */}
      {tab === "research" && (
        <ResearchPanel />
      )}

      {/* ── Executive ── */}
      {tab === "executive" && (
        <div className="space-y-4">
          {snapshots.length === 0 ? (
            <Card>
              <CardContent className="pt-5">
                <p className="text-sm text-slate-500">No executive snapshots captured yet.</p>
              </CardContent>
            </Card>
          ) : (
            snapshots.slice(0, 3).map((snap, i) => (
              <Card key={i}>
                <CardHeader>
                  <CardTitle className="text-sm">
                    Snapshot — {new Date(snap.captured_at).toLocaleDateString()}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <Kpi label="Network Pass Rate p50" value={snap.network_pass_rate_p50} unit="%" />
                    <Kpi label="Your Pass Rate" value={snap.tenant_pass_rate} unit="%" good />
                    <Kpi label="Network Defect Rate p50" value={snap.network_defect_rate_p50} unit="%" invert />
                    <Kpi label="Network Percentile" value={snap.network_percentile} unit="%" good />
                  </div>
                  <div className="mt-3 flex gap-4 text-xs text-slate-500">
                    <span>Open warnings: <strong>{snap.open_early_warnings_network}</strong></span>
                    <span>Recall exposure: <strong>{snap.tenant_recall_exposure_score}</strong></span>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
          <p className="text-xs text-slate-400">
            Executive intelligence outputs are decision-support indicators requiring human review.
            Peer comparison uses anonymized network aggregates only.
          </p>
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value, unit = "", good, invert }: {
  label: string; value: number | null; unit?: string; good?: boolean; invert?: boolean;
}) {
  const color = value == null
    ? "text-slate-400"
    : invert
      ? "text-slate-700"
      : good
        ? "text-emerald-600"
        : "text-slate-700";
  return (
    <div className="rounded border p-3">
      <div className={`text-2xl font-bold ${color}`}>
        {value != null ? `${value}${unit}` : "—"}
      </div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  );
}

function NetworkBenchmarkTable() {
  const [rows, setRows] = useState<Array<{
    id: number; instrument_category: string; metric_name: string;
    n_facilities: number; p50: number; mean: number;
  }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchJSON("/api/network-intelligence/lifecycle/benchmarks")
      .then(r => setRows(r.benchmarks || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-xs text-slate-400">Loading benchmarks…</p>;
  if (rows.length === 0) return <p className="text-sm text-slate-500">No benchmarks published yet.</p>;

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-xs uppercase text-slate-400">
          <th className="py-2 pr-3 text-left">Category</th>
          <th className="py-2 pr-3 text-left">Metric</th>
          <th className="py-2 pr-3 text-left">p50</th>
          <th className="py-2 pr-3 text-left">Mean</th>
          <th className="py-2 pr-3 text-left">Facilities</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(r => (
          <tr key={r.id} className="border-b last:border-0">
            <td className="py-2 pr-3">{r.instrument_category}</td>
            <td className="py-2 pr-3 text-slate-500">{r.metric_name}</td>
            <td className="py-2 pr-3">{r.p50}</td>
            <td className="py-2 pr-3">{r.mean}</td>
            <td className="py-2 pr-3">{r.n_facilities}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ResearchPanel() {
  const [datasets, setDatasets] = useState<Array<{
    id: number; dataset_ref: string; title: string;
    n_facilities_contributing: number; release_status: string;
  }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchJSON("/api/network-intelligence/research/datasets")
      .then(r => setDatasets(r.datasets || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const STATUS_V: Record<string, "success" | "warning" | "secondary"> = {
    released: "success", approved: "warning", draft: "secondary",
  };

  return (
    <Card>
      <CardHeader><CardTitle className="text-sm">Research Datasets</CardTitle></CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-xs text-slate-400">Loading…</p>
        ) : datasets.length === 0 ? (
          <p className="text-sm text-slate-500">No datasets created yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-xs uppercase text-slate-400">
                <th className="py-2 pr-3 text-left">Ref</th>
                <th className="py-2 pr-3 text-left">Title</th>
                <th className="py-2 pr-3 text-left">Facilities</th>
                <th className="py-2 pr-3 text-left">Status</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map(d => (
                <tr key={d.id} className="border-b last:border-0">
                  <td className="py-2 pr-3 font-mono text-xs">{d.dataset_ref}</td>
                  <td className="py-2 pr-3">{d.title}</td>
                  <td className="py-2 pr-3">{d.n_facilities_contributing}</td>
                  <td className="py-2 pr-3">
                    <Badge variant={STATUS_V[d.release_status] ?? "secondary"}>
                      {d.release_status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="mt-3 text-xs text-slate-400">
          All datasets are anonymized aggregates (k-anonymity floor 5). IRB and governance
          approval required before release. No causation claims permitted.
        </p>
      </CardContent>
    </Card>
  );
}
