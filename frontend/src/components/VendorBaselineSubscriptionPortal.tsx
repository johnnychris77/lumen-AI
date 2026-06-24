import { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://lumen-ai-53u4.onrender.com";


type ComplianceEvidenceBundleResponse = {
  status: string;
  bundle_hash: string;
  bundle_hash_algorithm: string;
  bundle_event_id?: number;
  bundle: {
    bundle_type: string;
    bundle_version: string;
    generated_at: string;
    generated_by: string;
    generated_role: string;
    tamper_evident: boolean;
    audit_export: {
      count: number;
      audit_export_hash: string;
      audit_export_hash_algorithm: string;
      audit_export_verification_url: string;
    };
    manifest: {
      manifest_hash: string;
      manifest_hash_algorithm: string;
      manifest_verification_url: string;
    };
    compliance_controls: string[];
    bundle_verification_url?: string;
  };
};

type ComplianceEvidenceSummaryResponse = {
  status: string;
  verified: boolean;
  summary_type?: string;
  bundle_hash: string;
  bundle_hash_algorithm: string;
  generated_at?: string;
  generated_by?: string;
  generated_role?: string;
  audit_export_hash?: string;
  manifest_hash?: string;
  export_count?: number;
  tamper_evident?: boolean;
  compliance_controls?: string[];
  message?: string;
};

type VendorBaselineRecord = {
  baseline_id: number;
  vendor_name: string;
  instrument_name: string;
  instrument_category: string;
  catalog_number: string;
  model_number: string;
  barcode_value: string;
  qr_code_value: string;
  key_dot_value: string;
  tray_name: string;
  baseline_image_url: string;
  acceptable_condition_notes: string;
  unacceptable_condition_examples: string;
  ifu_reference: string;
  subscription_tier: string;
  baseline_source: string;
  baseline_status: string;
  approval_status: string;
  baseline_version: string;
  created_at: string;
  updated_at: string;
  approved_by?: string;
  approval_notes?: string;
};

type VendorBaselineListResponse = {
  status: string;
  library_type: string;
  generated_at: string;
  record_count: number;
  total_library_count: number;
  records: VendorBaselineRecord[];
  recommended_use: string;
};

type VendorBaselineMatchResponse = {
  status: string;
  match_type: string;
  match_status: string;
  match_count: number;
  approved_match_count: number;
  best_match: VendorBaselineRecord | null;
  matches: VendorBaselineRecord[];
  recommended_action: string;
};

type VendorBaselineAuditEvent = {
  event_id?: number;
  event_type: string;
  actor?: string;
  actor_role?: string;
  decision?: string;
  notes?: string;
  evidence_source?: string;
  finding_id?: number | null;
  inspection_id?: number | null;
  matched_identifier_type?: string;
  matched_identifier_value?: string;
  previous_status?: string | null;
  new_status?: string;
  created_at?: string;
};

type VendorBaselineAuditResponse = {
  status: string;
  baseline_id: number;
  vendor?: string;
  instrument?: string;
  baseline_status?: string;
  approval_status?: string;
  audit_source?: string;
  audit_event_count: number;
  events: VendorBaselineAuditEvent[];
};

type GovernanceExportHistoryItem = {
  event_id: number;
  action_type: string;
  actor?: string;
  actor_role?: string;
  resource_type?: string;
  resource_id?: string;
  packet_type?: string;
  export_format?: string;
  filename?: string;
  included_vendor_baseline_audit_trail?: boolean;
  audit_event_count?: number | null;
  vendor_baseline_audit_event_count?: number | null;
  created_at?: string;
};

type GovernancePacketCertificate = {
  status: string;
  certificate_type: string;
  finding_id: number;
  resource_type: string;
  resource_id: string;
  event_id: number;
  action_type: string;
  filename: string;
  export_format: string;
  packet_hash_algorithm: string;
  packet_hash: string;
  tamper_evident: boolean;
  included_vendor_baseline_audit_trail: boolean;
  audit_event_count?: number | null;
  vendor_baseline_audit_event_count?: number | null;
  exported_by: string;
  exported_role: string;
  exported_at: string;
  verification_url: string;
  message: string;
};

type GovernanceExportHistoryResponse = {
  status: string;
  finding_id: number;
  export_count: number;
  last_exported_at: string;
  exports: GovernanceExportHistoryItem[];
};

type PacketHashVerificationResponse = {
  status: string;
  finding_id: number;
  verified: boolean;
  verification_status: string;
  packet_hash_algorithm?: string;
  packet_hash?: string;
  checked_hash_export_count?: number;
  message?: string;
  matched_export?: GovernanceExportHistoryItem;
};

const AUTH_HEADERS = {
  Authorization: `Bearer ${localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || ""}`,
  "X-LumenAI-Role": "vendor",
  "X-LumenAI-Actor": "stryker-demo",
};

async function fetchVendorBaselines(): Promise<VendorBaselineListResponse> {
  const response = await fetch(`${API_BASE}/api/enterprise/vendor-baseline-subscription/baselines?limit=50`, {
    headers: AUTH_HEADERS,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Vendor baseline list failed (${response.status})`);
  }

  return data;
}

async function createVendorBaseline(payload: Record<string, string>) {
  const response = await fetch(`${API_BASE}/api/enterprise/vendor-baseline-subscription/baselines`, {
    method: "POST",
    headers: {
      ...AUTH_HEADERS,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Vendor baseline creation failed (${response.status})`);
  }

  return data;
}

async function approveVendorBaseline(baselineId: number, approvalNotes: string) {
  const response = await fetch(`${API_BASE}/api/enterprise/vendor-baseline-subscription/baselines/${baselineId}/approve`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || ""}`,
      "X-LumenAI-Role": "manager",
      "X-LumenAI-Actor": "john-demo",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      approval_notes: approvalNotes,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Vendor baseline approval failed (${response.status})`);
  }

  return data;
}

async function fetchVendorBaselineAudit(baselineId: number): Promise<VendorBaselineAuditResponse> {
  const response = await fetch(`${API_BASE}/api/enterprise/vendor-baseline-subscription/baselines/${baselineId}/audit`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || ""}`,
      "X-LumenAI-Role": "hospital_admin",
      "X-LumenAI-Actor": "hospital-reviewer-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Vendor baseline audit failed (${response.status})`);
  }

  return data;
}

async function fetchGovernanceExportHistory(findingId: string): Promise<GovernanceExportHistoryResponse> {
  const response = await fetch(`${API_BASE}/api/enterprise/intake/${findingId}/governance-export-history`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || ""}`,
      "X-LumenAI-Role": "hospital_admin",
      "X-LumenAI-Actor": "hospital-reviewer-demo",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Governance export history failed (${response.status})`);
  }

  return data;
}

