import React, { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

export default function CapaWorkflowPanel() {
  const [health, setHealth] = useState(null);
  const [capas, setCapas] = useState([]);
  const [summary, setSummary] = useState({
    total: 0,
    open: 0,
    high_risk: 0,
    closed: 0,
  });
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadCapaData() {
    try {
      setLoading(true);
      setErrorMessage("");

      const [healthResponse, listResponse] = await Promise.all([
        fetch(`${API_BASE}/api/capa/health`),
        fetch(`${API_BASE}/api/capa?limit=10`),
      ]);

      if (!healthResponse.ok) {
        throw new Error(`CAPA health returned ${healthResponse.status}`);
      }

      if (!listResponse.ok) {
        throw new Error(`CAPA list returned ${listResponse.status}`);
      }

      const healthData = await healthResponse.json();
      const listData = await listResponse.json();

      setHealth(healthData);
      setCapas(listData.items || []);
      setSummary(listData.summary || healthData.summary || {});
    } catch (error) {
      setErrorMessage(error.message || "Unable to load CAPA workflow data.");
    } finally {
      setLoading(false);
    }
  }


  function downloadPowerBiCsv() {
    window.open(`${API_BASE}/api/capa/powerbi-csv?limit=500`, "_blank");
  }

  async function createAuditSignalCapa() {
    try {
      setCreating(true);
      setErrorMessage("");

      const response = await fetch(`${API_BASE}/api/capa/from-audit-signal`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          event_type: "High-Value Audit Event",
          event_summary:
            "Frontend demo CAPA created from a high-value audit signal requiring governance review.",
          risk_level: "high",
          owner: "Quality / Operations",
          due_date: "2026-06-15",
        }),
      });

      if (!response.ok) {
        throw new Error(`Create CAPA returned ${response.status}`);
      }

      await loadCapaData();
    } catch (error) {
      setErrorMessage(error.message || "Unable to create CAPA.");
    } finally {
      setCreating(false);
    }
  }

  useEffect(() => {
    loadCapaData();
  }, []);

  return (
    <section
      style={{
        marginTop: "24px",
        border: "1px solid #d1fae5",
        borderRadius: "24px",
        background: "#ffffff",
        boxShadow: "0 12px 32px rgba(15, 23, 42, 0.08)",
        padding: "24px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "16px",
          flexWrap: "wrap",
        }}
      >
        <div>
          <div
            style={{
              display: "inline-flex",
              borderRadius: "999px",
              background: "#ecfdf5",
              color: "#047857",
              padding: "6px 12px",
              fontSize: "12px",
              fontWeight: 800,
              border: "1px solid #a7f3d0",
              marginBottom: "10px",
            }}
          >
            CAPA Workflow · Production Backend
          </div>

          <h2 style={{ margin: 0, fontSize: "24px", color: "#0f172a" }}>
            Corrective and Preventive Action Workflow
          </h2>

          <p
            style={{
              marginTop: "8px",
              maxWidth: "780px",
              color: "#475569",
              lineHeight: 1.6,
            }}
          >
            Converts high-value audit signals into structured CAPA records with
            risk level, owner, due date, corrective action, preventive action,
            and governance status.
          </p>
        </div>

        <div
          style={{
            display: "flex",
            gap: "10px",
            flexWrap: "wrap",
            justifyContent: "flex-end",
          }}
        >
          <button
            onClick={downloadPowerBiCsv}
            style={{
              border: "1px solid #bfdbfe",
              borderRadius: "999px",
              background: "#eff6ff",
              color: "#1d4ed8",
              padding: "12px 18px",
              fontWeight: 800,
              cursor: "pointer",
              boxShadow: "0 8px 20px rgba(37, 99, 235, 0.12)",
            }}
          >
            Download Power BI CSV
          </button>

          <button
            onClick={createAuditSignalCapa}
            disabled={creating}
            style={{
              border: "none",
              borderRadius: "999px",
              background: creating ? "#94a3b8" : "#047857",
              color: "#ffffff",
              padding: "12px 18px",
              fontWeight: 800,
              cursor: creating ? "not-allowed" : "pointer",
              boxShadow: "0 8px 20px rgba(4, 120, 87, 0.22)",
            }}
          >
            {creating ? "Creating CAPA..." : "Create CAPA from Audit Signal"}
          </button>
        </div>
      </div>

      {loading && (
        <div style={{ marginTop: "20px", color: "#64748b" }}>
          Loading CAPA workflow data...
        </div>
      )}

      {errorMessage && (
        <div
          style={{
            marginTop: "20px",
            borderRadius: "16px",
            border: "1px solid #fecaca",
            background: "#fef2f2",
            color: "#991b1b",
            padding: "14px",
            fontWeight: 700,
          }}
        >
          {errorMessage}
        </div>
      )}

      {!loading && !errorMessage && (
        <>
          <div
            style={{
              marginTop: "22px",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
              gap: "14px",
            }}
          >
            <MetricCard label="Health" value={health?.status || "healthy"} />
            <MetricCard label="Total CAPAs" value={summary?.total ?? 0} />
            <MetricCard label="Open CAPAs" value={summary?.open ?? 0} />
            <MetricCard label="High Risk" value={summary?.high_risk ?? 0} />
            <MetricCard label="Closed" value={summary?.closed ?? 0} />
          </div>

          <div style={{ marginTop: "24px" }}>
            <h3 style={{ margin: "0 0 12px", color: "#0f172a" }}>
              Latest CAPA Records
            </h3>

            {capas.length === 0 ? (
              <div
                style={{
                  borderRadius: "18px",
                  border: "1px dashed #cbd5e1",
                  background: "#f8fafc",
                  padding: "18px",
                  color: "#64748b",
                }}
              >
                No CAPA records yet. Use the button above to create one from an
                audit signal.
              </div>
            ) : (
              <div style={{ display: "grid", gap: "14px" }}>
                {capas.map((capa) => (
                  <CapaCard key={capa.id} capa={capa} />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function MetricCard({ label, value }) {
  return (
    <div
      style={{
        borderRadius: "18px",
        border: "1px solid #e2e8f0",
        background: "#f8fafc",
        padding: "16px",
      }}
    >
      <div
        style={{
          color: "#64748b",
          fontSize: "12px",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          fontWeight: 800,
        }}
      >
        {label}
      </div>
      <div
        style={{
          marginTop: "6px",
          color: "#0f172a",
          fontSize: "24px",
          fontWeight: 900,
          textTransform: typeof value === "string" ? "uppercase" : "none",
        }}
      >
        {value}
      </div>
    </div>
  );
}

function CapaCard({ capa }) {
  const riskColor =
    capa.risk_level === "critical"
      ? "#7f1d1d"
      : capa.risk_level === "high"
      ? "#b91c1c"
      : capa.risk_level === "medium"
      ? "#92400e"
      : "#166534";

  return (
    <article
      style={{
        borderRadius: "20px",
        border: "1px solid #e2e8f0",
        background: "#ffffff",
        padding: "18px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h4 style={{ margin: 0, color: "#0f172a", fontSize: "18px" }}>
            {capa.title}
          </h4>
          <p style={{ color: "#475569", marginTop: "8px", lineHeight: 1.5 }}>
            {capa.description}
          </p>
        </div>

        <div style={{ display: "flex", gap: "8px", alignItems: "flex-start" }}>
          <span
            style={{
              borderRadius: "999px",
              background: "#fef2f2",
              color: riskColor,
              padding: "6px 10px",
              fontSize: "12px",
              fontWeight: 900,
              textTransform: "uppercase",
            }}
          >
            {capa.risk_level}
          </span>

          <span
            style={{
              borderRadius: "999px",
              background: "#eff6ff",
              color: "#1d4ed8",
              padding: "6px 10px",
              fontSize: "12px",
              fontWeight: 900,
              textTransform: "uppercase",
            }}
          >
            {capa.status}
          </span>
        </div>
      </div>

      <div
        style={{
          marginTop: "14px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "12px",
        }}
      >
        <InfoBlock label="Owner" value={capa.owner} />
        <InfoBlock label="Due Date" value={capa.due_date || "Not assigned"} />
        <InfoBlock label="Source" value={capa.source} />
        <InfoBlock label="Created" value={formatDate(capa.created_at)} />
      </div>

      <div
        style={{
          marginTop: "14px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "12px",
        }}
      >
        <InfoBlock
          label="Corrective Action"
          value={capa.corrective_action || "Pending definition"}
        />
        <InfoBlock
          label="Preventive Action"
          value={capa.preventive_action || "Pending definition"}
        />
      </div>
    </article>
  );
}

function InfoBlock({ label, value }) {
  return (
    <div
      style={{
        borderRadius: "14px",
        background: "#f8fafc",
        border: "1px solid #e2e8f0",
        padding: "12px",
      }}
    >
      <div
        style={{
          color: "#64748b",
          fontSize: "11px",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          fontWeight: 800,
        }}
      >
        {label}
      </div>
      <div style={{ marginTop: "6px", color: "#0f172a", fontWeight: 700 }}>
        {value}
      </div>
    </div>
  );
}

function formatDate(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}
