import React, { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL ?? "";

function getHeaders() {
  const token = localStorage.getItem("token") || "";
  return {
    Authorization: `Bearer ${token}`,
    "X-LumenAI-Role": "operator",
  };
}

const TENANT_ID = "default-tenant";

type EvidenceFactor = {
  factor: string;
  value: number | string;
  weight: number;
  signal: string;
};

type FailurePrediction = {
  instrument_name: string;
  risk_score: number;
  failure_probability: number;
  risk_category: string;
  recommended_action: string;
  data_source: string;
};

type RepairForecast = {
  instrument_name: string;
  repair_probability_90d: number;
  replacement_probability_180d: number;
  estimated_repair_cost_usd: number;
  estimated_replacement_cost_usd: number;
  risk_category: string;
  risk_score: number;
};

type RecallRisk = {
  instrument_category: string;
  exposure_score: number;
  urgency_tier: string;
  active_recall_count: number;
  recommended_action: string;
};

type TrayRisk = {
  tray_id: string;
  tray_risk_score: number;
  risk_category: string;
  instrument_count: number;
  high_risk_instrument_count: number;
  highest_risk_instrument: string;
  worst_failure_probability: number;
  recommended_action: string;
  evidence: EvidenceFactor[];
  data_source: string;
};

type Dashboard = {
  predicted_failures_30d: number;
  predicted_failures_90d: number;
  high_risk_instrument_count: number;
  critical_risk_instrument_count: number;
  projected_repair_cost_usd: number;
  projected_replacement_cost_usd: number;
  contamination_recurrence_rate_pct: number;
  recall_exposure_score: number;
  highest_risk_instruments: {
    instrument_name: string;
    risk_score: number;
    failure_probability: number;
    risk_category: string;
    recommended_action: string;
  }[];
  top_contamination_risks: {
    instrument_name: string;
    risk_score: number;
    dominant_contaminant: string;
    recurrence_probability: number;
  }[];
  recall_risk_by_category: RecallRisk[];
  top_risk_factors: string[];
  recommended_actions: string[];
  data_source: string;
};

function riskColor(cat: string): string {
  switch (cat) {
    case "critical": return "#dc2626";
    case "high": return "#ea580c";
    case "medium": return "#ca8a04";
    default: return "#16a34a";
  }
}

function urgencyColor(tier: string): string {
  switch (tier) {
    case "critical": return "#dc2626";
    case "act": return "#ea580c";
    case "watch": return "#ca8a04";
    default: return "#6b7280";
  }
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      background: color,
      color: "#fff",
      padding: "2px 8px",
      borderRadius: 9999,
      fontSize: 11,
      fontWeight: 600,
      textTransform: "uppercase",
    }}>
      {label}
    </span>
  );
}

function KpiCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div style={{
      background: "#1e293b",
      borderRadius: 10,
      padding: "18px 22px",
      minWidth: 140,
      flex: 1,
    }}>
      <div style={{ color: "#94a3b8", fontSize: 12, marginBottom: 4 }}>{label}</div>
      <div style={{ color: "#f1f5f9", fontSize: 28, fontWeight: 700 }}>{value}</div>
      {sub && <div style={{ color: "#64748b", fontSize: 11, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function MockBanner() {
  return (
    <div style={{
      background: "#fef9c3",
      border: "1px solid #fde047",
      borderRadius: 8,
      padding: "10px 16px",
      marginBottom: 16,
      color: "#92400e",
      fontSize: 13,
    }}>
      Demo mode: Showing seeded representative data. Connect CV inspection records to see live predictions.
    </div>
  );
}

export function PredictiveAnalyticsDashboard() {
  const [tab, setTab] = useState<"risk" | "repair" | "recall" | "tray">("risk");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [repairs, setRepairs] = useState<RepairForecast[]>([]);
  const [recallRisks, setRecallRisks] = useState<RecallRisk[]>([]);
  const [trayRisk, setTrayRisk] = useState<TrayRisk | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const params = `tenant_id=${TENANT_ID}`;
    Promise.all([
      fetch(`${API}/api/predictions/dashboard?${params}`, { headers: getHeaders() }).then(r => r.json()),
      fetch(`${API}/api/predictions/repairs?${params}`, { headers: getHeaders() }).then(r => r.json()),
      fetch(`${API}/api/predictions/recall-risk?${params}`, { headers: getHeaders() }).then(r => r.json()),
      fetch(`${API}/api/predictions/tray-risk?${params}&tray_id=default-tray`, { headers: getHeaders() }).then(r => r.json()),
    ]).then(([d, r, rc, t]) => {
      if (d.dashboard) setDashboard(d.dashboard);
      if (r.forecasts) setRepairs(r.forecasts);
      if (rc.recall_risks) setRecallRisks(rc.recall_risks);
      if (t.tray_risk) setTrayRisk(t.tray_risk);
    }).catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const tabs = [
    { key: "risk", label: "Predictive Risk" },
    { key: "repair", label: "Repair Forecasting" },
    { key: "recall", label: "Recall Exposure" },
    { key: "tray", label: "Tray Stability" },
  ] as const;

  return (
    <div style={{ color: "#f1f5f9", fontFamily: "system-ui, sans-serif" }}>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4, color: "#f8fafc" }}>
        P7: Predictive Instrument Failure Analytics
      </h2>
      <p style={{ color: "#94a3b8", fontSize: 13, marginBottom: 20 }}>
        AI-powered failure, contamination, repair, and recall risk predictions across your instrument inventory.
      </p>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 24, borderBottom: "1px solid #334155", paddingBottom: 0 }}>
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              padding: "8px 18px",
              background: tab === t.key ? "#3b82f6" : "transparent",
              color: tab === t.key ? "#fff" : "#94a3b8",
              border: "none",
              borderRadius: "6px 6px 0 0",
              cursor: "pointer",
              fontWeight: tab === t.key ? 700 : 400,
              fontSize: 13,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && <div style={{ color: "#94a3b8", padding: 20 }}>Loading predictions...</div>}
      {error && <div style={{ color: "#f87171", padding: 20 }}>Error: {error}</div>}

      {/* Tab 1: Predictive Risk */}
      {tab === "risk" && dashboard && (
        <div>
          {dashboard.data_source !== "real" && <MockBanner />}
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
            <KpiCard label="Predicted Failures (30d)" value={dashboard.predicted_failures_30d} />
            <KpiCard label="Predicted Failures (90d)" value={dashboard.predicted_failures_90d} />
            <KpiCard label="High-Risk Instruments" value={dashboard.high_risk_instrument_count} />
            <KpiCard label="Critical-Risk Instruments" value={dashboard.critical_risk_instrument_count} />
            <KpiCard label="Contamination Recurrence" value={`${dashboard.contamination_recurrence_rate_pct}%`} />
          </div>

          {dashboard.recommended_actions.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "#fbbf24", marginBottom: 8 }}>Recommended Actions</h3>
              {dashboard.recommended_actions.map((a, i) => (
                <div key={i} style={{
                  background: "#422006",
                  border: "1px solid #92400e",
                  borderRadius: 8,
                  padding: "10px 14px",
                  marginBottom: 8,
                  fontSize: 13,
                  color: "#fef3c7",
                }}>
                  {a}
                </div>
              ))}
            </div>
          )}

          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#cbd5e1", marginBottom: 10 }}>Highest-Risk Instruments</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ color: "#64748b", borderBottom: "1px solid #334155" }}>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Instrument</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Risk Score</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Failure Prob.</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Category</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.highest_risk_instruments.map((inst, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #1e293b" }}>
                  <td style={{ padding: "8px 8px", color: "#e2e8f0" }}>{inst.instrument_name}</td>
                  <td style={{ padding: "8px 8px", color: riskColor(inst.risk_category), fontWeight: 700 }}>{inst.risk_score.toFixed(1)}</td>
                  <td style={{ padding: "8px 8px" }}>{(inst.failure_probability * 100).toFixed(1)}%</td>
                  <td style={{ padding: "8px 8px" }}><Badge label={inst.risk_category} color={riskColor(inst.risk_category)} /></td>
                  <td style={{ padding: "8px 8px", color: "#94a3b8", fontSize: 12 }}>{inst.recommended_action}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {dashboard.top_risk_factors.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "#cbd5e1", marginBottom: 8 }}>Top Risk Factors</h3>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {dashboard.top_risk_factors.map((f, i) => (
                  <span key={i} style={{
                    background: "#1e293b",
                    color: "#94a3b8",
                    padding: "4px 12px",
                    borderRadius: 9999,
                    fontSize: 12,
                  }}>{f}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Repair Forecasting */}
      {tab === "repair" && (
        <div>
          {repairs.length > 0 && repairs[0].risk_score !== undefined && (
            <>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
                <KpiCard
                  label="Projected Repair Cost"
                  value={`$${repairs.filter(r => r.risk_score >= 25).reduce((s, r) => s + r.estimated_repair_cost_usd, 0).toLocaleString("en-US", { maximumFractionDigits: 0 })}`}
                  sub="instruments at medium+ risk"
                />
                <KpiCard
                  label="Projected Replacement Cost"
                  value={`$${repairs.filter(r => r.risk_score >= 75).reduce((s, r) => s + r.estimated_replacement_cost_usd, 0).toLocaleString("en-US", { maximumFractionDigits: 0 })}`}
                  sub="critical-risk instruments"
                />
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ color: "#64748b", borderBottom: "1px solid #334155" }}>
                    <th style={{ textAlign: "left", padding: "6px 8px" }}>Instrument</th>
                    <th style={{ textAlign: "left", padding: "6px 8px" }}>Repair Prob (90d)</th>
                    <th style={{ textAlign: "left", padding: "6px 8px" }}>Replace Prob (180d)</th>
                    <th style={{ textAlign: "left", padding: "6px 8px" }}>Repair Cost</th>
                    <th style={{ textAlign: "left", padding: "6px 8px" }}>Replace Cost</th>
                    <th style={{ textAlign: "left", padding: "6px 8px" }}>Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {[...repairs].sort((a, b) => b.risk_score - a.risk_score).map((f, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid #1e293b" }}>
                      <td style={{ padding: "8px 8px", color: "#e2e8f0" }}>{f.instrument_name}</td>
                      <td style={{ padding: "8px 8px" }}>{(f.repair_probability_90d * 100).toFixed(1)}%</td>
                      <td style={{ padding: "8px 8px" }}>{(f.replacement_probability_180d * 100).toFixed(1)}%</td>
                      <td style={{ padding: "8px 8px", color: "#fbbf24" }}>${f.estimated_repair_cost_usd.toLocaleString("en-US", { maximumFractionDigits: 0 })}</td>
                      <td style={{ padding: "8px 8px", color: "#f87171" }}>${f.estimated_replacement_cost_usd.toLocaleString("en-US", { maximumFractionDigits: 0 })}</td>
                      <td style={{ padding: "8px 8px" }}><Badge label={f.risk_category} color={riskColor(f.risk_category)} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}

      {/* Tab 3: Recall Exposure */}
      {tab === "recall" && (
        <div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
            <KpiCard
              label="Max Recall Exposure Score"
              value={recallRisks.length > 0 ? Math.max(...recallRisks.map(r => r.exposure_score)).toFixed(1) : "—"}
            />
            <KpiCard
              label="Active Recalls"
              value={recallRisks.reduce((s, r) => s + r.active_recall_count, 0)}
            />
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ color: "#64748b", borderBottom: "1px solid #334155" }}>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Category</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Exposure Score</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Urgency</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Active Recalls</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {[...recallRisks].sort((a, b) => b.exposure_score - a.exposure_score).map((r, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #1e293b" }}>
                  <td style={{ padding: "8px 8px", color: "#e2e8f0", textTransform: "capitalize" }}>{r.instrument_category}</td>
                  <td style={{ padding: "8px 8px", color: urgencyColor(r.urgency_tier), fontWeight: 700 }}>{r.exposure_score.toFixed(1)}</td>
                  <td style={{ padding: "8px 8px" }}><Badge label={r.urgency_tier} color={urgencyColor(r.urgency_tier)} /></td>
                  <td style={{ padding: "8px 8px" }}>{r.active_recall_count}</td>
                  <td style={{ padding: "8px 8px", color: "#94a3b8", fontSize: 12 }}>{r.recommended_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 4: Tray Stability */}
      {tab === "tray" && trayRisk && (
        <div>
          {trayRisk.data_source !== "real" && <MockBanner />}
          <div style={{ display: "flex", gap: 20, alignItems: "flex-start", marginBottom: 24 }}>
            <div style={{
              background: "#1e293b",
              borderRadius: 12,
              padding: "24px 32px",
              textAlign: "center",
              minWidth: 160,
            }}>
              <div style={{ color: "#94a3b8", fontSize: 12, marginBottom: 8 }}>Tray Risk Score</div>
              <div style={{
                fontSize: 52,
                fontWeight: 800,
                color: riskColor(trayRisk.risk_category),
                lineHeight: 1,
              }}>
                {trayRisk.tray_risk_score.toFixed(1)}
              </div>
              <div style={{ marginTop: 8 }}>
                <Badge label={trayRisk.risk_category} color={riskColor(trayRisk.risk_category)} />
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
                <KpiCard label="Instruments" value={trayRisk.instrument_count} />
                <KpiCard label="High-Risk Instruments" value={trayRisk.high_risk_instrument_count} />
                <KpiCard label="Worst Failure Prob." value={`${(trayRisk.worst_failure_probability * 100).toFixed(1)}%`} />
              </div>
              <div style={{
                background: "#1e293b",
                borderRadius: 8,
                padding: "12px 16px",
                marginBottom: 12,
              }}>
                <div style={{ color: "#64748b", fontSize: 11, marginBottom: 4 }}>Highest-Risk Instrument</div>
                <div style={{ color: "#fbbf24", fontWeight: 600 }}>{trayRisk.highest_risk_instrument}</div>
              </div>
              <div style={{
                background: "#422006",
                border: "1px solid #92400e",
                borderRadius: 8,
                padding: "10px 14px",
                fontSize: 13,
                color: "#fef3c7",
              }}>
                {trayRisk.recommended_action}
              </div>
            </div>
          </div>

          <h3 style={{ fontSize: 14, fontWeight: 600, color: "#cbd5e1", marginBottom: 10 }}>Evidence Factors</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ color: "#64748b", borderBottom: "1px solid #334155" }}>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Factor</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Value</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Weight</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Signal</th>
              </tr>
            </thead>
            <tbody>
              {trayRisk.evidence.map((ev, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #1e293b" }}>
                  <td style={{ padding: "8px 8px", color: "#e2e8f0" }}>{ev.factor.replace(/_/g, " ")}</td>
                  <td style={{ padding: "8px 8px" }}>{String(ev.value)}</td>
                  <td style={{ padding: "8px 8px" }}>{(ev.weight * 100).toFixed(0)}%</td>
                  <td style={{ padding: "8px 8px" }}>
                    <Badge
                      label={ev.signal}
                      color={ev.signal === "elevated" || ev.signal === "degrading" || ev.signal === "below_threshold" ? "#ea580c" : "#16a34a"}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default PredictiveAnalyticsDashboard;
