import React, { useEffect, useState } from "react";
import { fetchCapaReport } from "../api/capaApi.js";

const REPORT_API_HOST = window.location.hostname;
const REPORT_API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || `http://${REPORT_API_HOST}:18122`;

function buildReportFileUrl(url) {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  return `${REPORT_API_BASE_URL}${url}`;
}

export default function CapaReportDrawer({ capaId, onClose, setError }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    if (!capaId) return;

    async function loadReport() {
      try {
        setLoading(true);
        setLocalError("");
        setError("");
        const data = await fetchCapaReport(capaId);
        setReport(data);
      } catch (err) {
        setLocalError(err.message);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadReport();
  }, [capaId, setError]);

  if (!capaId) return null;

  function copyJson() {
    if (!report) return;
    navigator.clipboard.writeText(JSON.stringify(report, null, 2));
  }

  return (
    <div style={overlayStyle}>
      <aside style={drawerStyle}>
        <div style={headerStyle}>
          <div>
            <h2 style={{ margin: 0, fontSize: "26px", fontWeight: 900 }}>
              CAPA Quality Action Report
            </h2>
            <p style={{ color: "#6b7280", fontSize: "13px" }}>{capaId}</p>
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            {report && (
              <button onClick={copyJson} style={blueButton}>
                Copy JSON
              </button>
            )}
            <button onClick={onClose} style={whiteButton}>
              Close
            </button>
          </div>
        </div>

        {loading && <p>Loading report...</p>}

        {localError && (
          <div style={errorStyle}>
            {localError}
          </div>
        )}

        {report && (
          <>
            <section style={summaryStyle}>
              <div style={labelStyle}>Executive Summary</div>
              <p style={{ fontSize: "16px", lineHeight: 1.5 }}>
                {report.executive_summary}
              </p>
            </section>

            <div style={metricGridStyle}>
              <Metric label="Status" value={report.capa?.status} />
              <Metric label="Risk" value={report.capa?.risk_level} />
              <Metric
                label="Documentation Complete"
                value={report.documentation_complete ? "Yes" : "No"}
              />
              <Metric label="Due Date" value={formatDate(report.capa?.due_date)} />
            </div>

            <Section title="Recommended Next Action">
              {report.recommended_next_action}
            </Section>

            <Section title="CAPA Metadata">
              <p><strong>Facility:</strong> {report.capa?.facility}</p>
              <p><strong>Department:</strong> {report.capa?.department}</p>
              <p><strong>Owner:</strong> {report.capa?.owner}</p>
              <p><strong>CAPA Type:</strong> {report.capa?.capa_type}</p>
            </Section>

            <Section title="Quality Event">
              <p><strong>Event ID:</strong> {report.quality_event?.event_id}</p>
              <p><strong>Inspection ID:</strong> {report.quality_event?.inspection_id}</p>
              <p><strong>Instrument:</strong> {report.quality_event?.instrument_name}</p>
              <p><strong>Category:</strong> {report.quality_event?.instrument_category}</p>
              <p><strong>Vendor:</strong> {report.quality_event?.vendor}</p>
              <p><strong>Finding:</strong> {report.quality_event?.finding_type}</p>
            </Section>

            <Section title="Problem Statement">
              {report.quality_event?.problem_statement}
            </Section>

            <Section title="Containment Action">
              {report.quality_event?.containment_action}
            </Section>

            <Section title="RCA / CAPA Documentation">
              <p><strong>Root Cause:</strong> {report.capa_documentation?.root_cause || "Not documented"}</p>
              <p><strong>Corrective Action:</strong> {report.capa_documentation?.corrective_action || "Not documented"}</p>
              <p><strong>Preventive Action:</strong> {report.capa_documentation?.preventive_action || "Not documented"}</p>
              <p><strong>Closure Summary:</strong> {report.capa_documentation?.closure_summary || "Not documented"}</p>
            </Section>

            <Section title="Evidence">
              {report.evidence?.length ? (
                report.evidence.map((item) => (
                  <div key={item.evidence_id || item.url} style={cardStyle}>
                    <div style={{ fontWeight: 900 }}>{item.name}</div>
                    <div style={{ color: "#6b7280", fontSize: "13px" }}>
                      {item.type} · {item.url}
                    </div>
                    <div style={{ color: "#6b7280", fontSize: "12px" }}>
                      Added by {item.added_by} on {formatDateTime(item.added_at)}
                    </div>
                  </div>
                ))
              ) : (
                <span style={{ color: "#9ca3af" }}>No evidence attached</span>
              )}
            </Section>

            <Section title="Audit Trail">
              {report.audit_trail?.length ? (
                report.audit_trail.map((item, index) => (
                  <div key={`${item.timestamp}-${index}`} style={cardStyle}>
                    <div style={{ fontWeight: 900 }}>{item.action}</div>
                    <div style={{ color: "#6b7280", fontSize: "12px" }}>
                      {formatDateTime(item.timestamp)}
                    </div>
                    <div style={{ marginTop: "6px" }}>
                      {item.details || item.note}
                    </div>
                  </div>
                ))
              ) : (
                <span style={{ color: "#9ca3af" }}>No audit trail</span>
              )}
            </Section>
          </>
        )}
      </aside>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div style={cardStyle}>
      <div style={{ color: "#6b7280", fontSize: "12px", fontWeight: 800 }}>
        {label}
      </div>
      <div style={{ fontWeight: 900, marginTop: "4px" }}>
        {value || "N/A"}
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section style={sectionStyle}>
      <div style={labelStyle}>{title}</div>
      <div style={{ marginTop: "10px", color: "#374151" }}>
        {children || <span style={{ color: "#9ca3af" }}>Not documented</span>}
      </div>
    </section>
  );
}

