/**
 * LumenAI AI Specialist — Project Veritas: Baseline Governance, Evidence
 * Integrity & Clinical Data Quality.
 *
 * Frontend route `/veritas`, API prefix `/api/veritas`. Veritas does not
 * independently approve an instrument -- it determines whether the
 * evidence is trustworthy enough for the inspection workflow to proceed
 * and identifies what additional evidence is required.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Json = Record<string, unknown>;

const TABS = [
  "Workspace", "Watchlists", "Data Quality", "Training Dataset", "Reports",
] as const;
type Tab = (typeof TABS)[number];

const WATCHLIST_NAMES = [
  "no_approved_baseline", "baseline_review_overdue", "baseline_superseded",
  "repeated_poor_image_quality", "repeated_incomplete_coverage", "high_baseline_mismatch",
  "conflicting_evidence", "unapproved_training_candidates", "missing_provenance",
  "repeated_evidence_gate_override",
];

const REPORT_NAMES = [
  "baseline_governance", "evidence_readiness", "training_dataset_assurance",
  "provenance_audit", "baseline_review_aging", "data_quality_trend",
];

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

export default function VeritasWorkspace() {
  const [activeTab, setActiveTab] = useState<Tab>("Workspace");

  const [workspace, setWorkspace] = useState<Json | null>(null);
  const [watchlistName, setWatchlistName] = useState(WATCHLIST_NAMES[0]);
  const [watchlistEntries, setWatchlistEntries] = useState<Json[] | null>(null);
  const [dataQuality, setDataQuality] = useState<Json | null>(null);
  const [trainingDataset, setTrainingDataset] = useState<Json[] | null>(null);
  const [reportName, setReportName] = useState(REPORT_NAMES[0]);
  const [report, setReport] = useState<Json | null>(null);

  useEffect(() => {
    if (activeTab === "Workspace") api.get("/api/veritas/workspace").then(setWorkspace).catch(() => {});
    if (activeTab === "Data Quality") api.get("/api/veritas/data-quality").then(setDataQuality).catch(() => {});
    if (activeTab === "Training Dataset") api.get("/api/veritas/training-dataset").then((r: Json) => setTrainingDataset(r.entries as Json[])).catch(() => {});
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === "Watchlists") {
      api.get(`/api/veritas/watchlists/${watchlistName}`).then((r: Json) => setWatchlistEntries(r.entries as Json[])).catch(() => {});
    }
  }, [activeTab, watchlistName]);

  useEffect(() => {
    if (activeTab === "Reports") {
      api.get(`/api/veritas/reports/${reportName}`).then(setReport).catch(() => {});
    }
  }, [activeTab, reportName]);

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Veritas — Evidence Assurance</h1>
      <p className="text-xs text-slate-400">
        Veritas evaluates whether an inspection has sufficient, reliable, and governed evidence to support an
        AI recommendation. It does not independently approve an instrument. Every evidence decision remains
        versioned, explainable, auditable, tenant-isolated, and human-governed.
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
        <Section title="Evidence Readiness Overview, Pending Reviews &amp; Conflicts">
          {workspace && <JsonView data={workspace} />}
        </Section>
      )}

      {activeTab === "Watchlists" && (
        <Section title="Alerts and Watchlists">
          <select
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            value={watchlistName}
            onChange={(e) => setWatchlistName(e.target.value)}
          >
            {WATCHLIST_NAMES.map((name) => (
              <option key={name} value={name}>{name.replace(/_/g, " ")}</option>
            ))}
          </select>
          {watchlistEntries && <div className="mt-3"><JsonView data={watchlistEntries} /></div>}
        </Section>
      )}

      {activeTab === "Data Quality" && (
        <Section title="Data Quality Monitoring">
          {dataQuality && <JsonView data={dataQuality} />}
        </Section>
      )}

      {activeTab === "Training Dataset" && (
        <Section title="Training Dataset Assurance">
          {trainingDataset && <JsonView data={trainingDataset} />}
        </Section>
      )}

      {activeTab === "Reports" && (
        <Section title="Evidence Assurance Reports">
          <select
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            value={reportName}
            onChange={(e) => setReportName(e.target.value)}
          >
            {REPORT_NAMES.map((name) => (
              <option key={name} value={name}>{name.replace(/_/g, " ")}</option>
            ))}
          </select>
          {report && <div className="mt-3"><JsonView data={report} /></div>}
        </Section>
      )}
    </div>
  );
}
