import React, { useEffect, useMemo, useState } from "react";
import { CVInspectionDashboard } from "@/components/CVInspectionDashboard";
import { EnterpriseBenchmarkDashboard } from "@/components/EnterpriseBenchmarkDashboard";
import VendorIntelligenceDashboard from "@/components/VendorIntelligenceDashboard";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

const AUTH_TOKEN = localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || "";

type Summary = {
  total_inspections?: number;
  completed?: number;
  queued?: number;
  running?: number;
  failed?: number;
};

type Inspection = {
  id: number;
  created_at?: string;
  file_name?: string;
  status?: string;
  vendor_name?: string;
  instrument_type?: string;
  detected_issue?: string;
  risk_score?: number;
};

type ModuleStatus = {
  key: string;
  label: string;
  endpoint: string;
  status: "checking" | "online" | "protected" | "offline";
  httpStatus?: number;
  detail: string;
};

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function DashboardCard({
  title,
  value,
  detail,
}: {
  title: string;
  value: string | number;
  detail?: string;
}) {
  return (
    <div style={card}>
      <div style={cardLabel}>{title}</div>
      <div style={cardValue}>{value}</div>
      {detail ? <div style={cardDetail}>{detail}</div> : null}
    </div>
  );
}

const initialModuleStatuses: ModuleStatus[] = [
  {
    key: "vendor",
    label: "Vendor Governance",
    endpoint: "/api/analytics/vendors",
    status: "checking",
    detail: "Vendor analytics and governance readiness",
  },
  {
    key: "capa",
    label: "CAPA Workflow",
    endpoint: "/api/capa",
    status: "checking",
    detail: "Corrective action workflow availability",
  },
  {
    key: "audit",
    label: "Audit Command Center",
    endpoint: "/api/enterprise/audit/events?limit=1",
    status: "checking",
    detail: "Enterprise audit trail availability",
  },
  {
    key: "evidence",
    label: "Compliance Evidence",
    endpoint: "/api/enterprise/audit/evidence-bundle/verification-summary",
    status: "checking",
    detail: "Evidence verification workflow availability",
  },
];

function ModuleStatusCard({ item }: { item: ModuleStatus }) {
  const statusStyle =
    item.status === "online"
      ? goodPill
      : item.status === "protected"
        ? warnPill
        : item.status === "offline"
          ? dangerPill
          : neutralPill;

  return (
    <div style={moduleStatusCard}>
      <div style={moduleStatusHeader}>
        <h3 style={moduleStatusTitle}>{item.label}</h3>
        <span style={statusStyle}>
          {item.status === "protected" ? "protected" : item.status}
        </span>
      </div>

      <p style={muted}>{item.detail}</p>

      <div style={moduleEndpoint}>{item.endpoint}</div>

      <p style={moduleHttpStatus}>
        HTTP Status: {item.httpStatus ?? "pending"}
      </p>
    </div>
  );
}

type BaselineKPIs = {
  total_baselines: number;
  approved_baselines: number;
  pending_review: number;
  vendor_submissions: number;
  approval_rate: number;
};

