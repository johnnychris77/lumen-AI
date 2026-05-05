import React from "react";
import VisualInspectionIntelligencePanel from "./components/VisualInspectionIntelligencePanel.jsx";
import InspectionIntakeModule from "./components/InspectionIntakeModule.jsx";
import CapaDashboardCards from "./components/CapaDashboardCards.jsx";

export default function App() {
  return (
    <main style={{ minHeight: "100vh", background: "#f9fafb", padding: "24px" }}>
      <div style={{ maxWidth: "1440px", margin: "0 auto" }}>
        <header style={{ marginBottom: "24px" }}>
          <h1 style={{ fontSize: "30px", fontWeight: "800", color: "#111827" }}>
            LumenAI Quality Intelligence Dashboard
          </h1>
          <p style={{ color: "#6b7280", marginTop: "8px" }}>
            Inspection intake, CAPA, Infection Prevention review, vendor escalation, and quality action tracking.
          </p>
        </header>

        <VisualInspectionIntelligencePanel />

        <InspectionIntakeModule />

        <CapaDashboardCards />
      </div>
    </main>
  );
}
