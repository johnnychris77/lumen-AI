import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import InspectionHistory from "./pages/InspectionHistory";

function Home() {
  return (
    <div style={{ padding: "24px", maxWidth: "1100px", margin: "0 auto" }}>
      <h1 style={{ marginBottom: "8px" }}>LumenAI</h1>
      <p style={{ color: "#4b5563", marginBottom: "24px" }}>
        AI-powered inspection workflow for instrument quality review.
      </p>

      <div
        style={{
          display: "grid",
          gap: "16px",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
        }}
      >
        <div style={card}>
          <h2 style={{ marginTop: 0 }}>Inspection History</h2>
          <p style={{ color: "#4b5563" }}>
            Review completed and in-progress inspections, confidence scores,
            material classifications, model metadata, and PDF reports.
          </p>
          <Link to="/history">Open history</Link>
        </div>

        <div style={card}>
          <h2 style={{ marginTop: 0 }}>Reports</h2>
          <p style={{ color: "#4b5563" }}>
            Completed inspections expose report actions directly from the
            history table for quick QA review.
          </p>
          <Link to="/history">View completed reports</Link>
        </div>

        <div style={card}>
          <h2 style={{ marginTop: 0 }}>System Status</h2>
          <p style={{ color: "#4b5563" }}>
            LumenAI is running with API, Postgres, Redis, and worker-backed
            asynchronous processing.
          </p>
          <a href="/api/health" target="_blank" rel="noreferrer">
            Check API health
          </a>
        </div>
      </div>
    </div>
  );
}

function Layout() {
  return (
    <BrowserRouter>
      <div
        style={{
          borderBottom: "1px solid #e5e7eb",
          padding: "12px 24px",
          background: "#ffffff",
        }}
      >
        <div
          style={{
            maxWidth: "1100px",
            margin: "0 auto",
            display: "flex",
            gap: "16px",
            alignItems: "center",
          }}
        >
          <Link to="/" style={{ fontWeight: 700, textDecoration: "none" }}>
            LumenAI
          </Link>
          <Link to="/history">History</Link>
        </div>
      </div>

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/history" element={<InspectionHistory />} />
      </Routes>
    </BrowserRouter>
  );
}

const card = {
  border: "1px solid #e5e7eb",
  borderRadius: "12px",
  padding: "20px",
  background: "#fff",
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Layout />
  </React.StrictMode>
);