export default function DashboardApp() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recent, setRecent] = useState<Inspection[]>([]);
  const [health, setHealth] = useState("checking");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [moduleStatuses, setModuleStatuses] =
    useState<ModuleStatus[]>(initialModuleStatuses);
  const [baselineKPIs, setBaselineKPIs] = useState<BaselineKPIs | null>(null);

  const headers = useMemo(
    () => ({
      Authorization: `Bearer ${AUTH_TOKEN}`,
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
      "X-LumenAI-Role": "enterprise_admin",
      "X-LumenAI-Actor": "dashboard-viewer",
    }),
    []
  );

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const [healthRes, summaryRes, historyRes, baselineRes] = await Promise.allSettled([
          fetch(`${API_BASE}/api/health`),
          fetch(`${API_BASE}/api/history/summary`, { headers }),
          fetch(`${API_BASE}/api/history?limit=8`, { headers }),
          fetch(`${API_BASE}/api/enterprise/vendor-baseline-subscription/baselines`, { headers }),
        ]);

        if (cancelled) return;

        if (healthRes.status === "fulfilled" && healthRes.value.ok) {
          setHealth("online");
        } else {
          setHealth("unavailable");
        }

        if (summaryRes.status === "fulfilled" && summaryRes.value.ok) {
          setSummary(await summaryRes.value.json());
        } else {
          setSummary(null);
        }

        if (historyRes.status === "fulfilled" && historyRes.value.ok) {
          const data = await historyRes.value.json();
          setRecent(Array.isArray(data) ? data : data.items || []);
        } else {
          setRecent([]);
        }

        if (baselineRes.status === "fulfilled" && baselineRes.value.ok) {
          const data = await baselineRes.value.json();
          const baselines: { baseline_status?: string; approval_status?: string; baseline_source?: string }[] =
            Array.isArray(data) ? data : data.records || [];
          const approved = baselines.filter(
            (b) => ["approved", "active", "vendor_approved"].includes((b.baseline_status || "").toLowerCase())
          ).length;
          const pending = baselines.filter(
            (b) => (b.approval_status || "").toLowerCase().includes("pending")
          ).length;
          const vendorSubs = baselines.filter((b) => b.baseline_source === "vendor").length;
          setBaselineKPIs({
            total_baselines: baselines.length,
            approved_baselines: approved,
            pending_review: pending,
            vendor_submissions: vendorSubs,
            approval_rate: baselines.length > 0 ? Math.round((approved / baselines.length) * 100) : 0,
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [headers]);

  useEffect(() => {
    let cancelled = false;

    async function loadModuleStatuses() {
      const results = await Promise.all(
        initialModuleStatuses.map(async (item) => {
          try {
            const response = await fetch(`${API_BASE}${item.endpoint}`, {
              headers,
            });

            const protectedStatus = [401, 403, 422].includes(response.status);

            return {
              ...item,
              status: response.ok ? "online" : protectedStatus ? "protected" : "offline",
              httpStatus: response.status,
            } as ModuleStatus;
          } catch {
            return {
              ...item,
              status: "offline",
              httpStatus: undefined,
            } as ModuleStatus;
          }
        })
      );

      if (!cancelled) {
        setModuleStatuses(results);
      }
    }

    loadModuleStatuses();

    return () => {
      cancelled = true;
    };
  }, [headers]);

  return (
    <main style={page}>
      <section style={shell}>
        <div style={topbar}>
          <div>
            <h1 style={title}>LumenAI Live Dashboard</h1>
            <p style={subtitle}>
              Operational intelligence, quality review, vendor governance, and
              compliance evidence dashboard.
            </p>
          </div>

          <a href="/" style={homeLink}>
            Public Landing
          </a>
        </div>

        <div style={statusRow}>
          <span style={health === "online" ? goodPill : warnPill}>
            Backend: {health}
          </span>
          <span style={neutralPill}>
            API: {API_BASE}
          </span>
        </div>

        {error ? <div style={errorBox}>{error}</div> : null}

        <div style={grid}>
          <DashboardCard
            title="Total inspections"
            value={summary?.total_inspections ?? "—"}
            detail="All captured inspection records"
          />
          <DashboardCard
            title="Completed"
            value={summary?.completed ?? "—"}
            detail="Completed workflow items"
          />
          <DashboardCard
            title="Queued"
            value={summary?.queued ?? "—"}
            detail="Items waiting for action"
          />
          <DashboardCard
            title="Failed"
            value={summary?.failed ?? "—"}
            detail="Items needing review"
          />
        </div>

        <section style={panel}>
          <h2 style={panelTitle}>Inspection Intelligence</h2>
          <p style={muted}>
            Vendor baseline management, intake workflow, and review queue for sterile processing governance.
          </p>

          <div style={grid}>
            <DashboardCard
              title="Total Baselines"
              value={baselineKPIs?.total_baselines ?? "—"}
              detail="All baseline records on file"
            />
            <DashboardCard
              title="Approved Baselines"
              value={baselineKPIs?.approved_baselines ?? "—"}
              detail="Baselines passed vendor review"
            />
            <DashboardCard
              title="Pending Review"
              value={baselineKPIs?.pending_review ?? "—"}
              detail="Baselines awaiting approval"
            />
            <DashboardCard
              title="Vendor Submissions"
              value={baselineKPIs?.vendor_submissions ?? "—"}
              detail="Baselines submitted by vendors"
            />
            <DashboardCard
              title="Approval Rate"
              value={baselineKPIs ? `${baselineKPIs.approval_rate}%` : "—"}
              detail="Approved / total baselines"
            />
          </div>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "16px" }}>
            <a style={moduleLink} href="/vendor-intake">Vendor Intake</a>
            <a style={moduleLink} href="/manufacturer-baselines">Manufacturer Baselines</a>
            <a style={moduleLink} href="/baseline-review">Baseline Review Queue</a>
            <a style={moduleLink} href="/vendor-baseline-portal">Vendor Baseline Portal</a>
            <a style={moduleLink} href="/intake-history">Intake History</a>
          </div>
        </section>

        <section style={panel}>
          <h2 style={panelTitle}>Recent Activity</h2>

          {loading ? (
            <p style={muted}>Loading dashboard data...</p>
          ) : recent.length === 0 ? (
            <p style={muted}>
              No recent inspection records returned from the backend. The
              dashboard shell is loaded and ready.
            </p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={table}>
                <thead>
                  <tr>
                    <th style={th}>ID</th>
                    <th style={th}>File</th>
                    <th style={th}>Vendor</th>
                    <th style={th}>Instrument</th>
                    <th style={th}>Issue</th>
                    <th style={th}>Risk</th>
                    <th style={th}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((item) => (
                    <tr key={item.id}>
                      <td style={td}>{item.id}</td>
                      <td style={td}>{formatValue(item.file_name)}</td>
                      <td style={td}>{formatValue(item.vendor_name)}</td>
                      <td style={td}>{formatValue(item.instrument_type)}</td>
                      <td style={td}>{formatValue(item.detected_issue)}</td>
                      <td style={td}>{formatValue(item.risk_score)}</td>
                      <td style={td}>{formatValue(item.status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>


        <section style={panel}>
          <h2 style={panelTitle}>Live Module Status</h2>
          <p style={muted}>
            Real-time reachability checks for core LumenAI dashboard modules.
          </p>

          <div style={statusGrid}>
            {moduleStatuses.map((item) => (
              <ModuleStatusCard key={item.key} item={item} />
            ))}
          </div>
        </section>

        <section style={panel}>
          <h2 style={panelTitle}>Compliance Evidence Module</h2>
          <p style={muted}>
            Evidence workflow links for audit readiness, bundle verification, customer review,
            and public portfolio proof.
          </p>

          <div style={linkGrid}>
            <a style={moduleLink} href="/portfolio/audit-command-center">
              Audit Command Center Evidence
            </a>
            <a style={moduleLink} href="/portfolio/governance-hub">
              Governance Hub
            </a>
            <a style={moduleLink} href="/portfolio/governance-summary">
              Governance Summary
            </a>
            <a style={moduleLink} href="/portfolio/vendor-governance">
              Vendor Governance
            </a>
            <a style={moduleLink} href="/portfolio/capa-workflow">
              CAPA Workflow
            </a>

            <a style={moduleLink} href="/portfolio/live-dashboard">
              Live Dashboard Portfolio
            </a>

            <a style={moduleLink} href="/portfolio/erp-style-governance">
              ERP-Style Governance Portfolio
            </a>

            <a style={moduleLink} href="/portfolio/customer-demo">
              Enterprise Customer Demo Portfolio
            </a>

            <a style={moduleLink} href="/portfolio/investor-review">
              Investor Review Portfolio
            </a>

            <a style={moduleLink} href="/portfolio/sales-readiness">
              Sales Readiness Portfolio
            </a>

            <a style={moduleLink} href="/portfolio/compliance-evidence">
              Compliance Evidence Portfolio
            </a>

            <a style={moduleLink} href="/portfolio/vendor-accountability">
              Vendor Accountability Portfolio
            </a>

            <a style={moduleLink} href="/portfolio/capa-governance">
              CAPA Governance Portfolio
            </a>

            <a style={moduleLink} href="/portfolio/audit-readiness">
              Audit Readiness Portfolio
            </a>

            <a style={moduleLink} href="/portfolio">
              Portfolio Index
            </a>










          </div>

          <div style={evidenceNote}>
            <strong>Compliance Evidence v1.0:</strong> hash-backed exports, evidence bundles,
            verification summaries, demo script, customer review packet, investor brief, and
            portfolio landing page are available.
          </div>
        </section>


        {/* R8: CV Inspection Intelligence dashboard tile */}
        <section style={panel}>
          <CVInspectionDashboard tenantId="demo-tenant" />
        </section>

        {/* P5: Enterprise Multi-Hospital Benchmarking & Portfolio Intelligence */}
        <section style={panel}>
          <EnterpriseBenchmarkDashboard />
        </section>

        {/* P6: Vendor Intelligence Exchange & Manufacturer Collaboration Network */}
        <section style={panel}>
          <VendorIntelligenceDashboard />
        </section>

        <section style={threeColumnGrid}>
          <div style={modulePanel}>
            <h2 style={panelTitle}>Vendor Governance Summary</h2>
            <p style={muted}>
              Tracks vendor accountability, quality trends, baseline evidence, and governance review paths.
            </p>
            <ul style={moduleList}>
              <li>Vendor performance review</li>
              <li>Baseline evidence workflow</li>
              <li>Quality issue escalation</li>
              <li>Governance documentation</li>
            </ul>
            <a style={moduleLink} href="/portfolio/vendor-governance">
              Open Vendor Governance
            </a>
          </div>

          <div style={modulePanel}>
            <h2 style={panelTitle}>CAPA Workflow Summary</h2>
            <p style={muted}>
              Supports corrective action visibility, escalation tracking, and quality improvement review.
            </p>
            <ul style={moduleList}>
              <li>Open CAPA visibility</li>
              <li>Risk and priority tracking</li>
              <li>Evidence-linked corrective action</li>
              <li>Executive review readiness</li>
            </ul>
            <a style={moduleLink} href="/portfolio/capa-workflow">
              Open CAPA Workflow
            </a>
          </div>

          <div style={modulePanel}>
            <h2 style={panelTitle}>Audit Command Center Summary</h2>
            <p style={muted}>
              Shows audit readiness, evidence traceability, export verification, and compliance proof paths.
            </p>
            <ul style={moduleList}>
              <li>Audit export readiness</li>
              <li>Hash-backed evidence</li>
              <li>Verification summary workflow</li>
              <li>Compliance evidence review</li>
            </ul>
            <a style={moduleLink} href="/portfolio/audit-command-center">
              Open Audit Command Center
            </a>
          </div>
        </section>


        <section style={panel}>
          <h2 style={panelTitle}>Governance Modules</h2>
          <div style={linkGrid}>
            <a style={moduleLink} href="/portfolio/governance-hub">
              Governance Hub
            </a>
            <a style={moduleLink} href="/portfolio/governance-summary">
              Governance Summary
            </a>
            <a style={moduleLink} href="/portfolio/vendor-governance">
              Vendor Governance
            </a>
            <a style={moduleLink} href="/portfolio/audit-command-center">
              Audit Command Center
            </a>
            <a style={moduleLink} href="/portfolio/capa-workflow">
              CAPA Workflow
            </a>
          </div>
        </section>

        <section style={panel}>
          <h2 style={panelTitle}>Inspection Intelligence</h2>
          <p style={muted}>
            Vendor intake, manufacturer baselines, baseline review, and subscription portal for
            instrument inspection governance.
          </p>
          <div style={inspectionGrid}>
            <a style={inspectionCard} href="/vendor-intake">
              <span style={inspectionCardIcon}>📋</span>
              <span style={inspectionCardLabel}>Vendor Intake</span>
              <span style={inspectionCardDesc}>Submit enterprise instrument intake records</span>
            </a>
            <a style={inspectionCard} href="/manufacturer-baselines">
              <span style={inspectionCardIcon}>🏭</span>
              <span style={inspectionCardLabel}>Manufacturer Baselines</span>
              <span style={inspectionCardDesc}>View and approve manufacturer baseline evidence</span>
            </a>
            <a style={inspectionCard} href="/baseline-review">
              <span style={inspectionCardIcon}>🔍</span>
              <span style={inspectionCardLabel}>Baseline Review Queue</span>
              <span style={inspectionCardDesc}>Review pending baseline assessments</span>
            </a>
            <a style={inspectionCard} href="/vendor-baseline-portal">
              <span style={inspectionCardIcon}>🔗</span>
              <span style={inspectionCardLabel}>Vendor Baseline Portal</span>
              <span style={inspectionCardDesc}>Vendor subscription and baseline matching</span>
            </a>
            <a style={inspectionCard} href="/intake-history">
              <span style={inspectionCardIcon}>📂</span>
              <span style={inspectionCardLabel}>Intake History</span>
              <span style={inspectionCardDesc}>Audit trail of past intake submissions</span>
            </a>
          </div>
        </section>
      </section>
    </main>
  );
}

const page: React.CSSProperties = {
  minHeight: "100vh",
  background: "#f8fafc",
  color: "#0f172a",
  fontFamily: "Arial, sans-serif",
  padding: "28px",
};

const shell: React.CSSProperties = {
  maxWidth: "1180px",
  margin: "0 auto",
};

const topbar: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "20px",
  alignItems: "flex-start",
  marginBottom: "18px",
};

const title: React.CSSProperties = {
  margin: 0,
  fontSize: "36px",
};

const subtitle: React.CSSProperties = {
  marginTop: "8px",
  color: "#475569",
  fontSize: "16px",
};

const homeLink: React.CSSProperties = {
  background: "#0f172a",
  color: "#fff",
  padding: "10px 14px",
  borderRadius: "10px",
  textDecoration: "none",
  fontWeight: 700,
};

const statusRow: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "10px",
  marginBottom: "18px",
};

const pillBase: React.CSSProperties = {
  display: "inline-block",
  padding: "6px 10px",
  borderRadius: "999px",
  fontSize: "13px",
  fontWeight: 700,
};

const goodPill: React.CSSProperties = {
  ...pillBase,
  background: "#dcfce7",
  color: "#166534",
};

const warnPill: React.CSSProperties = {
  ...pillBase,
  background: "#fef3c7",
  color: "#92400e",
};

const neutralPill: React.CSSProperties = {
  ...pillBase,
  background: "#e0f2fe",
  color: "#075985",
};

const grid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
  gap: "16px",
  marginBottom: "18px",
};

const card: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: "16px",
  padding: "18px",
  boxShadow: "0 10px 24px rgba(15, 23, 42, 0.06)",
};

const cardLabel: React.CSSProperties = {
  color: "#64748b",
  fontSize: "13px",
  fontWeight: 700,
  textTransform: "uppercase",
};

const cardValue: React.CSSProperties = {
  fontSize: "32px",
  fontWeight: 800,
  marginTop: "8px",
};

const cardDetail: React.CSSProperties = {
  color: "#64748b",
  fontSize: "13px",
  marginTop: "6px",
};

const panel: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: "16px",
  padding: "18px",
  marginTop: "18px",
  boxShadow: "0 10px 24px rgba(15, 23, 42, 0.06)",
};

