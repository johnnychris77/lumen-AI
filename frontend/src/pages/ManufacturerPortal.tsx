/**
 * Manufacturer Portal — separate login + dashboard for medical device manufacturers.
 * Accessible at /manufacturer route.
 * Auth: Bearer token + X-Manufacturer-ID header (no enterprise role required).
 */
import React, { useEffect, useState } from "react";

const API = (import.meta as { env: Record<string, string> }).env.VITE_API_BASE_URL ?? "";

// ── Styles ────────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  root: {
    minHeight: "100vh",
    background: "#f1f5f9",
    fontFamily: "'Inter', system-ui, sans-serif",
  },
  header: {
    background: "#0f172a",
    color: "#f8fafc",
    padding: "16px 32px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  headerTitle: {
    margin: 0,
    fontSize: "1.2rem",
    fontWeight: 700,
    letterSpacing: "0.02em",
  },
  headerSub: {
    fontSize: "0.75rem",
    color: "#94a3b8",
    marginTop: 2,
  },
  signOutBtn: {
    background: "transparent",
    border: "1px solid #475569",
    color: "#cbd5e1",
    padding: "6px 16px",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: "0.85rem",
  },
  loginWrap: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "calc(100vh - 60px)",
  },
  loginCard: {
    background: "#ffffff",
    borderRadius: 12,
    padding: "40px 48px",
    boxShadow: "0 4px 24px rgba(0,0,0,0.10)",
    width: 380,
  },
  loginTitle: {
    margin: "0 0 8px",
    fontSize: "1.4rem",
    fontWeight: 700,
    color: "#0f172a",
  },
  loginSub: {
    color: "#64748b",
    fontSize: "0.9rem",
    marginBottom: 28,
  },
  label: {
    display: "block",
    fontSize: "0.8rem",
    fontWeight: 600,
    color: "#374151",
    marginBottom: 6,
    marginTop: 18,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  input: {
    width: "100%",
    padding: "10px 14px",
    border: "1px solid #d1d5db",
    borderRadius: 8,
    fontSize: "0.95rem",
    boxSizing: "border-box" as const,
    outline: "none",
  },
  loginBtn: {
    marginTop: 28,
    width: "100%",
    padding: "12px",
    background: "#0f172a",
    color: "#f8fafc",
    border: "none",
    borderRadius: 8,
    fontSize: "0.95rem",
    fontWeight: 600,
    cursor: "pointer",
  },
  errorMsg: {
    color: "#dc2626",
    fontSize: "0.85rem",
    marginTop: 14,
    background: "#fef2f2",
    borderRadius: 6,
    padding: "8px 12px",
    border: "1px solid #fecaca",
  },
  dashboard: {
    maxWidth: 1100,
    margin: "0 auto",
    padding: "32px 24px",
  },
  tabs: {
    display: "flex",
    gap: 4,
    marginBottom: 24,
    borderBottom: "2px solid #e2e8f0",
  },
  tab: (active: boolean): React.CSSProperties => ({
    padding: "10px 22px",
    border: "none",
    background: "transparent",
    cursor: "pointer",
    fontSize: "0.9rem",
    fontWeight: active ? 700 : 500,
    color: active ? "#0f172a" : "#64748b",
    borderBottom: active ? "3px solid #0f172a" : "3px solid transparent",
    marginBottom: -2,
  }),
  card: {
    background: "#fff",
    borderRadius: 10,
    padding: "24px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.07)",
    marginBottom: 20,
  },
  scoreNum: {
    fontSize: "4rem",
    fontWeight: 800,
    color: "#0f172a",
    lineHeight: 1,
  },
  riskBadge: (tier: string): React.CSSProperties => ({
    display: "inline-block",
    padding: "4px 14px",
    borderRadius: 100,
    fontSize: "0.78rem",
    fontWeight: 700,
    textTransform: "uppercase" as const,
    letterSpacing: "0.06em",
    marginLeft: 16,
    verticalAlign: "middle",
    background:
      tier === "low" ? "#dcfce7" : tier === "medium" ? "#fef9c3" : tier === "high" ? "#ffedd5" : "#fee2e2",
    color:
      tier === "low" ? "#166534" : tier === "medium" ? "#854d0e" : tier === "high" ? "#9a3412" : "#991b1b",
  }),
  progressWrap: {
    marginBottom: 14,
  },
  progressLabel: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: "0.85rem",
    color: "#374151",
    marginBottom: 4,
  },
  progressBar: {
    background: "#e2e8f0",
    borderRadius: 99,
    height: 10,
    overflow: "hidden",
  },
  progressFill: (pct: number): React.CSSProperties => ({
    background: pct >= 80 ? "#22c55e" : pct >= 60 ? "#f59e0b" : "#ef4444",
    width: `${Math.min(100, pct)}%`,
    height: "100%",
    borderRadius: 99,
    transition: "width 0.4s ease",
  }),
  table: {
    width: "100%",
    borderCollapse: "collapse" as const,
    fontSize: "0.9rem",
  },
  th: {
    textAlign: "left" as const,
    padding: "10px 14px",
    background: "#f8fafc",
    fontWeight: 600,
    color: "#374151",
    borderBottom: "2px solid #e2e8f0",
  },
  td: {
    padding: "10px 14px",
    borderBottom: "1px solid #f1f5f9",
    color: "#1e293b",
  },
  trendArrow: (dir: string): React.CSSProperties => ({
    color: dir === "improving" ? "#16a34a" : dir === "worsening" ? "#dc2626" : "#6b7280",
    fontWeight: 700,
    fontSize: "1.1rem",
  }),
  benchmarkRow: (highlight: boolean): React.CSSProperties => ({
    background: highlight ? "#f0f9ff" : "transparent",
    fontWeight: highlight ? 700 : 400,
  }),
  severityBadge: (sev: string): React.CSSProperties => ({
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 100,
    fontSize: "0.75rem",
    fontWeight: 700,
    background:
      sev === "class_i" ? "#fee2e2" : sev === "class_ii" ? "#ffedd5" : sev === "advisory" ? "#f1f5f9" : "#fef9c3",
    color:
      sev === "class_i" ? "#991b1b" : sev === "class_ii" ? "#9a3412" : sev === "advisory" ? "#475569" : "#854d0e",
  }),
  recallsSection: {
    marginTop: 24,
  },
  sectionTitle: {
    fontSize: "1rem",
    fontWeight: 700,
    color: "#0f172a",
    marginBottom: 12,
  },
};

