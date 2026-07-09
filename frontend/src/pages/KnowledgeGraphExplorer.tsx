import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

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

interface FamilyProfile {
  family_key: string;
  display_name: string;
  typical_anatomy: string[];
  high_risk_zones: string[];
  typical_contamination: string[];
  typical_damage: string[];
  typical_repair_issues: string[];
  inspection_priorities: string[];
  cleaning_priorities: string[];
  supervisor_focus_areas: string[];
  anatomy_family_note?: string;
}

interface ChainStep {
  node: string;
  value: unknown;
  outcome?: string;
  note?: string | null;
}

interface ReasoningResult {
  chain: ChainStep[];
  narrative: string;
}

interface Analytics {
  most_common_findings_by_manufacturer: { key: string; count: number }[];
  most_common_findings_by_anatomy: { key: string; count: number }[];
  highest_risk_anatomy_zone: string | null;
  most_common_repair_reason: { key: string; count: number }[];
  most_common_supervisor_override: { key: string; count: number }[];
  most_difficult_instrument_family: string | null;
  most_missed_anatomy_zones: { zone: string; missed_count: number; case_count: number }[];
  most_common_contamination_type: { key: string; count: number }[];
}

const EXPLORE_CATEGORIES = [
  "manufacturer", "instrument", "model", "finding", "zone",
  "failure_mode", "recommendation", "supervisor_learning", "instrument_family",
] as const;

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block text-xs bg-gray-100 text-gray-700 rounded px-2 py-0.5 mr-1 mb-1">
      {children}
    </span>
  );
}

function FamilyCard({ profile }: { profile: FamilyProfile }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="rounded-lg border bg-white p-4">
      <button className="w-full text-left" onClick={() => setExpanded((e) => !e)}>
        <p className="font-semibold text-gray-900">{profile.display_name}</p>
        <p className="text-xs text-gray-500 mt-1">{profile.typical_anatomy.length} anatomy zones · {profile.high_risk_zones.length} high-risk</p>
      </button>
      {expanded && (
        <div className="mt-3 space-y-2 text-sm">
          {profile.anatomy_family_note && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">{profile.anatomy_family_note}</p>
          )}
          <div><span className="font-medium">Typical anatomy: </span>{profile.typical_anatomy.map((z) => <Tag key={z}>{z}</Tag>)}</div>
          <div><span className="font-medium">Typical contamination: </span>{profile.typical_contamination.map((z) => <Tag key={z}>{z}</Tag>)}</div>
          <div><span className="font-medium">Typical damage: </span>{profile.typical_damage.map((z) => <Tag key={z}>{z}</Tag>)}</div>
          <div><span className="font-medium">Inspection priorities: </span>{profile.inspection_priorities.map((z) => <Tag key={z}>{z}</Tag>)}</div>
          <div><span className="font-medium">Cleaning priorities: </span>{profile.cleaning_priorities.map((z) => <Tag key={z}>{z}</Tag>)}</div>
          <div><span className="font-medium">Supervisor focus: </span>{profile.supervisor_focus_areas.map((z) => <Tag key={z}>{z}</Tag>)}</div>
        </div>
      )}
    </div>
  );
}

