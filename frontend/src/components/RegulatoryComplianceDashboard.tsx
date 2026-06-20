import React, { useCallback, useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const HEADERS = {
  Authorization: `Bearer ${localStorage.getItem("token") || "dev-token"}`,
  "X-LumenAI-Role": "operator",
  "Content-Type": "application/json",
};

const TENANT_ID =
  localStorage.getItem("tenant_id") || "demo-tenant";

// ── Types ────────────────────────────────────────────────────────────────────

interface AccreditationFinding {
  standard_code: string;
  finding_category: string;
  occurrence_count: number;
  rate_pct: number;
  severity: string;
  citation_text: string;
  remediation_guidance: string;
  auto_capa_required: boolean;
}

interface ReadinessData {
  overall_score: number;
  readiness_tier: string;
  joint_commission_score: number;
  aami_score: number;
  fda_score: number;
  cms_score: number;
  iso_score: number;
  deficiency_count: number;
  critical_deficiency_count: number;
  open_capa_count: number;
  findings: AccreditationFinding[];
  recommended_actions: string[];
  data_source: string;
}

interface AuditPackage {
  id: number | null;
  package_type: string;
  period_label: string;
  status: string;
  findings_count: number;
  created_at?: string;
}

interface FDASubmission {
  id: number | null;
  submission_type: string;
  submission_number: string | null;
  device_name: string;
  manufacturer: string;
  status: string;
  submission_date: string | null;
  decision_date: string | null;
  notes: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function scoreColor(score: number): string {
  if (score >= 90) return "#22c55e";
  if (score >= 75) return "#f59e0b";
  if (score >= 60) return "#f97316";
  return "#ef4444";
}

function tierLabel(tier: string): string {
  return tier.replace(/_/g, " ").toUpperCase();
}

function tierBadgeStyle(tier: string): React.CSSProperties {
  const colors: Record<string, string> = {
    survey_ready: "#22c55e",
    conditional: "#f59e0b",
    needs_improvement: "#f97316",
    at_risk: "#ef4444",
  };
  return {
    display: "inline-block",
    padding: "3px 10px",
    borderRadius: 12,
    background: colors[tier] || "#6b7280",
    color: "#fff",
    fontWeight: 700,
    fontSize: 12,
    marginLeft: 8,
  };
}

function sevBadgeStyle(sev: string): React.CSSProperties {
  const colors: Record<string, string> = {
    critical: "#dc2626",
    high: "#f97316",
    medium: "#f59e0b",
    low: "#6b7280",
  };
  return {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: 8,
    background: colors[sev] || "#6b7280",
    color: "#fff",
    fontWeight: 700,
    fontSize: 11,
  };
}

function statusBadgeStyle(status: string): React.CSSProperties {
  const colors: Record<string, string> = {
    cleared: "#22c55e",
    pending: "#f59e0b",
    denied: "#ef4444",
    withdrawn: "#6b7280",
  };
  return {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: 8,
    background: colors[status] || "#6b7280",
    color: "#fff",
    fontWeight: 700,
    fontSize: 11,
  };
}

function ScoreBar({
  label,
  score,
}: {
  label: string;
  score: number;
}) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 3 }}>
        <span>{label}</span>
        <span style={{ fontWeight: 700, color: scoreColor(score) }}>{score}/100</span>
      </div>
      <div style={{ background: "#e5e7eb", borderRadius: 4, height: 8 }}>
        <div
          style={{
            height: 8,
            borderRadius: 4,
            background: scoreColor(score),
            width: `${Math.min(score, 100)}%`,
            transition: "width 0.4s",
          }}
        />
      </div>
    </div>
  );
}

// ── Tabs ─────────────────────────────────────────────────────────────────────

const TABS = [
  "Readiness Overview",
  "Deficiency Findings",
  "Audit Packages",
  "FDA Tracking",
];

// ── Main Component ────────────────────────────────────────────────────────────

