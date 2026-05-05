import React, { useEffect, useState } from "react";
import { fetchCapaAnalytics } from "../api/capaApi.js";

function AnalyticsCard({ label, value, helper }) {
  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        background: "#ffffff",
        borderRadius: "16px",
        padding: "16px",
        boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
      }}
    >
      <div style={{ color: "#6b7280", fontSize: "13px", fontWeight: 800 }}>
        {label}
      </div>
      <div style={{ color: "#111827", fontSize: "32px", fontWeight: 950 }}>
        {value ?? "N/A"}
      </div>
      <div style={{ color: "#6b7280", fontSize: "13px" }}>{helper}</div>
    </div>
  );
}

function TrendTable({ title, rows }) {
  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        background: "#ffffff",
        borderRadius: "16px",
        padding: "16px",
        boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
      }}
    >
      <h3 style={{ marginTop: 0, fontSize: "18px", fontWeight: 900 }}>
        {title}
      </h3>

      {!rows?.length ? (
        <p style={{ color: "#6b7280" }}>No trend records yet.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ color: "#6b7280", textAlign: "left" }}>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>Total</th>
              <th style={thStyle}>Open</th>
              <th style={thStyle}>Closed</th>
              <th style={thStyle}>High Risk</th>
              <th style={thStyle}>Overdue</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.name}>
                <td style={tdStyle}>{row.name}</td>
                <td style={tdStyle}>{row.total}</td>
                <td style={tdStyle}>{row.open}</td>
                <td style={tdStyle}>{row.closed}</td>
                <td style={tdStyle}>{row.high_risk}</td>
                <td style={tdStyle}>{row.overdue}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function CapaExecutiveAnalytics({ setError }) {
  const [analytics, setAnalytics] = useState(null);
  const [filters, setFilters] = useState({
    status: "",
    facility: "",
    vendor: "",
    risk_level: "",
  });

  async function loadAnalytics(nextFilters = filters) {
    try {
      setError("");
      const data = await fetchCapaAnalytics(nextFilters);
      setAnalytics(data);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadAnalytics();
  }, []);

  function updateFilter(key, value) {
    const next = { ...filters, [key]: value };
    setFilters(next);
    loadAnalytics(next);
  }

  const summary = analytics?.summary || {};

  return (
    <section style={{ marginTop: "28px" }}>
      <div style={{ marginBottom: "16px" }}>
        <h2 style={{ fontSize: "26px", fontWeight: 950, color: "#111827" }}>
          Executive CAPA Analytics
        </h2>
        <p style={{ color: "#6b7280" }}>
          Filter quality actions by status, facility, vendor, and risk level.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "12px",
          marginBottom: "18px",
        }}
      >
        <select style={inputStyle} value={filters.status} onChange={(e) => updateFilter("status", e.target.value)}>
          <option value="">All Statuses</option>
          <option value="Open">Open</option>
          <option value="Pending IP Review">Pending IP Review</option>
          <option value="Pending Vendor Response">Pending Vendor Response</option>
          <option value="Action in Progress">Action in Progress</option>
          <option value="Closed">Closed</option>
        </select>

        <select style={inputStyle} value={filters.risk_level} onChange={(e) => updateFilter("risk_level", e.target.value)}>
          <option value="">All Risk Levels</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>

        <input
          style={inputStyle}
          placeholder="Facility filter"
          value={filters.facility}
          onChange={(e) => updateFilter("facility", e.target.value)}
        />

        <input
          style={inputStyle}
          placeholder="Vendor filter"
          value={filters.vendor}
          onChange={(e) => updateFilter("vendor", e.target.value)}
        />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "14px",
          marginBottom: "20px",
        }}
      >
        <AnalyticsCard label="Total CAPAs" value={summary.total_capas} helper="All matching records" />
        <AnalyticsCard label="Open" value={summary.open_capas} helper="Active actions" />
        <AnalyticsCard label="Closed" value={summary.closed_capas} helper="Verified closures" />
        <AnalyticsCard label="High Risk" value={summary.high_risk} helper="Patient-safety concern" />
        <AnalyticsCard label="Overdue" value={summary.overdue} helper="Past due date" />
        <AnalyticsCard label="Avg Days to Due" value={summary.average_days_to_due} helper="Remaining days" />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))",
          gap: "16px",
        }}
      >
        <TrendTable title="Facility Quality Trend" rows={analytics?.facility_trends || []} />
        <TrendTable title="Vendor Quality Trend" rows={analytics?.vendor_trends || []} />
        <TrendTable title="Status Trend" rows={analytics?.status_trends || []} />
        <TrendTable title="Risk Trend" rows={analytics?.risk_trends || []} />
      </div>
    </section>
  );
}

const inputStyle = {
  border: "1px solid #d1d5db",
  borderRadius: "12px",
  padding: "10px",
  fontSize: "14px",
  background: "#ffffff",
};

const thStyle = {
  borderBottom: "1px solid #e5e7eb",
  padding: "8px",
};

const tdStyle = {
  borderBottom: "1px solid #f3f4f6",
  padding: "8px",
};