function ReasoningChainPanel() {
  const [instrumentType, setInstrumentType] = useState("kerrison rongeur");
  const [findingType, setFindingType] = useState("blood");
  const [manufacturer, setManufacturer] = useState("");
  const [result, setResult] = useState<ReasoningResult | null>(null);
  const [loading, setLoading] = useState(false);

  const run = () => {
    setLoading(true);
    const params = new URLSearchParams({ instrument_type: instrumentType, finding_type: findingType, manufacturer });
    fetchJSON(`/api/knowledge-graph/reasoning-chain?${params}`)
      .then(setResult)
      .finally(() => setLoading(false));
  };

  useEffect(() => { run(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="flex flex-wrap gap-2 mb-4">
        <input value={instrumentType} onChange={(e) => setInstrumentType(e.target.value)} placeholder="Instrument type"
          className="text-sm border rounded px-2 py-1 flex-1 min-w-[160px]" />
        <input value={findingType} onChange={(e) => setFindingType(e.target.value)} placeholder="Finding type"
          className="text-sm border rounded px-2 py-1 flex-1 min-w-[140px]" />
        <input value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} placeholder="Manufacturer (optional)"
          className="text-sm border rounded px-2 py-1 flex-1 min-w-[160px]" />
        <button onClick={run} className="text-sm bg-blue-600 text-white rounded px-3 py-1">Trace reasoning</button>
      </div>
      {loading && <p className="text-sm text-gray-400">Reasoning…</p>}
      {result && !loading && (
        <>
          <div className="flex flex-wrap items-center gap-1 mb-4">
            {result.chain.map((step, i) => (
              <span key={step.node} className="flex items-center gap-1">
                <span className="text-xs bg-blue-50 border border-blue-200 text-blue-800 rounded px-2 py-1">
                  <span className="font-semibold">{step.node}:</span>{" "}
                  {Array.isArray(step.value) ? step.value.join(", ") || "—" : String(step.value ?? "—")}
                </span>
                {i < result.chain.length - 1 && <span className="text-gray-300">→</span>}
              </span>
            ))}
          </div>
          <p className="text-sm text-gray-800 bg-gray-50 border rounded p-3">{result.narrative}</p>
        </>
      )}
    </div>
  );
}

interface SPDRule {
  id: string;
  title: string;
  description: string;
  severity: string;
  spd_risk: string;
  recommendation: string[];
}

const RISK_TAG: Record<string, string> = {
  Low: "bg-emerald-50 text-emerald-800 border-emerald-200",
  Moderate: "bg-amber-50 text-amber-800 border-amber-200",
  High: "bg-orange-50 text-orange-800 border-orange-200",
  Critical: "bg-red-50 text-red-800 border-red-200",
};

function SPDRuleLibrary() {
  const [rules, setRules] = useState<SPDRule[]>([]);

  useEffect(() => {
    fetchJSON("/api/decision-rules/library").then((d) => setRules(d.rules)).catch(() => {});
  }, []);

  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
      {rules.map((rule) => (
        <div key={rule.id} className="rounded-lg border bg-white p-4">
          <div className="flex items-center justify-between gap-2 mb-1">
            <p className="font-semibold text-gray-900 text-sm">{rule.title}</p>
            <span className={`text-xs font-medium rounded-full border px-2 py-0.5 ${RISK_TAG[rule.spd_risk] ?? RISK_TAG.Moderate}`}>{rule.spd_risk}</span>
          </div>
          <p className="text-xs text-gray-500 mb-2">{rule.description}</p>
          <ul className="list-disc list-inside text-xs text-gray-700 space-y-0.5">
            {rule.recommendation.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      ))}
    </div>
  );
}

function Explorer() {
  const [category, setCategory] = useState<(typeof EXPLORE_CATEGORIES)[number]>("zone");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<unknown>(null);

  const run = () => {
    const params = new URLSearchParams({ category, q: query });
    fetchJSON(`/api/knowledge-graph/explore?${params}`).then((d) => setResults(d.results));
  };

  useEffect(() => { run(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [category]);

  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="flex flex-wrap gap-2 mb-3">
        {EXPLORE_CATEGORIES.map((c) => (
          <button key={c} onClick={() => setCategory(c)}
            className={`text-xs px-2 py-1 rounded border ${category === c ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-700 border-gray-300"}`}>
            {c.replace("_", " ")}
          </button>
        ))}
      </div>
      <div className="flex gap-2 mb-3">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search…"
          className="text-sm border rounded px-2 py-1 flex-1" onKeyDown={(e) => e.key === "Enter" && run()} />
        <button onClick={run} className="text-sm bg-gray-800 text-white rounded px-3 py-1">Search</button>
      </div>
      <pre className="text-xs bg-gray-50 border rounded p-3 overflow-x-auto max-h-80 overflow-y-auto">
        {JSON.stringify(results, null, 2)}
      </pre>
    </div>
  );
}

export default function KnowledgeGraphExplorer() {
  const [families, setFamilies] = useState<FamilyProfile[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJSON("/api/knowledge-graph/instrument-families").then((d) => setFamilies(d.families)).catch((e) => setError(String(e)));
    fetchJSON("/api/knowledge-graph/analytics").then(setAnalytics).catch(() => {});
  }, []);

  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">SPD Clinical Knowledge Graph</h1>
        <p className="text-sm text-gray-500 mt-1">
          Traceable reasoning from instrument identity through anatomy, findings, risk, and recommended action —
          not a black-box detector.
        </p>
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <section>
        <SectionHeader title="Clinical Reasoning Chain" subtitle="Trace how LumenAI reasons from instrument + finding to a recommended action." />
        <ReasoningChainPanel />
      </section>

      <section>
        <SectionHeader title="Instrument Family Intelligence" subtitle="Knowledge profiles for the ten instrument families SPD sees most often." />
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {families.map((f) => <FamilyCard key={f.family_key} profile={f} />)}
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between">
          <SectionHeader title="SPD Rule Library" subtitle="Structured, code-shipped clinical decision rules — description, evidence, severity, risk, recommendation." />
          <Link to="/supervisor-rule-builder" className="text-sm text-blue-600 hover:underline whitespace-nowrap">Supervisor Rule Builder →</Link>
        </div>
        <SPDRuleLibrary />
      </section>

      <section>
        <SectionHeader title="Knowledge Graph Explorer" subtitle="Browse by manufacturer, instrument, model, finding, zone, failure mode, recommendation, or supervisor learning." />
        <Explorer />
      </section>

      {analytics && (
        <section>
          <SectionHeader title="Enterprise Knowledge Analytics" />
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div className="rounded-lg border bg-white p-4">
              <p className="font-medium mb-2">Highest-risk anatomy zone</p>
              <p className="text-gray-700">{analytics.highest_risk_anatomy_zone ?? "Not enough data yet."}</p>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <p className="font-medium mb-2">Most difficult instrument family</p>
              <p className="text-gray-700">{analytics.most_difficult_instrument_family ?? "Not enough data yet."}</p>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <p className="font-medium mb-2">Most common contamination type</p>
              {analytics.most_common_contamination_type.map((c) => (
                <p key={c.key} className="text-gray-700">{c.key}: {c.count}</p>
              ))}
              {analytics.most_common_contamination_type.length === 0 && <p className="text-gray-400">No data yet.</p>}
            </div>
            <div className="rounded-lg border bg-white p-4">
              <p className="font-medium mb-2">Most missed anatomy zones</p>
              {analytics.most_missed_anatomy_zones.map((z) => (
                <p key={z.zone} className="text-gray-700">{z.zone}: {z.missed_count}/{z.case_count} missed</p>
              ))}
              {analytics.most_missed_anatomy_zones.length === 0 && <p className="text-gray-400">No pilot validation data yet.</p>}
            </div>
          </div>
        </section>
      )}

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
        ⚠ Knowledge-graph reasoning is advisory clinical knowledge, not a substitute for the device IFU or
        supervisor judgment. Every recommendation requires human validation before disposition.
      </p>
    </div>
  );
}
