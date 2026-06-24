import "./index.css";
import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { AuthProvider } from "@/lib/auth";
import { NotificationProvider } from "@/lib/notifications";
import { Spinner } from "@/components/ui/spinner";

// ─── Global error recovery ───────────────────────────────────────────────────
// Chunk-load failures (e.g. after a deploy re-hashes asset filenames) cause a
// white page because the browser cached the old chunk URL which is now a 404.
// Reload once per session to pick up the new asset manifest.
window.addEventListener("error", (e) => {
  const src = (e.target as HTMLScriptElement | null)?.src ?? "";
  if (src.includes("/assets/") && !sessionStorage.getItem("chunk_reload")) {
    sessionStorage.setItem("chunk_reload", "1");
    window.location.reload();
  }
}, true); // capture phase so it fires before React's own handlers

// Promise-based dynamic import failures (React.lazy) surface as
// unhandledrejection events — handle them the same way.
window.addEventListener("unhandledrejection", (e) => {
  const msg = String(e.reason?.message ?? e.reason ?? "");
  if (
    (msg.includes("Failed to fetch dynamically imported module") ||
      msg.includes("Importing a module script failed")) &&
    !sessionStorage.getItem("chunk_reload")
  ) {
    sessionStorage.setItem("chunk_reload", "1");
    window.location.reload();
  }
});

// Non-lazy pages (small, critical path)
import Dashboard from "./pages/Dashboard";
import VendorIntake from "./pages/VendorIntake";

