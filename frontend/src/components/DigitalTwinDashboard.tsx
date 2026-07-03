/**
 * P10: Digital Twin of SPD Operations Dashboard
 * Real-time twin of the full SPD workflow with what-if simulation.
 */
import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";


function authHeaders() {
  const token = localStorage.getItem("token") ?? "dev-token";
  return { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" };
}

// ---- Types ----
interface StationStatus {
  id: number;
  station_name: string;
  station_type: string;
  capacity: number;
  current_load: number;
  utilization_pct: number;
  status: string;
  avg_processing_time_minutes: number;
}

interface FlowRecord {
  id: number;
  instrument_name: string;
  from_station: string;
  to_station: string;
  station_type: string;
  arrived_at: string;
  processing_time_minutes: number;
  outcome: string;
}

interface AlertRecord {
  id: number;
  alert_type: string;
  severity: string;
  station_name: string;
  message: string;
  metric_value: number;
  threshold_value: number;
  acknowledged: boolean;
  created_at: string;
}

interface WhatIfResult {
  id: number | null;
  scenario_name: string;
  baseline: Record<string, number>;
  simulated: Record<string, number>;
  delta: Record<string, number | string>;
  recommendation: string;
  created_at: string;
}

interface TwinState {
  tenant_id: string;
  throughput_per_hour: number;
  bottleneck_station: string;
  avg_cycle_time_minutes: number;
  utilization_pct: number;
  total_instruments_in_flight: number;
  data_source: string;
  stations: StationStatus[];
  kpis: Record<string, number>;
}

// ---- Helpers ----
function utilizationColor(pct: number): string {
  if (pct >= 90) return "#dc2626";
  if (pct >= 70) return "#d97706";
  return "#16a34a";
}

function severityColor(sev: string): string {
  switch (sev) {
    case "critical": return "#dc2626";
    case "high": return "#ea580c";
    case "medium": return "#d97706";
    default: return "#16a34a";
  }
}

function outcomeColor(outcome: string): string {
  switch (outcome) {
    case "passed": return "#16a34a";
    case "failed": return "#dc2626";
    case "quarantined": return "#7c3aed";
    default: return "#6b7280";
  }
}

// ---- Station Card ----
function StationCard({ s }: { s: StationStatus }) {
  const color = utilizationColor(s.utilization_pct);
  return (
    <div style={{
      border: `1px solid ${color}`,
      borderRadius: 8,
      padding: "12px",
      background: "#1e1e2e",
      minWidth: 180,
    }}>
      <div style={{ fontWeight: 600, fontSize: 13, color: "#e2e8f0", marginBottom: 4 }}>
        {s.station_name}
      </div>
      <div style={{
        display: "inline-block",
        background: "#334155",
        color: "#94a3b8",
        borderRadius: 4,
        padding: "2px 8px",
        fontSize: 11,
        marginBottom: 8,
      }}>
        {s.station_type}
      </div>
      <div style={{ marginBottom: 6 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#94a3b8", marginBottom: 2 }}>
          <span>Load: {s.current_load}/{s.capacity}</span>
          <span style={{ color }}>{s.utilization_pct.toFixed(1)}%</span>
        </div>
        <div style={{ height: 6, background: "#334155", borderRadius: 3 }}>
          <div style={{
            width: `${Math.min(s.utilization_pct, 100)}%`,
            height: "100%",
            background: color,
            borderRadius: 3,
            transition: "width 0.3s",
          }} />
        </div>
      </div>
      <div style={{
        fontSize: 11,
        color: s.status === "active" ? "#16a34a" : "#dc2626",
        fontWeight: 500,
      }}>
        {s.status.toUpperCase()}
      </div>
    </div>
  );
}

// ---- Main Component ----
export function DigitalTwinDashboard() {
  const [tab, setTab] = useState<"live" | "flow" | "whatif" | "alerts">("live");
  const [twinState, setTwinState] = useState<TwinState | null>(null);
  const [flows, setFlows] = useState<FlowRecord[]>([]);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [scenarios, setScenarios] = useState<WhatIfResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // What-if form
  const [scenarioName, setScenarioName] = useState("");
  const [addStation, setAddStation] = useState("");
  const [removeStation, setRemoveStation] = useState("");
  const [volumeChange, setVolumeChange] = useState(0);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function fetchTwinState() {
    setLoading(true);
    try {
      const r = await apiFetch(`/api/digital-twin/state`, { raw: true, headers: authHeaders() });
      if (r.ok) setTwinState(await r.json());
      else setError("Failed to load twin state");
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  async function fetchFlows() {
    const r = await apiFetch(`/api/digital-twin/flow?limit=20`, { raw: true, headers: authHeaders() });
    if (r.ok) setFlows(await r.json());
  }

  async function fetchAlerts() {
    const r = await apiFetch(`/api/digital-twin/alerts`, { raw: true, headers: authHeaders() });
    if (r.ok) setAlerts(await r.json());
  }

  async function fetchScenarios() {
    const r = await apiFetch(`/api/digital-twin/whatif`, { raw: true, headers: authHeaders() });
    if (r.ok) setScenarios(await r.json());
  }

  useEffect(() => {
    fetchTwinState();
    fetchFlows();
    fetchAlerts();
    fetchScenarios();
  }, []);

  async function runWhatIf(e: React.FormEvent) {
    e.preventDefault();
    if (!scenarioName.trim()) return;
    setSubmitting(true);
    try {
      const payload: Record<string, unknown> = {
        scenario_name: scenarioName,
        volume_change_pct: volumeChange,
      };
      if (addStation) payload.add_station = addStation;
      if (removeStation) payload.remove_station = removeStation;

      const r = await apiFetch(`/api/digital-twin/whatif`, { raw: true,
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload),
      });
      if (r.ok) {
        const result = await r.json();
        setWhatIfResult(result);
        fetchScenarios();
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function acknowledgeAlert(alertId: number) {
    await apiFetch(`/api/digital-twin/alerts/${alertId}/acknowledge`, { raw: true,
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ acknowledged_by: "dashboard-user" }),
    });
    fetchAlerts();
  }

  const tabs = [
    { key: "live", label: "Live Twin" },
    { key: "flow", label: "Instrument Flow" },
    { key: "whatif", label: "What-If Simulator" },
    { key: "alerts", label: `Alerts${alerts.length ? ` (${alerts.length})` : ""}` },
  ];

  return (
    <div style={{ background: "#0f172a", color: "#e2e8f0", borderRadius: 12, padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: "#f1f5f9" }}>
            Digital Twin — SPD Operations
          </h2>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "#64748b" }}>
            Real-time workflow twin with bottleneck detection and what-if simulation
          </p>
        </div>
        {twinState && (
          <div style={{ display: "flex", gap: 16 }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#38bdf8" }}>{twinState.throughput_per_hour.toFixed(0)}</div>
              <div style={{ fontSize: 11, color: "#64748b" }}>instruments/hr</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#a78bfa" }}>{twinState.total_instruments_in_flight}</div>
              <div style={{ fontSize: 11, color: "#64748b" }}>in-flight</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: utilizationColor(twinState.utilization_pct) }}>
                {twinState.utilization_pct.toFixed(1)}%
              </div>
              <div style={{ fontSize: 11, color: "#64748b" }}>utilization</div>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 20, borderBottom: "1px solid #1e293b", paddingBottom: 0 }}>
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key as typeof tab)}
            style={{
              background: tab === t.key ? "#1e40af" : "transparent",
              color: tab === t.key ? "#fff" : "#94a3b8",
              border: "none",
              borderRadius: "6px 6px 0 0",
              padding: "8px 16px",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: tab === t.key ? 600 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <div style={{ color: "#dc2626", marginBottom: 12 }}>{error}</div>}
      {loading && <div style={{ color: "#64748b" }}>Loading twin state...</div>}

      {/* Tab: Live Twin */}
      {tab === "live" && twinState && (
        <div>
          {twinState.bottleneck_station && (
            <div style={{ background: "#7c2d12", borderRadius: 6, padding: "8px 14px", marginBottom: 16, fontSize: 13 }}>
              Bottleneck detected: <strong>{twinState.bottleneck_station}</strong>
            </div>
          )}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {twinState.stations.map(s => <StationCard key={s.id} s={s} />)}
          </div>
          <div style={{ marginTop: 16, display: "flex", gap: 24, fontSize: 13, color: "#94a3b8" }}>
            <span>Avg cycle time: <strong style={{ color: "#e2e8f0" }}>{twinState.avg_cycle_time_minutes.toFixed(1)} min</strong></span>
            <span>Data source: <strong style={{ color: "#e2e8f0" }}>{twinState.data_source}</strong></span>
          </div>
        </div>
      )}

      {/* Tab: Instrument Flow */}
      {tab === "flow" && (
        <div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ color: "#64748b", borderBottom: "1px solid #1e293b" }}>
                <th style={{ textAlign: "left", padding: "8px 12px" }}>Instrument</th>
                <th style={{ textAlign: "left", padding: "8px 12px" }}>From → To</th>
                <th style={{ textAlign: "left", padding: "8px 12px" }}>Arrived</th>
                <th style={{ textAlign: "right", padding: "8px 12px" }}>Time (min)</th>
                <th style={{ textAlign: "center", padding: "8px 12px" }}>Outcome</th>
              </tr>
            </thead>
            <tbody>
              {flows.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>No flow records yet</td>
                </tr>
              )}
              {flows.map(f => (
                <tr key={f.id} style={{ borderBottom: "1px solid #0f172a" }}>
                  <td style={{ padding: "8px 12px" }}>{f.instrument_name}</td>
                  <td style={{ padding: "8px 12px", color: "#94a3b8" }}>
                    {f.from_station ? `${f.from_station} → ` : ""}{f.to_station}
                  </td>
                  <td style={{ padding: "8px 12px", color: "#64748b" }}>
                    {new Date(f.arrived_at).toLocaleTimeString()}
                  </td>
                  <td style={{ padding: "8px 12px", textAlign: "right" }}>
                    {f.processing_time_minutes.toFixed(1)}
                  </td>
                  <td style={{ padding: "8px 12px", textAlign: "center" }}>
                    <span style={{
                      background: outcomeColor(f.outcome),
                      color: "#fff",
                      borderRadius: 4,
                      padding: "2px 8px",
                      fontSize: 11,
                    }}>
                      {f.outcome}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: What-If Simulator */}
      {tab === "whatif" && (
        <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 20 }}>
          <div>
            <form onSubmit={runWhatIf}>
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 4 }}>Scenario Name *</label>
                <input
                  value={scenarioName}
                  onChange={e => setScenarioName(e.target.value)}
                  placeholder="e.g. Add decon bay"
                  required
                  style={{ width: "100%", background: "#1e293b", border: "1px solid #334155", borderRadius: 6, padding: "7px 10px", color: "#e2e8f0", fontSize: 13, boxSizing: "border-box" }}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 4 }}>Add Station Type</label>
                <select
                  value={addStation}
                  onChange={e => setAddStation(e.target.value)}
                  style={{ width: "100%", background: "#1e293b", border: "1px solid #334155", borderRadius: 6, padding: "7px 10px", color: "#e2e8f0", fontSize: 13 }}
                >
                  <option value="">— none —</option>
                  <option value="decontamination">Decontamination</option>
                  <option value="inspection">Inspection</option>
                  <option value="sterilization">Sterilization</option>
                  <option value="storage">Storage</option>
                  <option value="dispatch">Dispatch</option>
                </select>
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 4 }}>Remove Station</label>
                <select
                  value={removeStation}
                  onChange={e => setRemoveStation(e.target.value)}
                  style={{ width: "100%", background: "#1e293b", border: "1px solid #334155", borderRadius: 6, padding: "7px 10px", color: "#e2e8f0", fontSize: 13 }}
                >
                  <option value="">— none —</option>
                  {twinState?.stations.map(s => (
                    <option key={s.id} value={s.station_name}>{s.station_name}</option>
                  ))}
                </select>
              </div>
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 4 }}>
                  Volume Change: {volumeChange > 0 ? "+" : ""}{volumeChange}%
                </label>
                <input
                  type="range"
                  min={-50}
                  max={100}
                  value={volumeChange}
                  onChange={e => setVolumeChange(Number(e.target.value))}
                  style={{ width: "100%" }}
                />
              </div>
              <button
                type="submit"
                disabled={submitting}
                style={{ width: "100%", background: "#1e40af", color: "#fff", border: "none", borderRadius: 6, padding: "9px 0", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
              >
                {submitting ? "Simulating..." : "Run Simulation"}
              </button>
            </form>

            {scenarios.length > 0 && (
              <div style={{ marginTop: 20 }}>
                <div style={{ fontSize: 12, color: "#64748b", marginBottom: 8 }}>Recent Scenarios</div>
                {scenarios.slice(0, 5).map(sc => (
                  <div
                    key={sc.id}
                    onClick={() => setWhatIfResult(sc)}
                    style={{
                      padding: "8px 10px",
                      background: "#1e293b",
                      borderRadius: 6,
                      marginBottom: 6,
                      cursor: "pointer",
                      fontSize: 12,
                      color: "#94a3b8",
                    }}
                  >
                    {sc.scenario_name}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            {whatIfResult ? (
              <div>
                <h3 style={{ margin: "0 0 12px", fontSize: 15, color: "#f1f5f9" }}>{whatIfResult.scenario_name}</h3>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ color: "#64748b", borderBottom: "1px solid #1e293b" }}>
                      <th style={{ textAlign: "left", padding: "8px 12px" }}>Metric</th>
                      <th style={{ textAlign: "right", padding: "8px 12px" }}>Baseline</th>
                      <th style={{ textAlign: "right", padding: "8px 12px" }}>Simulated</th>
                      <th style={{ textAlign: "right", padding: "8px 12px" }}>Delta</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.keys(whatIfResult.baseline).filter(k => typeof whatIfResult.baseline[k] === "number").map(metric => {
                      const d = whatIfResult.delta[metric];
                      const dNum = typeof d === "number" ? d : 0;
                      return (
                        <tr key={metric} style={{ borderBottom: "1px solid #0f172a" }}>
                          <td style={{ padding: "8px 12px", color: "#94a3b8" }}>{metric.replace(/_/g, " ")}</td>
                          <td style={{ padding: "8px 12px", textAlign: "right" }}>
                            {typeof whatIfResult.baseline[metric] === "number" ? (whatIfResult.baseline[metric] as number).toFixed(1) : "—"}
                          </td>
                          <td style={{ padding: "8px 12px", textAlign: "right" }}>
                            {typeof whatIfResult.simulated[metric] === "number" ? (whatIfResult.simulated[metric] as number).toFixed(1) : "—"}
                          </td>
                          <td style={{ padding: "8px 12px", textAlign: "right", color: dNum > 0 ? "#16a34a" : dNum < 0 ? "#dc2626" : "#64748b" }}>
                            {dNum > 0 ? "+" : ""}{dNum.toFixed(2)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <div style={{ marginTop: 14, background: "#1e293b", borderRadius: 6, padding: "10px 14px", fontSize: 13, color: "#94a3b8" }}>
                  <strong style={{ color: "#e2e8f0" }}>Recommendation:</strong> {whatIfResult.recommendation}
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200, color: "#334155", fontSize: 14 }}>
                Configure and run a simulation to see results
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab: Alerts */}
      {tab === "alerts" && (
        <div>
          {alerts.length === 0 && (
            <div style={{ textAlign: "center", padding: 40, color: "#334155" }}>No open alerts</div>
          )}
          {alerts.map(a => (
            <div
              key={a.id}
              style={{
                background: "#1e293b",
                borderLeft: `4px solid ${severityColor(a.severity)}`,
                borderRadius: "0 6px 6px 0",
                padding: "12px 16px",
                marginBottom: 10,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
              }}
            >
              <div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                  <span style={{
                    background: severityColor(a.severity),
                    color: "#fff",
                    fontSize: 10,
                    borderRadius: 3,
                    padding: "2px 6px",
                    fontWeight: 600,
                    textTransform: "uppercase",
                  }}>
                    {a.severity}
                  </span>
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>{a.alert_type.replace(/_/g, " ")}</span>
                  {a.station_name && (
                    <span style={{ fontSize: 12, color: "#64748b" }}>— {a.station_name}</span>
                  )}
                </div>
                <div style={{ fontSize: 13, color: "#e2e8f0" }}>{a.message}</div>
                <div style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>
                  {new Date(a.created_at).toLocaleString()}
                </div>
              </div>
              <button
                onClick={() => acknowledgeAlert(a.id)}
                style={{
                  background: "#334155",
                  color: "#94a3b8",
                  border: "none",
                  borderRadius: 6,
                  padding: "6px 12px",
                  cursor: "pointer",
                  fontSize: 12,
                  whiteSpace: "nowrap",
                  marginLeft: 12,
                }}
              >
                Acknowledge
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