export function RegulatoryComplianceDashboard() {
  const [activeTab, setActiveTab] = useState(0);
  const [readiness, setReadiness] = useState<ReadinessData | null>(null);
  const [findings, setFindings] = useState<AccreditationFinding[]>([]);
  const [findingsSeverity, setFindingsSeverity] = useState("all");
  const [expandedFinding, setExpandedFinding] = useState<number | null>(null);
  const [packages, setPackages] = useState<AuditPackage[]>([]);
  const [fda, setFDA] = useState<FDASubmission[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pkgType, setPkgType] = useState("joint_commission");
  const [pkgPeriod, setPkgPeriod] = useState("");
  const [generating, setGenerating] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);

  const isMock = readiness?.data_source !== "real";

  const fetchReadiness = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(
        `${API_BASE}/api/regulatory/readiness?tenant_id=${TENANT_ID}`,
        { headers: HEADERS }
      );
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = await r.json();
      setReadiness(j.readiness);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchFindings = useCallback(async () => {
    setLoading(true);
    try {
      const sev = findingsSeverity !== "all" ? `&severity=${findingsSeverity}` : "";
      const r = await fetch(
        `${API_BASE}/api/regulatory/readiness/findings?tenant_id=${TENANT_ID}${sev}`,
        { headers: HEADERS }
      );
      const j = await r.json();
      setFindings(j.findings || []);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [findingsSeverity]);

  const fetchPackages = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(
        `${API_BASE}/api/regulatory/audit-packages?tenant_id=${TENANT_ID}`,
        { headers: HEADERS }
      );
      const j = await r.json();
      setPackages(j.packages || []);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchFDA = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(
        `${API_BASE}/api/regulatory/fda-submissions?tenant_id=${TENANT_ID}`,
        { headers: HEADERS }
      );
      const j = await r.json();
      setFDA(j.submissions || []);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 0) fetchReadiness();
    else if (activeTab === 1) fetchFindings();
    else if (activeTab === 2) fetchPackages();
    else if (activeTab === 3) fetchFDA();
  }, [activeTab, fetchReadiness, fetchFindings, fetchPackages, fetchFDA]);

  useEffect(() => {
    if (activeTab === 1) fetchFindings();
  }, [findingsSeverity, fetchFindings, activeTab]);

  const handleGeneratePackage = async () => {
    setGenerating(true);
    try {
      const r = await fetch(`${API_BASE}/api/regulatory/audit-package`, {
        method: "POST",
        headers: HEADERS,
        body: JSON.stringify({
          tenant_id: TENANT_ID,
          package_type: pkgType,
          period_label: pkgPeriod || new Date().toISOString().slice(0, 7),
          generated_by: "dashboard-user",
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      await fetchPackages();
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadPdf = async (type: string, period: string) => {
    setPdfLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/regulatory/audit-package/pdf`, {
        method: "POST",
        headers: HEADERS,
        body: JSON.stringify({
          tenant_id: TENANT_ID,
          package_type: type,
          period_label: period || new Date().toISOString().slice(0, 7),
          generated_by: "dashboard-user",
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `lumenai-audit-${type}-${period}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setPdfLoading(false);
    }
  };

  // ── Styles ──
  const card: React.CSSProperties = {
    background: "#fff",
    border: "1px solid #e5e7eb",
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
  };

  const tabBarStyle: React.CSSProperties = {
    display: "flex",
    gap: 8,
    marginBottom: 20,
    borderBottom: "2px solid #e5e7eb",
    paddingBottom: 0,
  };

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: "8px 18px",
    border: "none",
    background: "none",
    cursor: "pointer",
    fontWeight: active ? 700 : 400,
    color: active ? "#0f172a" : "#6b7280",
    borderBottom: active ? "3px solid #3b82f6" : "3px solid transparent",
    marginBottom: -2,
    fontSize: 14,
  });

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 1100 }}>
      <h2 style={{ fontWeight: 800, fontSize: 22, marginBottom: 4, color: "#0f172a" }}>
        Regulatory &amp; Accreditation Compliance
      </h2>
      <p style={{ color: "#6b7280", marginBottom: 20, fontSize: 14 }}>
        Joint Commission · AAMI ST79 · FDA 21 CFR · CMS CoP · ISO 17664
      </p>

      {isMock && readiness && (
        <div style={{
          background: "#fef9c3",
          border: "1px solid #fbbf24",
          borderRadius: 8,
          padding: "10px 16px",
          marginBottom: 16,
          fontSize: 13,
          color: "#92400e",
        }}>
          Showing demo data — connect real inspection records to see live readiness scores.
        </div>
      )}

      {error && (
        <div style={{ background: "#fee2e2", border: "1px solid #f87171", borderRadius: 8, padding: 12, marginBottom: 16, color: "#991b1b", fontSize: 13 }}>
          {error}
        </div>
      )}

      <div style={tabBarStyle}>
        {TABS.map((t, i) => (
          <button key={t} style={tabStyle(activeTab === i)} onClick={() => setActiveTab(i)}>
            {t}
          </button>
        ))}
      </div>

      {loading && <div style={{ color: "#6b7280", padding: 20 }}>Loading…</div>}

      {/* Tab 1: Readiness Overview */}
      {activeTab === 0 && !loading && readiness && (
        <div>
          <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginBottom: 20 }}>
            {/* Score circle */}
            <div style={{ ...card, minWidth: 180, textAlign: "center", flex: "0 0 180px" }}>
              <div style={{
                width: 120, height: 120, borderRadius: "50%",
                border: `8px solid ${scoreColor(readiness.overall_score)}`,
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                margin: "0 auto 12px",
              }}>
                <span style={{ fontSize: 32, fontWeight: 900, color: scoreColor(readiness.overall_score) }}>
                  {readiness.overall_score}
                </span>
                <span style={{ fontSize: 11, color: "#6b7280" }}>/ 100</span>
              </div>
              <span style={tierBadgeStyle(readiness.readiness_tier)}>
                {tierLabel(readiness.readiness_tier)}
              </span>
            </div>

            {/* Score bars */}
            <div style={{ ...card, flex: 1, minWidth: 260 }}>
              <h3 style={{ fontWeight: 700, marginBottom: 14, fontSize: 15 }}>Scores by Body</h3>
              <ScoreBar label="Joint Commission" score={readiness.joint_commission_score} />
              <ScoreBar label="AAMI ST79" score={readiness.aami_score} />
              <ScoreBar label="FDA 21 CFR" score={readiness.fda_score} />
              <ScoreBar label="CMS CoP" score={readiness.cms_score} />
              <ScoreBar label="ISO 17664" score={readiness.iso_score} />
            </div>

            {/* Counts */}
            <div style={{ ...card, minWidth: 160, flex: "0 0 160px" }}>
              <h3 style={{ fontWeight: 700, marginBottom: 14, fontSize: 15 }}>Deficiencies</h3>
              <div style={{ fontSize: 28, fontWeight: 900, color: "#ef4444" }}>
                {readiness.deficiency_count}
              </div>
              <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 12 }}>Total Findings</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: "#dc2626" }}>
                {readiness.critical_deficiency_count}
              </div>
              <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 12 }}>Critical</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#f59e0b" }}>
                {readiness.open_capa_count}
              </div>
              <div style={{ fontSize: 12, color: "#6b7280" }}>CAPAs Required</div>
            </div>
          </div>

          {/* Recommended actions */}
          {readiness.recommended_actions.length > 0 && (
            <div style={card}>
              <h3 style={{ fontWeight: 700, marginBottom: 12, fontSize: 15 }}>Recommended Actions</h3>
              {readiness.recommended_actions.map((action, i) => (
                <div key={i} style={{
                  background: "#fef9c3",
                  border: "1px solid #fbbf24",
                  borderRadius: 8,
                  padding: "10px 14px",
                  marginBottom: 8,
                  fontSize: 13,
                  color: "#78350f",
                }}>
                  {action}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Deficiency Findings */}
      {activeTab === 1 && !loading && (
        <div>
          <div style={{ marginBottom: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
            {["all", "critical", "high", "medium", "low"].map((sev) => (
              <button
                key={sev}
                onClick={() => setFindingsSeverity(sev)}
                style={{
                  padding: "5px 14px",
                  borderRadius: 20,
                  border: "1px solid #d1d5db",
                  cursor: "pointer",
                  fontWeight: findingsSeverity === sev ? 700 : 400,
                  background: findingsSeverity === sev ? "#0f172a" : "#fff",
                  color: findingsSeverity === sev ? "#fff" : "#374151",
                  fontSize: 13,
                }}
              >
                {sev.toUpperCase()}
              </button>
            ))}
          </div>

          {findings.length === 0 ? (
            <div style={{ color: "#6b7280", padding: 20 }}>No findings for selected filter.</div>
          ) : (
            <div>
              {findings.map((f, i) => (
                <div key={i} style={{ ...card, cursor: "pointer" }} onClick={() => setExpandedFinding(expandedFinding === i ? null : i)}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                    <div>
                      <span style={{ fontWeight: 700, fontSize: 14 }}>{f.standard_code}</span>
                      <span style={{ color: "#6b7280", marginLeft: 8, fontSize: 13 }}>{f.finding_category}</span>
                    </div>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span style={sevBadgeStyle(f.severity)}>{f.severity.toUpperCase()}</span>
                      <span style={{ fontSize: 12, color: "#6b7280" }}>{f.occurrence_count} occurrences ({f.rate_pct}%)</span>
                      {f.auto_capa_required && (
                        <span style={{ fontSize: 11, background: "#fef9c3", border: "1px solid #fbbf24", borderRadius: 6, padding: "2px 6px", color: "#92400e" }}>
                          CAPA Required
                        </span>
                      )}
                    </div>
                  </div>
                  {expandedFinding === i && (
                    <div style={{ marginTop: 12, borderTop: "1px solid #e5e7eb", paddingTop: 12 }}>
                      <div style={{ fontSize: 13, color: "#374151", marginBottom: 8 }}>
                        <strong>Citation:</strong> {f.citation_text}
                      </div>
                      <div style={{ fontSize: 13, color: "#374151", marginBottom: 8 }}>
                        <strong>Remediation:</strong> {f.remediation_guidance}
                      </div>
                      {(f.severity === "critical" || f.severity === "high") && (
                        <button style={{
                          padding: "6px 14px",
                          background: "#ef4444",
                          color: "#fff",
                          border: "none",
                          borderRadius: 6,
                          cursor: "pointer",
                          fontSize: 13,
                          fontWeight: 600,
                        }}>
                          Open CAPA
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Audit Packages */}
      {activeTab === 2 && !loading && (
        <div>
          <div style={{ ...card, marginBottom: 20 }}>
            <h3 style={{ fontWeight: 700, marginBottom: 14, fontSize: 15 }}>Generate New Package</h3>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280", display: "block", marginBottom: 4 }}>Package Type</label>
                <select
                  value={pkgType}
                  onChange={(e) => setPkgType(e.target.value)}
                  style={{ padding: "7px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14 }}
                >
                  <option value="joint_commission">Joint Commission</option>
                  <option value="aami">AAMI ST79</option>
                  <option value="fda">FDA 21 CFR</option>
                  <option value="cms">CMS CoP</option>
                  <option value="full">Full (All Bodies)</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#6b7280", display: "block", marginBottom: 4 }}>Period (YYYY-MM)</label>
                <input
                  type="text"
                  placeholder="2026-06"
                  value={pkgPeriod}
                  onChange={(e) => setPkgPeriod(e.target.value)}
                  style={{ padding: "7px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14, width: 120 }}
                />
              </div>
              <button
                onClick={handleGeneratePackage}
                disabled={generating}
                style={{
                  padding: "8px 18px",
                  background: "#0f172a",
                  color: "#fff",
                  border: "none",
                  borderRadius: 6,
                  cursor: generating ? "wait" : "pointer",
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                {generating ? "Generating…" : "Generate Package"}
              </button>
              <button
                onClick={() => handleDownloadPdf(pkgType, pkgPeriod || new Date().toISOString().slice(0, 7))}
                disabled={pdfLoading}
                style={{
                  padding: "8px 18px",
                  background: "#3b82f6",
                  color: "#fff",
                  border: "none",
                  borderRadius: 6,
                  cursor: pdfLoading ? "wait" : "pointer",
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                {pdfLoading ? "Generating PDF…" : "Download PDF"}
              </button>
            </div>
          </div>

          {packages.length === 0 ? (
            <div style={{ color: "#6b7280", padding: 20 }}>No packages generated yet. Use the form above to create one.</div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f9fafb" }}>
                  <th style={{ padding: "8px 12px", textAlign: "left", border: "1px solid #e5e7eb" }}>Type</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", border: "1px solid #e5e7eb" }}>Period</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", border: "1px solid #e5e7eb" }}>Status</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", border: "1px solid #e5e7eb" }}>Findings</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", border: "1px solid #e5e7eb" }}>Created</th>
                </tr>
              </thead>
              <tbody>
                {packages.map((p, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid #e5e7eb" }}>
                    <td style={{ padding: "8px 12px", border: "1px solid #e5e7eb" }}>{p.package_type.replace(/_/g, " ")}</td>
                    <td style={{ padding: "8px 12px", border: "1px solid #e5e7eb" }}>{p.period_label}</td>
                    <td style={{ padding: "8px 12px", border: "1px solid #e5e7eb" }}>{p.status}</td>
                    <td style={{ padding: "8px 12px", border: "1px solid #e5e7eb" }}>{p.findings_count}</td>
                    <td style={{ padding: "8px 12px", border: "1px solid #e5e7eb" }}>{p.created_at ? p.created_at.slice(0, 10) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Tab 4: FDA Tracking */}
      {activeTab === 3 && !loading && (
        <div>
          {fda.length === 0 ? (
            <div style={{ color: "#6b7280", padding: 20 }}>No FDA submissions found.</div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f9fafb" }}>
                  <th style={{ padding: "8px 12px", textAlign: "left", border: "1px solid #e5e7eb" }}>Type</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", border: "1px solid #e5e7eb" }}>Number</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", border: "1px solid #e5e7eb" }}>Device</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", border: "1px solid #e5e7eb" }}>Manufacturer</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", border: "1px solid #e5e7eb" }}>Status</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", border: "1px solid #e5e7eb" }}>Submitted</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", border: "1px solid #e5e7eb" }}>Decision</th>
                </tr>
              </thead>
              <tbody>
                {fda.map((s, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid #e5e7eb" }}>
                    <td style={{ padding: "8px 12px", border: "1px solid #e5e7eb", fontWeight: 600 }}>{s.submission_type.toUpperCase()}</td>
                    <td style={{ padding: "8px 12px", border: "1px solid #e5e7eb" }}>{s.submission_number || "—"}</td>
                    <td style={{ padding: "8px 12px", border: "1px solid #e5e7eb" }}>{s.device_name}</td>
                    <td style={{ padding: "8px 12px", border: "1px solid #e5e7eb" }}>{s.manufacturer}</td>
                    <td style={{ padding: "8px 12px", border: "1px solid #e5e7eb" }}>
                      <span style={statusBadgeStyle(s.status)}>{s.status.toUpperCase()}</span>
                    </td>
                    <td style={{ padding: "8px 12px", border: "1px solid #e5e7eb" }}>{s.submission_date ? s.submission_date.slice(0, 10) : "—"}</td>
                    <td style={{ padding: "8px 12px", border: "1px solid #e5e7eb" }}>{s.decision_date ? s.decision_date.slice(0, 10) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
