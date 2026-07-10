/**
 * v4.7 — LumenAI OS: Project Apollo — Autonomous Clinical Quality
 * Management System (CQMS).
 *
 * Frontend route `/quality`, API prefix `/api/apollo` — deliberately
 * distinct from the pre-existing `/api/quality` (owned by
 * `quality_dashboard.py`) and the already-taken `/quality-command-center`,
 * `/quality-intelligence`, `/quality-dashboard` pages (see
 * `app/models/apollo_quality.py` for the full naming-disambiguation note).
 * Positioned as the unifying Quality Management Center front door, not a
 * fourth competing quality page.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const TABS = [
  "Quality Dashboard", "CAPA", "Audit Center", "Competencies", "Policies",
  "Standards", "Education", "Evidence", "Improvement Projects",
] as const;
type Tab = (typeof TABS)[number];

const AUDIT_PACKAGE_TYPES = ["joint_commission", "aami", "aami_st91", "fda", "cms", "aorn", "dnv", "internal", "vendor", "full"];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {children}
    </div>
  );
}

function Json({ data }: { data: unknown }) {
  return <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(data, null, 2)}</pre>;
}

export default function QualityManagementCenter() {
  const [activeTab, setActiveTab] = useState<Tab>("Quality Dashboard");
  const [executiveDashboard, setExecutiveDashboard] = useState<Record<string, unknown> | null>(null);

  const [capaSummary, setCapaSummary] = useState<Record<string, unknown> | null>(null);
  const [complaintForm, setComplaintForm] = useState({ source: "", description: "", severity: "medium", instrument_type: "" });

  const [auditSummary, setAuditSummary] = useState<Record<string, unknown> | null>(null);
  const [auditPackageType, setAuditPackageType] = useState("joint_commission");
  const [generatedAudit, setGeneratedAudit] = useState<Record<string, unknown> | null>(null);

  const [competencySummary, setCompetencySummary] = useState<Record<string, unknown> | null>(null);

  const [policies, setPolicies] = useState<Record<string, unknown>[] | null>(null);
  const [policyForm, setPolicyForm] = useState({ title: "", owner: "" });

  const [standardsLibrary, setStandardsLibrary] = useState<Record<string, unknown> | null>(null);

  const [rcaSummary, setRcaSummary] = useState<Record<string, unknown> | null>(null);

  const [improvementProjects, setImprovementProjects] = useState<Record<string, unknown>[] | null>(null);
  const [portfolioSummary, setPortfolioSummary] = useState<Record<string, unknown> | null>(null);
  const [projectForm, setProjectForm] = useState({ initiative: "", owner: "", methodology: "pi" });

  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/api/apollo/executive-dashboard").then(setExecutiveDashboard).catch(() => {});
  }, []);

  useEffect(() => {
    if (activeTab === "CAPA") api.get("/api/apollo/capa/summary").then(setCapaSummary).catch(() => {});
    if (activeTab === "Audit Center") api.get("/api/apollo/audit/summary").then(setAuditSummary).catch(() => {});
    if (activeTab === "Competencies") api.get("/api/apollo/competency/summary").then(setCompetencySummary).catch(() => {});
    if (activeTab === "Policies") api.get("/api/apollo/policies").then((r: Record<string, unknown>) => setPolicies(r.policies as Record<string, unknown>[])).catch(() => {});
    if (activeTab === "Standards") api.get("/api/apollo/standards/library").then(setStandardsLibrary).catch(() => {});
    if (activeTab === "Evidence") api.get("/api/apollo/rca/summary").then(setRcaSummary).catch(() => {});
    if (activeTab === "Improvement Projects") {
      api.get("/api/apollo/improvement-projects").then((r: Record<string, unknown>) => setImprovementProjects(r.projects as Record<string, unknown>[])).catch(() => {});
      api.get("/api/apollo/improvement-projects/summary").then(setPortfolioSummary).catch(() => {});
    }
  }, [activeTab]);

  async function submitComplaint() {
    if (!complaintForm.description.trim()) return;
    await api.post("/api/apollo/capa/complaints", complaintForm);
    setComplaintForm({ source: "", description: "", severity: "medium", instrument_type: "" });
    api.get("/api/apollo/capa/summary").then(setCapaSummary).catch(() => {});
  }

  async function generateAudit() {
    try {
      const res = await api.post<Record<string, unknown>>("/api/apollo/audit/generate", { package_type: auditPackageType });
      setGeneratedAudit(res);
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }

  async function createPolicy() {
    if (!policyForm.title.trim()) return;
    await api.post("/api/apollo/policies", policyForm);
    setPolicyForm({ title: "", owner: "" });
    api.get("/api/apollo/policies").then((r: Record<string, unknown>) => setPolicies(r.policies as Record<string, unknown>[])).catch(() => {});
  }

  async function createProject() {
    if (!projectForm.initiative.trim()) return;
    await api.post("/api/apollo/improvement-projects", projectForm);
    setProjectForm({ initiative: "", owner: "", methodology: "pi" });
    api.get("/api/apollo/improvement-projects").then((r: Record<string, unknown>) => setImprovementProjects(r.projects as Record<string, unknown>[])).catch(() => {});
    api.get("/api/apollo/improvement-projects/summary").then(setPortfolioSummary).catch(() => {});
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Quality Management Center</h1>
      <p className="text-xs text-slate-400">
        Composes CAPA, Root Cause Intelligence, Audit Center, Competency Center, Policy Intelligence, Standards Library,
        Continuous Improvement, and the Quality Digital Twin into one unified Clinical Quality Management System.
        Human oversight remains mandatory for all quality decisions.
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

      {activeTab === "Quality Dashboard" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {executiveDashboard && (
            <>
              <Section title="Quality Maturity Index">
                <p className="text-3xl font-bold text-indigo-600">{String(executiveDashboard.quality_maturity_index ?? "—")}</p>
                <Json data={executiveDashboard.quality_maturity_index_weights} />
              </Section>
              <Section title="Compliance / Audit Readiness"><Json data={executiveDashboard.audit_readiness} /></Section>
              <Section title="Open CAPAs"><Json data={{ open_capas: executiveDashboard.open_capas, closure_rate_pct: executiveDashboard.capa_closure_rate_pct }} /></Section>
              <Section title="Competency Status"><Json data={executiveDashboard.competency_status} /></Section>
              <Section title="High-Risk Policies / Upcoming Reviews">
                <Json data={{ high_risk: executiveDashboard.high_risk_policies, upcoming: executiveDashboard.upcoming_reviews }} />
              </Section>
              <Section title="Continuous Improvement"><Json data={executiveDashboard.continuous_improvement} /></Section>
            </>
          )}
        </div>
      )}

      {activeTab === "CAPA" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="CAPA Engine Summary">{capaSummary && <Json data={capaSummary} />}</Section>
          <Section title="Log a Customer Complaint (CAPA trigger source)">
            <div className="space-y-2 text-sm">
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Source" value={complaintForm.source}
                onChange={(e) => setComplaintForm({ ...complaintForm, source: e.target.value })} />
              <textarea className="w-full rounded border border-slate-300 p-2" placeholder="Description" value={complaintForm.description}
                onChange={(e) => setComplaintForm({ ...complaintForm, description: e.target.value })} />
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Instrument type" value={complaintForm.instrument_type}
                onChange={(e) => setComplaintForm({ ...complaintForm, instrument_type: e.target.value })} />
              <select className="w-full rounded border border-slate-300 p-2" value={complaintForm.severity}
                onChange={(e) => setComplaintForm({ ...complaintForm, severity: e.target.value })}>
                <option value="low">low</option><option value="medium">medium</option><option value="high">high</option>
              </select>
              <button className="rounded bg-indigo-600 px-4 py-2 text-white" onClick={submitComplaint}>Submit Complaint</button>
            </div>
          </Section>
        </div>
      )}

      {activeTab === "Audit Center" && (
        <Section title="Audit Center">
          {auditSummary && <Json data={auditSummary} />}
          <div className="mt-3 flex gap-2">
            <select className="rounded border border-slate-300 p-1 text-sm" value={auditPackageType} onChange={(e) => setAuditPackageType(e.target.value)}>
              {AUDIT_PACKAGE_TYPES.map((p) => <option key={p} value={p}>{p.replace(/_/g, " ")}</option>)}
            </select>
            <button className="rounded bg-indigo-600 px-4 py-1 text-sm text-white" onClick={generateAudit}>Generate Audit Package</button>
          </div>
          {error && <p className="mt-2 text-xs text-amber-600">{error}</p>}
          {generatedAudit && <div className="mt-3"><Json data={generatedAudit} /></div>}
        </Section>
      )}

      {activeTab === "Competencies" && (
        <Section title="Competency Center">{competencySummary && <Json data={competencySummary} />}</Section>
      )}

      {activeTab === "Policies" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Quality Policies">
            {policies?.map((p) => (
              <div key={String(p.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
                <span className="font-medium">{String(p.title)}</span> — v{String(p.version)} ({String(p.status)})
              </div>
            ))}
          </Section>
          <Section title="Draft a New Policy">
            <div className="space-y-2 text-sm">
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Title" value={policyForm.title}
                onChange={(e) => setPolicyForm({ ...policyForm, title: e.target.value })} />
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Owner" value={policyForm.owner}
                onChange={(e) => setPolicyForm({ ...policyForm, owner: e.target.value })} />
              <button className="rounded bg-indigo-600 px-4 py-2 text-white" onClick={createPolicy}>Create Draft</button>
            </div>
          </Section>
        </div>
      )}

      {activeTab === "Standards" && (
        <Section title="Standards Knowledge Library">{standardsLibrary && <Json data={standardsLibrary} />}</Section>
      )}

      {activeTab === "Education" && (
        <Section title="Education">{competencySummary && <Json data={competencySummary.technicians} />}</Section>
      )}

      {activeTab === "Evidence" && (
        <Section title="Root Cause Intelligence — Pareto / Trend Analysis">{rcaSummary && <Json data={rcaSummary} />}</Section>
      )}

      {activeTab === "Improvement Projects" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Portfolio Summary">{portfolioSummary && <Json data={portfolioSummary} />}</Section>
          <Section title="Projects">
            {improvementProjects?.map((p) => (
              <div key={String(p.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
                <span className="font-medium">{String(p.initiative)}</span> — {String(p.methodology)} ({String(p.status)})
              </div>
            ))}
            <div className="mt-3 space-y-2 text-sm">
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Initiative" value={projectForm.initiative}
                onChange={(e) => setProjectForm({ ...projectForm, initiative: e.target.value })} />
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Owner" value={projectForm.owner}
                onChange={(e) => setProjectForm({ ...projectForm, owner: e.target.value })} />
              <select className="w-full rounded border border-slate-300 p-2" value={projectForm.methodology}
                onChange={(e) => setProjectForm({ ...projectForm, methodology: e.target.value })}>
                <option value="pi">PI</option><option value="lean">Lean</option><option value="six_sigma">Six Sigma</option>
                <option value="kaizen">Kaizen</option><option value="other">Other</option>
              </select>
              <button className="rounded bg-indigo-600 px-4 py-2 text-white" onClick={createProject}>Create Project</button>
            </div>
          </Section>
        </div>
      )}
    </div>
  );
}
