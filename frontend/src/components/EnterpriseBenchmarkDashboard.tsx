/**
 * P5: Enterprise Multi-Hospital Benchmarking & Portfolio Intelligence Dashboard
 * Displays headline KPIs, risk snapshot, leaderboards, and trend insights for
 * Market Directors, SPD Directors, Quality Leaders, and C-suite.
 */
import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("token") || "";
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

interface TrendPoint {
  period_label: string;
  period_start: string;
  value: number;
}

interface HospitalEntry {
  hospital_id: string;
  hospital_name: string;
  compliance_score?: number;
  risk_tier?: string;
  contamination_rate_pct?: number;
}

interface VendorEntry {
  vendor_id: string;
  vendor_name: string;
  vendor_score?: number;
  baseline_adoption_rate_pct?: number;
}

interface ExecutiveDashboard {
  tenant_id: string;
  generated_at: string;
  period_label: string;
  data_source: string;   // "real" | "mock" | "insufficient"
  total_hospitals: number;
  total_inspections_mtd: number;
  portfolio_cleanliness_score: number;
  blood_detections_mtd: number;
  baseline_adoption_rate_pct: number;
  pct_hospitals_compliant: number;
  hospitals_at_critical_risk: number;
  hospitals_at_high_risk: number;
  open_critical_capas: number;
  cleanliness_score_delta: number;
  contamination_rate_delta: number;
  baseline_adoption_delta: number;
  top_performing_hospitals: HospitalEntry[];
  highest_risk_hospitals: HospitalEntry[];
  top_vendors: VendorEntry[];
  lowest_vendors: VendorEntry[];
  contamination_trend: TrendPoint[];
  cleanliness_trend: TrendPoint[];
  baseline_adoption_trend: TrendPoint[];
  spd_director_insights: string[];
  quality_leader_insights: string[];
  market_director_insights: string[];
}

function DeltaBadge({ value, invertColor = false }: { value: number; invertColor?: boolean }) {
  const positive = invertColor ? value < 0 : value > 0;
  const color = value === 0 ? "#6b7280" : positive ? "#10b981" : "#ef4444";
  const sign = value > 0 ? "▲" : value < 0 ? "▼" : "—";
  return (
    <span style={{ color, fontSize: "0.75rem", fontWeight: 600 }}>
      {sign} {Math.abs(value).toFixed(1)}%
    </span>
  );
}

function KPICard({
  label,
  value,
  delta,
  invertDelta,
  unit = "",
  alert = false,
}: {
  label: string;
  value: string | number;
  delta?: number;
  invertDelta?: boolean;
  unit?: string;
  alert?: boolean;
}) {
  return (
    <div
      style={{
        background: alert ? "#fff1f2" : "#fff",
        border: `1px solid ${alert ? "#fca5a5" : "#e5e7eb"}`,
        borderRadius: 8,
        padding: "16px 20px",
        minWidth: 140,
        flex: "1 1 140px",
      }}
    >
      <div style={{ fontSize: "0.72rem", color: "#6b7280", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: "1.6rem", fontWeight: 700, color: alert ? "#dc2626" : "#111827" }}>
        {value}
        {unit && <span style={{ fontSize: "0.9rem", fontWeight: 400 }}>{unit}</span>}
      </div>
      {delta !== undefined && <DeltaBadge value={delta} invertColor={invertDelta} />}
    </div>
  );
}

function RiskBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    low: "#d1fae5",
    medium: "#fef3c7",
    high: "#fee2e2",
    critical: "#fecaca",
  };
  const text: Record<string, string> = {
    low: "#065f46",
    medium: "#92400e",
    high: "#991b1b",
    critical: "#7f1d1d",
  };
  return (
    <span
      style={{
        background: colors[tier] ?? "#f3f4f6",
        color: text[tier] ?? "#374151",
        borderRadius: 4,
        padding: "2px 8px",
        fontSize: "0.7rem",
        fontWeight: 600,
        textTransform: "capitalize",
      }}
    >
      {tier}
    </span>
  );
}