async function verifyGovernancePacketHash(
  findingId: string,
  packetHash: string
): Promise<PacketHashVerificationResponse> {
  const response = await fetch(
    `${API_BASE}/api/enterprise/intake/${findingId}/governance-packet/verify-hash?packet_hash=${encodeURIComponent(packetHash)}`,
    {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || ""}`,
        "X-LumenAI-Role": "hospital_admin",
        "X-LumenAI-Actor": "hospital-reviewer-demo",
      },
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Packet hash verification failed (${response.status})`);
  }

  return data;
}

async function matchVendorBaseline(identifierValue: string): Promise<VendorBaselineMatchResponse> {
  const response = await fetch(`${API_BASE}/api/enterprise/vendor-baseline-subscription/match`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || ""}`,
      "X-LumenAI-Role": "viewer",
      "X-LumenAI-Actor": "john-demo",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      identifier_value: identifierValue,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Vendor baseline match failed (${response.status})`);
  }

  return data;
}

export default function VendorBaselineSubscriptionPortal() {

  const [evidenceBundleLoading, setEvidenceBundleLoading] = useState(false);
  const [evidenceBundleError, setEvidenceBundleError] = useState("");
  const [evidenceBundle, setEvidenceBundle] = useState<ComplianceEvidenceBundleResponse | null>(null);
  const [evidenceSummaryLoading, setEvidenceSummaryLoading] = useState(false);
  const [evidenceSummary, setEvidenceSummary] = useState<ComplianceEvidenceSummaryResponse | null>(null);
  const [records, setRecords] = useState<VendorBaselineRecord[]>([]);
  const [summary, setSummary] = useState<VendorBaselineListResponse | null>(null);
  const [matchResult, setMatchResult] = useState<VendorBaselineMatchResponse | null>(null);
  const [matchValue, setMatchValue] = useState("STRYKER-BARCODE-001");
  const [approvalNotes, setApprovalNotes] = useState("Approved as vendor baseline for scoring use.");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [matching, setMatching] = useState(false);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState("");
  const [selectedAudit, setSelectedAudit] = useState<VendorBaselineAuditResponse | null>(null);
  const [packetFindingId, setPacketFindingId] = useState("1");
  const [exportHistoryLoading, setExportHistoryLoading] = useState(false);
  const [exportHistoryError, setExportHistoryError] = useState("");
  const [certificateLoading, setCertificateLoading] = useState(false);
  const [certificateError, setCertificateError] = useState("");
  const [selectedCertificate, setSelectedCertificate] = useState<GovernancePacketCertificate | null>(null);
  const [exportHistory, setExportHistory] = useState<GovernanceExportHistoryResponse | null>(null);
  const [packetHashInput, setPacketHashInput] = useState("");
  const [packetVerificationLoading, setPacketVerificationLoading] = useState(false);
  const [packetVerificationError, setPacketVerificationError] = useState("");
  const [packetVerification, setPacketVerification] = useState<PacketHashVerificationResponse | null>(null);
  const [error, setError] = useState("");
  const [bundleHashToVerify, setBundleHashToVerify] = useState("");
  const [bundleVerificationLoading, setBundleVerificationLoading] = useState(false);
  const [bundleVerificationError, setBundleVerificationError] = useState("");
  const [bundleVerificationResult, setBundleVerificationResult] =
    useState<ComplianceEvidenceSummaryResponse | null>(null);

  const [form, setForm] = useState({
    vendor_name: "Stryker",
    instrument_name: "Kerrison Rongeur",
    instrument_category: "Orthopedic Instrument",
    catalog_number: "STR-KR-001",
    model_number: "KR-45",
    barcode_value: "STRYKER-BARCODE-001",
    qr_code_value: "STRYKER-QR-001",
    key_dot_value: "DOT-STR-001",
    tray_name: "Ortho Spine Tray",
    baseline_image_url: "https://example.com/stryker/kerrison-baseline.jpg",
    acceptable_condition_notes: "Normal clean jaw surface with no visible bioburden or damage.",
    unacceptable_condition_examples: "Bioburden, rust, cracked jaw, pitting, retained tissue.",
    ifu_reference: "Stryker IFU Reference Demo",
    subscription_tier: "vendor_enterprise",
  });

  async function loadRecords() {
    setLoading(true);
    setError("");

    try {
      const data = await fetchVendorBaselines();
      setSummary(data);
      setRecords(data.records || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown vendor baseline list error");
    } finally {
      setLoading(false);
    }
  }

  async function submitBaseline() {
    setSaving(true);
    setError("");

    try {
      await createVendorBaseline(form);
      await loadRecords();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown vendor baseline creation error");
    } finally {
      setSaving(false);
    }
  }

  async function approveBaseline(baselineId: number) {
    setSaving(true);
    setError("");

    try {
      await approveVendorBaseline(baselineId, approvalNotes);
      await loadRecords();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown vendor baseline approval error");
    } finally {
      setSaving(false);
    }
  }

  async function loadExportHistory() {
    const safeFindingId = packetFindingId.trim() || "1";
    setExportHistoryLoading(true);
    setExportHistoryError("");

    try {
      const data = await fetchGovernanceExportHistory(safeFindingId);
      setExportHistory(data);
    } catch (err) {
      setExportHistoryError(err instanceof Error ? err.message : "Unknown governance export history error");
    } finally {
      setExportHistoryLoading(false);
    }
  }

  function downloadGovernancePdf() {
    const safeFindingId = packetFindingId.trim() || "1";
    const pdfUrl = `${API_BASE}/api/enterprise/intake/${safeFindingId}/governance-packet.pdf`;

    window.open(pdfUrl, "_blank", "noopener,noreferrer");

    window.setTimeout(() => {
      loadExportHistory();
    }, 1200);
  }

  async function verifyPacketHash() {
    const safeFindingId = packetFindingId.trim() || "1";
    const safeHash = packetHashInput.trim();

    setPacketVerificationLoading(true);
    setPacketVerificationError("");
    setPacketVerification(null);

    if (!safeHash) {
      setPacketVerificationError("Enter a packet hash to verify.");
      setPacketVerificationLoading(false);
      return;
    }

    try {
      const data = await verifyGovernancePacketHash(safeFindingId, safeHash);
      setPacketVerification(data);
    } catch (err) {
      setPacketVerificationError(err instanceof Error ? err.message : "Unknown packet hash verification error");
    } finally {
      setPacketVerificationLoading(false);
    }
  }

  async function viewAuditTrail(baselineId: number) {
    setAuditLoading(true);
    setAuditError("");
    setSelectedAudit(null);

    try {
      const data = await fetchVendorBaselineAudit(baselineId);
      setSelectedAudit(data);
    } catch (err) {
      setAuditError(err instanceof Error ? err.message : "Unknown vendor baseline audit error");
    } finally {
      setAuditLoading(false);
    }
  }

  async function runMatch() {
    setMatching(true);
    setError("");

    try {
      const data = await matchVendorBaseline(matchValue);
      setMatchResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown vendor baseline match error");
    } finally {
      setMatching(false);
    }
  }

  useEffect(() => {
    loadRecords();
  }, []);

  
  async function handleGenerateComplianceEvidenceBundle() {
    try {
      setEvidenceBundleLoading(true);
      setEvidenceBundleError("");
      setEvidenceSummary(null);

      const response = await fetch(
        `${API_BASE}/api/enterprise/audit/evidence-bundle?limit=200`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || ""}`,
            "X-LumenAI-Role": "enterprise_admin",
            "X-LumenAI-Actor": "frontend-evidence-bundle-admin",
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Evidence bundle request returned ${response.status}`);
      }

      const payload = await response.json();
      setEvidenceBundle(payload);
    } catch (error: any) {
      setEvidenceBundleError(error?.message || "Unable to generate evidence bundle.");
    } finally {
      setEvidenceBundleLoading(false);
    }
  }

  async function handleViewEvidenceBundleSummary(bundleHash: string) {
    try {
      setEvidenceSummaryLoading(true);
      setEvidenceBundleError("");

      const response = await fetch(
        `${API_BASE}/api/enterprise/audit/evidence-bundle/verification-summary?bundle_hash=${encodeURIComponent(bundleHash)}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || ""}`,
            "X-LumenAI-Role": "enterprise_admin",
            "X-LumenAI-Actor": "frontend-evidence-summary-admin",
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Evidence summary request returned ${response.status}`);
      }

      const payload = await response.json();
      setEvidenceSummary(payload);
    } catch (error: any) {
      setEvidenceBundleError(error?.message || "Unable to load evidence bundle summary.");
    } finally {
      setEvidenceSummaryLoading(false);
    }
  }

  function handleDownloadEvidenceBundle() {
    const url = `${API_BASE}/api/enterprise/audit/evidence-bundle/download.json?limit=200`;
    window.open(url, "_blank", "noopener,noreferrer");
  }


  async function handleVerifyEvidenceBundleHash() {
    try {
      setBundleVerificationLoading(true);
      setBundleVerificationError("");
      setBundleVerificationResult(null);

      const cleanHash = bundleHashToVerify.trim();

      if (!cleanHash) {
        throw new Error("Enter a bundle hash to verify.");
      }

      const response = await fetch(
        `${API_BASE}/api/enterprise/audit/evidence-bundle/verification-summary?bundle_hash=${encodeURIComponent(cleanHash)}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || ""}`,
            "X-LumenAI-Role": "enterprise_admin",
            "X-LumenAI-Actor": "frontend-bundle-verification-admin",
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Bundle verification request returned ${response.status}`);
      }

      const payload = await response.json();
      setBundleVerificationResult(payload);
    } catch (error: any) {
      setBundleVerificationError(error?.message || "Unable to verify bundle hash.");
    } finally {
      setBundleVerificationLoading(false);
    }
  }

