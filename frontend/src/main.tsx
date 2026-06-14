import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";

const DashboardApp = lazy(() => import("./pages/DashboardApp"));
const OperationsDashboard = lazy(() => import("./pages/OperationsDashboard"));
const NewInspectionPage = lazy(() => import("./pages/NewInspectionPage"));
const FindingsQueuePage = lazy(() => import("./pages/FindingsQueuePage"));
const CapaQueuePage = lazy(() => import("./pages/CapaQueuePage"));
const AnalyticsDashboardPage = lazy(() => import("./pages/AnalyticsDashboardPage"));

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

          <a href="/portfolio/live-dashboard" style={card}>
            Live Dashboard Portfolio
          </a>

          <a href="/portfolio/erp-style-governance" style={card}>
            ERP-Style Governance Portfolio
          </a>

          <a href="/portfolio/customer-demo" style={card}>
            Enterprise Customer Demo Portfolio
          </a>

          <a href="/portfolio/investor-review" style={card}>
            Investor Review Portfolio
          </a>

          <a href="/portfolio/sales-readiness" style={card}>
            Sales Readiness Portfolio
          </a>

          <a href="/portfolio/compliance-evidence" style={card}>
            Compliance Evidence Portfolio
          </a>

          <a href="/portfolio/vendor-accountability" style={card}>
            Vendor Accountability Portfolio
          </a>

          <a href="/portfolio/capa-governance" style={card}>
            CAPA Governance Portfolio
          </a>

          <a href="/portfolio/audit-readiness" style={card}>
            Audit Readiness Portfolio
          </a>









        </div>

        <p style={{ marginTop: "28px", color: "#94a3b8" }}>
          Compliance Evidence v1.0: Complete · Sealed · Tagged · Indexed · Archived · Customer-Ready
        </p>
      </section>
    </main>
  );
}



class DashboardErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <main style={{ padding: "32px", fontFamily: "Arial, sans-serif", background: "#0f172a", minHeight: "100vh", color: "#f8fafc" }}>
          <h1>Dashboard temporarily unavailable</h1>
          <p>The public LumenAI landing page and portfolio pages are still available.</p>
          <pre style={{ whiteSpace: "pre-wrap", background: "#1e293b", padding: "16px", borderRadius: "12px" }}>
            {String(this.state.error.message || this.state.error)}
          </pre>
          <p><a href="/" style={{ color: "#93c5fd" }}>Return to public landing page</a></p>
        </main>
      );
    }

    return this.props.children;
  }
}

function RootRouter() {
  const path = window.location.pathname.replace(/\/$/, "") || "/";

  if (path === "/dashboard") {
    return (
      <DashboardErrorBoundary>
        <Suspense fallback={<main style={{ padding: "32px", fontFamily: "Arial, sans-serif" }}>Loading dashboard...</main>}>
          <DashboardApp />
        </Suspense>
      </DashboardErrorBoundary>
    );
  }

  if (path === "/operations") {
    return (
      <Suspense fallback={<main style={{ padding: "32px", fontFamily: "Arial, sans-serif" }}>Loading operations...</main>}>
        <OperationsDashboard />
      </Suspense>
    );
  }

  if (path === "/inspection/new") {
    return (
      <Suspense fallback={<main style={{ padding: "32px", fontFamily: "Arial, sans-serif" }}>Loading inspection form...</main>}>
        <NewInspectionPage />
      </Suspense>
    );
  }

  if (path === "/findings") {
    return (
      <Suspense fallback={<main style={{ padding: "32px", fontFamily: "Arial, sans-serif" }}>Loading findings queue...</main>}>
        <FindingsQueuePage />
      </Suspense>
    );
  }

  if (path === "/capa") {
    return (
      <Suspense fallback={<main style={{ padding: "32px", fontFamily: "Arial, sans-serif" }}>Loading CAPA queue...</main>}>
        <CapaQueuePage />
      </Suspense>
    );
  }

  if (path === "/analytics") {
    return (
      <Suspense fallback={<main style={{ padding: "32px", fontFamily: "Arial, sans-serif" }}>Loading analytics...</main>}>
        <AnalyticsDashboardPage />
      </Suspense>
    );
  }

  return <PublicLandingHome />;
}

const root = document.getElementById("root");

if (!root) {
  throw new Error("Missing root element");
}

ReactDOM.createRoot(root).render(<RootRouter />);
