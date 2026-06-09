import React from "react";
import ReactDOM from "react-dom/client";
import DashboardApp from "./pages/DashboardApp";

const card: React.CSSProperties = {
  display: "block",
  padding: "20px",
  borderRadius: "14px",
  background: "#1e293b",
  color: "#93c5fd",
  textDecoration: "none",
  fontWeight: 700,
  border: "1px solid #334155",
};

function PublicLandingHome() {
  return (
    <main
      style={{
        padding: "32px",
        fontFamily: "Arial, sans-serif",
        background: "#0f172a",
        minHeight: "100vh",
        color: "#f8fafc",
      }}
    >
      <section style={{ maxWidth: "1040px", margin: "0 auto" }}>
        <h1 style={{ fontSize: "40px", marginBottom: "12px" }}>
          LumenAI Enterprise Governance Suite
        </h1>

        <p style={{ fontSize: "18px", lineHeight: 1.6, color: "#cbd5e1" }}>
          Healthcare operations intelligence platform for sterile processing governance,
          vendor accountability, audit readiness, CAPA workflow, and tamper-evident
          compliance evidence.
        </p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "16px",
            marginTop: "28px",
          }}
        >
          <a href="/portfolio/governance-hub" style={card}>
            Enterprise Governance Portfolio Hub
          </a>
          <a href="/portfolio/governance-summary" style={card}>
            Enterprise Governance Summary
          </a>
          <a href="/portfolio/vendor-governance" style={card}>
            Vendor Governance Portfolio
          </a>
          <a href="/portfolio/audit-command-center" style={card}>
            Audit Command Center Evidence Page
          </a>
          <a href="/portfolio/capa-workflow" style={card}>
            CAPA Workflow Evidence Page
          </a>
        </div>

        <p style={{ marginTop: "28px", color: "#94a3b8" }}>
          Compliance Evidence v1.0: Complete · Sealed · Tagged · Indexed · Archived · Customer-Ready
        </p>
      </section>
    </main>
  );
}

const root = document.getElementById("root");

if (!root) {
  throw new Error("Missing root element");
}

ReactDOM.createRoot(root).render(<PublicLandingHome />);
