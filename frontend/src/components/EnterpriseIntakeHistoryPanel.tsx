import { useEffect, useState } from "react";
import type { CSSProperties } from "react";

type IntakeHistoryItem = {
  finding_id: number;
  vendor_id?: number | null;
  instrument_id?: number | null;
  risk_score_id?: number | null;
  disposition_id?: number | null;
  vendor_name?: string;
  instrument_name?: string;
  instrument_category?: string;
  finding_category?: string;
  finding_description?: string;
  severity?: string;
  confidence_score?: number;
  risk_tier?: string;
  overall_score?: number;
  recommended_action?: string;
  final_action?: string;
  disposition_status?: string;
  workflow_status?: string;
  human_review_status?: string;
  human_confirmed?: boolean;
  created_at?: string;
};

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

const AUTH_TOKEN = import.meta.env.VITE_AUTH_TOKEN || "dev-token";

export default function EnterpriseIntakeHistoryPanel() {
  const [items, setItems] = useState<IntakeHistoryItem[]>([]);
  const [selected, setSelected] = useState<IntakeHistoryItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadHistory() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE}/api/enterprise/intake/history?limit=10`,
        {
          headers: {
            Authorization: `Bearer ${AUTH_TOKEN}`,
            "X-LumenAI-Role": "viewer",
            "X-LumenAI-Actor": "john-demo",
            "X-Tenant-Id": "bonsecours",
            "X-Tenant-Name": "Bon Secours",
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || `History request failed (${response.status})`);
      }

      const nextItems = Array.isArray(data.items) ? data.items : [];
      setItems(nextItems);

      if (!selected && nextItems.length > 0) {
        setSelected(nextItems[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown history error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section style={panelStyle}>
      <div style={eyebrowStyle}>Enterprise Workflow Trace</div>

      <div style={headerRowStyle}>
        <div>
          <h2 style={{ margin: "8px 0 8px", color: "#0f172a" }}>
            Recent Enterprise Intake Records
          </h2>
          <p style={{ margin: 0, color: "#475569", lineHeight: 1.6 }}>
            Displays recent enterprise records created through the intake workflow.
            Select any record to preview the governance packet.
          </p>
        </div>

        <button type="button" onClick={loadHistory} disabled={loading} style={refreshButtonStyle(loading)}>
          {loading ? "Refreshing..." : "Refresh History"}
        </button>
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      {!error && items.length === 0 ? (
        <div style={emptyStyle}>
          No enterprise intake records found yet. Use the Create Enterprise Intake button above, then refresh this panel.
        </div>
      ) : null}

      {items.length > 0 ? (
        <div style={{ overflowX: "auto", marginTop: "16px" }}>
          <table style={tableStyle}>
            <thead>
              <tr style={{ background: "#eef2ff", color: "#312e81" }}>
                <th style={th}>Finding</th>
                <th style={th}>Vendor</th>
                <th style={th}>Instrument</th>
                <th style={th}>Issue</th>
                <th style={th}>Severity</th>
                <th style={th}>Risk</th>
                <th style={th}>Action</th>
                <th style={th}>Workflow</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const isSelected = selected?.finding_id === item.finding_id;

                return (
                  <tr
                    key={item.finding_id}
                    onClick={() => setSelected(item)}
                    style={{
                      borderTop: "1px solid #e5e7eb",
                      cursor: "pointer",
                      background: isSelected ? "#f5f3ff" : "#ffffff",
                    }}
                  >
                    <td style={td}>#{item.finding_id}</td>
                    <td style={td}>{item.vendor_name || "—"}</td>
                    <td style={td}>{item.instrument_name || "—"}</td>
                    <td style={td}>{item.finding_category || "—"}</td>
                    <td style={td}>
                      <strong style={{ color: severityColor(item.severity) }}>
                        {item.severity || "—"}
                      </strong>
                    </td>
                    <td style={td}>
                      {item.risk_tier || "—"} / {item.overall_score ?? 0}
                    </td>
                    <td style={td}>{item.recommended_action || "—"}</td>
                    <td style={td}>{item.workflow_status || "pending"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {selected ? (
        <GovernancePacketPreview item={selected} onClose={() => setSelected(null)} />
      ) : null}
    </section>
  );
}

function GovernancePacketPreview({
  item,
  onClose,
}: {
  item: IntakeHistoryItem;
  onClose: () => void;
}) {
  const [exporting, setExporting] = useState(false);
  const [pdfExporting, setPdfExporting] = useState(false);
  const [reviewing, setReviewing] = useState("");
  const [openingCapa, setOpeningCapa] = useState(false);
  const [exportError, setExportError] = useState("");
  const [exportSuccess, setExportSuccess] = useState("");
  const [reviewSuccess, setReviewSuccess] = useState("");
  const [capaSuccess, setCapaSuccess] = useState("");

  async function handleExportPacket() {
    setExporting(true);
    setExportError("");
    setExportSuccess("");

    try {
      const packet = await exportGovernancePacket(item.finding_id);
      setExportSuccess(`Governance packet exported: ${packet.title}`);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Unknown packet export error");
    } finally {
      setExporting(false);
    }
  }

  async function handleDownloadPdf() {
    setPdfExporting(true);
    setExportError("");
    setExportSuccess("");

    try {
      await downloadGovernancePacketPdf(item.finding_id);
      setExportSuccess(`Governance packet PDF downloaded for finding #${item.finding_id}`);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Unknown PDF download error");
    } finally {
      setPdfExporting(false);
    }
  }

  async function handleHumanReview(decision: string, notes: string) {
    setReviewing(decision);
    setExportError("");
    setReviewSuccess("");
    setCapaSuccess("");

    try {
      const result = await submitHumanReview(item.finding_id, decision, notes);
      setReviewSuccess(
        `Human review saved: ${result.workflow_status || result.decision}`
      );

      if (decision === "open_capa") {
        setOpeningCapa(true);
        const capa = await openEnterpriseCapa(item.finding_id);
        setCapaSuccess(
          `CAPA opened: ${capa.capa_number} (${capa.capa_status})`
        );
      }
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Unknown human review error");
    } finally {
      setReviewing("");
      setOpeningCapa(false);
    }
  }

  return (
    <div style={detailPanelStyle}>
      <div style={detailHeaderStyle}>
        <div>
          <div style={eyebrowStyle}>Governance Packet Preview</div>
          <h3 style={{ margin: "6px 0 0", color: "#0f172a" }}>
            Finding #{item.finding_id}: {item.instrument_name || "Instrument"} Review
          </h3>
        </div>

        <button type="button" onClick={onClose} style={closeButtonStyle}>
          Close Preview
        </button>
      </div>

      <div style={summaryGridStyle}>
        <InfoCard label="Vendor" value={item.vendor_name || "—"} />
        <InfoCard label="Instrument" value={item.instrument_name || "—"} />
        <InfoCard label="Category" value={item.instrument_category || "—"} />
        <InfoCard label="Finding" value={item.finding_category || "—"} />
        <InfoCard label="Severity" value={item.severity || "—"} emphasisColor={severityColor(item.severity)} />
        <InfoCard label="Risk Score" value={`${item.risk_tier || "—"} / ${item.overall_score ?? 0}`} />
        <InfoCard label="Disposition" value={item.disposition_status || "recommended"} />
        <InfoCard label="Workflow" value={item.workflow_status || "pending"} />
        <InfoCard label="Human Review" value={item.human_review_status || "Pending"} />
        <InfoCard label="Human Confirmed" value={item.human_confirmed ? "Yes" : "No"} />
      </div>

      <div style={packetSectionStyle}>
        <h4 style={packetHeadingStyle}>Case Summary</h4>
        <p style={packetTextStyle}>
          LumenAI recorded a <strong>{item.severity || "risk"}</strong> finding for{" "}
          <strong>{item.instrument_name || "the instrument"}</strong> associated with{" "}
          <strong>{item.vendor_name || "the vendor"}</strong>. The issue was classified as{" "}
          <strong>{item.finding_category || "a quality concern"}</strong>.
        </p>

        {item.finding_description ? (
          <p style={packetTextStyle}>{item.finding_description}</p>
        ) : null}

        <p style={{ ...packetTextStyle, marginTop: "10px" }}>
          <strong>Human review status:</strong>{" "}
          {item.human_review_status || "Pending human review"} |{" "}
          <strong>Human confirmed:</strong> {item.human_confirmed ? "Yes" : "No"}
        </p>
      </div>

      <div style={packetSectionStyle}>
        <h4 style={packetHeadingStyle}>Recommended Action</h4>
        <p style={packetTextStyle}>{item.recommended_action || "Pending recommended action."}</p>
      </div>

      <div style={packetSectionStyle}>
        <h4 style={packetHeadingStyle}>Evidence-to-Action Chain</h4>
        <ol style={chainListStyle}>
          <li>Enterprise intake record created</li>
          <li>Vendor and instrument context linked</li>
          <li>Finding classified and severity assigned</li>
          <li>Risk score generated</li>
          <li>Disposition recommended</li>
          <li>Workflow placed in pending human review status</li>
        </ol>
      </div>

      <div style={packetSectionStyle}>
        <h4 style={packetHeadingStyle}>Human Review Actions</h4>
        <p style={packetTextStyle}>
          Record a human-in-the-loop decision before final governance review.
          These actions create an auditable reviewer decision in the enterprise workflow.
        </p>

        <div style={reviewButtonRowStyle}>
          <button
            type="button"
            onClick={() =>
              handleHumanReview(
                "approve",
                "Finding reviewed and approved for documented disposition."
              )
            }
            disabled={Boolean(reviewing)}
            style={reviewButtonStyle("#166534", reviewing === "approve")}
          >
            {reviewing === "approve" ? "Saving..." : "Approve"}
          </button>

          <button
            type="button"
            onClick={() =>
              handleHumanReview(
                "escalate_to_ip",
                "Finding confirmed. Escalate to Infection Prevention for risk review."
              )
            }
            disabled={Boolean(reviewing)}
            style={reviewButtonStyle("#7c2d12", reviewing === "escalate_to_ip")}
          >
            {reviewing === "escalate_to_ip" ? "Saving..." : "Escalate to IP"}
          </button>

          <button
            type="button"
            onClick={() =>
              handleHumanReview(
                "request_more_evidence",
                "Additional image evidence or reviewer clarification requested."
              )
            }
            disabled={Boolean(reviewing)}
            style={reviewButtonStyle("#1d4ed8", reviewing === "request_more_evidence")}
          >
            {reviewing === "request_more_evidence" ? "Saving..." : "Request More Evidence"}
          </button>

          <button
            type="button"
            onClick={() =>
              handleHumanReview(
                "open_capa",
                "CAPA recommended due to severity and repeat-risk potential."
              )
            }
            disabled={Boolean(reviewing)}
            style={reviewButtonStyle("#7e22ce", reviewing === "open_capa")}
          >
            {reviewing === "open_capa" || openingCapa ? "Opening CAPA..." : "Open CAPA"}
          </button>
        </div>

        {reviewSuccess ? (
          <div style={reviewSuccessStyle}>{reviewSuccess}</div>
        ) : null}

        {capaSuccess ? (
          <div style={capaSuccessStyle}>{capaSuccess}</div>
        ) : null}
      </div>

      <div style={packetSectionStyle}>
        <h4 style={packetHeadingStyle}>Audit Readiness Preview</h4>
        <div style={auditGridStyle}>
          <InfoCard label="Finding ID" value={`#${item.finding_id}`} />
          <InfoCard label="Vendor ID" value={String(item.vendor_id ?? "—")} />
          <InfoCard label="Instrument ID" value={String(item.instrument_id ?? "—")} />
          <InfoCard label="Risk Score ID" value={String(item.risk_score_id ?? "—")} />
          <InfoCard label="Disposition ID" value={String(item.disposition_id ?? "—")} />
          <InfoCard label="Created" value={formatDate(item.created_at)} />
        </div>
      </div>

      <div style={packetFooterStyle}>
        <div>
          Export this case as a structured governance packet for executive review,
          quality committee discussion, vendor escalation, or survey readiness.
        </div>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "12px" }}>
          <button
            type="button"
            onClick={handleExportPacket}
            disabled={exporting}
            style={exportButtonStyle(exporting)}
          >
            {exporting ? "Exporting JSON..." : "Export Governance Packet JSON"}
          </button>

          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={pdfExporting}
            style={pdfButtonStyle(pdfExporting)}
          >
            {pdfExporting ? "Downloading PDF..." : "Download Governance Packet PDF"}
          </button>
        </div>

        {exportSuccess ? (
          <div style={exportSuccessStyle}>{exportSuccess}</div>
        ) : null}

        {exportError ? (
          <div style={exportErrorStyle}>{exportError}</div>
        ) : null}
      </div>
    </div>
  );
}

