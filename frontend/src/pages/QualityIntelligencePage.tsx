import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "";
const h = () => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${localStorage.getItem("token") || ""}`,
});

function HumanReviewBadge() {
  return (
    <span className="inline-block rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 border border-amber-200">
      Human Review Required
    </span>
  );
}

function RiskBadge({ score }: { score: number }) {
  const tier = score >= 0.7 ? "high" : score >= 0.4 ? "moderate" : "low";
  const cls = tier === "high" ? "bg-red-100 text-red-800 border-red-200"
    : tier === "moderate" ? "bg-yellow-100 text-yellow-800 border-yellow-200"
    : "bg-green-100 text-green-800 border-green-200";
  return (
    <span className={`inline-block rounded border px-2 py-0.5 text-xs font-semibold capitalize ${cls}`}>
      {tier} ({(score * 100).toFixed(0)}%)
    </span>
  );
}

type Tab = "graph" | "signals" | "emerging" | "investigations" | "recommendations";

export default function QualityIntelligencePage() {
  const [tab, setTab] = useState<Tab>("graph");
  const TABS: { id: Tab; label: string }[] = [
    { id: "graph", label: "Risk Graph" },
    { id: "signals", label: "Quality Signals" },
    { id: "emerging", label: "Emerging Risks" },
    { id: "investigations", label: "Investigations" },
    { id: "recommendations", label: "Recommendations" },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Quality Intelligence</h1>
        <p className="text-sm text-slate-500 mt-1">
          Enterprise risk graph, emerging signals, quality investigations, and preventive recommendations.
        </p>
      </div>
      <div className="rounded border border-amber-300 bg-amber-50 px-4 py-2 text-xs text-amber-800 mb-4">
        <strong>Decision-Support Only:</strong> All outputs represent potential signals and investigation
        candidates. Causation is never implied. Human review required before any operational decision.
      </div>
      <div className="flex gap-1 border-b border-slate-200 mb-6 overflow-x-auto">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors ${
              tab === t.id ? "border-b-2 border-blue-600 text-blue-600" : "text-slate-600 hover:text-slate-900"
            }`}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === "graph" && <RiskGraphTab />}
      {tab === "signals" && <SignalsTab />}
      {tab === "emerging" && <EmergingRisksTab />}
      {tab === "investigations" && <InvestigationsTab />}
      {tab === "recommendations" && <RecommendationsTab />}
    </div>
  );
}

