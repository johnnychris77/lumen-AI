import { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://lumen-ai-53u4.onrender.com";

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

const AUTH_HEADERS = {
  Authorization: "Bearer dev-token",
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
      Authorization: "Bearer dev-token",
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

async function matchVendorBaseline(identifierValue: string): Promise<VendorBaselineMatchResponse> {
  const response = await fetch(`${API_BASE}/api/enterprise/vendor-baseline-subscription/match`, {
    method: "POST",
    headers: {
      Authorization: "Bearer dev-token",
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
  const [records, setRecords] = useState<VendorBaselineRecord[]>([]);
  const [summary, setSummary] = useState<VendorBaselineListResponse | null>(null);
  const [matchResult, setMatchResult] = useState<VendorBaselineMatchResponse | null>(null);
  const [matchValue, setMatchValue] = useState("STRYKER-BARCODE-001");
  const [approvalNotes, setApprovalNotes] = useState("Approved as vendor baseline for scoring use.");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [matching, setMatching] = useState(false);
  const [error, setError] = useState("");

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
                      {record.baseline_status !== "approved" ? (
                        <button type="button" onClick={() => approveBaseline(record.baseline_id)} style={approveButtonStyle}>
                          Approve
                        </button>
                      ) : (
                        <span style={approvedTextStyle}>Approved</span>
                      )}
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

      <details style={detailsStyle}>
        <summary style={detailsSummaryStyle}>Why this matters</summary>
        <p style={bodyTextStyle}>
          Vendor baselines help hospitals distinguish true defects from normal manufacturer condition,
          acceptable wear, staining, coating changes, or non-contamination visual artifacts. Approved baselines
          improve scoring confidence and reduce disputes between SPD, OR, infection prevention, and vendors.
        </p>
      </details>
    </section>
  );
}

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
