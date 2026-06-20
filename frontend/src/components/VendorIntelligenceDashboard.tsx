/**
 * P6: Vendor Intelligence Exchange & Manufacturer Collaboration Network Dashboard
 * Executive intelligence view covering vendor scorecards, manufacturer quality,
 * shared defect signals, active recalls, and CAPA effectiveness.
 */
import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("token") || "";
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

interface VendorScorecard {
  vendor_id: string;
  vendor_name: string;
  composite_score: number;
  risk_tier: string;
  baseline_adoption_rate_pct: number;
  defect_rate_pct: number;
  capa_closure_rate_pct: number;
  contamination_recurrence_rate_pct: number;
  portfolio_rank: number;
  data_source: string;
}

interface ManufacturerScorecard {
  manufacturer_id: string;
  manufacturer_name: string;
  composite_score: number;
  risk_tier: string;
  baseline_quality_score: number;
  inspection_pass_rate_pct: number;
  recall_count: number;
  capa_effectiveness_score: number;
  portfolio_rank: number;
  data_source: string;
}

interface SharedDefectSignal {
  id: number;
  signal_type: string;
  instrument_category: string;
  finding_category: string;
  occurrence_count: number;
  severity: string;
  confidence_score: number;
}

interface RecallEvent {
  id: number;
  recall_number: string;
  recall_title: string;
  severity: string;
  status: string;
  source: string;
  recall_date: string;
  affected_instrument_categories: string[];
}

interface CapaEffectiveness {
  total_capas: number;
  open_capas: number;
  closed_capas: number;
  overdue_capas: number;
  closure_rate_pct: number;
  avg_closure_days: number;
  effectiveness_score: number;
  data_source: string;
}

interface IntelligenceDashboard {
  tenant_id: string;
  period_label: string;
  period_type: string;
  generated_at: string;
  data_source: string;
  total_vendors_scored: number;
  avg_vendor_composite_score: number;
  vendors_at_high_risk: number;
  vendors_at_critical_risk: number;
  total_manufacturers_scored: number;
  avg_manufacturer_composite_score: number;
  active_shared_defect_signals: number;
  active_recalls: number;
  critical_recalls: number;
  capa_effectiveness: CapaEffectiveness;
  vendor_scorecards: VendorScorecard[];
  manufacturer_scorecards: ManufacturerScorecard[];
  shared_defect_signals: SharedDefectSignal[];
  recall_events: RecallEvent[];
}

function KPICard({
  label,
  value,
  unit = "",
  alert = false,
}: {
  label: string;
  value: string | number;
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
      <div style={{ fontSize: "1.5rem", fontWeight: 700, color: alert ? "#dc2626" : "#111827" }}>
        {value}
        {unit && <span style={{ fontSize: "0.85rem", fontWeight: 400 }}> {unit}</span>}
      </div>
    </div>
  );
}

function RiskBadge({ tier }: { tier: string }) {
  const bg: Record<string, string> = {
    low: "#d1fae5", medium: "#fef3c7", high: "#fee2e2", critical: "#fecaca",
  };
  const fg: Record<string, string> = {
    low: "#065f46", medium: "#92400e", high: "#991b1b", critical: "#7f1d1d",
  };
  return (
    <span
      style={{
        background: bg[tier] ?? "#f3f4f6",
        color: fg[tier] ?? "#374151",
        borderRadius: 4,
        padding: "2px 8px",
        fontSize: "0.7rem",
        fontWeight: 600,
        textTransform: "uppercase",
      }}
    >
      {tier}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const bg: Record<string, string> = {
    critical: "#fecaca", high: "#fee2e2", medium: "#fef3c7",
    low: "#d1fae5", advisory: "#dbeafe",
  };
  return (
    <span
      style={{
        background: bg[severity] ?? "#f3f4f6",
        borderRadius: 4,
        padding: "2px 8px",
        fontSize: "0.7rem",
        fontWeight: 600,
        textTransform: "uppercase",
      }}
    >
      {severity}
    </span>
  );
}

function ScoreBar({ value }: { value: number }) {
  const color = value >= 85 ? "#10b981" : value >= 70 ? "#f59e0b" : value >= 50 ? "#ef4444" : "#7f1d1d";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, background: "#f3f4f6", borderRadius: 4, height: 8 }}>
        <div style={{ width: `${value}%`, background: color, borderRadius: 4, height: 8 }} />
      </div>
      <span style={{ fontSize: "0.8rem", fontWeight: 600, color, minWidth: 36 }}>
        {value.toFixed(0)}
      </span>
    </div>
  );
}

