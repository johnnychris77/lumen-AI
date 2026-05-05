import React from "react";
import CapaDashboardCards from "./components/CapaDashboardCards.jsx";

export default function App() {
  return (
    <main style={{ minHeight: "100vh", background: "#f9fafb", padding: "24px" }}>
      <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
        <header style={{ marginBottom: "24px" }}>
          <h1 style={{ fontSize: "28px", fontWeight: "700", color: "#111827" }}>
            LumenAI Quality Intelligence Dashboard
          </h1>
          <p style={{ color: "#6b7280", marginTop: "8px" }}>
            CAPA, Infection Prevention review, vendor escalation, and quality action tracking.
          </p>
        </header>

        <CapaDashboardCards />
      </div>
    </main>
  );
}
