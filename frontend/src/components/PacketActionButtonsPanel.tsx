import { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_BASE ||
  "http://127.0.0.1:18012";


type ExportReadinessCard = {
  key: string;
  title: string;
  ready: boolean;
  status: string;
  url: string;
  description: string;
};

type ExportReadinessStatus = {
  status: string;
  finding_id: number;
  baseline_evidence_count: number;
  approved_baseline_count: number;
  evidence_attachment_count: number;
  readiness_summary: string;
  cards: ExportReadinessCard[];
};


type ExportReadinessHistoryItem = {
  finding_id: number;
  generated_at: string;
  governance_zip_ready: boolean;
  vendor_pdf_ready: boolean;
  infection_prevention_pdf_ready: boolean;
  executive_pdf_ready: boolean;
  baseline_evidence_count: number;
  approved_baseline_count: number;
  evidence_attachment_count: number;
  readiness_summary: string;
};

type ExportReadinessHistoryResponse = {
  status: string;
  history_type: string;
  items: ExportReadinessHistoryItem[];
};

async function fetchExportReadinessHistory(
  limit: string,
  findingIdFilter: string
): Promise<ExportReadinessHistoryResponse> {
  const params = new URLSearchParams();
  params.set("limit", limit || "5");

  if (findingIdFilter.trim()) {
    params.set("finding_id", findingIdFilter.trim());
  }

  const response = await fetch(`${API_BASE}/api/enterprise/export-readiness-history?${params.toString()}`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-LumenAI-Role": "viewer",
      "X-LumenAI-Actor": "john-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Export readiness history failed (${response.status})`);
  }

  return data;
}

async function fetchExportReadiness(findingId: string): Promise<ExportReadinessStatus> {
  const response = await fetch(`${API_BASE}/api/enterprise/intake/${findingId}/export-readiness-status`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-LumenAI-Role": "viewer",
      "X-LumenAI-Actor": "john-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Export readiness failed (${response.status})`);
  }

  return data;
}


export default function PacketActionButtonsPanel() {
  const [findingId, setFindingId] = useState("2");
  const [readiness, setReadiness] = useState<ExportReadinessStatus | null>(null);
  const [readinessError, setReadinessError] = useState("");
  const [readinessLoading, setReadinessLoading] = useState(false);
  const [historyItems, setHistoryItems] = useState<ExportReadinessHistoryItem[]>([]);
  const [historyError, setHistoryError] = useState("");
  const [historyFindingId, setHistoryFindingId] = useState("2");
  const [historyLimit, setHistoryLimit] = useState("5");
  const [lastCheckedAt, setLastCheckedAt] = useState("");

  async function loadReadiness() {
    setReadinessLoading(true);
    setReadinessError("");

    try {
      const data = await fetchExportReadiness(findingId);
      setReadiness(data);
      setLastCheckedAt(new Date().toLocaleString());
    } catch (err) {
      setReadinessError(err instanceof Error ? err.message : "Unknown export readiness error");
    } finally {
      setReadinessLoading(false);
    }
  }

  useEffect(() => {
    loadReadiness();
    loadHistory();
  }, [findingId]);

  const [lastExport, setLastExport] = useState("");

  async function loadHistory() {
    setHistoryError("");

    try {
      const data = await fetchExportReadinessHistory(historyLimit, historyFindingId);
      setHistoryItems(data.items || []);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unknown export readiness history error");
    }
  }

  function clearHistoryFilters() {
    setHistoryFindingId("");
    setHistoryLimit("5");

    window.setTimeout(() => {
      loadHistory();
    }, 100);
  }

  function recordExport(label: string) {
    const timestamp = new Date().toLocaleString();
    setLastExport(`${label} export opened for Finding #${findingId} at ${timestamp}. This action is audit-tracked by the backend when the export endpoint is requested.`);

    window.setTimeout(() => {
      loadReadiness();
    }, 1200);
  }

  function scrollToAuditTrail() {
    const auditTrail = document.getElementById("enterprise-audit-trail");
    if (auditTrail) {
      auditTrail.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  const governanceZipUrl = `${API_BASE}/api/enterprise/intake/${findingId}/governance-zip-bundle`;
  const vendorPdfUrl = `${API_BASE}/api/enterprise/intake/${findingId}/vendor-escalation-packet.pdf`;
  const ipPdfUrl = `${API_BASE}/api/enterprise/intake/${findingId}/infection-prevention-review-packet.pdf`;
  const executivePdfUrl = `${API_BASE}/api/enterprise/executive-quality-review-dashboard.pdf`;
  const historyPdfParams = new URLSearchParams();
  historyPdfParams.set("limit", historyLimit || "10");
  if (historyFindingId.trim()) {
    historyPdfParams.set("finding_id", historyFindingId.trim());
  }
  const historyPdfUrl = `${API_BASE}/api/enterprise/export-readiness-history.pdf?${historyPdfParams.toString()}`;
  const historyCsvUrl = `${API_BASE}/api/enterprise/export-readiness-history.csv?${historyPdfParams.toString()}`;
  const historyPowerBiCsvUrl = `${API_BASE}/api/enterprise/export-readiness-history.powerbi.csv?${historyPdfParams.toString()}`;
  const powerBiDictionaryPdfUrl = `${API_BASE}/api/enterprise/export-readiness-history.powerbi.data-dictionary.pdf`;
  const powerBiDashboardSpecPdfUrl = `${API_BASE}/api/enterprise/export-readiness-history.powerbi.dashboard-spec.pdf`;


  async function downloadHistoryCsv() {
    try {
      const response = await fetch(historyCsvUrl, {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`History CSV download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = historyFindingId.trim()
        ? `lumenai-export-readiness-history-finding-${historyFindingId.trim()}.csv`
        : "lumenai-export-readiness-history-all.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unknown history CSV download error");
    }
  }

  async function downloadPowerBiCsv() {
    try {
      const response = await fetch(historyPowerBiCsvUrl, {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Power BI CSV download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = historyFindingId.trim()
        ? `lumenai-export-readiness-powerbi-finding-${historyFindingId.trim()}.csv`
        : "lumenai-export-readiness-powerbi-all.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unknown Power BI CSV download error");
    }
  }


  async function downloadPowerBiDictionaryPdf() {
    try {
      const response = await fetch(powerBiDictionaryPdfUrl, {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Power BI Data Dictionary PDF download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "lumenai-powerbi-data-dictionary.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unknown Power BI Data Dictionary PDF download error");
    }
  }


  async function downloadPowerBiDashboardSpecPdf() {
    try {
      const response = await fetch(powerBiDashboardSpecPdfUrl, {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Power BI Dashboard Spec PDF download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "lumenai-powerbi-starter-dashboard-spec.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unknown Power BI Dashboard Spec PDF download error");
    }
  }

  return (
    <section style={panelStyle}>
      <div>
        <div style={eyebrowStyle}>Packet Exports</div>
        <h2 style={titleStyle}>Governance & Review Export Actions</h2>
        <p style={subtitleStyle}>
          Download audit-ready governance, vendor escalation, infection prevention, and executive review packets.
        </p>
      </div>

      <div style={readinessHeaderStyle}>
        <div>
          <strong>Export Readiness Status</strong>
          <p style={readinessSummaryStyle}>
            {readiness?.readiness_summary || "Load export readiness to confirm available packets."}
          </p>
          <p style={autoRefreshTextStyle}>
            Auto-refreshes when the Finding ID changes or an export is opened.
          </p>
          {lastCheckedAt ? (
            <p style={lastCheckedTextStyle}>
              Last checked: {lastCheckedAt}
            </p>
          ) : null}
        </div>
        <button type="button" onClick={loadReadiness} disabled={readinessLoading} style={readinessButtonStyle}>
          {readinessLoading ? "Checking..." : "Check Readiness"}
        </button>
      </div>

      {readinessError ? <div style={readinessErrorStyle}>{readinessError}</div> : null}

      <div style={exportStatusGridStyle}>
        {(readiness?.cards || fallbackCards).map((card) => (
          <ExportStatusCard
            key={card.key}
            title={card.title}
            status={card.status}
            description={card.description}
            intent={getReadinessIntent(card)}
          />
        ))}
      </div>

      <div style={controlRowStyle}>
        <label style={labelStyle}>
          Finding ID
          <input
            value={findingId}
            onChange={(event) => setFindingId(event.target.value)}
            style={inputStyle}
          />
        </label>

        <a href={governanceZipUrl} target="_blank" rel="noreferrer" style={primaryButtonStyle} onClick={() => recordExport("Governance ZIP Bundle")}>
          Download Governance ZIP
        </a>

        <a href={vendorPdfUrl} target="_blank" rel="noreferrer" style={warningButtonStyle} onClick={() => recordExport("Vendor Escalation PDF")}>
          Download Vendor PDF
        </a>

        <a href={ipPdfUrl} target="_blank" rel="noreferrer" style={infoButtonStyle} onClick={() => recordExport("Infection Prevention PDF")}>
          Download IP PDF
        </a>

        <a href={executivePdfUrl} target="_blank" rel="noreferrer" style={executiveButtonStyle} onClick={() => recordExport("Executive Quality PDF")}>
          Download Executive PDF
        </a>
      </div>

      {lastExport ? (
        <div style={confirmationStyle}>
          <strong>Export confirmation</strong>
          <p style={confirmationTextStyle}>{lastExport}</p>
          <p style={confirmationTextStyle}>
            Review the Enterprise Audit Trail panel to verify the backend audit event after the export completes.
          </p>
          <button type="button" onClick={scrollToAuditTrail} style={auditTrailButtonStyle}>
            View Audit Trail
          </button>
        </div>
      ) : null}
      <div style={historyPanelStyle}>
        <div style={historyHeaderStyle}>
          <div>
            <strong>Recent Export Readiness Checks</strong>
            <p style={historySubtextStyle}>
              Shows the most recent backend readiness checks for packet exports.
            </p>
          </div>
          <div style={historyFilterRowStyle}>
            <label style={historyFilterLabelStyle}>
              Finding ID
              <input
                value={historyFindingId}
                onChange={(event) => setHistoryFindingId(event.target.value)}
                style={historyFilterInputStyle}
                placeholder="All"
              />
            </label>

            <label style={historyFilterLabelStyle}>
              Limit
              <input
                value={historyLimit}
                onChange={(event) => setHistoryLimit(event.target.value)}
                style={historyFilterInputStyle}
                placeholder="5"
              />
            </label>

            <button type="button" onClick={loadHistory} style={historyButtonStyle}>
              Refresh History
            </button>

            <button type="button" onClick={clearHistoryFilters} style={historySecondaryButtonStyle}>
              Clear
            </button>

            <a href={historyPdfUrl} target="_blank" rel="noreferrer" style={historyPdfButtonStyle}>
              Download History PDF
            </a>

            <button type="button" onClick={downloadHistoryCsv} style={historyCsvButtonStyle}>
              Download History CSV
            </button>

            <button type="button" onClick={downloadPowerBiCsv} style={powerBiCsvButtonStyle}>
              Download Power BI CSV
            </button>

            <button type="button" onClick={downloadPowerBiDictionaryPdf} style={dataDictionaryButtonStyle}>
              Download Data Dictionary PDF
            </button>

            <button type="button" onClick={downloadPowerBiDashboardSpecPdf} style={dashboardSpecButtonStyle}>
              Download Dashboard Spec PDF
            </button>
          </div>
        </div>

        {historyError ? <div style={historyErrorStyle}>{historyError}</div> : null}

        {historyItems.length ? (
          <div style={historyListStyle}>
            {historyItems.map((item) => (
              <div key={`${item.finding_id}-${item.generated_at}`} style={historyItemStyle}>
                <div style={historyItemHeaderStyle}>
                  <strong>Finding #{item.finding_id}</strong>
                  <span>{formatHistoryDate(item.generated_at)}</span>
                </div>
                <div style={historyBadgeRowStyle}>
                  <span style={readyBadgeStyle(item.governance_zip_ready)}>ZIP</span>
                  <span style={readyBadgeStyle(item.vendor_pdf_ready)}>Vendor PDF</span>
                  <span style={readyBadgeStyle(item.infection_prevention_pdf_ready)}>IP PDF</span>
                  <span style={readyBadgeStyle(item.executive_pdf_ready)}>Executive PDF</span>
                </div>
                <div style={historyCountRowStyle}>
                  <span>Baseline Evidence: {item.baseline_evidence_count}</span>
                  <span>Approved Baselines: {item.approved_baseline_count}</span>
                  <span>Evidence Attachments: {item.evidence_attachment_count}</span>
                </div>
                <p style={historySubtextStyle}>{item.readiness_summary}</p>
              </div>
            ))}
          </div>
        ) : (
          <p style={historySubtextStyle}>No readiness history yet. Click Check Readiness to create a history entry.</p>
        )}
      </div>

    </section>
  );
}


function getReadinessIntent(card: ExportReadinessCard): "ready" | "warning" | "error" | "neutral" {
  const status = (card.status || "").toLowerCase();
  const key = (card.key || "").toLowerCase();

  if (key === "executive_quality_pdf" && card.ready) {
    return "neutral";
  }

  if (card.ready || status === "ready") {
    return "ready";
  }

  if (status.includes("not ready") || status.includes("error") || status.includes("failed")) {
    return "error";
  }

  return "warning";
}

const fallbackCards: ExportReadinessCard[] = [
  {
    key: "governance_zip",
    title: "Governance ZIP Bundle",
    ready: true,
    status: "Ready",
    url: "",
    description: "Includes JSON packet, baseline evidence, evidence attachments, PDF summary, manifest, and README.",
  },
  {
    key: "vendor_escalation_pdf",
    title: "Vendor Escalation PDF",
    ready: true,
    status: "Ready",
    url: "",
    description: "Vendor-facing quality packet with finding context, baseline evidence, and recommended vendor action.",
  },
  {
    key: "infection_prevention_pdf",
    title: "Infection Prevention PDF",
    ready: true,
    status: "Ready",
    url: "",
    description: "IP-ready packet with patient-safety signal, infection-risk signal, and recommended documentation.",
  },
  {
    key: "executive_quality_pdf",
    title: "Executive Quality PDF",
    ready: true,
    status: "Ready",
    url: "",
    description: "Leadership-ready summary of findings, quality signal, vendor signals, CAPA status, and actions.",
  },
];

function formatHistoryDate(value: string) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}

function ExportStatusCard({
  title,
  status,
  description,
  intent,
}: {
  title: string;
  status: string;
  description: string;
  intent: "ready" | "warning" | "error" | "neutral";
}) {
  return (
    <div style={exportStatusCardStyle(intent)}>
      <div style={exportStatusHeaderStyle}>
        <strong>{title}</strong>
        <span style={exportStatusBadgeStyle(intent)}>{status}</span>
      </div>
      <p style={exportStatusDescriptionStyle}>{description}</p>
    </div>
  );
}

const readinessHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
  marginTop: "16px",
  padding: "12px",
  borderRadius: "16px",
  background: "#f8fafc",
  border: "1px solid #e2e8f0",
};

const readinessSummaryStyle: React.CSSProperties = {
  margin: "4px 0 0",
  color: "#475569",
  lineHeight: 1.45,
};

const readinessButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#7c3aed",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
  whiteSpace: "nowrap",
};

const readinessErrorStyle: React.CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 800,
};

const exportStatusGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
  gap: "12px",
  marginTop: "16px",
};

function exportStatusCardStyle(intent: "ready" | "warning" | "error" | "neutral"): React.CSSProperties {
  const palette = {
    ready: { border: "#bbf7d0", background: "#f0fdf4" },
    warning: { border: "#fed7aa", background: "#fff7ed" },
    error: { border: "#fecaca", background: "#fef2f2" },
    neutral: { border: "#bfdbfe", background: "#eff6ff" },
  }[intent];

  return {
    padding: "14px",
    borderRadius: "16px",
    border: `1px solid ${palette.border}`,
    background: palette.background,
  };
}

const exportStatusHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "10px",
  alignItems: "center",
  color: "#0f172a",
};

function exportStatusBadgeStyle(intent: "ready" | "warning" | "error" | "neutral"): React.CSSProperties {
  const palette = {
    ready: { background: "#dcfce7", color: "#166534" },
    warning: { background: "#ffedd5", color: "#9a3412" },
    error: { background: "#fee2e2", color: "#991b1b" },
    neutral: { background: "#dbeafe", color: "#1e40af" },
  }[intent];

  return {
    borderRadius: "999px",
    padding: "4px 8px",
    fontSize: "12px",
    fontWeight: 900,
    background: palette.background,
    color: palette.color,
    whiteSpace: "nowrap",
  };
}

const exportStatusDescriptionStyle: React.CSSProperties = {
  margin: "8px 0 0",
  color: "#475569",
  lineHeight: 1.45,
  fontSize: "13px",
};

const panelStyle: React.CSSProperties = {
  padding: "20px",
  borderRadius: "22px",
  background: "#ffffff",
  border: "1px solid #e2e8f0",
  boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
};

const eyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#7c3aed",
};

const titleStyle: React.CSSProperties = {
  margin: "4px 0",
  fontSize: "24px",
  fontWeight: 900,
  color: "#0f172a",
};

const subtitleStyle: React.CSSProperties = {
  margin: 0,
  color: "#475569",
  lineHeight: 1.5,
};

const controlRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  alignItems: "end",
  flexWrap: "wrap",
  marginTop: "16px",
};

const labelStyle: React.CSSProperties = {
  display: "grid",
  gap: "6px",
  fontWeight: 900,
  color: "#334155",
};

const inputStyle: React.CSSProperties = {
  padding: "10px",
  borderRadius: "12px",
  border: "1px solid #cbd5e1",
  minWidth: "120px",
};

const baseButtonStyle: React.CSSProperties = {
  borderRadius: "14px",
  padding: "11px 14px",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
};

const primaryButtonStyle: React.CSSProperties = {
  ...baseButtonStyle,
  background: "#ede9fe",
  color: "#5b21b6",
};

const warningButtonStyle: React.CSSProperties = {
  ...baseButtonStyle,
  background: "#ffedd5",
  color: "#9a3412",
};

const infoButtonStyle: React.CSSProperties = {
  ...baseButtonStyle,
  background: "#e0f2fe",
  color: "#075985",
};

const executiveButtonStyle: React.CSSProperties = {
  ...baseButtonStyle,
  background: "#dbeafe",
  color: "#1e40af",
};


const confirmationStyle: React.CSSProperties = {
  marginTop: "14px",
  padding: "12px 14px",
  borderRadius: "16px",
  border: "1px solid #bbf7d0",
  background: "#f0fdf4",
  color: "#166534",
};

const confirmationTextStyle: React.CSSProperties = {
  margin: "6px 0 0",
  lineHeight: 1.5,
};


const auditTrailButtonStyle: React.CSSProperties = {
  marginTop: "10px",
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#166534",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};


const autoRefreshTextStyle: React.CSSProperties = {
  margin: "4px 0 0",
  color: "#64748b",
  fontSize: "12px",
  lineHeight: 1.4,
};


const lastCheckedTextStyle: React.CSSProperties = {
  margin: "4px 0 0",
  color: "#334155",
  fontSize: "12px",
  fontWeight: 800,
  lineHeight: 1.4,
};


const historyPanelStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "14px",
  borderRadius: "18px",
  border: "1px solid #e2e8f0",
  background: "#f8fafc",
};

const historyHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
};

const historySubtextStyle: React.CSSProperties = {
  margin: "4px 0 0",
  color: "#475569",
  lineHeight: 1.45,
  fontSize: "13px",
};

const historyButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#334155",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};

const historyErrorStyle: React.CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 800,
};

const historyListStyle: React.CSSProperties = {
  display: "grid",
  gap: "10px",
  marginTop: "12px",
};

const historyItemStyle: React.CSSProperties = {
  padding: "12px",
  borderRadius: "14px",
  border: "1px solid #e2e8f0",
  background: "#ffffff",
};

const historyItemHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "10px",
  color: "#0f172a",
};

const historyBadgeRowStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "8px",
  marginTop: "8px",
};

function readyBadgeStyle(ready: boolean): React.CSSProperties {
  return {
    borderRadius: "999px",
    padding: "4px 8px",
    fontSize: "12px",
    fontWeight: 900,
    background: ready ? "#dcfce7" : "#ffedd5",
    color: ready ? "#166534" : "#9a3412",
  };
}


const historyCountRowStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "10px",
  marginTop: "8px",
  color: "#334155",
  fontSize: "12px",
  fontWeight: 800,
};


const historyFilterRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "8px",
  alignItems: "end",
  flexWrap: "wrap",
  justifyContent: "flex-end",
};

const historyFilterLabelStyle: React.CSSProperties = {
  display: "grid",
  gap: "4px",
  color: "#334155",
  fontSize: "12px",
  fontWeight: 900,
};

const historyFilterInputStyle: React.CSSProperties = {
  padding: "8px",
  borderRadius: "10px",
  border: "1px solid #cbd5e1",
  width: "90px",
};

const historySecondaryButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#e2e8f0",
  color: "#334155",
  fontWeight: 900,
  cursor: "pointer",
};


const historyPdfButtonStyle: React.CSSProperties = {
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#ede9fe",
  color: "#5b21b6",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
};


const historyCsvButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#dcfce7",
  color: "#166534",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
  cursor: "pointer",
};


const powerBiCsvButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#fef3c7",
  color: "#92400e",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
  cursor: "pointer",
};


const dataDictionaryButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#e0f2fe",
  color: "#075985",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
  cursor: "pointer",
};


const dashboardSpecButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#ede9fe",
  color: "#5b21b6",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
  cursor: "pointer",
};
