import { useState } from "react";

type IntakeResponse = {
  status: string;
  message: string;
  tenant_id: string;
  facility_id: number;
  department_id: number;
  vendor_id: number;
  instrument_id: number;
  evidence_id: number | null;
  finding_id: number;
  risk_score_id: number;
  disposition_id: number;
  workflow_status: string;
};

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

const AUTH_TOKEN = localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || "";

export default function EnterpriseIntakePanel() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IntakeResponse | null>(null);
  const [error, setError] = useState("");

  async function createEnterpriseIntake() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${API_BASE}/api/enterprise/intake`, {
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
          facility_name: "St. Mary’s Hospital",
          department_name: "Sterile Processing",
          vendor_name: "Medtronic",
          instrument_name: "Frazier suction",
          instrument_category: "lumened instrument",
          finding_category: "bioburden / retained debris",
          finding_description:
            "Suspected retained debris identified during borescope inspection.",
          severity: "critical",
          confidence_score: 0.91,
          recommended_action:
            "Quarantine + reclean + second inspection + IP review",
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || `Request failed (${response.status})`);
      }

      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown intake error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section
      style={{
        margin: "20px 0",
        padding: "20px",
        borderRadius: "18px",
        border: "1px solid #bbf7d0",
        background: "linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)",
        boxShadow: "0 12px 28px rgba(15, 23, 42, 0.08)",
      }}
    >
      <div
        style={{
          fontSize: "13px",
          fontWeight: 800,
          color: "#15803d",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
      >
        Enterprise Intake Workflow
      </div>

      <h2 style={{ margin: "8px 0 10px", color: "#0f172a" }}>
        Create Structured Evidence-to-Action Record
      </h2>

      <p style={{ margin: 0, color: "#475569", lineHeight: 1.65 }}>
        This panel sends the Frazier suction demo scenario into the enterprise
        backend workflow. The API creates structured facility, department,
        vendor, instrument, finding, risk score, and disposition records.
      </p>

      <button
        type="button"
        onClick={createEnterpriseIntake}
        disabled={loading}
        style={{
          marginTop: "16px",
          border: "0",
          borderRadius: "12px",
          padding: "12px 16px",
          fontWeight: 800,
          cursor: loading ? "not-allowed" : "pointer",
          background: loading ? "#94a3b8" : "#16a34a",
          color: "#ffffff",
          boxShadow: "0 10px 18px rgba(22, 163, 74, 0.25)",
        }}
      >
        {loading ? "Creating intake..." : "Create Enterprise Intake"}
      </button>

      {error ? (
        <div
          style={{
            marginTop: "14px",
            padding: "12px",
            borderRadius: "12px",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            color: "#991b1b",
            fontWeight: 700,
          }}
        >
          {error}
        </div>
      ) : null}

      {result ? (
        <div
          style={{
            marginTop: "16px",
            padding: "14px",
            borderRadius: "14px",
            background: "#ffffff",
            border: "1px solid #bbf7d0",
          }}
        >
          <div style={{ fontWeight: 900, color: "#166534" }}>
            ✅ {result.message}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: "10px",
              marginTop: "12px",
              color: "#334155",
              fontSize: "14px",
            }}
          >
            <div>Facility ID: {result.facility_id}</div>
            <div>Department ID: {result.department_id}</div>
            <div>Vendor ID: {result.vendor_id}</div>
            <div>Instrument ID: {result.instrument_id}</div>
            <div>Finding ID: {result.finding_id}</div>
            <div>Risk Score ID: {result.risk_score_id}</div>
            <div>Disposition ID: {result.disposition_id}</div>
            <div>Status: {result.workflow_status}</div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
