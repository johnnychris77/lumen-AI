/**
 * v5.1 — LumenAI Network: Project Olympus — Network Intelligence Center.
 *
 * Frontend route `/network`, API prefix `/api/olympus`.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const TABS = [
  "Directory", "Trust Network", "Intelligence Exchange", "Research Observatory",
  "AI Model Registry", "Certification Registry", "Innovation Marketplace", "Governance Council",
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

export default function NetworkIntelligenceCenter() {
  const [activeTab, setActiveTab] = useState<Tab>("Directory");

  const [directory, setDirectory] = useState<Record<string, unknown> | null>(null);
  const [participants, setParticipants] = useState<Record<string, unknown>[] | null>(null);
  const [leaderboard, setLeaderboard] = useState<Record<string, unknown>[] | null>(null);
  const [packages, setPackages] = useState<Record<string, unknown>[] | null>(null);
  const [observatory, setObservatory] = useState<Record<string, unknown> | null>(null);
  const [models, setModels] = useState<Record<string, unknown>[] | null>(null);
  const [certRegistry, setCertRegistry] = useState<Record<string, unknown> | null>(null);
  const [marketplace, setMarketplace] = useState<Record<string, unknown> | null>(null);
  const [cases, setCases] = useState<Record<string, unknown>[] | null>(null);
  const [councilSummary, setCouncilSummary] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (activeTab === "Directory") {
      api.get("/api/olympus/directory-summary").then(setDirectory).catch(() => {});
      api.get("/api/olympus/participants").then((r: Record<string, unknown>) => setParticipants(r.participants as Record<string, unknown>[])).catch(() => {});
    }
    if (activeTab === "Trust Network") {
      api.get("/api/olympus/trust/leaderboard").then((r: Record<string, unknown>) => setLeaderboard(r.leaderboard as Record<string, unknown>[])).catch(() => {});
    }
    if (activeTab === "Intelligence Exchange") {
      api.get("/api/olympus/exchange/packages").then((r: Record<string, unknown>) => setPackages(r.packages as Record<string, unknown>[])).catch(() => {});
    }
    if (activeTab === "Research Observatory") {
      api.get("/api/olympus/observatory/summary").then(setObservatory).catch(() => {});
    }
    if (activeTab === "AI Model Registry") {
      api.get("/api/olympus/models").then((r: Record<string, unknown>) => setModels(r.models as Record<string, unknown>[])).catch(() => {});
    }
    if (activeTab === "Certification Registry") {
      api.get("/api/olympus/certification-registry").then(setCertRegistry).catch(() => {});
    }
    if (activeTab === "Innovation Marketplace") {
      api.get("/api/olympus/marketplace/summary").then(setMarketplace).catch(() => {});
    }
    if (activeTab === "Governance Council") {
      api.get("/api/olympus/governance/cases").then((r: Record<string, unknown>) => setCases(r.cases as Record<string, unknown>[])).catch(() => {});
      api.get("/api/olympus/governance/summary").then(setCouncilSummary).catch(() => {});
    }
  }, [activeTab]);

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">LumenAI Healthcare Intelligence Network</h1>
      <p className="text-xs text-slate-400">
        A trusted network of hospitals, manufacturers, repair providers, research institutions, consultants,
        educators, and regulators exchanging governed, de-identified, evidence-based clinical intelligence.
        Every organization controls its own data; every exchange requires human governance approval.
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

      {activeTab === "Directory" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Network Directory Summary">{directory && <Json data={directory} />}</Section>
          <Section title="Participants">
            {participants?.map((p) => (
              <div key={String(p.tenant_id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
                <span className="font-medium">{String(p.tenant_id)}</span> — {String(p.organization_type)} (
                {String(p.participation_level)})
              </div>
            ))}
          </Section>
        </div>
      )}

      {activeTab === "Trust Network" && (
        <Section title="Network Trust Leaderboard">
          {leaderboard?.map((l) => (
            <div key={String(l.tenant_id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              <span className="font-medium">{String(l.tenant_id)}</span> — trust score {String(l.overall_trust_score)}
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Intelligence Exchange" && (
        <Section title="Published Exchange Packages (de-identified)">
          {packages?.map((p) => (
            <div key={String(p.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              <span className="font-medium">{String(p.title)}</span> — {String(p.package_type)} ({String(p.status)})
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Research Observatory" && (
        <Section title="Global Research Observatory">{observatory && <Json data={observatory} />}</Section>
      )}

      {activeTab === "AI Model Registry" && (
        <Section title="Registered AI Models">
          {models?.map((m) => (
            <div key={String(m.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              <span className="font-medium">{String(m.name)}</span> — {String(m.model_type)} v{String(m.version)} (
              {String(m.validation_status)}, {String(m.certification_status)})
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Certification Registry" && (
        <Section title="Certification Registry — Certified Workflows, AI Models, Knowledge & Education">
          {certRegistry && <Json data={certRegistry} />}
        </Section>
      )}

      {activeTab === "Innovation Marketplace" && (
        <Section title="Innovation Marketplace">{marketplace && <Json data={marketplace} />}</Section>
      )}

      {activeTab === "Governance Council" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Council Summary">{councilSummary && <Json data={councilSummary} />}</Section>
          <Section title="Cases">
            {cases?.map((c) => (
              <div key={String(c.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
                <span className="font-medium">{String(c.title)}</span> — {String(c.case_type)} ({String(c.status)})
              </div>
            ))}
          </Section>
        </div>
      )}
    </div>
  );
}