const panelTitle: React.CSSProperties = {
  marginTop: 0,
  marginBottom: "12px",
};

const muted: React.CSSProperties = {
  color: "#64748b",
};

const errorBox: React.CSSProperties = {
  background: "#fee2e2",
  color: "#991b1b",
  padding: "12px 16px",
  borderRadius: "10px",
  marginBottom: "18px",
};

const table: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
};

const th: React.CSSProperties = {
  textAlign: "left",
  padding: "10px",
  borderBottom: "1px solid #e2e8f0",
  color: "#475569",
  fontSize: "13px",
};

const td: React.CSSProperties = {
  padding: "10px",
  borderBottom: "1px solid #f1f5f9",
  fontSize: "14px",
};

const linkGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
  gap: "12px",
};

const moduleLink: React.CSSProperties = {
  display: "block",
  padding: "14px",
  background: "#f1f5f9",
  color: "#1d4ed8",
  borderRadius: "12px",
  textDecoration: "none",
  fontWeight: 700,
};


const evidenceNote: React.CSSProperties = {
  marginTop: "16px",
  padding: "14px",
  borderRadius: "12px",
  background: "#ecfeff",
  color: "#155e75",
  border: "1px solid #a5f3fc",
  fontSize: "14px",
};


const threeColumnGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
  gap: "16px",
  marginTop: "18px",
};

