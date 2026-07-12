/**
 * LumenAI AI Specialist — Project Sentinel-X: Clinical Risk Intelligence &
 * Patient Safety Agent.
 *
 * Frontend route `/risk`, API prefix `/api/sentinelx`. Distinct from the
 * pre-existing, unrelated "Project Sentinel" system at `/sentinel` (API
 * `/api/sentinel`) -- Sentinel-X never touches that system's data.
 *
 * Sentinel-X does not replace human clinical judgment. It prioritizes risk
 * and explains why -- every assessment is explainable, evidence-based,
 * confidence-scored, auditable, and subject to human review.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Json = Record<string, unknown>;

const TABS = [
  "Risk Dashboard", "Supervisor Workspace", "Patient Safety Alerts", "Heatmaps",
] as const;
type Tab = (typeof TABS)[number];

const HEATMAP_DIMENSIONS = ["facility", "department", "instrument_family", "anatomy", "manufacturer", "service_line"];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {children}
    </div>
  );
}

function JsonView({ data }: { data: unknown }) {
  return <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(data, null, 2)}</pre>;
}

export default function SentinelXRiskDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("Risk Dashboard");

  const [dashboard, setDashboard] = useState<Json | null>(null);
  const [supervisorWorkspace, setSupervisorWorkspace] = useState<Json | null>(null);
  const [alerts, setAlerts] = useState<Json[] | null>(null);
  const [heatmapDimension, setHeatmapDimension] = useState(HEATMAP_DIMENSIONS[0]);
  const [heatmap, setHeatmap] = useState<Json | null>(null);

  useEffect(() => {
    if (activeTab === "Risk Dashboard") api.get("/api/sentinelx/dashboard").then(setDashboard).catch(() => {});
    if (activeTab === "Supervisor Workspace") api.get("/api/sentinelx/supervisor-workspace").then(setSupervisorWorkspace).catch(() => {});
    if (activeTab === "Patient Safety Alerts") api.get("/api/sentinelx/alerts").then((r: Json) => setAlerts(r.alerts as Json[])).catch(() => {});
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === "Heatmaps") {
      api.get(`/api/sentinelx/heatmaps/${heatmapDimension}`).then(setHeatmap).catch(() => {});
    }
  }, [activeTab, heatmapDimension]);

  function scanForAlerts() {
    api.post("/api/sentinelx/alerts/scan", {}).then(() => api.get("/api/sentinelx/alerts")).then((r: Json) => setAlerts(r.alerts as Json[])).catch(() => {});
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Clinical Risk Intelligence</h1>
      <p className="text-xs text-slate-400">
        Sentinel-X continuously evaluates clinical, operational, and inspection risk before an instrument
        proceeds through the pre-sterilization workflow. It does not replace human clinical judgment -- it
        prioritizes risk and explains why.
      </p>

      <div className="flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`rounded px-3 py-1 text-sm ${activeTab === t ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {activeTab === "Risk Dashboard" && (
        <Section title="Enterprise, Facility, Instrument, Anatomy, Workflow, Education, Knowledge &amp; Digital Twin Risk">
          {dashboard && <JsonView data={dashboard} />}
        </Section>
      )}

      {activeTab === "Supervisor Workspace" && (
        <Section title="Highest-Risk Inspections, Pending Reviews &amp; Recommended Priorities">
          {supervisorWorkspace && <JsonView data={supervisorWorkspace} />}
        </Section>
      )}

      {activeTab === "Patient Safety Alerts" && (
        <Section title="Proactive Patient Safety Watch">
          <button className="mb-3 rounded bg-indigo-600 px-3 py-1 text-sm text-white" onClick={scanForAlerts}>
            Scan for New Alerts
          </button>
          {alerts && <JsonView data={alerts} />}
        </Section>
      )}

      {activeTab === "Heatmaps" && (
        <Section title="Enterprise Risk Heatmap">
          <select
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            value={heatmapDimension}
            onChange={(e) => setHeatmapDimension(e.target.value)}
          >
            {HEATMAP_DIMENSIONS.map((d) => (
              <option key={d} value={d}>{d.replace(/_/g, " ")}</option>
            ))}
          </select>
          {heatmap && <div className="mt-3"><JsonView data={heatmap} /></div>}
        </Section>
      )}
    </div>
  );
}
