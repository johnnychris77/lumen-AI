/**
 * v5.2 — LumenAI Network: Project GuardianX — AI Assurance Center.
 *
 * Frontend route `/ai-assurance`, API prefix `/api/guardianx`.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const TABS = [
  "AI Models", "Explainability", "Audit Replay", "Risk Registry",
  "Governance Workflow", "Compliance Mapping", "Evidence Ledger", "Trust Score", "Reports",
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

function Json({ data }: { data: unknown }) {
  return <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(data, null, 2)}</pre>;
}

export default function AIAssuranceCenter() {
  const [activeTab, setActiveTab] = useState<Tab>("AI Models");

  const [assuranceSummary, setAssuranceSummary] = useState<Record<string, unknown> | null>(null);
  const [models, setModels] = useState<Record<string, unknown>[] | null>(null);
  const [riskSummary, setRiskSummary] = useState<Record<string, unknown> | null>(null);
  const [complianceMatrix, setComplianceMatrix] = useState<Record<string, unknown> | null>(null);
  const [governanceReport, setGovernanceReport] = useState<Record<string, unknown> | null>(null);
  const [executiveReport, setExecutiveReport] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (activeTab === "AI Models") {
      api.get("/api/guardianx/assurance-center/summary").then(setAssuranceSummary).catch(() => {});
      api.get("/api/guardianx/models/governance").then((r: Record<string, unknown>) => setModels(r.models as Record<string, unknown>[])).catch(() => {});
    }
    if (activeTab === "Risk Registry") {
      api.get("/api/guardianx/risks/summary").then(setRiskSummary).catch(() => {});
    }
    if (activeTab === "Compliance Mapping") {
      api.get("/api/guardianx/compliance-mappings/traceability-matrix").then(setComplianceMatrix).catch(() => {});
    }
    if (activeTab === "Governance Workflow") {
      api.get("/api/guardianx/reports/governance").then(setGovernanceReport).catch(() => {});
    }
    if (activeTab === "Reports") {
      api.get("/api/guardianx/reports/executive").then(setExecutiveReport).catch(() => {});
    }
  }, [activeTab]);

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">AI Assurance Center</h1>
      <p className="text-xs text-slate-400">
        End-to-end governance, explainability, auditability, validation, and compliance traceability for every
        AI capability in LumenAI. Every score, explanation, and risk entry requires human review and is never a
        substitute for clinical judgment or a claim of regulatory certification.
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

      {activeTab === "AI Models" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Assurance Summary">{assuranceSummary && <Json data={assuranceSummary} />}</Section>
          <Section title="Model Governance Records">
            {models?.map((m) => (
              <div key={String(m.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
                <span className="font-medium">{String(m.name)}</span> — v{String(m.version)} (
                {String(m.validation_status)}, cert: {String(m.certification_status)}, gov: {String(m.governance_status)})
              </div>
            ))}
          </Section>
        </div>
      )}

      {activeTab === "Explainability" && (
        <Section title="Explainability Dashboard">
          <p className="text-xs text-slate-400">
            Look up an AI output's explanation by source type and id: input summary, evidence used, knowledge
            sources, Digital Twin context, clinical rules applied, confidence, alternative explanations, and
            human overrides. Query via GET /api/guardianx/explainability?source_type=...&source_id=...
          </p>
        </Section>
      )}

      {activeTab === "Audit Replay" && (
        <Section title="Audit Replay">
          <p className="text-xs text-slate-400">
            Replay an entire inspection, workflow execution, rule, or recommendation — including model version,
            rules, knowledge, evidence, and timeline — via /api/guardianx/audit-replay/*.
          </p>
        </Section>
      )}

      {activeTab === "Risk Registry" && (
        <Section title="AI Risk Registry Summary">{riskSummary && <Json data={riskSummary} />}</Section>
      )}

      {activeTab === "Governance Workflow" && (
        <Section title="Governance Report — Clinical Review Board, AI Governance Committee, Quality Leadership, Security, Compliance">
          {governanceReport && <Json data={governanceReport} />}
        </Section>
      )}

      {activeTab === "Compliance Mapping" && (
        <Section title="Compliance Traceability Matrix">{complianceMatrix && <Json data={complianceMatrix} />}</Section>
      )}

      {activeTab === "Evidence Ledger" && (
        <Section title="Evidence Ledger">
          <p className="text-xs text-slate-400">
            Append-only: every recommendation's evidence, knowledge/model/workflow version, reviewer, and digital
            signature. Nothing is ever deleted. Query via /api/guardianx/evidence?source_type=...&source_id=...
          </p>
        </Section>
      )}

      {activeTab === "Trust Score" && (
        <Section title="Trust Score">
          <p className="text-xs text-slate-400">
            Platform, Model, Knowledge, Workflow, and Digital Twin Trust Scores, each with a documented
            component breakdown for why it was calculated. Compute via POST /api/guardianx/trust/*/compute.
          </p>
        </Section>
      )}

      {activeTab === "Reports" && (
        <Section title="Executive AI Assurance Report">{executiveReport && <Json data={executiveReport} />}</Section>
      )}
    </div>
  );
}
