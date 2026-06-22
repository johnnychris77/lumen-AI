import "./index.css";
import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { AuthProvider } from "@/lib/auth";
import { Spinner } from "@/components/ui/spinner";

// New Tailwind pages
import Dashboard from "./pages/Dashboard";
import VendorIntake from "./pages/VendorIntake";

// Existing pages (lazy-loaded, wrapped in AppShell)
const OperationsDashboard = lazy(() => import("./pages/OperationsDashboard"));
const NewInspectionPage = lazy(() => import("./pages/NewInspectionPage"));
const FindingsQueuePage = lazy(() => import("./pages/FindingsQueuePage"));
const CapaQueuePage = lazy(() => import("./pages/CapaQueuePage"));
const AnalyticsDashboardPage = lazy(() => import("./pages/AnalyticsDashboardPage"));
const PilotAnalyticsDashboard = lazy(() => import("./pages/PilotAnalyticsDashboard"));
const EnterpriseDashboard = lazy(() => import("./pages/EnterpriseDashboard"));
const CommercialConsole = lazy(() => import("./pages/CommercialConsole"));
const GrowthConsole = lazy(() => import("./pages/GrowthConsole"));
const AccreditationConsole = lazy(() => import("./pages/AccreditationConsole"));
const NetworkIntelligenceConsole = lazy(() => import("./pages/NetworkIntelligenceConsole"));
const AutonomousOperationsConsole = lazy(() => import("./pages/AutonomousOperationsConsole"));
const GlobalIntelligenceConsole = lazy(() => import("./pages/GlobalIntelligenceConsole"));
const GlobalStandardsConsole = lazy(() => import("./pages/GlobalStandardsConsole"));
const GlobalInfrastructureConsole = lazy(() => import("./pages/GlobalInfrastructureConsole"));
const ManufacturerBaselinesPage = lazy(() => import("./pages/ManufacturerBaselinesPage"));
const BaselineReviewPage = lazy(() => import("./pages/BaselineReviewPage"));
const VendorBaselinePortalPage = lazy(() => import("./pages/VendorBaselinePortalPage"));
const IntakeHistoryPage = lazy(() => import("./pages/IntakeHistoryPage"));

// Legacy dashboard kept at /legacy for reference
const DashboardApp = lazy(() => import("./pages/DashboardApp"));
const LoginPage = lazy(() => import("./pages/LoginPage"));

function PageLoader() {
  return (
    <div className="flex h-64 items-center justify-center gap-3 text-slate-500">
      <Spinner className="h-5 w-5" />
      <span className="text-sm">Loading…</span>
    </div>
  );
}

class ErrorBoundary extends React.Component<
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
        <div className="p-8 text-center">
          <h2 className="text-lg font-semibold text-red-700 mb-2">Something went wrong</h2>
          <p className="text-sm text-slate-600 mb-4">{this.state.error.message}</p>
          <button
            className="text-sm text-blue-600 hover:underline"
            onClick={() => this.setState({ error: null })}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ErrorBoundary>
          <Routes>
            {/* Login — rendered outside AppShell (no nav) */}
            <Route
              path="/login"
              element={
                <Suspense fallback={<PageLoader />}>
                  <LoginPage />
                </Suspense>
              }
            />
            {/* All app routes live inside the AppShell */}
            <Route
              path="/*"
              element={
                <AppShell>
                  <Suspense fallback={<PageLoader />}>
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/vendor-intake" element={<VendorIntake />} />
                      <Route path="/operations" element={<OperationsDashboard />} />
                      <Route path="/inspection/new" element={<NewInspectionPage />} />
                      <Route path="/findings" element={<FindingsQueuePage />} />
                      <Route path="/capa" element={<CapaQueuePage />} />
                      <Route path="/analytics" element={<AnalyticsDashboardPage />} />
                      <Route path="/manufacturer-baselines" element={<ManufacturerBaselinesPage />} />
                      <Route path="/baseline-review" element={<BaselineReviewPage />} />
                      <Route path="/vendor-baseline-portal" element={<VendorBaselinePortalPage />} />
                      <Route path="/intake-history" element={<IntakeHistoryPage />} />
                      <Route path="/pilot-analytics" element={<PilotAnalyticsDashboard />} />
                      <Route path="/enterprise" element={<EnterpriseDashboard />} />
                      <Route path="/commercial" element={<CommercialConsole />} />
                      <Route path="/growth" element={<GrowthConsole />} />
                      <Route path="/accreditation" element={<AccreditationConsole />} />
                      <Route path="/network-intelligence" element={<NetworkIntelligenceConsole />} />
                      <Route path="/autonomous-operations" element={<AutonomousOperationsConsole />} />
                      <Route path="/global-intelligence" element={<GlobalIntelligenceConsole />} />
                      <Route path="/global-standards" element={<GlobalStandardsConsole />} />
                      <Route path="/infrastructure" element={<GlobalInfrastructureConsole />} />
                      <Route path="/legacy" element={<DashboardApp />} />
                      <Route
                        path="*"
                        element={
                          <div className="text-center py-16">
                            <p className="text-slate-500 text-sm">Page not found</p>
                          </div>
                        }
                      />
                    </Routes>
                  </Suspense>
                </AppShell>
              }
            />
          </Routes>
        </ErrorBoundary>
      </BrowserRouter>
    </AuthProvider>
  );
}

const root = document.getElementById("root");
if (!root) throw new Error("Missing root element");
ReactDOM.createRoot(root).render(<App />);