return (
    <section style={panelStyle}>
      <div style={headerRowStyle}>
        <div>
          <div style={eyebrowStyle}>Vendor Baseline Governance</div>
          <h2 style={titleStyle}>Vendor Baseline Subscription Portal</h2>
          <p style={subtitleStyle}>
            Vendor subscribers can publish baseline reference records so hospitals can improve instrument matching,
            baseline comparison, and LumenAI score confidence.
          </p>
        </div>

        <button type="button" onClick={loadRecords} style={refreshButtonStyle}>
          {loading ? "Refreshing..." : "Refresh Library"}
        </button>
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      <div style={summaryGridStyle}>
        <MetricCard label="Visible Records" value={records.length} />
        <MetricCard label="Library Count" value={summary?.total_library_count || 0} />
        <MetricCard label="Approved" value={records.filter((record) => record.baseline_status === "approved").length} />
        <MetricCard label="Pending Review" value={records.filter((record) => record.approval_status === "pending_hospital_review").length} />
      </div>

      <div style={formCardStyle}>
        <h3 style={sectionTitleStyle}>Create Vendor Baseline Record</h3>
        <p style={bodyTextStyle}>
          This demo creates a vendor-submitted baseline record with barcode, QR code, and key-dot identifiers.
        </p>

        <div style={formGridStyle}>
          {Object.entries(form).map(([key, value]) => (
            <label key={key} style={labelStyle}>
              {fieldLabel(key)}
              <input
                value={value}
                onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))}
                style={inputStyle}
              />
            </label>
          ))}
        </div>

        <button type="button" onClick={submitBaseline} style={primaryButtonStyle}>
          {saving ? "Saving..." : "Create Vendor Baseline"}
        </button>
      </div>

      <div style={matchCardStyle}>
        <h3 style={sectionTitleStyle}>Match Baseline by Barcode / QR / Key Dot</h3>
        <p style={bodyTextStyle}>
          Use this to simulate a technician scanning a barcode, QR code, key dot, catalog number, or model number.
        </p>

        <div style={matchRowStyle}>
          <input
            value={matchValue}
            onChange={(event) => setMatchValue(event.target.value)}
            style={matchInputStyle}
            placeholder="Scan or enter identifier"
          />

          <button type="button" onClick={runMatch} style={matchButtonStyle}>
            {matching ? "Matching..." : "Match Baseline"}
          </button>
        </div>

        {matchResult ? (
          <div style={matchResultStyle}>
            <div style={matchStatusBadgeStyle(matchResult.match_status)}>{matchResult.match_status}</div>
            <p style={bodyTextStyle}>{matchResult.recommended_action}</p>

            {matchResult.best_match ? (
              <div style={bestMatchStyle}>
                <strong>Best Match: {matchResult.best_match.instrument_name}</strong>
                <p>
                  {matchResult.best_match.vendor_name} · {matchResult.best_match.catalog_number} ·{" "}
                  {matchResult.best_match.baseline_status}
                </p>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <div style={exportCardStyle}>
        <div>
          <h3 style={sectionTitleStyle}>Governance Evidence Packet Export</h3>
          <p style={bodyTextStyle}>
            Download the governance PDF packet with baseline evidence and persistent vendor baseline audit trail.
          </p>
        </div>

        <div style={exportActionRowStyle}>
          <label style={exportLabelStyle}>
            Finding ID
            <input
              value={packetFindingId}
              onChange={(event) => setPacketFindingId(event.target.value)}
              style={exportInputStyle}
              placeholder="1"
            />
          </label>

          <button type="button" onClick={downloadGovernancePdf} style={exportButtonStyle}>
            Download Governance PDF
          </button>

          <button
            type="button"
            onClick={() => {
              const id = packetFindingId.trim() || "1";
              window.open(`${API_BASE}/api/enterprise/intake/${id}/governance-packet`, "_blank");
            }}
            style={{
              border: "1px solid #0f766e",
              borderRadius: "999px",
              background: "#f0fdfa",
              color: "#0f766e",
              padding: "10px 14px",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            View Certificate
          </button>

          <button type="button" onClick={loadExportHistory} style={exportHistoryButtonStyle}>
            View Export History
          </button>
        </div>

        <div style={packetVerifyPanelStyle}>
          <h4 style={{ margin: 0, color: "#064e3b", fontSize: "15px" }}>
            Verify Governance Packet Hash
          </h4>

          <p style={bodyTextStyle}>
            Paste a SHA-256 packet hash to confirm whether it matches a stored governance PDF export record.
          </p>

          <div style={packetVerifyRowStyle}>
            <input
              value={packetHashInput}
              onChange={(event) => setPacketHashInput(event.target.value)}
              style={packetHashInputStyle}
              placeholder="Paste SHA-256 packet hash"
            />

            <button type="button" onClick={verifyPacketHash} style={packetVerifyButtonStyle}>
              {packetVerificationLoading ? "Verifying..." : "Verify Packet"}
            </button>
          </div>

          {packetVerificationError ? (
            <div style={errorStyle}>{packetVerificationError}</div>
          ) : null}

          {packetVerification ? (
            <div
              style={
                packetVerification.verified
                  ? packetVerifiedResultStyle
                  : packetNotVerifiedResultStyle
              }
            >
              <div style={{ fontWeight: 900 }}>
                {packetVerification.verified ? "Verified Packet" : "Packet Not Verified"}
              </div>

              <div style={mutedTextStyle}>
                Status: {packetVerification.verification_status}
              </div>

              <div style={mutedTextStyle}>
                Algorithm: {packetVerification.packet_hash_algorithm || "SHA-256"}
              </div>

              <div style={hashTextStyle}>
                Hash: {packetVerification.packet_hash || "N/A"}
              </div>

              <div style={mutedTextStyle}>
                Checked Export Records: {packetVerification.checked_hash_export_count ?? "N/A"}
              </div>

              <div style={mutedTextStyle}>
                Message: {packetVerification.message || "N/A"}
              </div>

              {packetVerification.matched_export ? (
                <>
                  <div style={matchedExportStyle}>
                    <strong>Matched Export</strong>
                    <div style={mutedTextStyle}>
                      Event ID: {packetVerification.matched_export.event_id}
                    </div>
                    <div style={mutedTextStyle}>
                      Actor: {packetVerification.matched_export.actor || "N/A"} ({packetVerification.matched_export.actor_role || "N/A"})
                    </div>
                    <div style={mutedTextStyle}>
                      File: {packetVerification.matched_export.filename || "N/A"}
                    </div>
                    <div style={mutedTextStyle}>
                      Created: {packetVerification.matched_export.created_at || "N/A"}
                    </div>
                    <div style={mutedTextStyle}>
                      Vendor Baseline Audit Trail Included: {packetVerification.matched_export.included_vendor_baseline_audit_trail ? "Yes" : "No"}
                    </div>
                  </div>

                  <div style={immutableCertificateStyle}>
                    <div style={certificateHeaderStyle}>
                      <div>
                        <div style={certificateEyebrowStyle}>Immutable Export Certificate</div>
                        <h4 style={certificateTitleStyle}>Verified Governance Evidence Packet</h4>
                      </div>
                      <div style={certificateSealStyle}>VERIFIED</div>
                    </div>

                    <div style={certificateGridStyle}>
                      <div>
                        <strong>Finding ID</strong>
                        <div>{packetVerification.finding_id}</div>
                      </div>
                      <div>
                        <strong>Export Event ID</strong>
                        <div>{packetVerification.matched_export.event_id}</div>
                      </div>
                      <div>
                        <strong>Algorithm</strong>
                        <div>{packetVerification.packet_hash_algorithm || "SHA-256"}</div>
                      </div>
                      <div>
                        <strong>Tamper Evident</strong>
                        <div>{packetVerification.matched_export.tamper_evident ? "Yes" : "No"}</div>
                      </div>
                      <div>
                        <strong>Actor</strong>
                        <div>{packetVerification.matched_export.actor || "N/A"}</div>
                      </div>
                      <div>
                        <strong>Role</strong>
                        <div>{packetVerification.matched_export.actor_role || "N/A"}</div>
                      </div>
                      <div>
                        <strong>Filename</strong>
                        <div>{packetVerification.matched_export.filename || "N/A"}</div>
                      </div>
                      <div>
                        <strong>Exported At</strong>
                        <div>{packetVerification.matched_export.created_at || "N/A"}</div>
                      </div>
                      <div>
                        <strong>Audit Trail Included</strong>
                        <div>{packetVerification.matched_export.included_vendor_baseline_audit_trail ? "Yes" : "No"}</div>
                      </div>
                    </div>

                    <div style={certificateHashBoxStyle}>
                      <strong>Packet Hash</strong>
                      <div>{packetVerification.packet_hash || packetVerification.matched_export.packet_hash || "N/A"}</div>
                    </div>

                    <p style={certificateFootnoteStyle}>
                      This certificate confirms that the supplied SHA-256 packet hash matches a stored LumenAI governance PDF export record.
                    </p>
                  </div>
                </>
              ) : null}
            </div>
          ) : null}
        </div>

        {(exportHistoryLoading || exportHistoryError || exportHistory) ? (
          <div style={exportHistoryPanelStyle}>
            <h4 style={{ margin: 0, color: "#312e81", fontSize: "15px" }}>
              Governance Packet Export History
            </h4>

            {exportHistoryLoading ? (
              <p style={bodyTextStyle}>Loading export history...</p>
            ) : null}

            {exportHistoryError ? (
              <div style={errorStyle}>{exportHistoryError}</div>
            ) : null}

            {exportHistory ? (
              <>
                <div style={exportHistorySummaryStyle}>
                  <div>
                    <strong>Finding ID:</strong> {exportHistory.finding_id}
                  </div>
                  <div>
                    <strong>Export Count:</strong> {exportHistory.export_count}
                  </div>
                  <div>
                    <strong>Last Exported:</strong> {exportHistory.last_exported_at || "N/A"}
                  </div>
                </div>

                <div style={exportHistoryListStyle}>
                  {(exportHistory.exports || []).slice(0, 5).map((item) => (
                    <div key={item.event_id} style={exportHistoryItemStyle}>
                      <div style={{ fontWeight: 900, color: "#0f172a" }}>
                        {item.action_type}
                      </div>
                      <div style={mutedTextStyle}>
                        Actor: {item.actor || "N/A"} ({item.actor_role || "N/A"})
                      </div>
                      <div style={mutedTextStyle}>
                        Format: {item.export_format || "N/A"} · Filename: {item.filename || "N/A"}
                      </div>
                      <div style={mutedTextStyle}>
                        Vendor Baseline Audit Trail Included: {item.included_vendor_baseline_audit_trail ? "Yes" : "No"}
                      </div>
                      <div style={mutedTextStyle}>
                        Audit Events: {item.audit_event_count ?? "N/A"} · Vendor Baseline Audit Events: {item.vendor_baseline_audit_event_count ?? "N/A"}
                      </div>
                      <div style={mutedTextStyle}>
                        Created: {item.created_at || "N/A"}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : null}
          </div>
        ) : null}
      </div>

      <div style={libraryCardStyle}>
        <div style={tableHeaderStyle}>
          <h3 style={sectionTitleStyle}>Vendor Baseline Library</h3>
          <span style={smallBadgeStyle}>{records.length} shown</span>
        </div>

        {records.length > 0 ? (
          <div style={tableWrapStyle}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>ID</th>
                  <th style={thStyle}>Vendor</th>
                  <th style={thStyle}>Instrument</th>
                  <th style={thStyle}>Identifiers</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Approval</th>
                  <th style={thStyle}>Action</th>
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <tr key={record.baseline_id}>
                    <td style={tdStyle}>{record.baseline_id}</td>
                    <td style={tdStyle}>{record.vendor_name}</td>
                    <td style={tdStyle}>
                      <strong>{record.instrument_name}</strong>
                      <div style={mutedTextStyle}>{record.instrument_category}</div>
                      <div style={mutedTextStyle}>{record.tray_name}</div>
                    </td>
                    <td style={tdStyle}>
                      <div>Barcode: {record.barcode_value || "—"}</div>
                      <div>QR: {record.qr_code_value || "—"}</div>
                      <div>Key Dot: {record.key_dot_value || "—"}</div>
                    </td>
                    <td style={tdStyle}>
                      <span style={statusBadgeStyle(record.baseline_status)}>{record.baseline_status}</span>
                    </td>
                    <td style={tdStyle}>{record.approval_status}</td>
                    <td style={tdStyle}>
                      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                        {record.baseline_status !== "approved" ? (
                          <button type="button" onClick={() => approveBaseline(record.baseline_id)} style={approveButtonStyle}>
                            Approve
                          </button>
                        ) : (
                          <span style={approvedTextStyle}>Approved</span>
                        )}

                        <button
                          type="button"
                          onClick={() => viewAuditTrail(record.baseline_id)}
                          style={auditButtonStyle}
                        >
                          View Audit
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={emptyStyle}>No vendor baseline records are loaded yet. Create one to begin.</p>
        )}
      </div>

      {(auditLoading || auditError || selectedAudit) ? (
        <div style={auditPanelStyle}>
          <h3 style={sectionTitleStyle}>Vendor Baseline Audit Trail</h3>

          {auditLoading ? (
            <p style={bodyTextStyle}>Loading audit trail...</p>
          ) : null}

          {auditError ? (
            <div style={errorStyle}>{auditError}</div>
          ) : null}

          {selectedAudit ? (
            <>
              <div style={auditSummaryStyle}>
                <div>
                  <strong>Baseline ID:</strong> {selectedAudit.baseline_id}
                </div>
                <div>
                  <strong>Vendor:</strong> {selectedAudit.vendor || "N/A"}
                </div>
                <div>
                  <strong>Instrument:</strong> {selectedAudit.instrument || "N/A"}
                </div>
                <div>
                  <strong>Status:</strong> {selectedAudit.approval_status || "N/A"}
                </div>
                <div>
                  <strong>Audit Source:</strong> {selectedAudit.audit_source || "N/A"}
                </div>
                <div>
                  <strong>Events:</strong> {selectedAudit.audit_event_count}
                </div>
              </div>

              <div style={auditEventGridStyle}>
                {(selectedAudit.events || []).map((event, index) => (
                  <div key={event.event_id || index} style={auditEventCardStyle}>
                    <div style={{ fontWeight: 900, color: "#0f172a" }}>
                      {event.event_type}
                    </div>
                    <div style={mutedTextStyle}>
                      Decision: {event.decision || "N/A"}
                    </div>
                    <div style={mutedTextStyle}>
                      Actor: {event.actor || "N/A"} ({event.actor_role || "N/A"})
                    </div>
                    <div style={mutedTextStyle}>
                      Identifier: {event.matched_identifier_type || "N/A"} = {event.matched_identifier_value || "N/A"}
                    </div>
                    <div style={mutedTextStyle}>
                      Status: {event.previous_status || "none"} → {event.new_status || "N/A"}
                    </div>
                    <div style={mutedTextStyle}>
                      Evidence: {event.evidence_source || "N/A"}
                    </div>
                    <div style={mutedTextStyle}>
                      Notes: {event.notes || "N/A"}
                    </div>
                    <div style={mutedTextStyle}>
                      Created: {event.created_at || "N/A"}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </div>
      ) : null}

      <details style={detailsStyle}>
        <summary style={detailsSummaryStyle}>Why this matters</summary>
        <p style={bodyTextStyle}>
          Vendor baselines help hospitals distinguish true defects from normal manufacturer condition,
          acceptable wear, staining, coating changes, or non-contamination visual artifacts. Approved baselines
          improve scoring confidence and reduce disputes between SPD, OR, infection prevention, and vendors.
        </p>
      </details>

      {certificateLoading && (
        <div
          style={{
            marginTop: "16px",
            borderRadius: "16px",
            border: "1px solid #bae6fd",
            background: "#f0f9ff",
            color: "#075985",
            padding: "14px",
            fontWeight: 700,
          }}
        >
          Loading governance packet certificate...
        </div>
      )}

      {certificateError && (
        <div
          style={{
            marginTop: "16px",
            borderRadius: "16px",
            border: "1px solid #fecaca",
            background: "#fef2f2",
            color: "#991b1b",
            padding: "14px",
            fontWeight: 700,
          }}
        >
          {certificateError}
        </div>
      )}

      {selectedCertificate && (
        <div
          style={{
            marginTop: "18px",
            borderRadius: "20px",
            border: "1px solid #99f6e4",
            background: "#f0fdfa",
            padding: "18px",
            color: "#134e4a",
          }}
        >
          <h3 style={{ marginTop: 0 }}>Governance Packet Certificate</h3>

          <p>
            <strong>Finding ID:</strong> {selectedCertificate.finding_id} |{" "}
            <strong>Event ID:</strong> {selectedCertificate.event_id} |{" "}
            <strong>Format:</strong> {selectedCertificate.export_format}
          </p>

          <p>
            <strong>Filename:</strong> {selectedCertificate.filename}
          </p>

          <p>
            <strong>Exported By:</strong> {selectedCertificate.exported_by} |{" "}
            <strong>Role:</strong> {selectedCertificate.exported_role} |{" "}
            <strong>Exported At:</strong> {selectedCertificate.exported_at}
          </p>

          <p>
            <strong>Hash Algorithm:</strong> {selectedCertificate.packet_hash_algorithm}
          </p>

          <p style={{ wordBreak: "break-all" }}>
            <strong>Packet Hash:</strong> {selectedCertificate.packet_hash}
          </p>

          <p>
            <strong>Tamper Evident:</strong>{" "}
            {selectedCertificate.tamper_evident ? "Yes" : "No"} |{" "}
            <strong>Vendor Baseline Audit Included:</strong>{" "}
            {selectedCertificate.included_vendor_baseline_audit_trail ? "Yes" : "No"}
          </p>

          <p style={{ wordBreak: "break-all" }}>
            <strong>Verification URL:</strong> {selectedCertificate.verification_url}
          </p>
        </div>
      )}

    
      <div
        style={{
          marginTop: "24px",
          borderRadius: "22px",
          border: "1px solid #c7d2fe",
          background: "#eef2ff",
          padding: "20px",
          color: "#312e81",
        }}
      >
        <h3 style={{ marginTop: 0 }}>Compliance Evidence Bundle</h3>
        <p>
          Generate a tamper-evident enterprise evidence bundle containing audit export hash,
          manifest hash, verification links, and compliance metadata.
        </p>

        <button
          type="button"
          onClick={handleGenerateComplianceEvidenceBundle}
          disabled={evidenceBundleLoading}
          style={{
            border: "1px solid #4338ca",
            borderRadius: "999px",
            background: evidenceBundleLoading ? "#e0e7ff" : "#4338ca",
            color: evidenceBundleLoading ? "#3730a3" : "#ffffff",
            padding: "10px 16px",
            fontWeight: 800,
            cursor: evidenceBundleLoading ? "not-allowed" : "pointer",
          }}
        >
          {evidenceBundleLoading ? "Generating..." : "Generate Evidence Bundle"}
        </button>

        {evidenceBundleError && (
          <div
            style={{
              marginTop: "14px",
              borderRadius: "14px",
              border: "1px solid #fecaca",
              background: "#fef2f2",
              color: "#991b1b",
              padding: "12px",
              fontWeight: 700,
            }}
          >
            {evidenceBundleError}
          </div>
        )}

        {evidenceBundle && (
          <div
            style={{
              marginTop: "16px",
              borderRadius: "18px",
              border: "1px solid #a5b4fc",
              background: "#ffffff",
              padding: "16px",
            }}
          >
            <p>
              <strong>Status:</strong>{" "}
              {evidenceBundle.bundle.tamper_evident ? "Tamper-evident" : "Not marked tamper-evident"} |{" "}
              <strong>Generated By:</strong> {evidenceBundle.bundle.generated_by} |{" "}
              <strong>Generated At:</strong> {evidenceBundle.bundle.generated_at}
            </p>

            <p>
              <strong>Bundle Event ID:</strong> {evidenceBundle.bundle_event_id || "N/A"} |{" "}
              <strong>Audit Event Count:</strong> {evidenceBundle.bundle.audit_export.count}
            </p>

            <p style={{ wordBreak: "break-all" }}>
              <strong>Bundle Hash:</strong> {evidenceBundle.bundle_hash}
            </p>

            <p style={{ wordBreak: "break-all" }}>
              <strong>Audit Export Hash:</strong> {evidenceBundle.bundle.audit_export.audit_export_hash}
            </p>

            <p style={{ wordBreak: "break-all" }}>
              <strong>Manifest Hash:</strong> {evidenceBundle.bundle.manifest.manifest_hash}
            </p>

            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "12px" }}>
              <button
                type="button"
                onClick={handleDownloadEvidenceBundle}
                style={{
                  border: "1px solid #0f766e",
                  borderRadius: "999px",
                  background: "#f0fdfa",
                  color: "#0f766e",
                  padding: "9px 13px",
                  fontWeight: 800,
                  cursor: "pointer",
                }}
              >
                Download Bundle JSON
              </button>

              <button
                type="button"
                onClick={() => handleViewEvidenceBundleSummary(evidenceBundle.bundle_hash)}
                disabled={evidenceSummaryLoading}
                style={{
                  border: "1px solid #4338ca",
                  borderRadius: "999px",
                  background: "#eef2ff",
                  color: "#4338ca",
                  padding: "9px 13px",
                  fontWeight: 800,
                  cursor: evidenceSummaryLoading ? "not-allowed" : "pointer",
                }}
              >
                {evidenceSummaryLoading ? "Verifying..." : "View Verification Summary"}
              </button>
            </div>

            {evidenceSummary && (
              <div
                style={{
                  marginTop: "14px",
                  borderRadius: "16px",
                  border: "1px solid #bbf7d0",
                  background: "#f0fdf4",
                  color: "#14532d",
                  padding: "14px",
                }}
              >
                <h4 style={{ marginTop: 0 }}>Verification Summary</h4>
                <p>
                  <strong>Verified:</strong> {evidenceSummary.verified ? "Yes" : "No"} |{" "}
                  <strong>Tamper Evident:</strong> {evidenceSummary.tamper_evident ? "Yes" : "No"}
                </p>
                <p>{evidenceSummary.message}</p>
                <p style={{ wordBreak: "break-all" }}>
                  <strong>Bundle Hash:</strong> {evidenceSummary.bundle_hash}
                </p>
              </div>
            )}
          </div>
        )}
      </div>


      <div
        style={{
          marginTop: "24px",
          borderRadius: "22px",
          border: "1px solid #bfdbfe",
          background: "#eff6ff",
          padding: "20px",
          color: "#1e3a8a",
        }}
      >
        <h3 style={{ marginTop: 0 }}>Evidence Bundle Verification</h3>
        <p>
          Paste a compliance evidence bundle hash to verify that the bundle exists,
          is tamper-evident, and is tied to a recorded audit event.
        </p>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <input
            type="text"
            value={bundleHashToVerify}
            onChange={(event) => setBundleHashToVerify(event.target.value)}
            placeholder="Paste bundle hash"
            style={{
              flex: "1 1 360px",
              border: "1px solid #93c5fd",
              borderRadius: "14px",
              padding: "10px 12px",
              fontFamily: "monospace",
            }}
          />

          <button
            type="button"
            onClick={handleVerifyEvidenceBundleHash}
            disabled={bundleVerificationLoading}
            style={{
              border: "1px solid #1d4ed8",
              borderRadius: "999px",
              background: bundleVerificationLoading ? "#dbeafe" : "#1d4ed8",
              color: bundleVerificationLoading ? "#1e40af" : "#ffffff",
              padding: "10px 16px",
              fontWeight: 800,
              cursor: bundleVerificationLoading ? "not-allowed" : "pointer",
            }}
          >
            {bundleVerificationLoading ? "Verifying..." : "Verify Bundle"}
          </button>
        </div>

        {bundleVerificationError && (
          <div
            style={{
              marginTop: "14px",
              borderRadius: "14px",
              border: "1px solid #fecaca",
              background: "#fef2f2",
              color: "#991b1b",
              padding: "12px",
              fontWeight: 700,
            }}
          >
            {bundleVerificationError}
          </div>
        )}

        {bundleVerificationResult && (
          <div
            style={{
              marginTop: "16px",
              borderRadius: "18px",
              border: bundleVerificationResult.verified
                ? "1px solid #86efac"
                : "1px solid #fecaca",
              background: bundleVerificationResult.verified ? "#f0fdf4" : "#fef2f2",
              color: bundleVerificationResult.verified ? "#14532d" : "#991b1b",
              padding: "16px",
            }}
          >
            <h4 style={{ marginTop: 0 }}>
              {bundleVerificationResult.verified ? "Bundle Verified" : "Bundle Not Verified"}
            </h4>

            <p>{bundleVerificationResult.message}</p>

            <p style={{ wordBreak: "break-all" }}>
              <strong>Bundle Hash:</strong> {bundleVerificationResult.bundle_hash}
            </p>

            {bundleVerificationResult.verified && (
              <>
                <p>
                  <strong>Generated By:</strong> {bundleVerificationResult.generated_by || "N/A"} |{" "}
                  <strong>Generated At:</strong> {bundleVerificationResult.generated_at || "N/A"}
                </p>

                <p>
                  <strong>Export Count:</strong> {bundleVerificationResult.export_count ?? "N/A"} |{" "}
                  <strong>Tamper Evident:</strong>{" "}
                  {bundleVerificationResult.tamper_evident ? "Yes" : "No"}
                </p>

                <p style={{ wordBreak: "break-all" }}>
                  <strong>Audit Export Hash:</strong>{" "}
                  {bundleVerificationResult.audit_export_hash || "N/A"}
                </p>

                <p style={{ wordBreak: "break-all" }}>
                  <strong>Manifest Hash:</strong>{" "}
                  {bundleVerificationResult.manifest_hash || "N/A"}
                </p>
              </>
            )}
          </div>
        )}
      </div>
\n</section>
  );
}

const auditButtonStyle: React.CSSProperties = {
  border: "1px solid #bfdbfe",
  borderRadius: "999px",
  background: "#eff6ff",
  color: "#1d4ed8",
  padding: "8px 12px",
  fontWeight: 800,
  cursor: "pointer",
};

const auditPanelStyle: React.CSSProperties = {
  marginTop: "18px",
  border: "1px solid #bfdbfe",
  borderRadius: "18px",
  background: "#eff6ff",
  padding: "16px",
};

const auditSummaryStyle: React.CSSProperties = {
  marginTop: "12px",
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "10px",
  color: "#1e3a8a",
  fontSize: "13px",
};

const auditEventGridStyle: React.CSSProperties = {
  marginTop: "14px",
  display: "grid",
  gap: "10px",
};

const auditEventCardStyle: React.CSSProperties = {
  border: "1px solid #dbeafe",
  borderRadius: "14px",
  background: "#ffffff",
  padding: "12px",
};

const exportCardStyle: React.CSSProperties = {
  marginTop: "18px",
  border: "1px solid #c7d2fe",
  borderRadius: "18px",
  background: "#eef2ff",
  padding: "16px",
  display: "flex",
  justifyContent: "space-between",
  gap: "16px",
  flexWrap: "wrap",
  alignItems: "center",
};

const exportActionRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  flexWrap: "wrap",
  alignItems: "end",
};

const exportLabelStyle: React.CSSProperties = {
  display: "grid",
  gap: "6px",
  color: "#3730a3",
  fontSize: "12px",
  fontWeight: 900,
  textTransform: "uppercase",
};

const exportInputStyle: React.CSSProperties = {
  border: "1px solid #c7d2fe",
  borderRadius: "12px",
  padding: "10px 12px",
  minWidth: "100px",
  fontWeight: 800,
};

const exportButtonStyle: React.CSSProperties = {
  border: "none",
  borderRadius: "999px",
  background: "#4f46e5",
  color: "#ffffff",
  padding: "12px 18px",
  fontWeight: 900,
  cursor: "pointer",
  boxShadow: "0 8px 20px rgba(79, 70, 229, 0.22)",
};

const exportHistoryButtonStyle: React.CSSProperties = {
  border: "1px solid #c7d2fe",
  borderRadius: "999px",
  background: "#ffffff",
  color: "#3730a3",
  padding: "12px 18px",
  fontWeight: 900,
  cursor: "pointer",
};

const exportHistoryPanelStyle: React.CSSProperties = {
  width: "100%",
  marginTop: "14px",
  border: "1px solid #c7d2fe",
  borderRadius: "16px",
  background: "#ffffff",
  padding: "14px",
};

const exportHistorySummaryStyle: React.CSSProperties = {
  marginTop: "10px",
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "10px",
  color: "#3730a3",
  fontSize: "13px",
};

const exportHistoryListStyle: React.CSSProperties = {
  marginTop: "12px",
  display: "grid",
  gap: "10px",
};

const exportHistoryItemStyle: React.CSSProperties = {
  border: "1px solid #e0e7ff",
  borderRadius: "14px",
  background: "#f8fafc",
  padding: "12px",
};

const packetVerifyPanelStyle: React.CSSProperties = {
  width: "100%",
  marginTop: "14px",
  border: "1px solid #bbf7d0",
  borderRadius: "16px",
  background: "#f0fdf4",
  padding: "14px",
};

const packetVerifyRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  flexWrap: "wrap",
  alignItems: "center",
  marginTop: "10px",
};

const packetHashInputStyle: React.CSSProperties = {
  flex: 1,
  minWidth: "260px",
  border: "1px solid #bbf7d0",
  borderRadius: "12px",
  padding: "10px 12px",
  fontFamily: "monospace",
  fontSize: "12px",
};

const packetVerifyButtonStyle: React.CSSProperties = {
  border: "none",
  borderRadius: "999px",
  background: "#15803d",
  color: "#ffffff",
  padding: "12px 18px",
  fontWeight: 900,
  cursor: "pointer",
};

const packetVerifiedResultStyle: React.CSSProperties = {
  marginTop: "12px",
  border: "1px solid #86efac",
  borderRadius: "14px",
  background: "#dcfce7",
  color: "#14532d",
  padding: "12px",
};

const packetNotVerifiedResultStyle: React.CSSProperties = {
  marginTop: "12px",
  border: "1px solid #fecaca",
  borderRadius: "14px",
  background: "#fef2f2",
  color: "#7f1d1d",
  padding: "12px",
};

const hashTextStyle: React.CSSProperties = {
  marginTop: "6px",
  color: "#334155",
  fontFamily: "monospace",
  fontSize: "11px",
  overflowWrap: "anywhere",
};

const matchedExportStyle: React.CSSProperties = {
  marginTop: "10px",
  border: "1px solid #bbf7d0",
  borderRadius: "12px",
  background: "#ffffff",
  padding: "10px",
};

const immutableCertificateStyle: React.CSSProperties = {
  marginTop: "12px",
  border: "2px solid #16a34a",
  borderRadius: "18px",
  background: "linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)",
  color: "#14532d",
  padding: "16px",
  boxShadow: "0 10px 24px rgba(22, 163, 74, 0.16)",
};

const certificateHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  flexWrap: "wrap",
  alignItems: "center",
  borderBottom: "1px solid #bbf7d0",
  paddingBottom: "10px",
  marginBottom: "12px",
};

const certificateEyebrowStyle: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: 900,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  color: "#15803d",
};

const certificateTitleStyle: React.CSSProperties = {
  margin: "4px 0 0",
  color: "#14532d",
  fontSize: "18px",
};

const certificateSealStyle: React.CSSProperties = {
  border: "2px solid #16a34a",
  borderRadius: "999px",
  color: "#166534",
  background: "#dcfce7",
  padding: "8px 12px",
  fontWeight: 1000,
  fontSize: "12px",
  letterSpacing: "0.08em",
};

const certificateGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
  gap: "10px",
  fontSize: "13px",
};

const certificateHashBoxStyle: React.CSSProperties = {
  marginTop: "12px",
  border: "1px solid #bbf7d0",
  borderRadius: "12px",
  background: "#ffffff",
  padding: "10px",
  fontFamily: "monospace",
  fontSize: "11px",
  overflowWrap: "anywhere",
};

const certificateFootnoteStyle: React.CSSProperties = {
  margin: "10px 0 0",
  color: "#166534",
  fontSize: "12px",
  lineHeight: 1.5,
};

function fieldLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={metricCardStyle}>
      <span style={metricLabelStyle}>{label}</span>
      <strong style={metricValueStyle}>{value}</strong>
    </div>
  );
}

function statusBadgeStyle(status: string): React.CSSProperties {
  const normalized = (status || "").toLowerCase();
  const approved = normalized === "approved";

  return {
    borderRadius: "999px",
    padding: "5px 9px",
    fontSize: "11px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: approved ? "#dcfce7" : "#ffedd5",
    color: approved ? "#166534" : "#9a3412",
  };
}

function matchStatusBadgeStyle(status: string): React.CSSProperties {
  const normalized = (status || "").toLowerCase();
  const approved = normalized === "approved_match";
  const pending = normalized === "pending_match";

  return {
    display: "inline-block",
    borderRadius: "999px",
    padding: "6px 10px",
    fontSize: "12px",
    fontWeight: 900,
    textTransform: "uppercase",
    background: approved ? "#dcfce7" : pending ? "#ffedd5" : "#fee2e2",
    color: approved ? "#166534" : pending ? "#9a3412" : "#991b1b",
  };
}

const panelStyle: React.CSSProperties = {
  marginTop: "20px",
  padding: "20px",
  borderRadius: "24px",
  border: "1px solid #bae6fd",
  background: "linear-gradient(135deg, #f0f9ff 0%, #ffffff 100%)",
  boxShadow: "0 12px 32px rgba(14, 116, 144, 0.08)",
};

const headerRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "16px",
  alignItems: "flex-start",
  flexWrap: "wrap",
};

const eyebrowStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 900,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#0369a1",
};

const titleStyle: React.CSSProperties = {
  margin: "4px 0 0",
  fontSize: "24px",
  fontWeight: 900,
  color: "#0c4a6e",
};

const subtitleStyle: React.CSSProperties = {
  margin: "8px 0 0",
  color: "#475569",
  lineHeight: 1.5,
  maxWidth: "860px",
};

const refreshButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#0369a1",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};

const summaryGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
  gap: "12px",
  marginTop: "18px",
};

const metricCardStyle: React.CSSProperties = {
  padding: "14px",
  borderRadius: "18px",
  border: "1px solid #bae6fd",
  background: "#ffffff",
};

const metricLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "11px",
  fontWeight: 900,
  textTransform: "uppercase",
  color: "#64748b",
};

