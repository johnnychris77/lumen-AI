import React, { useEffect, useState } from "react";
import {
  fetchCapaDashboardSummary,
  updateCapaStatus,
  closeCapaWithVerification,
} from "../api/capaApi.js";
import RcaEvidencePanel from "./RcaEvidencePanel.jsx";
import CapaDetailsDrawer from "./CapaDetailsDrawer.jsx";
import CapaReportDrawer from "./CapaReportDrawer.jsx";
import CapaExecutiveAnalytics from "./CapaExecutiveAnalytics.jsx";

function MetricCard({ label, value, helper, tone = "neutral" }) {
  const tones = {
    neutral: { border: "#e5e7eb", background: "#ffffff", accent: "#111827" },
    warning: { border: "#f59e0b", background: "#fffbeb", accent: "#92400e" },
    danger: { border: "#ef4444", background: "#fef2f2", accent: "#991b1b" },
    info: { border: "#3b82f6", background: "#eff6ff", accent: "#1e40af" },
    success: { border: "#10b981", background: "#ecfdf5", accent: "#065f46" },
  };

  const style = tones[tone] || tones.neutral;

  return (
    <div
      style={{
        border: `1px solid ${style.border}`,
        background: style.background,
        borderRadius: "18px",
        padding: "18px",
        boxShadow: "0 8px 24px rgba(15, 23, 42, 0.06)",
      }}
    >
      <div style={{ color: "#6b7280", fontSize: "13px", fontWeight: 600 }}>
        {label}
      </div>
      <div
        style={{
          color: style.accent,
          fontSize: "34px",
          fontWeight: 800,
          marginTop: "8px",
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      <div style={{ color: "#6b7280", fontSize: "12px", marginTop: "10px" }}>
        {helper}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  let background = "#f3f4f6";
  let color = "#374151";

  if (status === "Open") {
    background = "#fef3c7";
    color = "#92400e";
  }

  if (status === "Pending IP Review") {
    background = "#dbeafe";
    color = "#1e40af";
  }

  if (status === "Pending Vendor Response") {
    background = "#fce7f3";
    color = "#9d174d";
  }

  if (status === "Action in Progress") {
    background = "#e0f2fe";
    color = "#075985";
  }

  if (status === "Closed") {
    background = "#dcfce7";
    color = "#166534";
  }

  return (
    <span
      style={{
        background,
        color,
        padding: "4px 10px",
        borderRadius: "999px",
        fontSize: "12px",
        fontWeight: 700,
        whiteSpace: "nowrap",
      }}
    >
      {status}
    </span>
  );
}

function RiskBadge({ risk }) {
  const isHigh = risk === "High";

  return (
    <span
      style={{
        background: isHigh ? "#fee2e2" : "#f3f4f6",
        color: isHigh ? "#991b1b" : "#374151",
        padding: "4px 10px",
        borderRadius: "999px",
        fontSize: "12px",
        fontWeight: 700,
      }}
    >
      {risk}
    </span>
  );
}

function WorkflowButton({ children, onClick, disabled, tone = "neutral" }) {
  const tones = {
    neutral: { background: "#ffffff", border: "#d1d5db", color: "#374151" },
    info: { background: "#eff6ff", border: "#93c5fd", color: "#1e40af" },
    vendor: { background: "#fdf2f8", border: "#f9a8d4", color: "#9d174d" },
    progress: { background: "#ecfeff", border: "#67e8f9", color: "#155e75" },
    close: { background: "#ecfdf5", border: "#86efac", color: "#166534" },
    evidence: { background: "#f5f3ff", border: "#c4b5fd", color: "#5b21b6" },
  };

  const style = tones[tone] || tones.neutral;

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.55 : 1,
        background: style.background,
        border: `1px solid ${style.border}`,
        color: style.color,
        borderRadius: "999px",
        padding: "6px 10px",
        fontSize: "12px",
        fontWeight: 700,
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </button>
  );
}

function TextAreaField({ label, value, onChange, placeholder }) {
  return (
    <label style={{ display: "block" }}>
      <div style={{ fontSize: "13px", fontWeight: 800, color: "#374151" }}>
        {label}
      </div>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        rows={3}
        style={{
          marginTop: "6px",
          width: "100%",
          border: "1px solid #d1d5db",
          borderRadius: "12px",
          padding: "10px",
          fontSize: "14px",
          fontFamily: "inherit",
          resize: "vertical",
        }}
      />
    </label>
  );
}

function InputField({ label, value, onChange, placeholder }) {
  return (
    <label style={{ display: "block" }}>
      <div style={{ fontSize: "13px", fontWeight: 800, color: "#374151" }}>
        {label}
      </div>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        style={{
          marginTop: "6px",
          width: "100%",
          border: "1px solid #d1d5db",
          borderRadius: "12px",
          padding: "10px",
          fontSize: "14px",
          fontFamily: "inherit",
        }}
      />
    </label>
  );
}

export default function CapaDashboardCards() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [updatingId, setUpdatingId] = useState("");
  const [selectedCapa, setSelectedCapa] = useState(null);
  const [selectedDetailsCapaId, setSelectedDetailsCapaId] = useState("");
  const [selectedReportCapaId, setSelectedReportCapaId] = useState("");

  async function loadSummary() {
    setError("");
    const data = await fetchCapaDashboardSummary();
    setSummary(data);
  }

  useEffect(() => {
    loadSummary().catch((err) => setError(err.message));
  }, []);


  async function handleVerifiedClose(capaId) {
    try {
      setUpdatingId(capaId);
      setActionMessage("");

      await closeCapaWithVerification(
        capaId,
        "Dashboard verified closure requested."
      );

      await loadSummary();
      setActionMessage("CAPA closed with verification.");
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdatingId("");
    }
  }

  async function handleStatusUpdate(capaId, status) {
    try {
      setUpdatingId(capaId);
      setActionMessage("");

      await updateCapaStatus(
        capaId,
        status,
        `Dashboard workflow updated CAPA to ${status}.`
      );

      await loadSummary();
      setActionMessage(`CAPA updated to ${status}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdatingId("");
    }
  }

  async function handlePanelSaved(message) {
    await loadSummary();
    setActionMessage(message);
  }

  if (error) {
    return (
      <div
        style={{
          color: "#991b1b",
          border: "1px solid #fecaca",
          background: "#fef2f2",
          padding: "16px",
          borderRadius: "14px",
        }}
      >
        CAPA dashboard failed to load: {error}
      </div>
    );
  }

  if (!summary) {
    return (
      <div
        style={{
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: "16px",
          borderRadius: "14px",
        }}
      >
        Loading CAPA dashboard...
      </div>
    );
  }

  return (
    <section style={{ marginTop: "28px" }}>
      <CapaReportDrawer
        capaId={selectedReportCapaId}
        onClose={() => setSelectedReportCapaId("")}
        setError={setError}
      />
      <div style={{ marginBottom: "18px" }}>
        <h2 style={{ fontSize: "26px", fontWeight: 800, color: "#111827" }}>
          CAPA Quality Action Dashboard
        </h2>
        <p style={{ color: "#6b7280", marginTop: "6px", fontSize: "15px" }}>
          Closed-loop quality actions generated from LumenAI inspection and quality events.
        </p>
      </div>

      {actionMessage && (
        <div
          style={{
            background: "#ecfdf5",
            border: "1px solid #86efac",
            color: "#166534",
            padding: "12px 14px",
            borderRadius: "12px",
            marginBottom: "16px",
            fontWeight: 700,
          }}
        >
          {actionMessage}
        </div>
      )}

      <CapaDetailsDrawer
        capaId={selectedDetailsCapaId}
        onClose={() => setSelectedDetailsCapaId("")}
        setError={setError}
      />

      <RcaEvidencePanel
        selectedCapa={selectedCapa}
        onClose={() => setSelectedCapa(null)}
        onSaved={handlePanelSaved}
        setError={setError}
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "16px",
          marginBottom: "28px",
        }}
      >
        <MetricCard
          label="Open CAPAs"
          value={summary.open_capas}
          helper="Active quality actions"
          tone={summary.open_capas > 0 ? "warning" : "success"}
        />
        <MetricCard
          label="Pending IP Review"
          value={summary.pending_ip_review}
          helper="Needs Infection Prevention review"
          tone={summary.pending_ip_review > 0 ? "info" : "neutral"}
        />
        <MetricCard
          label="Vendor Pending"
          value={summary.vendor_pending}
          helper="Awaiting vendor response"
          tone={summary.vendor_pending > 0 ? "warning" : "neutral"}
        />
        <MetricCard
          label="High Risk"
          value={summary.high_risk}
          helper="High patient-safety concern"
          tone={summary.high_risk > 0 ? "danger" : "success"}
        />
        <MetricCard
          label="Due Soon"
          value={summary.due_soon}
          helper="Due within 3 days"
          tone={summary.due_soon > 0 ? "warning" : "neutral"}
        />
        <MetricCard
          label="Avg Days to Due"
          value={summary.average_days_to_due ?? "N/A"}
          helper="Average remaining days"
          tone="info"
        />
      </div>

      <div
        style={{
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: "18px",
          padding: "20px",
          boxShadow: "0 8px 24px rgba(15, 23, 42, 0.06)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "12px",
            alignItems: "center",
            marginBottom: "16px",
          }}
        >
          <div>
            <h3 style={{ fontSize: "20px", fontWeight: 800, color: "#111827" }}>
              Recent CAPA Actions
            </h3>
            <p style={{ color: "#6b7280", marginTop: "4px", fontSize: "14px" }}>
              Latest quality actions requiring follow-up, review, or closure.
            </p>
          </div>
          <div
            style={{
              background: "#f9fafb",
              border: "1px solid #e5e7eb",
              borderRadius: "999px",
              padding: "8px 12px",
              fontSize: "13px",
              color: "#374151",
              fontWeight: 700,
            }}
          >
            Total: {summary.total_capas}
          </div>
        </div>

        {summary.recent_items?.length === 0 ? (
          <p style={{ color: "#6b7280" }}>No CAPA records yet.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "14px",
              }}
            >
              <thead>
                <tr style={{ borderBottom: "1px solid #e5e7eb" }}>
                  <th style={thStyle}>CAPA ID</th>
                  <th style={thStyle}>Facility</th>
                  <th style={thStyle}>Instrument</th>
                  <th style={thStyle}>Risk</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Owner</th>
                  <th style={thStyle}>Due Date</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {summary.recent_items.map((item) => {
                  const isUpdating = updatingId === item.capa_id;
                  const isClosed = item.status === "Closed";

                  return (
                    <tr
                      key={item.capa_id}
                      style={{ borderBottom: "1px solid #f3f4f6" }}
                    >
                      <td style={tdMonoStyle}>{shortenId(item.capa_id)}</td>
                      <td style={tdStyle}>{item.facility}</td>
                      <td style={tdStyle}>{item.instrument_name}</td>
                      <td style={tdStyle}>
                        <RiskBadge risk={item.risk_level} />
                      </td>
                      <td style={tdStyle}>
                        <StatusBadge status={item.status} />
                      </td>
                      <td style={tdStyle}>{item.owner}</td>
                      <td style={tdStyle}>
                        {item.due_date
                          ? new Date(item.due_date).toLocaleDateString()
                          : "N/A"}
                      </td>
                      <td style={tdStyle}>
                        <div
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: "8px",
                          }}
                        >
                          <WorkflowButton
                            tone="info"
                            disabled={isUpdating || isClosed}
                            onClick={() =>
                              handleStatusUpdate(
                                item.capa_id,
                                "Pending IP Review"
                              )
                            }
                          >
                            Send to IP
                          </WorkflowButton>

                          <WorkflowButton
                            tone="vendor"
                            disabled={isUpdating || isClosed}
                            onClick={() =>
                              handleStatusUpdate(
                                item.capa_id,
                                "Pending Vendor Response"
                              )
                            }
                          >
                            Vendor
                          </WorkflowButton>

                          <WorkflowButton
                            tone="progress"
                            disabled={isUpdating || isClosed}
                            onClick={() =>
                              handleStatusUpdate(
                                item.capa_id,
                                "Action in Progress"
                              )
                            }
                          >
                            In Progress
                          </WorkflowButton>

                          <WorkflowButton
                            tone="close"
                            disabled={isUpdating || isClosed}
                            onClick={() => handleVerifiedClose(item.capa_id)}
                          >
                            Close Verified
                          </WorkflowButton>

                          <WorkflowButton
                            tone="evidence"
                            disabled={isUpdating}
                            onClick={() => setSelectedCapa(item)}
                          >
                            Add RCA / Evidence
                          </WorkflowButton>

                          <WorkflowButton
                            tone="info"
                            disabled={isUpdating}
                            onClick={() => setSelectedReportCapaId(item.capa_id)}
                          >
                            View Report
                          </WorkflowButton>

                          <WorkflowButton
                            tone="neutral"
                            disabled={isUpdating}
                            onClick={() => setSelectedDetailsCapaId(item.capa_id)}
                          >
                            View Details
                          </WorkflowButton>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    

      <CapaExecutiveAnalytics setError={setError} />
</section>
);
}

const thStyle = {
  textAlign: "left",
  padding: "12px",
  color: "#6b7280",
  fontSize: "12px",
  fontWeight: 800,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const tdStyle = {
  padding: "14px 12px",
  color: "#111827",
  verticalAlign: "top",
};

const tdMonoStyle = {
  ...tdStyle,
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  fontSize: "12px",
};

function shortenId(id = "") {
  if (id.length <= 18) return id;
  return `${id.slice(0, 12)}...${id.slice(-6)}`;
}