function InfoCard({
  label,
  value,
  emphasisColor,
}: {
  label: string;
  value: string;
  emphasisColor?: string;
}) {
  return (
    <div style={infoCardStyle}>
      <div style={infoLabelStyle}>{label}</div>
      <div style={{ ...infoValueStyle, color: emphasisColor || "#0f172a" }}>{value}</div>
    </div>
  );
}

function formatDate(value?: string) {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString();
}

const panelStyle: CSSProperties = {
  margin: "20px 0",
  padding: "20px",
  borderRadius: "18px",
  border: "1px solid #c7d2fe",
  background: "linear-gradient(135deg, #eef2ff 0%, #ffffff 100%)",
  boxShadow: "0 12px 28px rgba(15, 23, 42, 0.08)",
};

const eyebrowStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 800,
  color: "#4338ca",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
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
    fontWeight: 800,
    cursor: loading ? "not-allowed" : "pointer",
    background: loading ? "#94a3b8" : "#4f46e5",
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
  fontWeight: 700,
};

const emptyStyle: CSSProperties = {
  marginTop: "14px",
  padding: "12px",
  borderRadius: "12px",
  background: "#ffffff",
  border: "1px solid #e0e7ff",
  color: "#475569",
};

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

const detailPanelStyle: CSSProperties = {
  marginTop: "18px",
  padding: "18px",
  borderRadius: "18px",
  border: "1px solid #a5b4fc",
  background: "#ffffff",
  boxShadow: "0 16px 32px rgba(79, 70, 229, 0.12)",
};

const detailHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
  flexWrap: "wrap",
};

const closeButtonStyle: CSSProperties = {
  border: "1px solid #c7d2fe",
  borderRadius: "12px",
  padding: "9px 12px",
  background: "#eef2ff",
  color: "#312e81",
  fontWeight: 800,
  cursor: "pointer",
};

const summaryGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
  gap: "10px",
  marginTop: "16px",
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
};

const packetSectionStyle: CSSProperties = {
  marginTop: "16px",
  paddingTop: "12px",
  borderTop: "1px solid #e5e7eb",
};

const packetHeadingStyle: CSSProperties = {
  margin: "0 0 8px",
  color: "#111827",
};

const packetTextStyle: CSSProperties = {
  margin: 0,
  color: "#475569",
  lineHeight: 1.65,
};

const chainListStyle: CSSProperties = {
  margin: 0,
  paddingLeft: "20px",
  color: "#475569",
  lineHeight: 1.7,
};

const auditGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
  gap: "10px",
};


const reviewButtonRowStyle: CSSProperties = {
  display: "flex",
  gap: "10px",
  flexWrap: "wrap",
  marginTop: "12px",
};

function reviewButtonStyle(background: string, active: boolean): CSSProperties {
  return {
    border: "0",
    borderRadius: "12px",
    padding: "10px 13px",
    background: active ? "#94a3b8" : background,
    color: "#ffffff",
    fontWeight: 900,
    cursor: active ? "not-allowed" : "pointer",
    boxShadow: "0 10px 18px rgba(15, 23, 42, 0.12)",
  };
}


