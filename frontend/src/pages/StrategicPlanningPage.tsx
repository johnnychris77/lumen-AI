/**
 * v4.6 — Project Vanguard, Section 5: Strategic Planning Workspace.
 * Frontend route `/strategy`. Every generator button below calls a real
 * `/api/vanguard/strategy/generate/{initiative_type}` endpoint backed by
 * real composed data — no fabricated projection.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Initiative {
  id: number;
  initiative_type: string;
  title: string;
  status: string;
  rationale: string;
  created_at: string;
}

const INITIATIVE_TYPES = ["scenario_planning", "capital_planning", "quality_initiative", "service_line_expansion", "capacity_planning"];
const STATUSES = ["draft", "under_review", "approved", "archived"];

export default function StrategicPlanningPage() {
  const [initiatives, setInitiatives] = useState<Initiative[]>([]);
  const [filterType, setFilterType] = useState("");
  const [scenarioText, setScenarioText] = useState("");
  const [loading, setLoading] = useState(false);

  async function refresh() {
    const res = await api.get<{ initiatives: Initiative[] }>(`/api/vanguard/strategy/initiatives${filterType ? `?initiative_type=${filterType}` : ""}`);
    setInitiatives(res.initiatives);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterType]);

  async function generate(initiativeType: string) {
    setLoading(true);
    try {
      const payload = initiativeType === "scenario_planning" ? { scenario_description: scenarioText || "Untitled scenario" } : {};
      await api.post(`/api/vanguard/strategy/generate/${initiativeType}`, payload);
      await refresh();
      if (initiativeType === "scenario_planning") setScenarioText("");
    } finally {
      setLoading(false);
    }
  }

  async function setStatus(id: number, status: string) {
    await api.patch(`/api/vanguard/strategy/initiatives/${id}/status`, { status });
    await refresh();
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Strategic Planning Workspace</h1>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Generate a new initiative</h3>
        <div className="mb-3 flex gap-2">
          <input
            className="flex-1 rounded border border-slate-300 p-2 text-sm"
            placeholder="Scenario description (for Scenario Planning)"
            value={scenarioText}
            onChange={(e) => setScenarioText(e.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {INITIATIVE_TYPES.map((t) => (
            <button
              key={t} disabled={loading}
              className="rounded bg-indigo-600 px-3 py-1 text-xs text-white disabled:opacity-50"
              onClick={() => generate(t)}
            >
              {t.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">Initiatives</h3>
          <select className="rounded border border-slate-300 p-1 text-sm" value={filterType} onChange={(e) => setFilterType(e.target.value)}>
            <option value="">All types</option>
            {INITIATIVE_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        <ul className="space-y-2">
          {initiatives.map((i) => (
            <li key={i.id} className="rounded border border-slate-200 p-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">{i.title}</span>
                <select
                  className="rounded border border-slate-300 p-1 text-xs"
                  value={i.status}
                  onChange={(e) => setStatus(i.id, e.target.value)}
                >
                  {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                </select>
              </div>
              <p className="mt-1 text-xs text-slate-500">{i.initiative_type.replace(/_/g, " ")} · {new Date(i.created_at).toLocaleString()}</p>
              <p className="mt-1 text-xs text-slate-600">{i.rationale}</p>
            </li>
          ))}
          {!initiatives.length && <p className="text-xs text-slate-400">No initiatives yet — generate one above.</p>}
        </ul>
      </div>
    </div>
  );
}