function MiniTrend({ points, color = "#6366f1" }: { points: TrendPoint[]; color?: string }) {
  if (!points.length) return <span style={{ color: "#9ca3af", fontSize: "0.75rem" }}>No data</span>;
  const vals = points.map((p) => p.value);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const w = 120;
  const h = 36;
  const pts = vals
    .map((v, i) => {
      const x = (i / (vals.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth={2} />
    </svg>
  );
}

export function EnterpriseBenchmarkDashboard() {
  const [dashboard, setDashboard] = useState<ExecutiveDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "hospitals" | "vendors" | "insights">(
    "overview"
  );

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/api/enterprise/benchmarks/executive-dashboard`, {
      headers: authHeaders(),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
      .then((data: ExecutiveDashboard) => {
        setDashboard(data);
        setError(null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 24, color: "#6b7280", fontSize: "0.9rem" }}>
        Loading enterprise dashboard…
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div style={{ padding: 24, color: "#dc2626", fontSize: "0.85rem" }}>
        Failed to load enterprise dashboard: {error ?? "Unknown error"}
      </div>
    );
  }

  const tabStyle = (tab: string) => ({
    padding: "6px 14px",
    borderRadius: 6,
    border: "none",
    cursor: "pointer",
    fontWeight: activeTab === tab ? 600 : 400,
    background: activeTab === tab ? "#6366f1" : "transparent",
    color: activeTab === tab ? "#fff" : "#374151",
    fontSize: "0.82rem",
  });

  return (
    <div
      style={{
        background: "#f9fafb",
        borderRadius: 12,
        padding: 24,
        border: "1px solid #e5e7eb",
        marginBottom: 24,
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 700 }}>
            Enterprise Portfolio Intelligence
          </h2>
          <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: 2 }}>
            Period: {dashboard.period_label} · {dashboard.total_hospitals} hospitals ·{" "}
            {dashboard.total_inspections_mtd.toLocaleString()} inspections MTD
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {(["overview", "hospitals", "vendors", "insights"] as const).map((t) => (
            <button key={t} style={tabStyle(t)} onClick={() => setActiveTab(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Data source banner — shown when no real inspection data is available */}
      {dashboard.data_source !== "real" && (
        <div
          style={{
            background: "#fffbeb",
            border: "1px solid #fcd34d",
            borderRadius: 6,
            padding: "10px 14px",
            fontSize: "0.8rem",
            color: "#92400e",
            marginBottom: 16,
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span style={{ fontWeight: 700 }}>⚠ No inspection data for this period.</span>
          {dashboard.data_source === "insufficient"
            ? " Run CV inspections to populate real benchmark data for this portfolio."
            : " Connect your hospital network to see live benchmarks."}
        </div>
      )}

      {/* Headline KPIs */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 20 }}>
        <KPICard
          label="Portfolio Cleanliness"
          value={dashboard.portfolio_cleanliness_score.toFixed(1)}
          unit="%"
          delta={dashboard.cleanliness_score_delta}
        />
        <KPICard
          label="Baseline Adoption"
          value={dashboard.baseline_adoption_rate_pct.toFixed(1)}
          unit="%"
          delta={dashboard.baseline_adoption_delta}
        />
        <KPICard
          label="Hospitals Compliant"
          value={dashboard.pct_hospitals_compliant.toFixed(1)}
          unit="%"
        />
        <KPICard
          label="Blood Detections MTD"
          value={dashboard.blood_detections_mtd}
          alert={dashboard.blood_detections_mtd > 50}
        />
        <KPICard
          label="Critical Risk Hospitals"
          value={dashboard.hospitals_at_critical_risk}
          alert={dashboard.hospitals_at_critical_risk > 0}
        />
        <KPICard
          label="High Risk Hospitals"
          value={dashboard.hospitals_at_high_risk}
          alert={dashboard.hospitals_at_high_risk > 2}
        />
      </div>

      {/* Tab content */}
      {activeTab === "overview" && (
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
          {/* Trend charts */}
          <div style={{ background: "#fff", borderRadius: 8, padding: 16, border: "1px solid #e5e7eb", flex: "1 1 240px" }}>
            <div style={{ fontSize: "0.78rem", fontWeight: 600, color: "#374151", marginBottom: 8 }}>
              Cleanliness Score Trend
            </div>
            <MiniTrend points={dashboard.cleanliness_trend} color="#10b981" />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.68rem", color: "#9ca3af", marginTop: 4 }}>
              {dashboard.cleanliness_trend.slice(0, 1).map((p) => (
                <span key={p.period_label}>{p.period_label}</span>
              ))}
              {dashboard.cleanliness_trend.slice(-1).map((p) => (
                <span key={p.period_label}>{p.period_label}</span>
              ))}
            </div>
          </div>

          <div style={{ background: "#fff", borderRadius: 8, padding: 16, border: "1px solid #e5e7eb", flex: "1 1 240px" }}>
            <div style={{ fontSize: "0.78rem", fontWeight: 600, color: "#374151", marginBottom: 8 }}>
              Contamination Rate Trend
            </div>
            <MiniTrend points={dashboard.contamination_trend} color="#ef4444" />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.68rem", color: "#9ca3af", marginTop: 4 }}>
              {dashboard.contamination_trend.slice(0, 1).map((p) => (
                <span key={p.period_label}>{p.period_label}</span>
              ))}
              {dashboard.contamination_trend.slice(-1).map((p) => (
                <span key={p.period_label}>{p.period_label}</span>
              ))}
            </div>
          </div>

          <div style={{ background: "#fff", borderRadius: 8, padding: 16, border: "1px solid #e5e7eb", flex: "1 1 240px" }}>
            <div style={{ fontSize: "0.78rem", fontWeight: 600, color: "#374151", marginBottom: 8 }}>
              Baseline Adoption Trend
            </div>
            <MiniTrend points={dashboard.baseline_adoption_trend} color="#6366f1" />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.68rem", color: "#9ca3af", marginTop: 4 }}>
              {dashboard.baseline_adoption_trend.slice(0, 1).map((p) => (
                <span key={p.period_label}>{p.period_label}</span>
              ))}
              {dashboard.baseline_adoption_trend.slice(-1).map((p) => (
                <span key={p.period_label}>{p.period_label}</span>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "hospitals" && (
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 280px" }}>
            <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#374151", marginBottom: 8 }}>
              Top Performing
            </div>
            {dashboard.top_performing_hospitals.map((h, i) => (
              <div
                key={h.hospital_id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 12px",
                  background: "#fff",
                  borderRadius: 6,
                  border: "1px solid #e5e7eb",
                  marginBottom: 6,
                }}
              >
                <div>
                  <span style={{ color: "#9ca3af", fontSize: "0.72rem", marginRight: 6 }}>#{i + 1}</span>
                  <span style={{ fontSize: "0.82rem", fontWeight: 500 }}>{h.hospital_name}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {h.compliance_score !== undefined && (
                    <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#065f46" }}>
                      {h.compliance_score.toFixed(1)}%
                    </span>
                  )}
                  {h.risk_tier && <RiskBadge tier={h.risk_tier} />}
                </div>
              </div>
            ))}
          </div>
          <div style={{ flex: "1 1 280px" }}>
            <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#dc2626", marginBottom: 8 }}>
              Highest Risk
            </div>
            {dashboard.highest_risk_hospitals.map((h) => (
              <div
                key={h.hospital_id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 12px",
                  background: "#fff7f7",
                  borderRadius: 6,
                  border: "1px solid #fca5a5",
                  marginBottom: 6,
                }}
              >
                <span style={{ fontSize: "0.82rem", fontWeight: 500 }}>{h.hospital_name}</span>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {h.contamination_rate_pct !== undefined && (
                    <span style={{ fontSize: "0.78rem", color: "#dc2626" }}>
                      {h.contamination_rate_pct.toFixed(1)}% contam
                    </span>
                  )}
                  {h.risk_tier && <RiskBadge tier={h.risk_tier} />}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "vendors" && (
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 280px" }}>
            <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#374151", marginBottom: 8 }}>
              Top Vendors
            </div>
            {dashboard.top_vendors.map((v, i) => (
              <div
                key={v.vendor_id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 12px",
                  background: "#fff",
                  borderRadius: 6,
                  border: "1px solid #e5e7eb",
                  marginBottom: 6,
                }}
              >
                <div>
                  <span style={{ color: "#9ca3af", fontSize: "0.72rem", marginRight: 6 }}>#{i + 1}</span>
                  <span style={{ fontSize: "0.82rem", fontWeight: 500 }}>{v.vendor_name}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {v.vendor_score !== undefined && (
                    <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#6366f1" }}>
                      {v.vendor_score.toFixed(1)}
                    </span>
                  )}
                  {v.baseline_adoption_rate_pct !== undefined && (
                    <span style={{ fontSize: "0.72rem", color: "#6b7280" }}>
                      {v.baseline_adoption_rate_pct.toFixed(0)}% adopt
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div style={{ flex: "1 1 280px" }}>
            <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#dc2626", marginBottom: 8 }}>
              Lowest Vendors
            </div>
            {dashboard.lowest_vendors.map((v) => (
              <div
                key={v.vendor_id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 12px",
                  background: "#fff7f7",
                  borderRadius: 6,
                  border: "1px solid #fca5a5",
                  marginBottom: 6,
                }}
              >
                <span style={{ fontSize: "0.82rem", fontWeight: 500 }}>{v.vendor_name}</span>
                {v.vendor_score !== undefined && (
                  <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#dc2626" }}>
                    {v.vendor_score.toFixed(1)}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "insights" && (
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          {[
            { label: "SPD Director", key: "spd_director_insights" as const, color: "#6366f1" },
            { label: "Quality Leader", key: "quality_leader_insights" as const, color: "#10b981" },
            { label: "Market Director", key: "market_director_insights" as const, color: "#f59e0b" },
          ].map(({ label, key, color }) => (
            <div
              key={key}
              style={{
                flex: "1 1 240px",
                background: "#fff",
                borderRadius: 8,
                padding: 16,
                border: `1px solid ${color}40`,
              }}
            >
              <div
                style={{
                  fontSize: "0.78rem",
                  fontWeight: 700,
                  color,
                  marginBottom: 10,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                {label}
              </div>
              <ul style={{ margin: 0, paddingLeft: 16 }}>
                {dashboard[key].map((insight, i) => (
                  <li
                    key={i}
                    style={{ fontSize: "0.8rem", color: "#374151", marginBottom: 6, lineHeight: 1.45 }}
                  >
                    {insight}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