const capaSuccessStyle: CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#f3e8ff",
  color: "#6b21a8",
  fontWeight: 800,
};

const reviewSuccessStyle: CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#dcfce7",
  color: "#166534",
  fontWeight: 800,
};


const packetFooterStyle: CSSProperties = {
  marginTop: "16px",
  padding: "12px",
  borderRadius: "14px",
  background: "#f0fdf4",
  color: "#166534",
  fontWeight: 800,
  border: "1px solid #bbf7d0",
};




async function openEnterpriseCapa(findingId: number) {
  const response = await fetch(
    `${API_BASE}/api/enterprise/intake/${findingId}/capa`,
    {
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
        title: "CAPA - Frazier suction retained debris concern",
        description:
          "CAPA opened due to confirmed high-risk retained debris finding during borescope inspection.",
        owner_id: null,
        due_date: "2026-06-30",
        status: "open",
      }),
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `CAPA creation failed (${response.status})`);
  }

  return data;
}


async function submitHumanReview(
  findingId: number,
  decision: string,
  reviewNotes: string
) {
  const response = await fetch(
    `${API_BASE}/api/enterprise/intake/${findingId}/review`,
    {
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
        human_confirmed: true,
      }),
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Human review failed (${response.status})`);
  }

  return data;
}


async function exportGovernancePacket(findingId: number) {
  const response = await fetch(
    `${API_BASE}/api/enterprise/intake/${findingId}/governance-packet`,
    {
      headers: {
        Authorization: `Bearer ${AUTH_TOKEN}`,
        "X-LumenAI-Role": "viewer",
        "X-LumenAI-Actor": "john-demo",
        "X-Tenant-Id": "bonsecours",
        "X-Tenant-Name": "Bon Secours",
      },
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || `Packet export failed (${response.status})`);
  }

  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `lumenai-governance-packet-finding-${findingId}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);

  return data;
}