// ── Types ─────────────────────────────────────────────────────────────────────

interface Scorecard {
  composite_score: number;
  risk_tier: string;
  baseline_quality_score: number;
  inspection_pass_rate_pct: number;
  instrument_defect_frequency: number;
  capa_effectiveness_score: number;
  manufacturer_name?: string;
}

interface TrendPoint {
  period_label: string;
  avg_defect_rate?: number;
  defect_rate_pct?: number;
  trend_direction: string;
  total_defects?: number;
}

interface BenchmarkData {
  my_composite_score: number;
  network_avg_composite_score: number;
  top_performer_score: number;
  my_rank: number;
  total_manufacturers: number;
  anonymized: boolean;
}

interface Recall {
  id: number;
  recall_number: string;
  recall_title: string;
  severity: string;
  status: string;
  vendor_id?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function ManufacturerPortal() {
  // Auth state
  const [mfrId, setMfrId] = useState(() => localStorage.getItem("mfr_id") ?? "");
  const [token, setToken] = useState(() => localStorage.getItem("mfr_token") ?? "");
  const [loggedIn, setLoggedIn] = useState(() => !!(localStorage.getItem("mfr_id") && localStorage.getItem("mfr_token")));

  // Login form
  const [loginId, setLoginId] = useState("");
  const [loginToken, setLoginToken] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  // Dashboard state
  const [activeTab, setActiveTab] = useState<"scorecard" | "trends" | "benchmark">("scorecard");
  const [scorecard, setScorecard] = useState<Scorecard | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [benchmark, setBenchmark] = useState<BenchmarkData | null>(null);
  const [recalls, setRecalls] = useState<Recall[]>([]);
  const [dashLoading, setDashLoading] = useState(false);
  const [dashError, setDashError] = useState("");

  const authHeaders = {
    Authorization: `Bearer ${token}`,
    "X-Manufacturer-ID": mfrId,
    "Content-Type": "application/json",
  };

  // Load dashboard data on login
  useEffect(() => {
    if (!loggedIn) return;
    setDashLoading(true);
    setDashError("");

    const fetchAll = async () => {
      try {
        const [scRes, trRes, bnRes, rcRes] = await Promise.allSettled([
          fetch(`${API}/api/manufacturer-portal/my-scorecard`, { headers: authHeaders }),
          fetch(`${API}/api/manufacturer-portal/my-defect-trends`, { headers: authHeaders }),
          fetch(`${API}/api/manufacturer-portal/network-benchmark`, { headers: authHeaders }),
          fetch(`${API}/api/intelligence/recalls?tenant_id=global`, { headers: authHeaders }),
        ]);

        if (scRes.status === "fulfilled" && scRes.value.ok) {
          const d = await scRes.value.json();
          setScorecard(d.scorecard ?? null);
        }
        if (trRes.status === "fulfilled" && trRes.value.ok) {
          const d = await trRes.value.json();
          const pts: TrendPoint[] = [];
          (d.trends ?? []).forEach((t: { trend_points?: TrendPoint[] }) => {
            (t.trend_points ?? []).forEach((pt) => pts.push(pt));
          });
          setTrends(pts);
        }
        if (bnRes.status === "fulfilled" && bnRes.value.ok) {
          const d = await bnRes.value.json();
          setBenchmark(d ?? null);
        }
        if (rcRes.status === "fulfilled" && rcRes.value.ok) {
          const d = await rcRes.value.json();
          const allRecalls: Recall[] = d.recalls ?? [];
          setRecalls(allRecalls.filter((r) => r.vendor_id && mfrId.includes(r.vendor_id)));
        }
      } catch {
        setDashError("Failed to load dashboard data.");
      } finally {
        setDashLoading(false);
      }
    };

    fetchAll();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loggedIn]);

  // ── Login handler ──────────────────────────────────────────────────────────

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError("");
    setLoginLoading(true);

    try {
      const res = await fetch(`${API}/api/manufacturer-portal/my-scorecard`, {
        headers: {
          Authorization: `Bearer ${loginToken}`,
          "X-Manufacturer-ID": loginId,
        },
      });

      if (res.status === 200) {
        localStorage.setItem("mfr_token", loginToken);
        localStorage.setItem("mfr_id", loginId);
        setToken(loginToken);
        setMfrId(loginId);
        setLoggedIn(true);
      } else if (res.status === 401 || res.status === 403) {
        setLoginError("Invalid credentials. Check your Manufacturer ID and API Token.");
      } else {
        setLoginError(`Sign-in failed (HTTP ${res.status}). Please try again.`);
      }
    } catch {
      setLoginError("Network error. Please check your connection.");
    } finally {
      setLoginLoading(false);
    }
  };

