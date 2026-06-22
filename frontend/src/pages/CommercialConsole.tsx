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

async function postJSON(path: string, body: object) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function money(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-lg font-semibold text-gray-800">{title}</h2>
      {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
    </div>
  );
}

const HEALTH_COLOR: Record<string, string> = {
  healthy: "bg-green-100 text-green-800 border-green-300",
  watch: "bg-yellow-100 text-yellow-800 border-yellow-300",
  at_risk: "bg-red-100 text-red-800 border-red-300",
};

function PricingEstimator() {
  const [facilities, setFacilities] = useState(5);
  const [termYears, setTermYears] = useState(1);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  async function estimate() {
    setErr(null);
    try {
      const r = await postJSON("/api/commercial/pricing/estimate", {
        num_facilities: facilities,
        term_years: termYears,
      });
      setResult(r);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  useEffect(() => {
    estimate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facilities, termYears]);

  return (
    <section className="border rounded-lg p-4 bg-white">
      <SectionHeader title="Pricing Estimator" subtitle="Non-binding list estimate; not a quote." />
      <div className="flex flex-wrap gap-6 items-end">
        <label className="text-sm">
          Facilities: <span className="font-semibold">{facilities}</span>
          <input
            type="range"
            min={1}
            max={30}
            value={facilities}
            onChange={(e) => setFacilities(Number(e.target.value))}
            className="block w-48"
          />
        </label>
        <label className="text-sm">
          Term (years)
          <select
            value={termYears}
            onChange={(e) => setTermYears(Number(e.target.value))}
            className="block border rounded px-2 py-1"
          >
            <option value={1}>1</option>
            <option value={2}>2</option>
            <option value={3}>3</option>
          </select>
        </label>
      </div>
      {err && <p className="text-red-600 text-sm mt-2">{err}</p>}
      {result && (
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div className="border rounded p-2">
            <div className="text-xs text-gray-500">Recommended tier</div>
            <div className="font-semibold capitalize">{result.recommended_tier?.replace("_", " ")}</div>
          </div>
          <div className="border rounded p-2">
            <div className="text-xs text-gray-500">Gross annual</div>
            <div className="font-semibold">{money(result.gross_annual_usd)}</div>
          </div>
          <div className="border rounded p-2">
            <div className="text-xs text-gray-500">Total discount</div>
            <div className="font-semibold">{result.total_discount_pct}%</div>
          </div>
          <div className="border rounded p-2 bg-green-50">
            <div className="text-xs text-gray-500">Net annual</div>
            <div className="font-bold text-green-800">{money(result.net_annual_usd)}</div>
          </div>
        </div>
      )}
    </section>
  );
}

function RoiCalculator() {
  const [monthly, setMonthly] = useState(2000);
  const [facilities, setFacilities] = useState(5);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  async function calc() {
    setErr(null);
    try {
      const r = await postJSON("/api/commercial/roi/calculate", {
        monthly_inspections: monthly,
        num_facilities: facilities,
      });
      setResult(r);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  useEffect(() => {
    calc();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [monthly, facilities]);

  return (
    <section className="border rounded-lg p-4 bg-white">
      <SectionHeader title="ROI Calculator" subtitle="Modeled estimate from validated pilot constants. Not a guarantee." />
      <div className="flex flex-wrap gap-6 items-end">
        <label className="text-sm">
          Monthly inspections / facility: <span className="font-semibold">{monthly}</span>
          <input
            type="range"
            min={200}
            max={10000}
            step={200}
            value={monthly}
            onChange={(e) => setMonthly(Number(e.target.value))}
            className="block w-48"
          />
        </label>
        <label className="text-sm">
          Facilities: <span className="font-semibold">{facilities}</span>
          <input
            type="range"
            min={1}
            max={30}
            value={facilities}
            onChange={(e) => setFacilities(Number(e.target.value))}
            className="block w-48"
          />
        </label>
      </div>
      {err && <p className="text-red-600 text-sm mt-2">{err}</p>}
      {result && (
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div className="border rounded p-2">
            <div className="text-xs text-gray-500">Gross benefit</div>
            <div className="font-semibold">{money(result.savings?.gross_benefit_usd)}</div>
          </div>
          <div className="border rounded p-2">
            <div className="text-xs text-gray-500">Annual cost</div>
            <div className="font-semibold">{money(result.annual_cost_usd)}</div>
          </div>
          <div className="border rounded p-2 bg-green-50">
            <div className="text-xs text-gray-500">Net benefit</div>
            <div className="font-bold text-green-800">{money(result.net_benefit_usd)}</div>
          </div>
          <div className="border rounded p-2">
            <div className="text-xs text-gray-500">ROI / Payback</div>
            <div className="font-semibold">
              {result.roi_pct ?? "—"}% / {result.payback_months ?? "—"} mo
            </div>
          </div>
        </div>
      )}
      <p className="text-xs text-gray-400 italic mt-2">
        ROI estimate for business-case modeling only. Validate assumptions before contracting.
      </p>
    </section>
  );
}

function ExpansionBoard() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetchJSON("/api/commercial/expansion/opportunities")
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <p className="text-red-600 text-sm">{err}</p>;
  if (!data) return <p className="text-gray-400 text-sm">Loading expansion signals…</p>;

  return (
    <section className="border rounded-lg p-4 bg-white">
      <SectionHeader
        title="Expansion & Renewal Signals"
        subtitle="Candidate signals for account-team review only."
      />
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <h3 className="text-sm font-semibold text-green-700 mb-1">
            Opportunities ({data.opportunity_count})
          </h3>
          {data.opportunities?.length ? (
            <ul className="text-sm space-y-1">
              {data.opportunities.map((o: any, i: number) => (
                <li key={i} className="border rounded p-2">
                  <span className="font-medium">{o.tenant_id}</span> — {o.signal} (
                  {o.utilization_pct}% util)
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 text-sm">None.</p>
          )}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-red-700 mb-1">
            Renewal risks ({data.renewal_risk_count})
          </h3>
          {data.renewal_risks?.length ? (
            <ul className="text-sm space-y-1">
              {data.renewal_risks.map((r: any, i: number) => (
                <li key={i} className="border rounded p-2">
                  <span className="font-medium">{r.tenant_id}</span> — {r.signal} (
                  {r.change_pct}%)
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 text-sm">None.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function HealthScore() {
  const [tenant, setTenant] = useState("");
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setErr(null);
    try {
      const q = tenant ? `?tenant_id=${encodeURIComponent(tenant)}` : "";
      setData(await fetchJSON(`/api/commercial/customer-success/health-score${q}`));
    } catch (e: any) {
      setErr(e.message);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="border rounded-lg p-4 bg-white">
      <SectionHeader title="Customer Health Score" subtitle="Operational triage indicator, not a clinical measure." />
      <div className="flex gap-2 items-end mb-3">
        <label className="text-sm">
          Tenant ID (optional)
          <input
            value={tenant}
            onChange={(e) => setTenant(e.target.value)}
            className="block border rounded px-2 py-1"
            placeholder="all tenants"
          />
        </label>
        <button onClick={load} className="px-3 py-1 bg-blue-600 text-white rounded text-sm">
          Load
        </button>
      </div>
      {err && <p className="text-red-600 text-sm">{err}</p>}
      {data && (
        <div className="flex flex-wrap gap-3 items-center">
          <div className={`border rounded-lg px-4 py-2 ${HEALTH_COLOR[data.status] || ""}`}>
            <div className="text-xs uppercase">{data.status}</div>
            <div className="text-2xl font-bold">{data.composite_score}</div>
          </div>
          {Object.entries(data.dimensions || {}).map(([k, v]: any) => (
            <div key={k} className="border rounded p-2 text-sm">
              <div className="text-xs text-gray-500 capitalize">{k}</div>
              <div className="font-semibold">{v}</div>
            </div>
          ))}
          <div className="text-xs text-gray-400">source: {data.source}</div>
        </div>
      )}
    </section>
  );
}

export default function CommercialConsole() {
  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Commercial Console</h1>
        <p className="text-sm text-gray-500">
          Sales enablement: packaging, pricing, ROI, customer health, and expansion signals.
        </p>
      </div>
      <PricingEstimator />
      <RoiCalculator />
      <HealthScore />
      <ExpansionBoard />
      <p className="text-xs text-gray-400 italic">
        All figures are estimates for modeling only; not quotes. LumenAI does not claim FDA
        clearance or regulatory approval. All quality signals require human review.
      </p>
    </div>
  );
}
