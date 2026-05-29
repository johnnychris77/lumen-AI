import { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_BASE ||
  "http://127.0.0.1:18012";






type PowerBiProductionLockCriterion = {
  criterion: string;
  status: string;
};

type PowerBiProductionLock = {
  status: string;
  lock_type: string;
  release_status: string;
  generated_at: string;
  toolkit_name: string;
  toolkit_version: string;
  toolkit_release: string;
  readiness_model_version: string;
  dataset_name: string;
  health_status: string;
  health_failed_checks: number;
  health_warning_checks: number;
  final_validation_status: string;
  final_validation_failed_items: number;
  final_validation_passed_items: number;
  production_lock_criteria: PowerBiProductionLockCriterion[];
  locked_assets: string[];
  executive_message: string;
  recommended_next_step: string;
};

async function fetchPowerBiProductionLock(): Promise<PowerBiProductionLock> {
  const response = await fetch(`${API_BASE}/api/enterprise/export-readiness-history.powerbi-toolkit.production-lock`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-LumenAI-Role": "viewer",
      "X-LumenAI-Actor": "john-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Power BI production lock failed (${response.status})`);
  }

  return data;
}

type PowerBiFinalValidationItem = {
  key: string;
  label: string;
  status: string;
  detail: string;
};

type PowerBiFinalValidation = {
  status: string;
  validation_type: string;
  final_status: string;
  generated_at: string;
  toolkit_version: string;
  readiness_model_version: string;
  dataset_name: string;
  total_items: number;
  passed_items: number;
  failed_items: number;
  validation_items: PowerBiFinalValidationItem[];
  executive_summary: string;
  recommended_next_step: string;
};

async function fetchPowerBiFinalValidation(): Promise<PowerBiFinalValidation> {
  const response = await fetch(`${API_BASE}/api/enterprise/export-readiness-history.powerbi-toolkit.final-validation`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-LumenAI-Role": "viewer",
      "X-LumenAI-Actor": "john-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Power BI final validation failed (${response.status})`);
  }

  return data;
}

type PowerBiToolkitHealthCheck = {
  check_name: string;
  status: string;
  message: string;
  endpoint?: string;
};

type PowerBiToolkitHealth = {
  status: string;
  health_type: string;
  overall_status: string;
  generated_at: string;
  toolkit_version: string;
  readiness_model_version: string;
  dataset_name: string;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  warning_checks: number;
  checks: PowerBiToolkitHealthCheck[];
  recommended_action: string;
};

async function fetchPowerBiToolkitHealth(): Promise<PowerBiToolkitHealth> {
  const response = await fetch(`${API_BASE}/api/enterprise/export-readiness-history.powerbi-toolkit.health`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-LumenAI-Role": "viewer",
      "X-LumenAI-Actor": "john-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Power BI toolkit health check failed (${response.status})`);
  }

  return data;
}

type PowerBiToolkitMetadataAsset = {
  file_name: string;
  asset_type: string;
  purpose: string;
};

type PowerBiToolkitMetadata = {
  status: string;
  toolkit_name: string;
  toolkit_version: string;
  toolkit_release: string;
  generated_at: string;
  dataset_name: string;
  source_system: string;
  readiness_model_version: string;
  included_assets: PowerBiToolkitMetadataAsset[];
  recommended_refresh_cadence?: {
    leadership_dashboard?: string;
    quality_committee?: string;
    survey_readiness_review?: string;
  };
};

async function fetchPowerBiToolkitMetadata(): Promise<PowerBiToolkitMetadata> {
  const response = await fetch(`${API_BASE}/api/enterprise/export-readiness-history.powerbi-toolkit.metadata`, {
    headers: {
      Authorization: "Bearer dev-token",
      "X-LumenAI-Role": "viewer",
      "X-LumenAI-Actor": "john-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Power BI toolkit metadata failed (${response.status})`);
  }

  return data;
}

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
  const [toolkitMetadata, setToolkitMetadata] = useState<PowerBiToolkitMetadata | null>(null);
  const [toolkitMetadataError, setToolkitMetadataError] = useState("");
  const [toolkitHealth, setToolkitHealth] = useState<PowerBiToolkitHealth | null>(null);
  const [toolkitHealthError, setToolkitHealthError] = useState("");
  const [finalValidation, setFinalValidation] = useState<PowerBiFinalValidation | null>(null);
  const [finalValidationError, setFinalValidationError] = useState("");
  const [productionLock, setProductionLock] = useState<PowerBiProductionLock | null>(null);
  const [productionLockError, setProductionLockError] = useState("");
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
    loadPowerBiToolkitMetadata();
    loadPowerBiToolkitHealth();
    loadPowerBiFinalValidation();
    loadPowerBiProductionLock();
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

  async function loadPowerBiProductionLock() {
    setProductionLockError("");

    try {
      const data = await fetchPowerBiProductionLock();
      setProductionLock(data);
    } catch (err) {
      setProductionLockError(err instanceof Error ? err.message : "Unknown Power BI production lock error");
    }
  }

  async function loadPowerBiFinalValidation() {
    setFinalValidationError("");

    try {
      const data = await fetchPowerBiFinalValidation();
      setFinalValidation(data);
    } catch (err) {
      setFinalValidationError(err instanceof Error ? err.message : "Unknown Power BI final validation error");
    }
  }

  async function loadPowerBiToolkitHealth() {
    setToolkitHealthError("");

    try {
      const data = await fetchPowerBiToolkitHealth();
      setToolkitHealth(data);
    } catch (err) {
      setToolkitHealthError(err instanceof Error ? err.message : "Unknown Power BI toolkit health error");
    }
  }

  async function loadPowerBiToolkitMetadata() {
    setToolkitMetadataError("");

    try {
      const data = await fetchPowerBiToolkitMetadata();
      setToolkitMetadata(data);
    } catch (err) {
      setToolkitMetadataError(err instanceof Error ? err.message : "Unknown Power BI toolkit metadata error");
    }
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
  const powerBiToolkitZipUrl = `${API_BASE}/api/enterprise/export-readiness-history.powerbi-toolkit.zip?${historyPdfParams.toString()}`;
  const powerBiToolkitReadmePdfUrl = `${API_BASE}/api/enterprise/export-readiness-history.powerbi-toolkit.readme.pdf`;
  const powerBiExecutiveSummaryPdfUrl = `${API_BASE}/api/enterprise/export-readiness-history.powerbi-toolkit.executive-summary.pdf`;
  const powerBiReleaseNotesPdfUrl = `${API_BASE}/api/enterprise/export-readiness-history.powerbi-toolkit.release-notes.pdf`;
  const powerBiCompletionCertificatePdfUrl = `${API_BASE}/api/enterprise/export-readiness-history.powerbi-toolkit.completion-certificate.pdf`;


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


  async function downloadPowerBiToolkitZip() {
    try {
      const response = await fetch(powerBiToolkitZipUrl, {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Power BI Toolkit ZIP download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = historyFindingId.trim()
        ? `lumenai-powerbi-export-toolkit-finding-${historyFindingId.trim()}.zip`
        : "lumenai-powerbi-export-toolkit-all.zip";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unknown Power BI Toolkit ZIP download error");
    }
  }


  async function downloadPowerBiToolkitReadmePdf() {
    try {
      const response = await fetch(powerBiToolkitReadmePdfUrl, {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Power BI Toolkit README PDF download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "lumenai-powerbi-toolkit-readme.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unknown Power BI Toolkit README PDF download error");
    }
  }


  async function downloadPowerBiExecutiveSummaryPdf() {
    try {
      const response = await fetch(powerBiExecutiveSummaryPdfUrl, {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Power BI Executive Summary PDF download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "lumenai-powerbi-toolkit-executive-summary.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unknown Power BI Executive Summary PDF download error");
    }
  }


  async function downloadPowerBiReleaseNotesPdf() {
    try {
      const response = await fetch(powerBiReleaseNotesPdfUrl, {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Power BI Release Notes PDF download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "lumenai-powerbi-toolkit-v1-release-notes.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unknown Power BI Release Notes PDF download error");
    }
  }


  async function downloadPowerBiCompletionCertificatePdf() {
    try {
      const response = await fetch(powerBiCompletionCertificatePdfUrl, {
        headers: {
          Authorization: "Bearer dev-token",
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
        },
      });

      if (!response.ok) {
        throw new Error(`Power BI Completion Certificate PDF download failed (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "lumenai-powerbi-toolkit-v1-completion-certificate.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Unknown Power BI Completion Certificate PDF download error");
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

        <div style={powerBiToolkitBadgeStyle}>
          <span style={powerBiToolkitBadgeIconStyle}>✓</span>
          <div>
            <strong>Power BI Toolkit Complete</strong>
            <p style={powerBiToolkitBadgeTextStyle}>
              CSV export, Power BI CSV, data dictionary, dashboard spec, toolkit ZIP, and README PDF are available.
            </p>

            <div style={toolkitHealthMiniBadgeStyle}>
              <span style={toolkitHealthMiniStatusStyle(toolkitHealth?.overall_status || "pending")}>
                Toolkit Health: {toolkitHealth?.overall_status || "Pending"}
              </span>
              <span>Passed: {toolkitHealth?.passed_checks ?? "-"}</span>
              <span>Failed: {toolkitHealth?.failed_checks ?? "-"}</span>
              <span>Version: {toolkitHealth?.toolkit_version || "-"}</span>
            </div>
          </div>
        </div>
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

      <div style={powerBiToolkitSummaryCardStyle}>
        <div style={powerBiToolkitSummaryHeaderStyle}>
          <div>
            <div style={powerBiToolkitSummaryEyebrowStyle}>Power BI Toolkit</div>
            <h3 style={powerBiToolkitSummaryTitleStyle}>Export Readiness Analytics Package</h3>
          </div>
          <span style={powerBiToolkitSummaryBadgeStyle}>Complete</span>
        </div>

        <div style={powerBiToolkitSummaryGridStyle}>
          <ToolkitAsset label="Standard History CSV" status="Ready" />
          <ToolkitAsset label="Power BI CSV" status="Ready" />
          <ToolkitAsset label="Data Dictionary PDF" status="Ready" />
          <ToolkitAsset label="Dashboard Spec PDF" status="Ready" />
          <ToolkitAsset label="Toolkit ZIP" status="Ready" />
          <ToolkitAsset label="README PDF" status="Ready" />
        </div>

        <p style={powerBiToolkitSummaryTextStyle}>
          Toolkit files support Excel review, Power BI dashboard development, audit readiness,
          export-readiness trending, and leadership reporting.
        </p>
      </div>

      <div style={productionLockCardStyle}>
        <div style={productionLockHeaderStyle}>
          <div>
            <div style={productionLockEyebrowStyle}>Production Lock</div>
            <h3 style={productionLockTitleStyle}>Power BI Toolkit Production Lock</h3>
          </div>
          <button type="button" onClick={loadPowerBiProductionLock} style={productionLockButtonStyle}>
            Refresh Lock
          </button>
        </div>

        {productionLockError ? (
          <div style={productionLockErrorStyle}>{productionLockError}</div>
        ) : null}

        {productionLock ? (
          <>
            <div style={productionLockStatusRowStyle}>
              <span style={productionLockBadgeStyle(productionLock.release_status)}>
                {productionLock.release_status}
              </span>
              <span style={productionLockGeneratedStyle}>
                Generated: {productionLock.generated_at ? new Date(productionLock.generated_at).toLocaleString() : "Not available"}
              </span>
            </div>

            <div style={productionLockGridStyle}>
              <ProductionLockMetric label="Toolkit Version" value={productionLock.toolkit_version} />
              <ProductionLockMetric label="Health Status" value={productionLock.health_status} />
              <ProductionLockMetric label="Validation Status" value={productionLock.final_validation_status} />
              <ProductionLockMetric label="Health Failed Checks" value={String(productionLock.health_failed_checks)} />
              <ProductionLockMetric label="Validation Failed Items" value={String(productionLock.final_validation_failed_items)} />
              <ProductionLockMetric label="Dataset" value={productionLock.dataset_name} />
            </div>

            <div style={productionLockMessageStyle}>
              <strong>Executive Message</strong>
              <p>{productionLock.executive_message}</p>
            </div>

            <div style={productionLockNextStepStyle}>
              <strong>Recommended Next Step</strong>
              <p>{productionLock.recommended_next_step}</p>
            </div>

            <details style={productionLockDetailsStyle}>
              <summary style={productionLockSummaryStyle}>View lock criteria and assets</summary>

              <div style={productionLockCriteriaListStyle}>
                {(productionLock.production_lock_criteria || []).map((item) => (
                  <div key={item.criterion} style={productionLockCriteriaItemStyle}>
                    <span style={productionLockCriteriaBadgeStyle(item.status)}>{item.status}</span>
                    <strong>{item.criterion}</strong>
                  </div>
                ))}
              </div>

              <div style={productionLockAssetsStyle}>
                <strong>Locked Assets</strong>
                <div style={productionLockAssetGridStyle}>
                  {(productionLock.locked_assets || []).map((asset) => (
                    <span key={asset} style={productionLockAssetStyle}>{asset}</span>
                  ))}
                </div>
              </div>
            </details>
          </>
        ) : (
          <p style={productionLockEmptyStyle}>Production lock has not loaded yet.</p>
        )}
      </div>

      <div style={finalValidationCardStyle}>
        <div style={finalValidationHeaderStyle}>
          <div>
            <div style={finalValidationEyebrowStyle}>Final Validation</div>
            <h3 style={finalValidationTitleStyle}>Power BI Toolkit Final Validation Checklist</h3>
          </div>
          <button type="button" onClick={loadPowerBiFinalValidation} style={finalValidationButtonStyle}>
            Refresh Validation
          </button>
        </div>

        {finalValidationError ? (
          <div style={finalValidationErrorStyle}>{finalValidationError}</div>
        ) : null}

        {finalValidation ? (
          <>
            <div style={finalValidationStatusRowStyle}>
              <span style={finalValidationBadgeStyle(finalValidation.final_status)}>
                {finalValidation.final_status}
              </span>
              <span style={finalValidationGeneratedStyle}>
                Generated: {finalValidation.generated_at ? new Date(finalValidation.generated_at).toLocaleString() : "Not available"}
              </span>
            </div>

            <div style={finalValidationGridStyle}>
              <ValidationMetric label="Toolkit Version" value={finalValidation.toolkit_version} />
              <ValidationMetric label="Readiness Model" value={finalValidation.readiness_model_version} />
              <ValidationMetric label="Dataset" value={finalValidation.dataset_name} />
              <ValidationMetric label="Total Items" value={String(finalValidation.total_items)} />
              <ValidationMetric label="Passed" value={String(finalValidation.passed_items)} />
              <ValidationMetric label="Failed" value={String(finalValidation.failed_items)} />
            </div>

            <div style={finalValidationSummaryStyle}>
              <strong>Executive Summary</strong>
              <p>{finalValidation.executive_summary}</p>
            </div>

            <div style={finalValidationNextStepStyle}>
              <strong>Recommended Next Step</strong>
              <p>{finalValidation.recommended_next_step}</p>
            </div>

            <details style={finalValidationDetailsStyle}>
              <summary style={finalValidationDetailsSummaryStyle}>View validation checklist</summary>
              <div style={finalValidationListStyle}>
                {(finalValidation.validation_items || []).map((item) => (
                  <div key={item.key} style={finalValidationItemStyle}>
                    <span style={finalValidationItemBadgeStyle(item.status)}>{item.status}</span>
                    <div>
                      <strong>{item.label}</strong>
                      <p>{item.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          </>
        ) : (
          <p style={finalValidationEmptyStyle}>Final validation has not loaded yet.</p>
        )}
      </div>

      <div style={toolkitHealthCardStyle}>
        <div style={toolkitHealthHeaderStyle}>
          <div>
            <div style={toolkitHealthEyebrowStyle}>Toolkit Health</div>
            <h3 style={toolkitHealthTitleStyle}>
              Power BI Toolkit Health Check
            </h3>
          </div>
          <button type="button" onClick={loadPowerBiToolkitHealth} style={toolkitHealthButtonStyle}>
            Refresh Health
          </button>
        </div>

        {toolkitHealthError ? (
          <div style={toolkitHealthErrorStyle}>{toolkitHealthError}</div>
        ) : null}

        {toolkitHealth ? (
          <>
            <div style={toolkitHealthStatusRowStyle}>
              <span style={toolkitHealthBadgeStyle(toolkitHealth.overall_status)}>
                {toolkitHealth.overall_status}
              </span>
              <span style={toolkitHealthGeneratedStyle}>
                Generated: {toolkitHealth.generated_at ? new Date(toolkitHealth.generated_at).toLocaleString() : "Not available"}
              </span>
            </div>

            <div style={toolkitHealthGridStyle}>
              <HealthMetric label="Toolkit Version" value={toolkitHealth.toolkit_version} />
              <HealthMetric label="Readiness Model" value={toolkitHealth.readiness_model_version} />
              <HealthMetric label="Dataset" value={toolkitHealth.dataset_name} />
              <HealthMetric label="Total Checks" value={String(toolkitHealth.total_checks)} />
              <HealthMetric label="Passed" value={String(toolkitHealth.passed_checks)} />
              <HealthMetric label="Failed" value={String(toolkitHealth.failed_checks)} />
              <HealthMetric label="Warnings" value={String(toolkitHealth.warning_checks)} />
            </div>

            <div style={toolkitHealthActionStyle}>
              <strong>Recommended Action</strong>
              <p>{toolkitHealth.recommended_action}</p>
            </div>

            <details style={toolkitHealthDetailsStyle}>
              <summary style={toolkitHealthSummaryStyle}>View health checks</summary>
              <div style={toolkitHealthCheckListStyle}>
                {(toolkitHealth.checks || []).map((check) => (
                  <div key={check.check_name} style={toolkitHealthCheckItemStyle}>
                    <span style={toolkitHealthCheckBadgeStyle(check.status)}>{check.status}</span>
                    <div>
                      <strong>{check.check_name}</strong>
                      <p>{check.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          </>
        ) : (
          <p style={toolkitHealthEmptyStyle}>Toolkit health has not loaded yet.</p>
        )}
      </div>

      <div style={toolkitMetadataCardStyle}>
        <div style={toolkitMetadataHeaderStyle}>
          <div>
            <div style={toolkitMetadataEyebrowStyle}>Toolkit Metadata</div>
            <h3 style={toolkitMetadataTitleStyle}>
              {toolkitMetadata?.toolkit_name || "LumenAI Power BI Export Toolkit"}
            </h3>
          </div>
          <button type="button" onClick={loadPowerBiToolkitMetadata} style={toolkitMetadataButtonStyle}>
            Refresh Metadata
          </button>
        </div>

        {toolkitMetadataError ? (
          <div style={toolkitMetadataErrorStyle}>{toolkitMetadataError}</div>
        ) : null}

        {toolkitMetadata ? (
          <>
            <div style={toolkitMetadataGridStyle}>
              <MetadataItem label="Toolkit Version" value={toolkitMetadata.toolkit_version} />
              <MetadataItem label="Readiness Model" value={toolkitMetadata.readiness_model_version} />
              <MetadataItem label="Dataset" value={toolkitMetadata.dataset_name} />
              <MetadataItem
                label="Generated"
                value={toolkitMetadata.generated_at ? new Date(toolkitMetadata.generated_at).toLocaleString() : ""}
              />
              <MetadataItem label="Included Assets" value={String(toolkitMetadata.included_assets?.length || 0)} />
              <MetadataItem label="Source System" value={toolkitMetadata.source_system} />
            </div>

            <div style={toolkitAssetListStyle}>
              {(toolkitMetadata.included_assets || []).map((asset) => (
                <div key={asset.file_name} style={toolkitAssetMetadataStyle}>
                  <strong>{asset.file_name}</strong>
                  <span>{asset.asset_type}</span>
                  <p>{asset.purpose}</p>
                </div>
              ))}
            </div>

            <div style={toolkitRefreshPlanStyle}>
              <strong>Recommended Refresh Cadence</strong>
              <p>Leadership dashboard: {toolkitMetadata.recommended_refresh_cadence?.leadership_dashboard || "Not specified"}</p>
              <p>Quality committee: {toolkitMetadata.recommended_refresh_cadence?.quality_committee || "Not specified"}</p>
              <p>Survey readiness: {toolkitMetadata.recommended_refresh_cadence?.survey_readiness_review || "Not specified"}</p>
            </div>
          </>
        ) : (
          <p style={toolkitMetadataEmptyStyle}>Toolkit metadata has not loaded yet.</p>
        )}
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

            <button type="button" onClick={downloadPowerBiToolkitZip} style={powerBiToolkitButtonStyle}>
              Download Power BI Toolkit ZIP
            </button>

            <button type="button" onClick={downloadPowerBiToolkitReadmePdf} style={toolkitReadmeButtonStyle}>
              Download Toolkit README PDF
            </button>

            <button type="button" onClick={downloadPowerBiExecutiveSummaryPdf} style={executiveSummaryButtonStyle}>
              Download Executive Summary PDF
            </button>

            <button type="button" onClick={downloadPowerBiReleaseNotesPdf} style={releaseNotesButtonStyle}>
              Download Release Notes PDF
            </button>

            <button type="button" onClick={downloadPowerBiCompletionCertificatePdf} style={completionCertificateButtonStyle}>
              Download Completion Certificate PDF
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

function ProductionLockMetric({ label, value }: { label: string; value?: string }) {
  return (
    <div style={productionLockMetricStyle}>
      <span style={productionLockMetricLabelStyle}>{label}</span>
      <strong style={productionLockMetricValueStyle}>{value || "Not available"}</strong>
    </div>
  );
}

function ValidationMetric({ label, value }: { label: string; value?: string }) {
  return (
    <div style={validationMetricStyle}>
      <span style={validationMetricLabelStyle}>{label}</span>
      <strong style={validationMetricValueStyle}>{value || "Not available"}</strong>
    </div>
  );
}

function HealthMetric({ label, value }: { label: string; value?: string }) {
  return (
    <div style={healthMetricStyle}>
      <span style={healthMetricLabelStyle}>{label}</span>
      <strong style={healthMetricValueStyle}>{value || "Not available"}</strong>
    </div>
  );
}

function MetadataItem({ label, value }: { label: string; value?: string }) {
  return (
    <div style={metadataItemStyle}>
      <span style={metadataItemLabelStyle}>{label}</span>
      <strong style={metadataItemValueStyle}>{value || "Not available"}</strong>
    </div>
  );
}

function ToolkitAsset({ label, status }: { label: string; status: string }) {
  return (
    <div style={toolkitAssetStyle}>
      <span style={toolkitAssetLabelStyle}>{label}</span>
      <strong style={toolkitAssetStatusStyle}>{status}</strong>
    </div>
  );
}

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


const powerBiToolkitButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#f3e8ff",
  color: "#6b21a8",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
  cursor: "pointer",
};


const toolkitReadmeButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#ccfbf1",
  color: "#115e59",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
  cursor: "pointer",
};


const powerBiToolkitBadgeStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  alignItems: "flex-start",
  marginTop: "14px",
  padding: "12px 14px",
  borderRadius: "16px",
  border: "1px solid #bbf7d0",
  background: "linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)",
  color: "#166534",
};

const powerBiToolkitBadgeIconStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: "24px",
  height: "24px",
  borderRadius: "999px",
  background: "#16a34a",
  color: "#ffffff",
  fontWeight: 900,
  flex: "0 0 auto",
};

const powerBiToolkitBadgeTextStyle: React.CSSProperties = {
  margin: "4px 0 0",
  color: "#166534",
  lineHeight: 1.45,
  fontSize: "13px",
};


const powerBiToolkitSummaryCardStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "16px",
  borderRadius: "20px",
  border: "1px solid #c4b5fd",
  background: "linear-gradient(135deg, #faf5ff 0%, #ffffff 100%)",
  boxShadow: "0 8px 24px rgba(88, 28, 135, 0.08)",
};

const powerBiToolkitSummaryHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
};

const powerBiToolkitSummaryEyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#7c3aed",
};

const powerBiToolkitSummaryTitleStyle: React.CSSProperties = {
  margin: "4px 0 0",
  fontSize: "18px",
  fontWeight: 900,
  color: "#2e1065",
};

const powerBiToolkitSummaryBadgeStyle: React.CSSProperties = {
  borderRadius: "999px",
  padding: "6px 10px",
  background: "#dcfce7",
  color: "#166534",
  fontWeight: 900,
  fontSize: "12px",
  whiteSpace: "nowrap",
};

const powerBiToolkitSummaryGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "10px",
  marginTop: "14px",
};

const toolkitAssetStyle: React.CSSProperties = {
  padding: "10px",
  borderRadius: "14px",
  border: "1px solid #e9d5ff",
  background: "#ffffff",
};

const toolkitAssetLabelStyle: React.CSSProperties = {
  display: "block",
  color: "#4c1d95",
  fontWeight: 800,
  fontSize: "13px",
};

const toolkitAssetStatusStyle: React.CSSProperties = {
  display: "block",
  marginTop: "4px",
  color: "#166534",
  fontSize: "12px",
};

const powerBiToolkitSummaryTextStyle: React.CSSProperties = {
  margin: "12px 0 0",
  color: "#475569",
  lineHeight: 1.5,
  fontSize: "13px",
};

const toolkitMetadataCardStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "16px",
  borderRadius: "20px",
  border: "1px solid #bae6fd",
  background: "linear-gradient(135deg, #f0f9ff 0%, #ffffff 100%)",
  boxShadow: "0 8px 24px rgba(14, 116, 144, 0.08)",
};

const toolkitMetadataHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
};

const toolkitMetadataEyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#0369a1",
};

const toolkitMetadataTitleStyle: React.CSSProperties = {
  margin: "4px 0 0",
  fontSize: "18px",
  fontWeight: 900,
  color: "#0c4a6e",
};

const toolkitMetadataButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#0ea5e9",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
  whiteSpace: "nowrap",
};

const toolkitMetadataGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "10px",
  marginTop: "14px",
};

const metadataItemStyle: React.CSSProperties = {
  padding: "10px",
  borderRadius: "14px",
  border: "1px solid #bae6fd",
  background: "#ffffff",
};

const metadataItemLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "11px",
  fontWeight: 900,
  textTransform: "uppercase",
  color: "#64748b",
};

const metadataItemValueStyle: React.CSSProperties = {
  display: "block",
  marginTop: "4px",
  color: "#0f172a",
  fontSize: "13px",
};

const toolkitAssetListStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
  gap: "10px",
  marginTop: "14px",
};

const toolkitAssetMetadataStyle: React.CSSProperties = {
  padding: "10px",
  borderRadius: "14px",
  border: "1px solid #e2e8f0",
  background: "#ffffff",
  color: "#334155",
};

const toolkitRefreshPlanStyle: React.CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "14px",
  background: "#ecfeff",
  color: "#164e63",
};

const toolkitMetadataErrorStyle: React.CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 800,
};

const toolkitMetadataEmptyStyle: React.CSSProperties = {
  margin: "12px 0 0",
  color: "#64748b",
};



const toolkitHealthCardStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "16px",
  borderRadius: "20px",
  border: "1px solid #bbf7d0",
  background: "linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)",
  boxShadow: "0 8px 24px rgba(22, 101, 52, 0.08)",
};

const toolkitHealthHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
};

const toolkitHealthEyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#15803d",
};

const toolkitHealthTitleStyle: React.CSSProperties = {
  margin: "4px 0 0",
  fontSize: "18px",
  fontWeight: 900,
  color: "#14532d",
};

const toolkitHealthButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#16a34a",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
  whiteSpace: "nowrap",
};

const toolkitHealthStatusRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  flexWrap: "wrap",
  marginTop: "14px",
};

function toolkitHealthBadgeStyle(status: string): React.CSSProperties {
  const normalized = (status || "").toLowerCase();
  const isHealthy = normalized === "healthy";
  const isWarning = normalized === "warning";

  return {
    borderRadius: "999px",
    padding: "6px 10px",
    fontSize: "12px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: isHealthy ? "#dcfce7" : isWarning ? "#ffedd5" : "#fee2e2",
    color: isHealthy ? "#166534" : isWarning ? "#9a3412" : "#991b1b",
  };
}

const toolkitHealthGeneratedStyle: React.CSSProperties = {
  color: "#475569",
  fontSize: "13px",
  fontWeight: 700,
};

const toolkitHealthGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
  gap: "10px",
  marginTop: "14px",
};

const healthMetricStyle: React.CSSProperties = {
  padding: "10px",
  borderRadius: "14px",
  border: "1px solid #bbf7d0",
  background: "#ffffff",
};

const healthMetricLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "11px",
  fontWeight: 900,
  textTransform: "uppercase",
  color: "#64748b",
};

const healthMetricValueStyle: React.CSSProperties = {
  display: "block",
  marginTop: "4px",
  color: "#0f172a",
  fontSize: "13px",
};

const toolkitHealthActionStyle: React.CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "14px",
  background: "#ffffff",
  border: "1px solid #bbf7d0",
  color: "#14532d",
};

const toolkitHealthDetailsStyle: React.CSSProperties = {
  marginTop: "12px",
};

const toolkitHealthSummaryStyle: React.CSSProperties = {
  cursor: "pointer",
  fontWeight: 900,
  color: "#166534",
};

const toolkitHealthCheckListStyle: React.CSSProperties = {
  display: "grid",
  gap: "8px",
  marginTop: "10px",
};

const toolkitHealthCheckItemStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  padding: "10px",
  borderRadius: "12px",
  border: "1px solid #e2e8f0",
  background: "#ffffff",
};

function toolkitHealthCheckBadgeStyle(status: string): React.CSSProperties {
  const normalized = (status || "").toLowerCase();

  return {
    alignSelf: "flex-start",
    borderRadius: "999px",
    padding: "4px 8px",
    fontSize: "11px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: normalized === "pass" ? "#dcfce7" : normalized === "warning" ? "#ffedd5" : "#fee2e2",
    color: normalized === "pass" ? "#166534" : normalized === "warning" ? "#9a3412" : "#991b1b",
  };
}

const toolkitHealthErrorStyle: React.CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 800,
};

const toolkitHealthEmptyStyle: React.CSSProperties = {
  margin: "12px 0 0",
  color: "#64748b",
};



const toolkitHealthMiniBadgeStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "8px",
  marginTop: "8px",
  fontSize: "12px",
  fontWeight: 900,
  color: "#166534",
};

function toolkitHealthMiniStatusStyle(status: string): React.CSSProperties {
  const normalized = (status || "").toLowerCase();
  const isHealthy = normalized === "healthy";
  const isWarning = normalized === "warning";
  const isPending = normalized === "pending";

  return {
    borderRadius: "999px",
    padding: "3px 8px",
    background: isHealthy
      ? "#dcfce7"
      : isWarning
      ? "#ffedd5"
      : isPending
      ? "#e2e8f0"
      : "#fee2e2",
    color: isHealthy
      ? "#166534"
      : isWarning
      ? "#9a3412"
      : isPending
      ? "#334155"
      : "#991b1b",
  };
}


const executiveSummaryButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#fee2e2",
  color: "#991b1b",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
  cursor: "pointer",
};



const finalValidationCardStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "16px",
  borderRadius: "20px",
  border: "1px solid #c4b5fd",
  background: "linear-gradient(135deg, #f5f3ff 0%, #ffffff 100%)",
  boxShadow: "0 8px 24px rgba(91, 33, 182, 0.08)",
};

const finalValidationHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
};

const finalValidationEyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#6d28d9",
};

const finalValidationTitleStyle: React.CSSProperties = {
  margin: "4px 0 0",
  fontSize: "18px",
  fontWeight: 900,
  color: "#3b0764",
};

const finalValidationButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#7c3aed",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
  whiteSpace: "nowrap",
};

const finalValidationStatusRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  flexWrap: "wrap",
  marginTop: "14px",
};

function finalValidationBadgeStyle(status: string): React.CSSProperties {
  const normalized = (status || "").toLowerCase();
  const isReady = normalized === "ready";

  return {
    borderRadius: "999px",
    padding: "6px 10px",
    fontSize: "12px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: isReady ? "#dcfce7" : "#fee2e2",
    color: isReady ? "#166534" : "#991b1b",
  };
}

const finalValidationGeneratedStyle: React.CSSProperties = {
  color: "#475569",
  fontSize: "13px",
  fontWeight: 700,
};

const finalValidationGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
  gap: "10px",
  marginTop: "14px",
};

const validationMetricStyle: React.CSSProperties = {
  padding: "10px",
  borderRadius: "14px",
  border: "1px solid #ddd6fe",
  background: "#ffffff",
};

const validationMetricLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "11px",
  fontWeight: 900,
  textTransform: "uppercase",
  color: "#64748b",
};

const validationMetricValueStyle: React.CSSProperties = {
  display: "block",
  marginTop: "4px",
  color: "#0f172a",
  fontSize: "13px",
};

const finalValidationSummaryStyle: React.CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "14px",
  background: "#ffffff",
  border: "1px solid #ddd6fe",
  color: "#3b0764",
};

const finalValidationNextStepStyle: React.CSSProperties = {
  marginTop: "10px",
  padding: "12px",
  borderRadius: "14px",
  background: "#f0fdf4",
  border: "1px solid #bbf7d0",
  color: "#14532d",
};

const finalValidationDetailsStyle: React.CSSProperties = {
  marginTop: "12px",
};

const finalValidationDetailsSummaryStyle: React.CSSProperties = {
  cursor: "pointer",
  fontWeight: 900,
  color: "#6d28d9",
};

const finalValidationListStyle: React.CSSProperties = {
  display: "grid",
  gap: "8px",
  marginTop: "10px",
};

const finalValidationItemStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  padding: "10px",
  borderRadius: "12px",
  border: "1px solid #e2e8f0",
  background: "#ffffff",
};

function finalValidationItemBadgeStyle(status: string): React.CSSProperties {
  const normalized = (status || "").toLowerCase();

  return {
    alignSelf: "flex-start",
    borderRadius: "999px",
    padding: "4px 8px",
    fontSize: "11px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: normalized === "pass" ? "#dcfce7" : "#fee2e2",
    color: normalized === "pass" ? "#166534" : "#991b1b",
  };
}

const finalValidationErrorStyle: React.CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 800,
};

const finalValidationEmptyStyle: React.CSSProperties = {
  margin: "12px 0 0",
  color: "#64748b",
};



const productionLockCardStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "16px",
  borderRadius: "20px",
  border: "1px solid #facc15",
  background: "linear-gradient(135deg, #fefce8 0%, #ffffff 100%)",
  boxShadow: "0 8px 24px rgba(161, 98, 7, 0.08)",
};

const productionLockHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
};

const productionLockEyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#a16207",
};

const productionLockTitleStyle: React.CSSProperties = {
  margin: "4px 0 0",
  fontSize: "18px",
  fontWeight: 900,
  color: "#713f12",
};

const productionLockButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#ca8a04",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
  whiteSpace: "nowrap",
};

const productionLockStatusRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  flexWrap: "wrap",
  marginTop: "14px",
};

function productionLockBadgeStyle(status: string): React.CSSProperties {
  const normalized = (status || "").toLowerCase();
  const isLocked = normalized === "locked";

  return {
    borderRadius: "999px",
    padding: "6px 10px",
    fontSize: "12px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: isLocked ? "#dcfce7" : "#fee2e2",
    color: isLocked ? "#166534" : "#991b1b",
  };
}

const productionLockGeneratedStyle: React.CSSProperties = {
  color: "#475569",
  fontSize: "13px",
  fontWeight: 700,
};

const productionLockGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
  gap: "10px",
  marginTop: "14px",
};

const productionLockMetricStyle: React.CSSProperties = {
  padding: "10px",
  borderRadius: "14px",
  border: "1px solid #fde68a",
  background: "#ffffff",
};

const productionLockMetricLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "11px",
  fontWeight: 900,
  textTransform: "uppercase",
  color: "#64748b",
};

const productionLockMetricValueStyle: React.CSSProperties = {
  display: "block",
  marginTop: "4px",
  color: "#0f172a",
  fontSize: "13px",
};

const productionLockMessageStyle: React.CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "14px",
  background: "#ffffff",
  border: "1px solid #fde68a",
  color: "#713f12",
};

const productionLockNextStepStyle: React.CSSProperties = {
  marginTop: "10px",
  padding: "12px",
  borderRadius: "14px",
  background: "#f0fdf4",
  border: "1px solid #bbf7d0",
  color: "#14532d",
};

const productionLockDetailsStyle: React.CSSProperties = {
  marginTop: "12px",
};

const productionLockSummaryStyle: React.CSSProperties = {
  cursor: "pointer",
  fontWeight: 900,
  color: "#a16207",
};

const productionLockCriteriaListStyle: React.CSSProperties = {
  display: "grid",
  gap: "8px",
  marginTop: "10px",
};

const productionLockCriteriaItemStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  alignItems: "center",
  padding: "10px",
  borderRadius: "12px",
  border: "1px solid #e2e8f0",
  background: "#ffffff",
};

function productionLockCriteriaBadgeStyle(status: string): React.CSSProperties {
  const normalized = (status || "").toLowerCase();

  return {
    borderRadius: "999px",
    padding: "4px 8px",
    fontSize: "11px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: normalized === "pass" ? "#dcfce7" : "#fee2e2",
    color: normalized === "pass" ? "#166534" : "#991b1b",
  };
}

const productionLockAssetsStyle: React.CSSProperties = {
  marginTop: "12px",
};

const productionLockAssetGridStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "8px",
  marginTop: "8px",
};

const productionLockAssetStyle: React.CSSProperties = {
  borderRadius: "999px",
  padding: "5px 9px",
  background: "#fef3c7",
  color: "#713f12",
  fontSize: "12px",
  fontWeight: 800,
};

const productionLockErrorStyle: React.CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 800,
};

const productionLockEmptyStyle: React.CSSProperties = {
  margin: "12px 0 0",
  color: "#64748b",
};


const releaseNotesButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#fce7f3",
  color: "#9d174d",
  fontWeight: 900,
  textDecoration: "none",
  whiteSpace: "nowrap",
  cursor: "pointer",
};


const completionCertificateButtonStyle: React.CSSProperties = {
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