const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 23, 42, 0.45)",
  zIndex: 9999,
  display: "flex",
  justifyContent: "flex-end",
};

const drawerStyle = {
  width: "760px",
  maxWidth: "96vw",
  height: "100vh",
  background: "#f8fafc",
  borderLeft: "1px solid #e5e7eb",
  boxShadow: "-16px 0 40px rgba(15, 23, 42, 0.25)",
  overflowY: "auto",
  padding: "24px",
};

const headerStyle = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  alignItems: "flex-start",
  marginBottom: "18px",
};

const summaryStyle = {
  border: "1px solid #bfdbfe",
  background: "#eff6ff",
  borderRadius: "16px",
  padding: "16px",
  marginBottom: "16px",
};

const metricGridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
  gap: "12px",
  marginBottom: "16px",
};

const sectionStyle = {
  border: "1px solid #e5e7eb",
  background: "#ffffff",
  borderRadius: "14px",
  padding: "14px",
  marginBottom: "14px",
};

const cardStyle = {
  border: "1px solid #e5e7eb",
  background: "#f9fafb",
  borderRadius: "12px",
  padding: "12px",
  marginBottom: "10px",
};

const labelStyle = {
  color: "#111827",
  fontSize: "14px",
  fontWeight: 900,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const blueButton = {
  border: "1px solid #93c5fd",
  background: "#eff6ff",
  color: "#1e40af",
  borderRadius: "999px",
  padding: "8px 12px",
  cursor: "pointer",
  fontWeight: 900,
};

const whiteButton = {
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#111827",
  borderRadius: "999px",
  padding: "8px 12px",
  cursor: "pointer",
  fontWeight: 900,
};

const errorStyle = {
  border: "1px solid #fecaca",
  background: "#fef2f2",
  color: "#991b1b",
  borderRadius: "12px",
  padding: "12px",
  fontWeight: 700,
  marginBottom: "16px",
};

function formatDate(value) {
  if (!value) return "N/A";
  return new Date(value).toLocaleDateString();
}

function formatDateTime(value) {
  if (!value) return "N/A";
  return new Date(value).toLocaleString();
}