const modulePanel: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: "16px",
  padding: "18px",
  boxShadow: "0 10px 24px rgba(15, 23, 42, 0.06)",
};

const moduleList: React.CSSProperties = {
  marginTop: "10px",
  marginBottom: "16px",
  paddingLeft: "20px",
  color: "#334155",
  lineHeight: 1.7,
  fontSize: "14px",
};


const dangerPill: React.CSSProperties = {
  ...pillBase,
  background: "#fee2e2",
  color: "#991b1b",
};

const statusGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
  gap: "14px",
  marginTop: "14px",
};

const moduleStatusCard: React.CSSProperties = {
  background: "#f8fafc",
  border: "1px solid #e2e8f0",
  borderRadius: "14px",
  padding: "16px",
};

const moduleStatusHeader: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "12px",
  marginBottom: "8px",
};

const moduleStatusTitle: React.CSSProperties = {
  margin: 0,
  fontSize: "17px",
};

const moduleEndpoint: React.CSSProperties = {
  marginTop: "10px",
  padding: "8px",
  borderRadius: "8px",
  background: "#e2e8f0",
  color: "#334155",
  fontFamily: "monospace",
  fontSize: "12px",
  overflowWrap: "anywhere",
};

const moduleHttpStatus: React.CSSProperties = {
  marginBottom: 0,
  color: "#475569",
  fontSize: "13px",
  fontWeight: 700,
};

const inspectionGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
  gap: "14px",
  marginTop: "14px",
};

const inspectionCard: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  background: "#f8fafc",
  border: "1px solid #e2e8f0",
  borderRadius: "14px",
  padding: "18px 16px",
  textDecoration: "none",
  color: "#0f172a",
  boxShadow: "0 2px 8px rgba(15,23,42,0.04)",
  transition: "box-shadow 0.15s",
};

const inspectionCardIcon: React.CSSProperties = {
  fontSize: "24px",
};

const inspectionCardLabel: React.CSSProperties = {
  fontWeight: 700,
  fontSize: "15px",
  color: "#1e40af",
};

const inspectionCardDesc: React.CSSProperties = {
  fontSize: "13px",
  color: "#64748b",
};