  // ── Sign out ───────────────────────────────────────────────────────────────

  const handleSignOut = () => {
    localStorage.removeItem("mfr_token");
    localStorage.removeItem("mfr_id");
    setToken("");
    setMfrId("");
    setLoggedIn(false);
    setScorecard(null);
    setTrends([]);
    setBenchmark(null);
    setRecalls([]);
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div style={styles.root}>
      {/* Header */}
      <header style={styles.header}>
        <div>
          <h1 style={styles.headerTitle}>LumenAI Manufacturer Portal</h1>
          <div style={styles.headerSub}>
            {loggedIn ? `Signed in as ${mfrId}` : "Medical Device Quality Intelligence"}
          </div>
        </div>
        {loggedIn && (
          <button style={styles.signOutBtn} onClick={handleSignOut}>
            Sign Out
          </button>
        )}
      </header>

      {/* Login Screen */}
      {!loggedIn && (
        <div style={styles.loginWrap}>
          <div style={styles.loginCard}>
            <h2 style={styles.loginTitle}>Manufacturer Sign In</h2>
            <p style={styles.loginSub}>
              Access your quality scorecard, defect trends, and network benchmark.
            </p>
            <form onSubmit={handleLogin}>
              <label style={styles.label}>Manufacturer ID</label>
              <input
                style={styles.input}
                type="text"
                placeholder="e.g. mfr-stryker"
                value={loginId}
                onChange={(e) => setLoginId(e.target.value)}
                required
              />
              <label style={styles.label}>API Token</label>
              <input
                style={styles.input}
                type="password"
                placeholder="Bearer token"
                value={loginToken}
                onChange={(e) => setLoginToken(e.target.value)}
                required
              />
              {loginError && <div style={styles.errorMsg}>{loginError}</div>}
              <button style={styles.loginBtn} type="submit" disabled={loginLoading}>
                {loginLoading ? "Signing in…" : "Sign In"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Dashboard Screen */}
      {loggedIn && (
        <div style={styles.dashboard}>
          {dashError && <div style={styles.errorMsg}>{dashError}</div>}
          {dashLoading && <p style={{ color: "#64748b" }}>Loading dashboard…</p>}

          {/* Tabs */}
          <div style={styles.tabs}>
            {(["scorecard", "trends", "benchmark"] as const).map((t) => (
              <button key={t} style={styles.tab(activeTab === t)} onClick={() => setActiveTab(t)}>
                {t === "scorecard" ? "My Scorecard" : t === "trends" ? "Defect Trends" : "Network Benchmark"}
              </button>
            ))}
          </div>

          {/* Tab: My Scorecard */}
          {activeTab === "scorecard" && (
            <>
              <div style={styles.card}>
                <div style={{ marginBottom: 24 }}>
                  <span style={styles.scoreNum}>{scorecard ? scorecard.composite_score.toFixed(1) : "—"}</span>
                  {scorecard && (
                    <span style={styles.riskBadge(scorecard.risk_tier)}>{scorecard.risk_tier} risk</span>
                  )}
                  <div style={{ color: "#64748b", fontSize: "0.85rem", marginTop: 6 }}>
                    Composite Quality Score&nbsp;·&nbsp;{scorecard?.manufacturer_name ?? mfrId}
                  </div>
                </div>

                {scorecard && (
                  <div>
                    <ProgressBar label="Baseline Quality" value={scorecard.baseline_quality_score} />
                    <ProgressBar label="Inspection Pass Rate" value={scorecard.inspection_pass_rate_pct} />
                    <ProgressBar
                      label="Defect Frequency (inverted)"
                      value={Math.max(0, 100 - scorecard.instrument_defect_frequency * 6.67)}
                    />
                    <ProgressBar label="CAPA Effectiveness" value={scorecard.capa_effectiveness_score} />
                  </div>
                )}
              </div>

              {/* Recalls affecting this manufacturer */}
              <div style={styles.recallsSection}>
                <div style={styles.sectionTitle}>
                  Recalls Potentially Affecting You ({recalls.length})
                </div>
                {recalls.length === 0 ? (
                  <div style={{ color: "#64748b", fontSize: "0.9rem" }}>
                    No active recalls matched to your manufacturer ID.
                  </div>
                ) : (
                  <div style={styles.card}>
                    <table style={styles.table}>
                      <thead>
                        <tr>
                          <th style={styles.th}>Recall #</th>
                          <th style={styles.th}>Title</th>
                          <th style={styles.th}>Severity</th>
                          <th style={styles.th}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {recalls.map((r) => (
                          <tr key={r.id}>
                            <td style={styles.td}>{r.recall_number}</td>
                            <td style={styles.td}>{r.recall_title}</td>
                            <td style={styles.td}>
                              <span style={styles.severityBadge(r.severity)}>{r.severity}</span>
                            </td>
                            <td style={styles.td}>{r.status}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Tab: Defect Trends */}
          {activeTab === "trends" && (
            <div style={styles.card}>
              <div style={styles.sectionTitle}>Defect Trends by Period</div>
              {trends.length === 0 ? (
                <p style={{ color: "#64748b" }}>No trend data available.</p>
              ) : (
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Period</th>
                      <th style={styles.th}>Avg Defect Rate (%)</th>
                      <th style={styles.th}>Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trends.map((pt, i) => (
                      <tr key={i}>
                        <td style={styles.td}>{pt.period_label}</td>
                        <td style={styles.td}>
                          {(pt.avg_defect_rate ?? pt.defect_rate_pct ?? 0).toFixed(1)}%
                        </td>
                        <td style={styles.td}>
                          <span style={styles.trendArrow(pt.trend_direction)}>
                            {pt.trend_direction === "improving" ? "↓" : pt.trend_direction === "worsening" ? "↑" : "→"}
                          </span>{" "}
                          <span style={{ color: "#64748b", fontSize: "0.85rem" }}>{pt.trend_direction}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* Tab: Network Benchmark */}
          {activeTab === "benchmark" && (
            <div style={styles.card}>
              <div style={styles.sectionTitle}>Network Benchmark Comparison</div>
              {!benchmark ? (
                <p style={{ color: "#64748b" }}>No benchmark data available.</p>
              ) : (
                <>
                  <div style={{ color: "#64748b", fontSize: "0.85rem", marginBottom: 16 }}>
                    Rank {benchmark.my_rank} of {benchmark.total_manufacturers} manufacturers
                    {benchmark.anonymized ? " · Anonymized network data" : ""}
                  </div>
                  <table style={styles.table}>
                    <thead>
                      <tr>
                        <th style={styles.th}>Metric</th>
                        <th style={styles.th}>Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={styles.benchmarkRow(true)}>
                        <td style={styles.td}>Your Score</td>
                        <td style={styles.td}>{benchmark.my_composite_score.toFixed(1)}</td>
                      </tr>
                      <tr style={styles.benchmarkRow(false)}>
                        <td style={styles.td}>Network Average</td>
                        <td style={styles.td}>{benchmark.network_avg_composite_score.toFixed(1)}</td>
                      </tr>
                      <tr style={styles.benchmarkRow(false)}>
                        <td style={styles.td}>Top Performer</td>
                        <td style={styles.td}>{benchmark.top_performer_score.toFixed(1)}</td>
                      </tr>
                    </tbody>
                  </table>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ProgressBar({ label, value }: { label: string; value: number }) {
  return (
    <div style={styles.progressWrap}>
      <div style={styles.progressLabel}>
        <span>{label}</span>
        <span>{value.toFixed(1)}</span>
      </div>
      <div style={styles.progressBar}>
        <div style={styles.progressFill(value)} />
      </div>
    </div>
  );
}