const metricValueStyle: React.CSSProperties = {
  display: "block",
  marginTop: "6px",
  color: "#0c4a6e",
  fontSize: "26px",
  fontWeight: 900,
};

const formCardStyle: React.CSSProperties = {
  marginTop: "18px",
  padding: "16px",
  borderRadius: "18px",
  background: "#ffffff",
  border: "1px solid #bae6fd",
};

const matchCardStyle: React.CSSProperties = {
  marginTop: "18px",
  padding: "16px",
  borderRadius: "18px",
  background: "#ecfeff",
  border: "1px solid #a5f3fc",
};

const libraryCardStyle: React.CSSProperties = {
  marginTop: "18px",
  padding: "16px",
  borderRadius: "18px",
  background: "#ffffff",
  border: "1px solid #bae6fd",
};

const sectionTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: "16px",
  fontWeight: 900,
  color: "#0c4a6e",
};

const bodyTextStyle: React.CSSProperties = {
  margin: "8px 0 0",
  color: "#475569",
  lineHeight: 1.5,
};

const formGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
  gap: "12px",
  marginTop: "14px",
};

const labelStyle: React.CSSProperties = {
  display: "grid",
  gap: "6px",
  color: "#334155",
  fontWeight: 800,
  fontSize: "12px",
};

const inputStyle: React.CSSProperties = {
  border: "1px solid #bae6fd",
  borderRadius: "10px",
  padding: "9px 10px",
  fontWeight: 700,
};