export default function VendorIntelligenceDashboard({ tenantId = "default-tenant" }: { tenantId?: string }) {
  const [dashboard, setDashboard] = useState<IntelligenceDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"vendors" | "manufacturers" | "intelligence">("vendors");

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const res = await fetch(
          `${API_BASE}/api/intelligence/dashboard?tenant_id=${encodeURIComponent(tenantId)}`,
          { headers: authHeaders() }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setDashboard(data.dashboard);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load intelligence dashboard");
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, [tenantId]);

  if (loading) {
    return (
      <div style={{ padding: 32, textAlign: "center", color: "#6b7280" }}>
        Loading Vendor Intelligence Dashboard...
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div style={{ padding: 32, color: "#dc2626" }}>
        Error loading intelligence dashboard: {error}
      </div>
    );
  }

  const tabs = [
    { id: "vendors" as const, label: `Vendors (${dashboard.total_vendors_scored})` },
    { id: "manufacturers" as const, label: `Manufacturers (${dashboard.total_manufacturers_scored})` },
    { id: "intelligence" as const, label: `Intelligence (${dashboard.active_shared_defect_signals} signals)` },
  ];

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", background: "#f9fafb", minHeight: "100vh", padding: 24 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: "1.4rem", fontWeight: 700, color: "#111827" }}>
          Vendor Intelligence Exchange
        </h2>
        <div style={{ fontSize: "0.8rem", color: "#6b7280", marginTop: 4 }}>
          Period: {dashboard.period_label} &bull; Tenant: {dashboard.tenant_id} &bull;{" "}
          Data: {dashboard.data_source} &bull; Generated: {new Date(dashboard.generated_at).toLocaleString()}
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 24 }}>
        <KPICard label="Avg Vendor Score" value={dashboard.avg_vendor_composite_score.toFixed(1)} unit="/ 100" />
        <KPICard label="Vendors Scored" value={dashboard.total_vendors_scored} />
        <KPICard label="High Risk Vendors" value={dashboard.vendors_at_high_risk} alert={dashboard.vendors_at_high_risk > 0} />
        <KPICard label="Critical Risk Vendors" value={dashboard.vendors_at_critical_risk} alert={dashboard.vendors_at_critical_risk > 0} />
        <KPICard label="Avg Mfr Score" value={dashboard.avg_manufacturer_composite_score.toFixed(1)} unit="/ 100" />
        <KPICard label="Active Recalls" value={dashboard.active_recalls} alert={dashboard.active_recalls > 0} />
        <KPICard label="Critical Recalls" value={dashboard.critical_recalls} alert={dashboard.critical_recalls > 0} />
        <KPICard label="Defect Signals" value={dashboard.active_shared_defect_signals} />
        <KPICard label="CAPA Effectiveness" value={dashboard.capa_effectiveness.effectiveness_score.toFixed(1)} unit="/ 100" />
        <KPICard label="CAPA Closure Rate" value={`${dashboard.capa_effectiveness.closure_rate_pct.toFixed(1)}%`} />
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 0, marginBottom: 0, borderBottom: "2px solid #e5e7eb" }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              padding: "10px 20px",
              border: "none",
              background: "none",
              cursor: "pointer",
              fontSize: "0.9rem",
              fontWeight: activeTab === t.id ? 700 : 400,
              color: activeTab === t.id ? "#2563eb" : "#6b7280",
              borderBottom: activeTab === t.id ? "2px solid #2563eb" : "2px solid transparent",
              marginBottom: -2,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderTop: "none", borderRadius: "0 0 8px 8px", padding: 20 }}>
        {/* Vendors Tab */}
        {activeTab === "vendors" && (
          <div>
            <h3 style={{ margin: "0 0 16px", fontSize: "1rem", fontWeight: 600 }}>Vendor Performance Scorecards</h3>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ background: "#f9fafb", textAlign: "left" }}>
                  {["Rank", "Vendor", "Composite Score", "Baseline Adoption", "Defect Rate", "CAPA Closure", "Risk Tier"].map((h) => (
                    <th key={h} style={{ padding: "8px 12px", fontWeight: 600, color: "#374151", borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dashboard.vendor_scorecards.map((v) => (
                  <tr key={v.vendor_id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "8px 12px", color: "#6b7280" }}>#{v.portfolio_rank}</td>
                    <td style={{ padding: "8px 12px", fontWeight: 600, color: "#111827" }}>{v.vendor_name}</td>
                    <td style={{ padding: "8px 12px", minWidth: 150 }}><ScoreBar value={v.composite_score} /></td>
                    <td style={{ padding: "8px 12px" }}>{v.baseline_adoption_rate_pct.toFixed(1)}%</td>
                    <td style={{ padding: "8px 12px", color: v.defect_rate_pct > 10 ? "#dc2626" : "#374151" }}>
                      {v.defect_rate_pct.toFixed(1)}%
                    </td>
                    <td style={{ padding: "8px 12px" }}>{v.capa_closure_rate_pct.toFixed(1)}%</td>
                    <td style={{ padding: "8px 12px" }}><RiskBadge tier={v.risk_tier} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Manufacturers Tab */}
        {activeTab === "manufacturers" && (
          <div>
            <h3 style={{ margin: "0 0 16px", fontSize: "1rem", fontWeight: 600 }}>Manufacturer Quality Scorecards</h3>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ background: "#f9fafb", textAlign: "left" }}>
                  {["Rank", "Manufacturer", "Composite Score", "Baseline Quality", "Inspection Pass Rate", "Recalls", "CAPA Effectiveness", "Risk Tier"].map((h) => (
                    <th key={h} style={{ padding: "8px 12px", fontWeight: 600, color: "#374151", borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dashboard.manufacturer_scorecards.map((m) => (
                  <tr key={m.manufacturer_id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "8px 12px", color: "#6b7280" }}>#{m.portfolio_rank}</td>
                    <td style={{ padding: "8px 12px", fontWeight: 600, color: "#111827" }}>{m.manufacturer_name}</td>
                    <td style={{ padding: "8px 12px", minWidth: 150 }}><ScoreBar value={m.composite_score} /></td>
                    <td style={{ padding: "8px 12px" }}>{m.baseline_quality_score.toFixed(1)}</td>
                    <td style={{ padding: "8px 12px" }}>{m.inspection_pass_rate_pct.toFixed(1)}%</td>
                    <td style={{ padding: "8px 12px", color: m.recall_count > 0 ? "#dc2626" : "#374151", fontWeight: m.recall_count > 0 ? 700 : 400 }}>
                      {m.recall_count}
                    </td>
                    <td style={{ padding: "8px 12px" }}>{m.capa_effectiveness_score.toFixed(1)}</td>
                    <td style={{ padding: "8px 12px" }}><RiskBadge tier={m.risk_tier} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Intelligence Tab */}
        {activeTab === "intelligence" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {/* Shared Defect Signals */}
            <div>
              <h3 style={{ margin: "0 0 12px", fontSize: "1rem", fontWeight: 600 }}>
                Shared Defect Signals
                <span style={{ fontSize: "0.75rem", fontWeight: 400, color: "#6b7280", marginLeft: 8 }}>
                  (anonymized — no hospital identifiers)
                </span>
              </h3>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.83rem" }}>
                <thead>
                  <tr style={{ background: "#f9fafb", textAlign: "left" }}>
                    {["Signal Type", "Instrument", "Finding", "Count", "Severity", "Confidence"].map((h) => (
                      <th key={h} style={{ padding: "8px 12px", fontWeight: 600, color: "#374151", borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dashboard.shared_defect_signals.map((s) => (
                    <tr key={s.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                      <td style={{ padding: "8px 12px" }}>{s.signal_type.replace(/_/g, " ")}</td>
                      <td style={{ padding: "8px 12px" }}>{s.instrument_category}</td>
                      <td style={{ padding: "8px 12px" }}>{s.finding_category.replace(/_/g, " ")}</td>
                      <td style={{ padding: "8px 12px", fontWeight: 600 }}>{s.occurrence_count}</td>
                      <td style={{ padding: "8px 12px" }}><SeverityBadge severity={s.severity} /></td>
                      <td style={{ padding: "8px 12px" }}>{(s.confidence_score * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Active Recalls */}
            <div>
              <h3 style={{ margin: "0 0 12px", fontSize: "1rem", fontWeight: 600 }}>
                Active Recalls &amp; Advisories
              </h3>
              {dashboard.recall_events.length === 0 ? (
                <p style={{ color: "#6b7280", fontSize: "0.85rem" }}>No active recalls.</p>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.83rem" }}>
                  <thead>
                    <tr style={{ background: "#f9fafb", textAlign: "left" }}>
                      {["Recall #", "Title", "Severity", "Status", "Source", "Date", "Categories"].map((h) => (
                        <th key={h} style={{ padding: "8px 12px", fontWeight: 600, color: "#374151", borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.recall_events.map((r) => (
                      <tr key={r.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                        <td style={{ padding: "8px 12px", fontFamily: "monospace", fontSize: "0.78rem" }}>{r.recall_number}</td>
                        <td style={{ padding: "8px 12px", maxWidth: 240 }}>{r.recall_title}</td>
                        <td style={{ padding: "8px 12px" }}><SeverityBadge severity={r.severity} /></td>
                        <td style={{ padding: "8px 12px", color: r.status === "active" ? "#dc2626" : "#374151" }}>
                          {r.status}
                        </td>
                        <td style={{ padding: "8px 12px" }}>{r.source}</td>
                        <td style={{ padding: "8px 12px", color: "#6b7280" }}>
                          {r.recall_date ? new Date(r.recall_date).toLocaleDateString() : "—"}
                        </td>
                        <td style={{ padding: "8px 12px" }}>{r.affected_instrument_categories.join(", ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* CAPA Effectiveness */}
            <div>
              <h3 style={{ margin: "0 0 12px", fontSize: "1rem", fontWeight: 600 }}>CAPA Effectiveness</h3>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
                <KPICard label="Total CAPAs" value={dashboard.capa_effectiveness.total_capas} />
                <KPICard label="Open" value={dashboard.capa_effectiveness.open_capas} />
                <KPICard label="Closed" value={dashboard.capa_effectiveness.closed_capas} />
                <KPICard label="Overdue" value={dashboard.capa_effectiveness.overdue_capas} alert={dashboard.capa_effectiveness.overdue_capas > 0} />
                <KPICard label="Closure Rate" value={`${dashboard.capa_effectiveness.closure_rate_pct.toFixed(1)}%`} />
                <KPICard label="Avg Closure Days" value={dashboard.capa_effectiveness.avg_closure_days.toFixed(1)} unit="days" />
                <KPICard label="Effectiveness Score" value={dashboard.capa_effectiveness.effectiveness_score.toFixed(1)} unit="/ 100" />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
