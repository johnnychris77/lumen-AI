/**
 * v5.3 — LumenAI Network: Project Genesis AI — Global Sterile Processing
 * Intelligence Cloud.
 *
 * Frontend route `/intelligence-cloud`, API prefix `/api/genesis-ai`.
 *
 * "Project Genesis AI" (this page) is not "Project Genesis" (v4.0, the
 * platform/module registry) — same name prefix, unrelated systems.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const TABS = [
  "Overview", "Anatomy Registry", "Evidence Cloud", "Manufacturer Portal",
  "Learning Engine", "Research Hub", "Intelligence Exchange", "Standards Observatory",
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

export default function IntelligenceCloudCenter() {
  const [activeTab, setActiveTab] = useState<Tab>("Overview");

  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [anatomy, setAnatomy] = useState<Record<string, unknown> | null>(null);
  const [evidence, setEvidence] = useState<Record<string, unknown> | null>(null);
  const [mfrUpdates, setMfrUpdates] = useState<Record<string, unknown>[] | null>(null);
  const [learning, setLearning] = useState<Record<string, unknown> | null>(null);
  const [researchHub, setResearchHub] = useState<Record<string, unknown> | null>(null);
  const [exchange, setExchange] = useState<Record<string, unknown> | null>(null);
  const [observatory, setObservatory] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (activeTab === "Overview") api.get("/api/genesis-ai/summary").then(setSummary).catch(() => {});
    if (activeTab === "Anatomy Registry") api.get("/api/genesis-ai/anatomy-profiles/summary").then(setAnatomy).catch(() => {});
    if (activeTab === "Evidence Cloud") api.get("/api/genesis-ai/evidence-cloud/summary").then(setEvidence).catch(() => {});
    if (activeTab === "Manufacturer Portal") {
      api.get("/api/genesis-ai/manufacturer-updates").then((r: Record<string, unknown>) => setMfrUpdates(r.updates as Record<string, unknown>[])).catch(() => {});
    }
    if (activeTab === "Learning Engine") api.get("/api/genesis-ai/learning-engine/summary").then(setLearning).catch(() => {});
    if (activeTab === "Research Hub") api.get("/api/genesis-ai/research-hub/summary").then(setResearchHub).catch(() => {});
    if (activeTab === "Intelligence Exchange") api.get("/api/genesis-ai/intelligence-exchange/summary").then(setExchange).catch(() => {});
    if (activeTab === "Standards Observatory") api.get("/api/genesis-ai/standards-observatory/summary").then(setObservatory).catch(() => {});
  }, [activeTab]);

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Global Sterile Processing Intelligence Cloud</h1>
      <p className="text-xs text-slate-400">
        A secure, governed global intelligence cloud for sterile processing. Organizations retain ownership of
        their own data; only approved, de-identified intelligence is shared. Every finding requires human review
        and describes a potential association only, never causation.
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

      {activeTab === "Overview" && <Section title="Intelligence Cloud Summary">{summary && <Json data={summary} />}</Section>}

      {activeTab === "Anatomy Registry" && (
        <Section title="Global Anatomy Registry — Standardized Instrument Profiles">{anatomy && <Json data={anatomy} />}</Section>
      )}

      {activeTab === "Evidence Cloud" && (
        <Section title="Clinical Evidence Cloud">{evidence && <Json data={evidence} />}</Section>
      )}

      {activeTab === "Manufacturer Portal" && (
        <Section title="Manufacturer Knowledge Portal — IFUs, Inspection Guidance, Repair Advisories">
          {mfrUpdates?.map((u) => (
            <div key={String(u.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              <span className="font-medium">{String(u.title)}</span> — {String(u.update_type)} v{String(u.version)} (
              {String(u.status)})
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Learning Engine" && (
        <Section title="Global Learning Engine">{learning && <Json data={learning} />}</Section>
      )}

      {activeTab === "Research Hub" && (
        <Section title="Research Collaboration Hub (opt-in)">{researchHub && <Json data={researchHub} />}</Section>
      )}

      {activeTab === "Intelligence Exchange" && (
        <Section title="Clinical Intelligence Exchange">{exchange && <Json data={exchange} />}</Section>
      )}

      {activeTab === "Standards Observatory" && (
        <Section title="Global Standards Observatory">{observatory && <Json data={observatory} />}</Section>
      )}
    </div>
  );
}