// Lazy-loaded pages
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
const VendorIntelligencePage = lazy(() => import("./pages/VendorIntelligencePage"));
const DigitalTwinPage = lazy(() => import("./pages/DigitalTwinPage"));
const QualityIntelligencePage = lazy(() => import("./pages/QualityIntelligencePage"));
const DemoImageLibraryPage = lazy(() => import("./pages/DemoImageLibraryPage"));
const BaselineImageUploadPage = lazy(() => import("./pages/BaselineImageUploadPage"));
const InspectionImageUploadPage = lazy(() => import("./pages/InspectionImageUploadPage"));
const ManufacturerBaselinesPage = lazy(() => import("./pages/ManufacturerBaselinesPage"));
const BaselineReviewPage = lazy(() => import("./pages/BaselineReviewPage"));
const VendorBaselinePortalPage = lazy(() => import("./pages/VendorBaselinePortalPage"));
const IntakeHistoryPage = lazy(() => import("./pages/IntakeHistoryPage"));
const BaselineLibraryPage = lazy(() => import("./pages/BaselineLibraryPage"));
const InstrumentPassportPage = lazy(() => import("./pages/InstrumentPassportPage"));
const AuditEvidencePage = lazy(() => import("./pages/AuditEvidencePage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const ExecutiveCommandCenterPage = lazy(() => import("./pages/ExecutiveCommandCenterPage"));
const GlobalRegistryPage = lazy(() => import("./pages/GlobalRegistryPage"));
const SurgicalReadinessDashboard = lazy(() => import("./pages/SurgicalReadinessDashboard"));
const NetworkDashboardPage = lazy(() => import("./pages/NetworkDashboardPage"));
const ImageQualityPage = lazy(() => import("./pages/ImageQualityPage"));
const GoLiveCenterPage = lazy(() => import("./pages/GoLiveCenterPage"));
const ImplementationTrackerPage = lazy(() => import("./pages/ImplementationTrackerPage"));
const TrainingCompliancePage = lazy(() => import("./pages/TrainingCompliancePage"));
const BaselineReadinessPage = lazy(() => import("./pages/BaselineReadinessPage"));
const InspectionReadinessPage = lazy(() => import("./pages/InspectionReadinessPage"));
const ExecutiveAdoptionPage = lazy(() => import("./pages/ExecutiveAdoptionPage"));
const ValueRealizationPage = lazy(() => import("./pages/ValueRealizationPage"));
const CustomerOnboardingPage = lazy(() => import("./pages/CustomerOnboardingPage"));
const CustomerSuccessDashboard = lazy(() => import("./pages/CustomerSuccessDashboard"));
const DeploymentReadinessPage = lazy(() => import("./pages/DeploymentReadinessPage"));
const TrainingCenterPage = lazy(() => import("./pages/TrainingCenterPage"));
const ROICenterPage = lazy(() => import("./pages/ROICenterPage"));
const SubscriptionReadinessPage = lazy(() => import("./pages/SubscriptionReadinessPage"));
const DashboardApp = lazy(() => import("./pages/DashboardApp"));
const LoginPage = lazy(() => import("./pages/LoginPage"));

// ─── Loading spinner shown during lazy chunk loads ────────────────────────────

function PageLoader() {
  return (
    <div className="flex h-64 items-center justify-center gap-3 text-slate-500">
      <Spinner className="h-5 w-5" />
      <span className="text-sm">Loading…</span>
    </div>
  );
}

// ─── Top-level error boundary — catches crashes in ANY part of the tree ───────

class RootErrorBoundary extends React.Component<
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
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Log to console in all environments so developers can diagnose
    console.error("[LumenAI] Uncaught render error:", error, info.componentStack);
  }
  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 p-8">
          <div className="max-w-md w-full text-center space-y-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-red-100 mx-auto">
              <span className="text-3xl">⚠</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900">Something went wrong loading LumenAI</h1>
            <p className="text-sm text-slate-600">{this.state.error.message}</p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
                onClick={() => { this.setState({ error: null }); window.location.href = "/"; }}
              >
                Back to Dashboard
              </button>
              <button
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
                onClick={() => window.location.reload()}
              >
                Reload page
              </button>
            </div>
            <p className="text-xs text-slate-400">
              If this keeps happening, check the browser console for details.
            </p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ─── Per-page error boundary — catches chunk load failures and page crashes ───

class PageErrorBoundary extends React.Component<
  { children: React.ReactNode; pageName?: string; locationKey?: string },
  { error: Error | null; locationKey?: string }
> {
  constructor(props: { children: React.ReactNode; pageName?: string; locationKey?: string }) {
    super(props);
    this.state = { error: null, locationKey: props.locationKey };
  }
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  // Auto-clear error when user navigates to a different route
  static getDerivedStateFromProps(
    props: { locationKey?: string },
    state: { error: Error | null; locationKey?: string }
  ) {
    if (state.error && props.locationKey !== state.locationKey) {
      return { error: null, locationKey: props.locationKey };
    }
    return { locationKey: props.locationKey };
  }
  componentDidCatch(error: Error) {
    console.error(`[LumenAI] Page error${this.props.pageName ? ` (${this.props.pageName})` : ""}:`, error);
  }
  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center py-20 gap-4 text-center px-4">
          <p className="text-slate-600 font-medium">This page encountered an error.</p>
          <p className="text-sm text-slate-400">{this.state.error.message}</p>
          <div className="flex gap-3">
            <button
              className="text-sm text-blue-600 underline"
              onClick={() => this.setState({ error: null })}
            >
              Try again
            </button>
            <Link to="/" className="text-sm text-slate-500 underline">
              Return to Dashboard
            </Link>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ─── Wrap a lazy page with both Suspense and a per-page error boundary ────────
// locationKey resets the error boundary on route change so stale errors don't
// linger when the user navigates away and back.

function Page({ children, name }: { children: React.ReactNode; name?: string }) {
  const loc = useLocation();
  return (
    <PageErrorBoundary pageName={name} locationKey={loc.key}>
      <Suspense fallback={<PageLoader />}>
        {children}
      </Suspense>
    </PageErrorBoundary>
  );
}

// ─── Not Found page ───────────────────────────────────────────────────────────

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4 text-center px-4">
      <p className="text-4xl font-bold text-slate-300">404</p>
      <p className="text-slate-600 font-medium">Page not found</p>
      <p className="text-sm text-slate-400">The page you're looking for doesn't exist or has moved.</p>
      <Link to="/" className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
        Back to Dashboard
      </Link>
    </div>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────

function App() {
  return (
    // RootErrorBoundary is OUTERMOST — catches crashes in AuthProvider,
    // NotificationProvider, or any component below
    <RootErrorBoundary>
      <AuthProvider>
        <NotificationProvider>
          <BrowserRouter>
            <Routes>
              {/* Login — no AppShell */}
              <Route
                path="/login"
                element={
                  <Page name="Login">
                    <LoginPage />
                  </Page>
                }
              />

              {/* All app routes inside AppShell */}
              <Route
                path="/*"
                element={
                  <AppShell>
                    <Routes>
                      <Route path="/" element={<Page name="Dashboard"><Dashboard /></Page>} />
                      <Route path="/vendor-intake" element={<Page name="VendorIntake"><VendorIntake /></Page>} />
                      <Route path="/operations" element={<Page name="Operations"><OperationsDashboard /></Page>} />
                      <Route path="/inspection/new" element={<Page name="NewInspection"><NewInspectionPage /></Page>} />
                      <Route path="/findings" element={<Page name="Findings"><FindingsQueuePage /></Page>} />
                      <Route path="/capa" element={<Page name="CAPA"><CapaQueuePage /></Page>} />
                      <Route path="/analytics" element={<Page name="Analytics"><AnalyticsDashboardPage /></Page>} />
                      <Route path="/manufacturer-baselines" element={<Page name="ManufacturerBaselines"><ManufacturerBaselinesPage /></Page>} />
                      <Route path="/baseline-review" element={<Page name="BaselineReview"><BaselineReviewPage /></Page>} />
                      <Route path="/vendor-baseline-portal" element={<Page name="VendorBaselines"><VendorBaselinePortalPage /></Page>} />
                      <Route path="/intake-history" element={<Page name="IntakeHistory"><IntakeHistoryPage /></Page>} />
                      <Route path="/pilot-analytics" element={<Page name="PilotAnalytics"><PilotAnalyticsDashboard /></Page>} />
                      <Route path="/enterprise" element={<Page name="Enterprise"><EnterpriseDashboard /></Page>} />
                      <Route path="/commercial" element={<Page name="Commercial"><CommercialConsole /></Page>} />
                      <Route path="/growth" element={<Page name="Growth"><GrowthConsole /></Page>} />
                      <Route path="/accreditation" element={<Page name="Accreditation"><AccreditationConsole /></Page>} />
                      <Route path="/network-intelligence" element={<Page name="NetworkIntelligence"><NetworkIntelligenceConsole /></Page>} />
                      <Route path="/autonomous-operations" element={<Page name="AutonomousOps"><AutonomousOperationsConsole /></Page>} />
                      <Route path="/global-intelligence" element={<Page name="GlobalIntelligence"><GlobalIntelligenceConsole /></Page>} />
                      <Route path="/global-standards" element={<Page name="GlobalStandards"><GlobalStandardsConsole /></Page>} />
                      <Route path="/infrastructure" element={<Page name="Infrastructure"><GlobalInfrastructureConsole /></Page>} />
                      <Route path="/vendor-intelligence" element={<Page name="VendorIntelligence"><VendorIntelligencePage /></Page>} />
                      <Route path="/digital-twin" element={<Page name="DigitalTwin"><DigitalTwinPage /></Page>} />
                      <Route path="/quality-intelligence" element={<Page name="QualityIntelligence"><QualityIntelligencePage /></Page>} />
                      <Route path="/baseline-library" element={<Page name="BaselineLibrary"><BaselineLibraryPage /></Page>} />
                      <Route path="/instrument-passport" element={<Page name="InstrumentPassport"><InstrumentPassportPage /></Page>} />
                      <Route path="/executive-command-center" element={<Page name="CommandCenter"><ExecutiveCommandCenterPage /></Page>} />
                      <Route path="/global-registry" element={<Page name="GlobalRegistry"><GlobalRegistryPage /></Page>} />
                      <Route path="/surgical-readiness" element={<Page name="SurgicalReadiness"><SurgicalReadinessDashboard /></Page>} />
                      <Route path="/audit-evidence" element={<Page name="AuditEvidence"><AuditEvidencePage /></Page>} />
                      <Route path="/users" element={<Page name="Users"><UsersPage /></Page>} />
                      <Route path="/roles" element={<Page name="Roles"><RolesPage /></Page>} />
                      <Route path="/settings" element={<Page name="Settings"><SettingsPage /></Page>} />
                      <Route path="/demo-image-library" element={<Page name="DemoImageLibrary"><DemoImageLibraryPage /></Page>} />
                      <Route path="/baseline-image-upload" element={<Page name="BaselineImageUpload"><BaselineImageUploadPage /></Page>} />
                      <Route path="/inspection-image-upload" element={<Page name="InspectionImageUpload"><InspectionImageUploadPage /></Page>} />
                      <Route path="/network-dashboard" element={<Page name="NetworkDashboard"><NetworkDashboardPage /></Page>} />
                      <Route path="/image-quality" element={<Page name="ImageQuality"><ImageQualityPage /></Page>} />
                      <Route path="/go-live-center" element={<Page name="GoLiveCenter"><GoLiveCenterPage /></Page>} />
                      <Route path="/implementation-tracker" element={<Page name="ImplementationTracker"><ImplementationTrackerPage /></Page>} />
                      <Route path="/training-compliance" element={<Page name="TrainingCompliance"><TrainingCompliancePage /></Page>} />
                      <Route path="/baseline-readiness" element={<Page name="BaselineReadiness"><BaselineReadinessPage /></Page>} />
                      <Route path="/inspection-readiness" element={<Page name="InspectionReadiness"><InspectionReadinessPage /></Page>} />
                      <Route path="/executive-adoption" element={<Page name="ExecutiveAdoption"><ExecutiveAdoptionPage /></Page>} />
                      <Route path="/value-realization" element={<Page name="ValueRealization"><ValueRealizationPage /></Page>} />
                      <Route path="/customer-onboarding" element={<Page name="CustomerOnboarding"><CustomerOnboardingPage /></Page>} />
                      <Route path="/customer-success" element={<Page name="CustomerSuccess"><CustomerSuccessDashboard /></Page>} />
                      <Route path="/deployment-readiness" element={<Page name="DeploymentReadiness"><DeploymentReadinessPage /></Page>} />
                      <Route path="/training-center" element={<Page name="TrainingCenter"><TrainingCenterPage /></Page>} />
                      <Route path="/roi-center" element={<Page name="ROICenter"><ROICenterPage /></Page>} />
                      <Route path="/subscription-readiness" element={<Page name="SubscriptionReadiness"><SubscriptionReadinessPage /></Page>} />
                      <Route path="/legacy" element={<Page name="Legacy"><DashboardApp /></Page>} />
                      <Route path="*" element={<NotFound />} />
                    </Routes>
                  </AppShell>
                }
              />
            </Routes>
          </BrowserRouter>
        </NotificationProvider>
      </AuthProvider>
    </RootErrorBoundary>
  );
}

const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element — check index.html");
ReactDOM.createRoot(root).render(<App />);