function pdfButtonStyle(exporting: boolean): CSSProperties {
  return {
    border: "0",
    borderRadius: "12px",
    padding: "11px 14px",
    background: exporting ? "#94a3b8" : "#1d4ed8",
    color: "#ffffff",
    fontWeight: 900,
    cursor: exporting ? "not-allowed" : "pointer",
    boxShadow: "0 10px 18px rgba(29, 78, 216, 0.20)",
  };
}

function exportButtonStyle(exporting: boolean): CSSProperties {
  return {
    marginTop: "12px",
    border: "0",
    borderRadius: "12px",
    padding: "11px 14px",
    background: exporting ? "#94a3b8" : "#166534",
    color: "#ffffff",
    fontWeight: 900,
    cursor: exporting ? "not-allowed" : "pointer",
    boxShadow: "0 10px 18px rgba(22, 101, 52, 0.20)",
  };
}

const exportSuccessStyle: CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#dcfce7",
  color: "#166534",
  fontWeight: 800,
};

const exportErrorStyle: CSSProperties = {
  marginTop: "10px",
  padding: "10px",
  borderRadius: "12px",
  background: "#fef2f2",
  color: "#991b1b",
  fontWeight: 800,
};



async function downloadGovernancePacketPdf(findingId: number) {
  const response = await fetch(
    `${API_BASE}/api/enterprise/intake/${findingId}/governance-packet.pdf`,
    {
      headers: {
        Authorization: `Bearer ${AUTH_TOKEN}`,
        "X-LumenAI-Role": "viewer",
        "X-LumenAI-Actor": "john-demo",
        "X-Tenant-Id": "bonsecours",
        "X-Tenant-Name": "Bon Secours",
      },
    }
  );

  if (!response.ok) {
    let message = `PDF download failed (${response.status})`;
    try {
      const data = await response.json();
      message = data?.detail || message;
    } catch {
      // PDF route may not return JSON on failure.
    }
    throw new Error(message);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `lumenai-governance-packet-finding-${findingId}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}


function severityColor(severity?: string) {
  const s = (severity || "").toLowerCase();
  if (s === "critical") return "#991b1b";
  if (s === "high") return "#b45309";
  if (s === "moderate") return "#a16207";
  return "#166534";
}
