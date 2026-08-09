import { Routes, Route } from "react-router-dom";
import { MarketingLayout } from "./MarketingLayout";
import {
  HomePage,
  ProblemPage,
  WorkflowPage,
  PlatformPage,
  ArchitecturePage,
  SecurityPage,
  UseCasesPage,
  ExecutivePage,
  VideoPage,
  AboutPage,
  ContactPage,
  NotFoundPage,
} from "./pages";

/**
 * Public marketing site. Mounted at `/site/*` in the app router, OUTSIDE the
 * authenticated AppShell and auth guard. Self-contained: no production API
 * calls, no shared app state — a marketing/education/demonstration layer only.
 */
export default function MarketingApp() {
  return (
    <Routes>
      <Route element={<MarketingLayout />}>
        <Route index element={<HomePage />} />
        <Route path="problem" element={<ProblemPage />} />
        <Route path="workflow" element={<WorkflowPage />} />
        <Route path="platform" element={<PlatformPage />} />
        <Route path="architecture" element={<ArchitecturePage />} />
        <Route path="security" element={<SecurityPage />} />
        <Route path="use-cases" element={<UseCasesPage />} />
        <Route path="executive" element={<ExecutivePage />} />
        <Route path="video" element={<VideoPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="contact" element={<ContactPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
