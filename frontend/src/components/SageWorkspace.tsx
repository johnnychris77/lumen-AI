/**
 * LumenAI AI Specialist — Project Sage: SPD Education, Competency &
 * Workforce Intelligence.
 *
 * Frontend route `/sage`, API prefix `/api/sage`. Sage does not discipline
 * employees, independently determine competency, or replace supervisor and
 * educator judgment -- every recommendation here requires human approval
 * before assignment.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Json = Record<string, unknown>;

const TABS = [
  "Workspace", "Knowledge Gaps", "Learning Plans", "Microlearning",
  "Assessments", "Image Library", "Executive Summary",
] as const;
type Tab = (typeof TABS)[number];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {children}
    </div>
  );
}

function JsonView({ data }: { data: unknown }) {
  return <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(data, null, 2)}</pre>;
}

export default function SageWorkspace() {
  const [activeTab, setActiveTab] = useState<Tab>("Workspace");

  const [workspace, setWorkspace] = useState<Json | null>(null);
  const [gaps, setGaps] = useState<Json[] | null>(null);
  const [plans, setPlans] = useState<Json[] | null>(null);
  const [modules, setModules] = useState<Json[] | null>(null);
  const [assessments, setAssessments] = useState<Json[] | null>(null);
  const [images, setImages] = useState<Json[] | null>(null);
  const [executiveSummary, setExecutiveSummary] = useState<Json | null>(null);

  const [gapTechnician, setGapTechnician] = useState("");

  useEffect(() => {
    if (activeTab === "Workspace") api.get("/api/sage/workspace").then(setWorkspace).catch(() => {});
    if (activeTab === "Knowledge Gaps") api.get("/api/sage/gaps").then((r: Json) => setGaps(r.gaps as Json[])).catch(() => {});
    if (activeTab === "Learning Plans") api.get("/api/sage/learning-plans").then((r: Json) => setPlans(r.plans as Json[])).catch(() => {});
    if (activeTab === "Microlearning") api.get("/api/sage/microlearning").then((r: Json) => setModules(r.modules as Json[])).catch(() => {});
    if (activeTab === "Assessments") api.get("/api/sage/assessments").then((r: Json) => setAssessments(r.assessments as Json[])).catch(() => {});
    if (activeTab === "Image Library") api.get("/api/sage/images").then((r: Json) => setImages(r.images as Json[])).catch(() => {});
    if (activeTab === "Executive Summary") api.get("/api/sage/executive-summary").then(setExecutiveSummary).catch(() => {});
  }, [activeTab]);

  function runGapDetection() {
    if (!gapTechnician) return;
    api
      .post(`/api/sage/gaps/detect/${encodeURIComponent(gapTechnician)}`, {})
      .then((r: Json) => setGaps(r.gaps as Json[]))
      .catch(() => {});
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Sage — Education, Competency &amp; Workforce Intelligence</h1>
      <p className="text-xs text-slate-400">
        Sage supports technicians, supervisors, educators, and SPD leaders. It does not discipline employees,
        independently determine competency, or replace supervisor and educator judgment. Every recommendation
        is evidence-based, confidence-scored, non-punitive, and requires human approval before assignment.
      </p>

      <div className="flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`rounded px-3 py-1 text-sm ${activeTab === t ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {activeTab === "Workspace" && (
        <Section title="Recommended Plans, Overdue Competencies &amp; Recurring Gaps">
          {workspace && <JsonView data={workspace} />}
        </Section>
      )}

      {activeTab === "Knowledge Gaps" && (
        <Section title="Detected Knowledge Gaps (non-punitive, human-reviewed)">
          <div className="mb-3 flex gap-2">
            <input
              className="rounded border border-slate-300 px-2 py-1 text-sm"
              placeholder="technician email"
              value={gapTechnician}
              onChange={(e) => setGapTechnician(e.target.value)}
            />
            <button className="rounded bg-indigo-600 px-3 py-1 text-sm text-white" onClick={runGapDetection}>
              Run Gap Detection
            </button>
          </div>
          {gaps && <JsonView data={gaps} />}
        </Section>
      )}

      {activeTab === "Learning Plans" && (
        <Section title="Adaptive Learning Plans">
          {plans && <JsonView data={plans} />}
        </Section>
      )}

      {activeTab === "Microlearning" && (
        <Section title="Approved Microlearning Modules">
          {modules && <JsonView data={modules} />}
        </Section>
      )}

      {activeTab === "Assessments" && (
        <Section title="Competency Assessments (advisory until validated)">
          {assessments && <JsonView data={assessments} />}
        </Section>
      )}

      {activeTab === "Image Library" && (
        <Section title="Image-Based Learning Library (PHI-cleared only)">
          {images && <JsonView data={images} />}
        </Section>
      )}

      {activeTab === "Executive Summary" && (
        <Section title="Executive Workforce Intelligence (aggregate only, no individual ranking)">
          {executiveSummary && <JsonView data={executiveSummary} />}
        </Section>
      )}
    </div>
  );
}
