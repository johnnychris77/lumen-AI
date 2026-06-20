import { useEffect, useState } from "react";
import type { CSSProperties } from "react";

type RecentInstrumentOption = {
  finding_id: number;
  instrument_id: number;
  vendor_id?: number | null;
  vendor_name?: string;
  instrument_name?: string;
  instrument_category?: string;
  finding_category?: string;
  severity?: string;
  created_at?: string;
};

type BaselineApprovalResult = {
  status: string;
  message: string;
  baseline_id: number;
  instrument_id: number;
  vendor_id?: number | null;
  baseline_status: string;
  approved_by?: string;
  approved_at?: string;
  workflow_status: string;
};

type BaselineItem = {
  baseline_id: number;
  instrument_id: number;
  vendor_id?: number | null;
  manufacturer_name: string;
  model_number?: string;
  catalog_number?: string;
  baseline_type: string;
  file_name: string;
  storage_uri: string;
  known_normal_characteristics?: string;
  known_abnormal_characteristics?: string;
  baseline_notes?: string;
  baseline_status?: string;
  approved_by?: string;
  approved_at?: string;
  created_at?: string;
};

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

const AUTH_TOKEN = localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || "";


async function reviewManufacturerBaseline(
  baselineId: number,
  decision: "approve" | "reject" | "request_more_evidence",
  reviewNotes: string
): Promise<BaselineApprovalResult> {
  const response = await fetch(`${API_BASE}/api/enterprise/baselines/${baselineId}/review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${AUTH_TOKEN}`,
      "X-LumenAI-Role": "operator",
      "X-LumenAI-Actor": "john-demo",
      "X-Tenant-Id": "bonsecours",
      "X-Tenant-Name": "Bon Secours",
    },
    body: JSON.stringify({
      reviewer_name: "Quality Reviewer",
      reviewer_role: "quality_reviewer",
      decision,
      review_notes: reviewNotes,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Baseline review failed (${response.status})`);
  }

  return data;
}


export default function ManufacturerBaselinePanel() {
  const [instrumentId, setInstrumentId] = useState("1");
  const [recentInstruments, setRecentInstruments] = useState<RecentInstrumentOption[]>([]);
  const [manufacturerName, setManufacturerName] = useState("Carl Storz");
  const [modelNumber, setModelNumber] = useState("Rigid Scope Demo Model");
  const [catalogNumber, setCatalogNumber] = useState("CS-RIGID-DEMO");
  const [baselineType, setBaselineType] = useState("manufacturer_reference");
  const [knownNormal, setKnownNormal] = useState(
    "Internal weld pattern and machining marks may appear as discoloration under borescope but may represent normal manufacturing artifact."
  );
  const [knownAbnormal, setKnownAbnormal] = useState(
    "Loose debris, biological material, flaking, progressive corrosion, or foreign material not consistent with manufacturer baseline."
  );
  const [baselineNotes, setBaselineNotes] = useState(
    "Use this baseline to reduce false positive rust/corrosion findings and improve vendor-quality scoring."
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [items, setItems] = useState<BaselineItem[]>([]);
  const [selected, setSelected] = useState<BaselineItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  async function loadRecentInstruments() {
    try {
      const response = await fetch(`${API_BASE}/api/enterprise/intake/history?limit=25`, {
        headers: {
          Authorization: `Bearer ${AUTH_TOKEN}`,
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
          "X-Tenant-Id": "bonsecours",
          "X-Tenant-Name": "Bon Secours",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || `Recent instrument request failed (${response.status})`);
      }

      const historyItems = Array.isArray(data.items) ? data.items : [];

      const uniqueByInstrument = new Map<number, RecentInstrumentOption>();

      for (const item of historyItems) {
        if (item.instrument_id && !uniqueByInstrument.has(item.instrument_id)) {
          uniqueByInstrument.set(item.instrument_id, {
            finding_id: item.finding_id,
            instrument_id: item.instrument_id,
            vendor_id: item.vendor_id,
            vendor_name: item.vendor_name,
            instrument_name: item.instrument_name,
            instrument_category: item.instrument_category,
            finding_category: item.finding_category,
            severity: item.severity,
            created_at: item.created_at,
          });
        }
      }

      const options = Array.from(uniqueByInstrument.values());
      setRecentInstruments(options);

      if (options.length > 0 && !options.some((option) => String(option.instrument_id) === instrumentId)) {
        setInstrumentId(String(options[0].instrument_id));
      }
    } catch (err) {
      console.warn(err);
    }
  }

  async function loadBaselines() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/api/enterprise/vendor-baselines?limit=25`, {
        headers: {
          Authorization: `Bearer ${AUTH_TOKEN}`,
          "X-LumenAI-Role": "viewer",
          "X-LumenAI-Actor": "john-demo",
          "X-Tenant-Id": "bonsecours",
          "X-Tenant-Name": "Bon Secours",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || `Baseline request failed (${response.status})`);
      }

      const nextItems = Array.isArray(data.items) ? data.items : [];
      setItems(nextItems);

      if (!selected && nextItems.length > 0) {
        setSelected(nextItems[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown baseline error");
    } finally {
      setLoading(false);
    }
  }

  async function uploadBaseline() {
    if (!selectedFile) {
      setError("Select a manufacturer baseline file before uploading.");
      return;
    }

    const numericInstrumentId = Number(instrumentId);
    if (!numericInstrumentId || numericInstrumentId < 1) {
      setError("Enter a valid instrument ID.");
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("manufacturer_name", manufacturerName);
    formData.append("model_number", modelNumber);
    formData.append("catalog_number", catalogNumber);
    formData.append("baseline_type", baselineType);
    formData.append("known_normal_characteristics", knownNormal);
    formData.append("known_abnormal_characteristics", knownAbnormal);
    formData.append("baseline_notes", baselineNotes);
    formData.append("baseline_status", "pending_review");

    try {
      const response = await fetch(
        `${API_BASE}/api/enterprise/instruments/${numericInstrumentId}/baseline`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${AUTH_TOKEN}`,
            "X-LumenAI-Role": "operator",
            "X-LumenAI-Actor": "john-demo",
            "X-Tenant-Id": "bonsecours",
            "X-Tenant-Name": "Bon Secours",
          },
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || `Baseline upload failed (${response.status})`);
      }

      setSuccess(
        `Baseline uploaded: ${data.file_name} linked to instrument #${data.instrument_id}`
      );
      setSelectedFile(null);
      await loadBaselines();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown baseline upload error");
    } finally {
      setUploading(false);
    }
  }

  useEffect(() => {
    loadRecentInstruments();
    loadBaselines();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section style={panelStyle}>
      <div style={eyebrowStyle}>Manufacturer Baseline Intelligence</div>

      <div style={headerRowStyle}>
        <div>
          <h2 style={{ margin: "8px 0 8px", color: "#0f172a" }}>
            Instrument Reference Baseline Library
          </h2>
          <p style={{ margin: 0, color: "#475569", lineHeight: 1.6 }}>
            Capture manufacturer/new-condition reference files so LumenAI can distinguish normal
            weld patterns, machining marks, and surface variation from true defects.
          </p>
        </div>

        <div style={headerButtonGroupStyle}>
          <button
            type="button"
            onClick={loadRecentInstruments}
            style={secondaryRefreshButtonStyle}
          >
            Refresh Instruments
          </button>

          <button
            type="button"
            onClick={loadBaselines}
            disabled={loading}
            style={refreshButtonStyle(loading)}
          >
            {loading ? "Refreshing..." : "Refresh Baselines"}
          </button>
        </div>
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}
      {success ? <div style={successStyle}>{success}</div> : null}

      <div style={uploadGridStyle}>
        <Field label="Instrument">
          {recentInstruments.length > 0 ? (
            <select
              value={instrumentId}
              onChange={(event) => setInstrumentId(event.target.value)}
              style={inputStyle}
            >
              {recentInstruments.map((option) => (
                <option key={option.instrument_id} value={option.instrument_id}>
                  #{option.instrument_id} — {option.instrument_name || "Instrument"} / Finding #{option.finding_id}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={instrumentId}
              onChange={(event) => setInstrumentId(event.target.value)}
              style={inputStyle}
              placeholder="Enter instrument ID"
            />
          )}

          {recentInstruments.length === 0 ? (
            <span style={helperTextStyle}>
              No recent instruments loaded. Create an enterprise intake, then refresh instruments.
            </span>
          ) : null}
        </Field>

        <Field label="Manufacturer">
          <input
            value={manufacturerName}
            onChange={(event) => setManufacturerName(event.target.value)}
            style={inputStyle}
          />
        </Field>

        <Field label="Model Number">
          <input
            value={modelNumber}
            onChange={(event) => setModelNumber(event.target.value)}
            style={inputStyle}
          />
        </Field>

        <Field label="Catalog Number">
          <input
            value={catalogNumber}
            onChange={(event) => setCatalogNumber(event.target.value)}
            style={inputStyle}
          />
        </Field>

        <Field label="Baseline Type">
          <select
            value={baselineType}
            onChange={(event) => setBaselineType(event.target.value)}
            style={inputStyle}
          >
            <option value="manufacturer_reference">Manufacturer Reference</option>
            <option value="new_condition_borescope">New-Condition Borescope</option>
            <option value="external_reference_image">External Reference Image</option>
            <option value="vendor_quality_reference">Vendor Quality Reference</option>
          </select>
        </Field>

        <Field label="Baseline File">
          <input
            type="file"
            onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
            style={inputStyle}
          />
        </Field>
      </div>

      {recentInstruments.length > 0 ? (
        <div style={selectedInstrumentStyle}>
          {(() => {
            const selectedInstrument = recentInstruments.find(
              (option) => String(option.instrument_id) === instrumentId
            );

            if (!selectedInstrument) {
              return "Selected instrument context unavailable.";
            }

            return (
              <>
                <strong>Selected Instrument Context:</strong>{" "}
                Instrument #{selectedInstrument.instrument_id} • Finding #{selectedInstrument.finding_id} •{" "}
                {selectedInstrument.vendor_name || "Vendor"} •{" "}
                {selectedInstrument.instrument_name || "Instrument"} •{" "}
                {selectedInstrument.finding_category || "Finding category unavailable"}
              </>
            );
          })()}
        </div>
      ) : null}

      <div style={textareaGridStyle}>
        <Field label="Known Normal Characteristics">
          <textarea
            value={knownNormal}
            onChange={(event) => setKnownNormal(event.target.value)}
            style={textareaStyle}
          />
        </Field>

        <Field label="Known Abnormal Characteristics">
          <textarea
            value={knownAbnormal}
            onChange={(event) => setKnownAbnormal(event.target.value)}
            style={textareaStyle}
          />
        </Field>

        <Field label="Baseline Notes">
          <textarea
            value={baselineNotes}
            onChange={(event) => setBaselineNotes(event.target.value)}
            style={textareaStyle}
          />
        </Field>
      </div>

      <button
        type="button"
        onClick={uploadBaseline}
        disabled={uploading}
        style={uploadButtonStyle(uploading)}
      >
        {uploading ? "Uploading Baseline..." : "Upload Manufacturer Baseline"}
      </button>

      {items.length > 0 ? (
        <div style={{ overflowX: "auto", marginTop: "18px" }}>
          <table style={tableStyle}>
            <thead>
              <tr style={{ background: "#ecfeff", color: "#155e75" }}>
                <th style={th}>Baseline</th>
                <th style={th}>Instrument</th>
                <th style={th}>Manufacturer</th>
                <th style={th}>Model</th>
                <th style={th}>Type</th>
                <th style={th}>Status</th>
                <th style={th}>Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const isSelected = selected?.baseline_id === item.baseline_id;

                return (
                  <tr
                    key={item.baseline_id}
                    onClick={() => setSelected(item)}
                    style={{
                      borderTop: "1px solid #e5e7eb",
                      cursor: "pointer",
                      background: isSelected ? "#ecfeff" : "#ffffff",
                    }}
                  >
                    <td style={td}>
                      <strong>#{item.baseline_id}</strong>
                      <div style={smallTextStyle}>{item.file_name}</div>
                    </td>
                    <td style={td}>#{item.instrument_id}</td>
                    <td style={td}>{item.manufacturer_name || "—"}</td>
                    <td style={td}>{item.model_number || "—"}</td>
                    <td style={td}>{formatLabel(item.baseline_type)}</td>
                    <td style={td}>
                      <strong style={{ color: statusColor(item.baseline_status) }}>
                        {formatLabel(item.baseline_status || "pending_review")}
                      </strong>
                    </td>
                    <td style={td}>{formatDate(item.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={emptyStyle}>
          No manufacturer baselines found yet. Upload a baseline reference file to begin.
        </div>
      )}

      {selected ? <BaselineDetail item={selected} onReviewed={loadBaselines} /> : null}
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={fieldStyle}>
      <span style={fieldLabelStyle}>{label}</span>
      {children}
    </label>
  );
}

function BaselineDetail({
  item,
  onReviewed,
}: {
  item: BaselineItem;
  onReviewed: () => Promise<void>;
}) {
  const [reviewing, setReviewing] = useState("");
  const [reviewNotes, setReviewNotes] = useState(
    "Baseline reviewed as manufacturer reference for comparison scoring."
  );
  const [reviewMessage, setReviewMessage] = useState("");
  const [reviewError, setReviewError] = useState("");

  async function handleReview(
    decision: "approve" | "reject" | "request_more_evidence"
  ) {
    setReviewing(decision);
    setReviewMessage("");
    setReviewError("");

    try {
      const result = await reviewManufacturerBaseline(
        item.baseline_id,
        decision,
        reviewNotes
      );

      setReviewMessage(
        `${formatLabel(result.baseline_status)}: ${result.message}`
      );

      await onReviewed();
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Unknown baseline review error");
    } finally {
      setReviewing("");
    }
  }
  return (
    <div style={detailPanelStyle}>
      <div style={eyebrowStyle}>Baseline Detail</div>

      <h3 style={{ margin: "6px 0 12px", color: "#0f172a" }}>
        {item.manufacturer_name || "Manufacturer"} Baseline #{item.baseline_id}
      </h3>

      <div style={detailGridStyle}>
        <InfoCard label="Instrument" value={`#${item.instrument_id}`} />
        <InfoCard label="Vendor" value={String(item.vendor_id ?? "—")} />
        <InfoCard label="Manufacturer" value={item.manufacturer_name || "—"} />
        <InfoCard label="Model" value={item.model_number || "—"} />
        <InfoCard label="Catalog" value={item.catalog_number || "—"} />
        <InfoCard label="Baseline Type" value={formatLabel(item.baseline_type)} />
        <InfoCard label="Status" value={formatLabel(item.baseline_status || "pending_review")} />
        <InfoCard label="Created" value={formatDate(item.created_at)} />
      </div>

      <div style={detailSectionStyle}>
        <h4 style={sectionHeadingStyle}>Known Normal Characteristics</h4>
        <p style={paragraphStyle}>{item.known_normal_characteristics || "No normal characteristics documented."}</p>
      </div>

      <div style={detailSectionStyle}>
        <h4 style={sectionHeadingStyle}>Known Abnormal Characteristics</h4>
        <p style={paragraphStyle}>{item.known_abnormal_characteristics || "No abnormal characteristics documented."}</p>
      </div>

      <div style={detailSectionStyle}>
        <h4 style={sectionHeadingStyle}>Vendor Management Value</h4>
        <p style={paragraphStyle}>
          This baseline helps LumenAI compare current inspection evidence against known manufacturer appearance,
          reducing false-positive rust/corrosion findings and strengthening vendor-quality scoring.
        </p>
      </div>

      <div style={approvalPanelStyle}>
        <h4 style={sectionHeadingStyle}>Baseline Review Decision</h4>
        <p style={paragraphStyle}>
          Approve this baseline only after confirming it represents a trusted manufacturer or new-condition reference.
        </p>

        <textarea
          value={reviewNotes}
          onChange={(event) => setReviewNotes(event.target.value)}
          style={reviewTextareaStyle}
        />

        <div style={approvalButtonRowStyle}>
          <button
            type="button"
            onClick={() => handleReview("approve")}
            disabled={Boolean(reviewing)}
            style={approveButtonStyle(Boolean(reviewing))}
          >
            {reviewing === "approve" ? "Approving..." : "Approve Baseline"}
          </button>

          <button
            type="button"
            onClick={() => handleReview("request_more_evidence")}
            disabled={Boolean(reviewing)}
            style={moreEvidenceButtonStyle(Boolean(reviewing))}
          >
            {reviewing === "request_more_evidence"
              ? "Requesting..."
              : "Request More Evidence"}
          </button>

          <button
            type="button"
            onClick={() => handleReview("reject")}
            disabled={Boolean(reviewing)}
            style={rejectButtonStyle(Boolean(reviewing))}
          >
            {reviewing === "reject" ? "Rejecting..." : "Reject Baseline"}
          </button>
        </div>

        {reviewMessage ? <div style={reviewSuccessStyle}>{reviewMessage}</div> : null}
        {reviewError ? <div style={reviewErrorStyle}>{reviewError}</div> : null}
      </div>

      <div style={footerStyle}>
        Future scoring: current inspection image + manufacturer baseline + instrument history + vendor defect history.
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={infoCardStyle}>
      <div style={infoLabelStyle}>{label}</div>
      <div style={infoValueStyle}>{value}</div>
    </div>
  );
}

function formatLabel(value?: string) {
  if (!value) return "—";
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function statusColor(status?: string) {
  const s = (status || "").toLowerCase();
  if (s === "approved") return "#166534";
  if (s === "rejected") return "#991b1b";
  if (s === "pending_review") return "#a16207";
  return "#334155";
}

const panelStyle: CSSProperties = {
  margin: "20px 0",
  padding: "20px",
  borderRadius: "18px",
  border: "1px solid #a5f3fc",
  background: "linear-gradient(135deg, #ecfeff 0%, #ffffff 100%)",
  boxShadow: "0 12px 28px rgba(15, 23, 42, 0.08)",
};

const eyebrowStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 900,
  color: "#0e7490",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
};


const headerButtonGroupStyle: CSSProperties = {
  display: "flex",
  gap: "10px",
  flexWrap: "wrap",
};

const secondaryRefreshButtonStyle: CSSProperties = {
  border: "1px solid #a5f3fc",
  borderRadius: "12px",
  padding: "10px 14px",
  fontWeight: 900,
  cursor: "pointer",
  background: "#ecfeff",
  color: "#0e7490",
};

const helperTextStyle: CSSProperties = {
  color: "#64748b",
  fontSize: "12px",
  fontWeight: 700,
};

const selectedInstrumentStyle: CSSProperties = {
  marginTop: "12px",
  padding: "12px",
  borderRadius: "14px",
  border: "1px solid #a5f3fc",
  background: "#ecfeff",
  color: "#155e75",
  fontWeight: 800,
  lineHeight: 1.55,
};

const headerRowStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "center",
  flexWrap: "wrap",
};

function refreshButtonStyle(loading: boolean): CSSProperties {
  return {
    border: "0",
    borderRadius: "12px",
    padding: "10px 14px",
    fontWeight: 900,
    cursor: loading ? "not-allowed" : "pointer",
    background: loading ? "#94a3b8" : "#0e7490",
    color: "#ffffff",
  };
}

const errorStyle: CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "12px",
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#991b1b",
  fontWeight: 800,
};

const successStyle: CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "12px",
  background: "#dcfce7",
  border: "1px solid #bbf7d0",
  color: "#166534",
  fontWeight: 800,
};

const uploadGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
  gap: "10px",
  marginTop: "16px",
};

const textareaGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
  gap: "10px",
  marginTop: "10px",
};

const fieldStyle: CSSProperties = {
  display: "grid",
  gap: "5px",
};

const fieldLabelStyle: CSSProperties = {
  fontSize: "12px",
  color: "#475569",
  fontWeight: 900,
};

const inputStyle: CSSProperties = {
  padding: "10px",
  borderRadius: "12px",
  border: "1px solid #cbd5e1",
  background: "#ffffff",
};

const textareaStyle: CSSProperties = {
  minHeight: "86px",
  padding: "10px",
  borderRadius: "12px",
  border: "1px solid #cbd5e1",
  background: "#ffffff",
  resize: "vertical",
};

function uploadButtonStyle(uploading: boolean): CSSProperties {
  return {
    marginTop: "12px",
    border: "0",
    borderRadius: "12px",
    padding: "12px 16px",
    background: uploading ? "#94a3b8" : "#0e7490",
    color: "#ffffff",
    fontWeight: 900,
    cursor: uploading ? "not-allowed" : "pointer",
  };
}

const tableStyle: CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  background: "#ffffff",
  borderRadius: "14px",
  overflow: "hidden",
  fontSize: "14px",
};

const th: CSSProperties = {
  textAlign: "left",
  padding: "12px",
  fontWeight: 900,
  whiteSpace: "nowrap",
};

const td: CSSProperties = {
  padding: "12px",
  color: "#334155",
  verticalAlign: "top",
};

const smallTextStyle: CSSProperties = {
  marginTop: "4px",
  color: "#64748b",
  fontSize: "12px",
};

const emptyStyle: CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "12px",
  background: "#ffffff",
  border: "1px solid #a5f3fc",
  color: "#475569",
};

const detailPanelStyle: CSSProperties = {
  marginTop: "18px",
  padding: "18px",
  borderRadius: "18px",
  border: "1px solid #67e8f9",
  background: "#ffffff",
  boxShadow: "0 16px 32px rgba(14, 116, 144, 0.12)",
};

const detailGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
  gap: "10px",
};

const infoCardStyle: CSSProperties = {
  padding: "12px",
  borderRadius: "14px",
  background: "#f8fafc",
  border: "1px solid #e2e8f0",
};

const infoLabelStyle: CSSProperties = {
  fontSize: "12px",
  color: "#64748b",
  fontWeight: 800,
};

const infoValueStyle: CSSProperties = {
  marginTop: "3px",
  fontWeight: 900,
  color: "#0f172a",
};

const detailSectionStyle: CSSProperties = {
  marginTop: "16px",
  paddingTop: "12px",
  borderTop: "1px solid #e5e7eb",
};

const sectionHeadingStyle: CSSProperties = {
  margin: "0 0 8px",
  color: "#111827",
};

const paragraphStyle: CSSProperties = {
  margin: 0,
  color: "#475569",
  lineHeight: 1.65,
};


const approvalPanelStyle: CSSProperties = {
  marginTop: "16px",
  padding: "14px",
  borderRadius: "16px",
  border: "1px solid #bfdbfe",
  background: "linear-gradient(135deg, #eff6ff 0%, #ffffff 100%)",
};

const reviewTextareaStyle: CSSProperties = {
  width: "100%",
  minHeight: "72px",
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  border: "1px solid #cbd5e1",
  background: "#ffffff",
  resize: "vertical",
};

const approvalButtonRowStyle: CSSProperties = {
  display: "flex",
  gap: "10px",
  flexWrap: "wrap",
  marginTop: "12px",
};

function approveButtonStyle(disabled: boolean): CSSProperties {
  return {
    border: "0",
    borderRadius: "12px",
    padding: "10px 14px",
    background: disabled ? "#94a3b8" : "#166534",
    color: "#ffffff",
    fontWeight: 900,
    cursor: disabled ? "not-allowed" : "pointer",
  };
}

function moreEvidenceButtonStyle(disabled: boolean): CSSProperties {
  return {
    border: "0",
    borderRadius: "12px",
    padding: "10px 14px",
    background: disabled ? "#94a3b8" : "#a16207",
    color: "#ffffff",
    fontWeight: 900,
    cursor: disabled ? "not-allowed" : "pointer",
  };
}

function rejectButtonStyle(disabled: boolean): CSSProperties {
  return {
    border: "0",
    borderRadius: "12px",
    padding: "10px 14px",
    background: disabled ? "#94a3b8" : "#991b1b",
    color: "#ffffff",
    fontWeight: 900,
    cursor: disabled ? "not-allowed" : "pointer",
  };
}

const reviewSuccessStyle: CSSProperties = {
  marginTop: "12px",
  padding: "10px",
  borderRadius: "12px",
  background: "#dcfce7",
  color: "#166534",
  border: "1px solid #bbf7d0",
  fontWeight: 800,
};

const reviewErrorStyle: CSSProperties = {
  marginTop: "12px",
  padding: "10px",
  borderRadius: "12px",
  background: "#fef2f2",
  color: "#991b1b",
  border: "1px solid #fecaca",
  fontWeight: 800,
};

const footerStyle: CSSProperties = {
  marginTop: "16px",
  padding: "12px",
  borderRadius: "14px",
  background: "#ecfeff",
  color: "#155e75",
  fontWeight: 800,
  border: "1px solid #a5f3fc",
};