// --- Risk Graph ---
function RiskGraphTab() {
  const [data, setData] = useState<{ nodes: Record<string, unknown>[]; edges: Record<string, unknown>[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [typeFilter, setTypeFilter] = useState("");

  useEffect(() => {
    fetch(`${API}/api/intelligence/risk-graph`, { headers: h() })
      .then((r) => r.json())
      .then((d) => setData({ nodes: d.nodes ?? [], edges: d.edges ?? [] }))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading risk graph…</p>;
  if (!data) return <p className="text-sm text-red-600">Failed to load graph.</p>;

  const nodeTypes = [...new Set(data.nodes.map((n) => String(n.node_type ?? "")))];
  const filtered = typeFilter ? data.nodes.filter((n) => n.node_type === typeFilter) : data.nodes;

  const nodeEdges = (nodeId: unknown) =>
    data.edges.filter((e) => e.source_node_id === nodeId || e.target_node_id === nodeId);

  return (
    <div className="grid md:grid-cols-3 gap-6">
      <div className="md:col-span-2">
        <div className="flex gap-2 mb-3">
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
            className="border border-slate-300 rounded px-2 py-1.5 text-sm">
            <option value="">All node types</option>
            {nodeTypes.map((t) => <option key={t} value={t} className="capitalize">{t}</option>)}
          </select>
          <span className="text-xs text-slate-500 self-center">{filtered.length} nodes · {data.edges.length} edges</span>
        </div>
        <div className="overflow-x-auto rounded border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {["Node", "Type", "Risk Score", "Connections"].map((c) => (
                  <th key={c} className="px-3 py-2 text-left text-xs font-semibold text-slate-600">{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((node, i) => {
                const connections = nodeEdges(node.id ?? node.node_id).length;
                return (
                  <tr key={i} onClick={() => setSelected(node)}
                    className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer">
                    <td className="px-3 py-2 font-medium text-slate-800">{String(node.node_label ?? node.node_id ?? "—")}</td>
                    <td className="px-3 py-2">
                      <span className="text-xs bg-slate-100 text-slate-700 rounded px-1.5 py-0.5 capitalize">
                        {String(node.node_type ?? "—")}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <RiskBadge score={typeof node.risk_score === "number" ? node.risk_score : 0} />
                    </td>
                    <td className="px-3 py-2 text-slate-500">{connections}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-3"><HumanReviewBadge /></div>
      </div>

      <div>
        {selected ? (
          <div className="border border-slate-200 rounded-lg p-4 bg-white">
            <p className="text-sm font-semibold text-slate-800 mb-3">{String(selected.node_label ?? "Node Detail")}</p>
            <div className="space-y-1.5 mb-4">
              {Object.entries(selected).filter(([k]) => !["id", "tenant_id"].includes(k)).map(([k, v]) => (
                <div key={k} className="flex justify-between text-xs">
                  <span className="text-slate-500 capitalize">{k.replace(/_/g, " ")}</span>
                  <span className="text-slate-800 font-medium text-right max-w-[60%] break-all">
                    {typeof v === "number" ? v.toFixed(3) : String(v ?? "—")}
                  </span>
                </div>
              ))}
            </div>
            <p className="text-xs font-semibold text-slate-600 mb-2">Connected Edges</p>
            <div className="space-y-1">
              {nodeEdges(selected.id ?? selected.node_id).map((e, i) => (
                <div key={i} className="text-xs bg-slate-50 rounded px-2 py-1 text-slate-600 capitalize">
                  {String(e.edge_type ?? "—").replace(/_/g, " ")} — weight: {typeof e.weight === "number" ? e.weight.toFixed(2) : "—"}
                </div>
              ))}
              {nodeEdges(selected.id ?? selected.node_id).length === 0 && (
                <p className="text-xs text-slate-400">No edges found.</p>
              )}
            </div>
          </div>
        ) : (
          <div className="border border-dashed border-slate-300 rounded-lg p-6 text-center text-slate-400 text-sm">
            Click a node to view details and connections.
          </div>
        )}
      </div>
    </div>
  );
}

// --- Quality Signals ---
function SignalsTab() {
  const [signals, setSignals] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/intelligence/signals`, { headers: h() })
      .then((r) => r.json())
      .then((d) => setSignals(d.signals ?? d ?? []))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div>
      <div className="grid md:grid-cols-2 gap-4">
        {signals.map((sig, i) => (
          <div key={i} className="border border-slate-200 rounded-lg p-4 bg-white">
            <div className="flex justify-between items-start mb-2">
              <p className="text-sm font-semibold text-slate-800 capitalize">
                {String(sig.signal_type ?? "Signal").replace(/_/g, " ")}
              </p>
              <RiskBadge score={typeof sig.risk_score === "number" ? sig.risk_score : 0} />
            </div>
            <p className="text-xs text-slate-500 mb-2">
              Domain: {String(sig.domain ?? "—")} · Status: {String(sig.status ?? "—")}
            </p>
            {sig.summary && <p className="text-xs text-slate-600 italic">"{String(sig.summary)}"</p>}
            <div className="mt-3"><HumanReviewBadge /></div>
          </div>
        ))}
        {signals.length === 0 && <p className="text-sm text-slate-400 col-span-2 text-center py-8">No signals found.</p>}
      </div>
    </div>
  );
}

// --- Emerging Risks ---
function EmergingRisksTab() {
  const [risks, setRisks] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/intelligence/emerging-risks`, { headers: h() })
      .then((r) => r.json())
      .then((d) => setRisks(d.risks ?? d ?? []))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="space-y-4">
      {risks.map((risk, i) => (
        <div key={i} className="border border-slate-200 rounded-lg p-4 bg-white">
          <div className="flex justify-between items-start mb-2">
            <p className="text-sm font-semibold text-slate-800 capitalize">
              {String(risk.risk_category ?? "Emerging Risk").replace(/_/g, " ")}
            </p>
            <RiskBadge score={typeof risk.risk_score === "number" ? risk.risk_score : 0} />
          </div>
          <p className="text-xs text-slate-500 mb-1">
            Trend: {String(risk.trend_direction ?? "—")} · Confidence: {
              typeof risk.confidence_score === "number" ? (risk.confidence_score * 100).toFixed(0) + "%" : "—"
            }
          </p>
          {risk.contributing_factors && (
            <p className="text-xs text-slate-600">
              Potential contributing factors (not causation): {String(risk.contributing_factors)}
            </p>
          )}
          <div className="mt-3"><HumanReviewBadge /></div>
        </div>
      ))}
      {risks.length === 0 && <p className="text-sm text-slate-400 text-center py-8">No emerging risks detected.</p>}
    </div>
  );
}

// --- Investigations ---
function InvestigationsTab() {
  const [investigations, setInvestigations] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/intelligence/investigations`, { headers: h() })
      .then((r) => r.json())
      .then((d) => setInvestigations(d.investigations ?? d ?? []))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="overflow-x-auto rounded border border-slate-200">
      <table className="w-full text-sm">
        <thead className="bg-slate-50">
          <tr>
            {["Title", "Status", "Priority", "Risk Score", "Opened"].map((c) => (
              <th key={c} className="px-3 py-2 text-left text-xs font-semibold text-slate-600">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {investigations.map((inv, i) => (
            <tr key={i} className="border-t border-slate-100 hover:bg-slate-50">
              <td className="px-3 py-2 font-medium">{String(inv.title ?? "—")}</td>
              <td className="px-3 py-2 capitalize">{String(inv.status ?? "—")}</td>
              <td className="px-3 py-2 capitalize">{String(inv.priority ?? "—")}</td>
              <td className="px-3 py-2">
                <RiskBadge score={typeof inv.risk_score === "number" ? inv.risk_score : 0} />
              </td>
              <td className="px-3 py-2 text-xs text-slate-400">
                {inv.created_at ? new Date(String(inv.created_at)).toLocaleDateString() : "—"}
              </td>
            </tr>
          ))}
          {investigations.length === 0 && (
            <tr><td colSpan={5} className="px-3 py-8 text-center text-slate-400">No investigations found.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// --- Recommendations ---
function RecommendationsTab() {
  const [recs, setRecs] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/intelligence/recommendations`, { headers: h() })
      .then((r) => r.json())
      .then((d) => setRecs(d.recommendations ?? d ?? []))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="space-y-4">
      {recs.map((rec, i) => (
        <div key={i} className="border border-slate-200 rounded-lg p-4 bg-white">
          <div className="flex justify-between items-start mb-2">
            <p className="text-sm font-semibold text-slate-800">{String(rec.title ?? "Recommendation")}</p>
            <span className={`text-xs rounded px-2 py-0.5 border capitalize ${
              rec.priority === "high" ? "bg-red-50 text-red-800 border-red-200"
              : rec.priority === "medium" ? "bg-yellow-50 text-yellow-800 border-yellow-200"
              : "bg-green-50 text-green-800 border-green-200"}`}>
              {String(rec.priority ?? "—")} priority
            </span>
          </div>
          <p className="text-xs text-slate-600 mb-2">{String(rec.description ?? "—")}</p>
          {rec.action_type && (
            <p className="text-xs text-slate-500">Action type: <span className="capitalize">{String(rec.action_type).replace(/_/g, " ")}</span></p>
          )}
          <div className="mt-3"><HumanReviewBadge /></div>
        </div>
      ))}
      {recs.length === 0 && <p className="text-sm text-slate-400 text-center py-8">No recommendations available.</p>}
    </div>
  );
}