const primaryButtonStyle: React.CSSProperties = {
  marginTop: "14px",
  border: 0,
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#0e7490",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};

const matchRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  flexWrap: "wrap",
  marginTop: "12px",
};

const matchInputStyle: React.CSSProperties = {
  flex: "1 1 280px",
  border: "1px solid #67e8f9",
  borderRadius: "10px",
  padding: "10px",
  fontWeight: 800,
};

const matchButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "14px",
  padding: "10px 14px",
  background: "#0891b2",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};

const matchResultStyle: React.CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "14px",
  background: "#ffffff",
  border: "1px solid #a5f3fc",
};

const bestMatchStyle: React.CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#f0fdf4",
  border: "1px solid #bbf7d0",
  color: "#166534",
};

const tableHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "center",
};

const smallBadgeStyle: React.CSSProperties = {
  borderRadius: "999px",
  padding: "5px 9px",
  background: "#f0f9ff",
  color: "#0369a1",
  fontSize: "12px",
  fontWeight: 800,
};

const tableWrapStyle: React.CSSProperties = {
  overflowX: "auto",
  marginTop: "12px",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "13px",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "10px",
  borderBottom: "1px solid #bae6fd",
  color: "#0369a1",
  fontSize: "12px",
  textTransform: "uppercase",
};

const tdStyle: React.CSSProperties = {
  padding: "10px",
  borderBottom: "1px solid #e0f2fe",
  color: "#334155",
  verticalAlign: "top",
};

const mutedTextStyle: React.CSSProperties = {
  marginTop: "3px",
  color: "#64748b",
  fontSize: "12px",
};

const approveButtonStyle: React.CSSProperties = {
  border: 0,
  borderRadius: "10px",
  padding: "7px 10px",
  background: "#16a34a",
  color: "#ffffff",
  fontWeight: 900,
  cursor: "pointer",
};

const approvedTextStyle: React.CSSProperties = {
  color: "#166534",
  fontWeight: 900,
};

const detailsStyle: React.CSSProperties = {
  marginTop: "16px",
  padding: "14px",
  borderRadius: "18px",
  background: "#f0f9ff",
  border: "1px solid #bae6fd",
};

const detailsSummaryStyle: React.CSSProperties = {
  cursor: "pointer",
  fontWeight: 900,
  color: "#0369a1",
};

const errorStyle: React.CSSProperties = {
  marginTop: "12px",
  padding: "12px",
  borderRadius: "14px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 800,
};

const emptyStyle: React.CSSProperties = {
  margin: "16px 0 0",
  color: "#64748b",
};
