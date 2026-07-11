/**
 * LumenAI AI Specialist — Project Vulcan: Instrument Forensics Workspace.
 *
 * Frontend route `/instrument-forensics`, API prefix `/api/vulcan`. Vulcan is
 * a deterministic, evidence-based reliability agent -- not an autonomous LLM
 * -- and every conclusion shown here is advisory, confidence-scored, and
 * requires human review before any operational action.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Json = Record<string, unknown>;

const WATCHLIST_NAMES = [
  "recurring_corrosion", "recurring_rust", "repeated_cleaning_failure", "repeat_repair",
  "structural_defect_progression", "damaged_o_rings", "insulation_failures", "drill_flute_failures",
  "box_lock_failures", "instruments_awaiting_manufacturer_review", "retirement_candidates",
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

export default function InstrumentForensicsWorkspace() {
  const [instrumentIdentity, setInstrumentIdentity] = useState("");
  const [instrumentType, setInstrumentType] = useState("");
  const [record, setRecord] = useState<Json | null>(null);

  const [filters, setFilters] = useState({
    manufacturer: "", instrument_family: "", anatomy_zone: "", failure_category: "",
    repair_vendor: "", facility: "", date_from: "", date_to: "",
  });
  const [searchResults, setSearchResults] = useState<Json[] | null>(null);

  const [watchlistName, setWatchlistName] = useState(WATCHLIST_NAMES[0]);
  const [watchlistEntries, setWatchlistEntries] = useState<Json[] | null>(null);

  const [executiveSummary, setExecutiveSummary] = useState<Json | null>(null);

  useEffect(() => {
    api.get("/api/vulcan/executive-summary").then(setExecutiveSummary).catch(() => {});
  }, []);

  useEffect(() => {
    api
      .get(`/api/vulcan/watchlists/${watchlistName}`)
      .then((r: Json) => setWatchlistEntries(r.entries as Json[]))
      .catch(() => {});
  }, [watchlistName]);

  function lookupInstrument() {
    if (!instrumentIdentity) return;
    api
      .get(`/api/vulcan/forensics/${encodeURIComponent(instrumentIdentity)}?instrument_type=${encodeURIComponent(instrumentType)}`)
      .then(setRecord)
      .catch(() => setRecord(null));
  }

  function assessInstrument() {
    if (!instrumentIdentity) return;
    api
      .post("/api/vulcan/assess", { instrument_identity: instrumentIdentity, instrument_type: instrumentType })
      .then(() => lookupInstrument())
      .catch(() => {});
  }

  function runSearch() {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v) params.set(k, v);
    });
    api
      .get(`/api/vulcan/forensics/search?${params.toString()}`)
      .then((r: Json) => setSearchResults(r.results as Json[]))
      .catch(() => setSearchResults(null));
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Instrument Forensics Workspace</h1>
      <p className="text-xs text-slate-400">
        Vulcan investigates recurring instrument defects, condition changes, repair patterns, and premature
        failures. It does not certify instrument safety independently -- supervisor, clinical engineering,
        repair vendor, and manufacturer review remain available where appropriate. Every conclusion is
        evidence-based, confidence-scored, and human-reviewed.
      </p>

      <Section title="Instrument Lookup">
        <div className="flex flex-wrap gap-2">
          <input
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            placeholder="instrument_identity (e.g. barcode:ABC123)"
            value={instrumentIdentity}
            onChange={(e) => setInstrumentIdentity(e.target.value)}
          />
          <input
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            placeholder="instrument_type (e.g. kerrison rongeur)"
            value={instrumentType}
            onChange={(e) => setInstrumentType(e.target.value)}
          />
          <button className="rounded bg-slate-100 px-3 py-1 text-sm text-slate-700" onClick={lookupInstrument}>
            Load Forensics Record
          </button>
          <button className="rounded bg-indigo-600 px-3 py-1 text-sm text-white" onClick={assessInstrument}>
            Run Vulcan Assessment
          </button>
        </div>
        {record && (
          <div className="mt-3 space-y-3">
            {(record.latest_assessment as Json | null) && (
              <div className="rounded border border-indigo-200 bg-indigo-50 p-3 text-sm text-slate-700">
                <p className="font-semibold">{(record.latest_assessment as Json).reasoning_narrative as string}</p>
                <p className="mt-1 text-xs text-slate-500">
                  Reliability: {(record.latest_assessment as Json).reliability_category as string} (
                  {(record.latest_assessment as Json).reliability_score as number}) — Confidence:{" "}
                  {(record.latest_assessment as Json).confidence as string} — Recommended disposition:{" "}
                  {(record.latest_assessment as Json).recommended_disposition as string}
                </p>
              </div>
            )}
            <JsonView data={record} />
          </div>
        )}
      </Section>

      <Section title="Forensics Search Filters">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {(Object.keys(filters) as (keyof typeof filters)[]).map((key) => (
            <input
              key={key}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
              placeholder={key.replace(/_/g, " ")}
              value={filters[key]}
              onChange={(e) => setFilters((f) => ({ ...f, [key]: e.target.value }))}
            />
          ))}
        </div>
        <button className="mt-2 rounded bg-slate-100 px-3 py-1 text-sm text-slate-700" onClick={runSearch}>
          Search
        </button>
        {searchResults && <div className="mt-3"><JsonView data={searchResults} /></div>}
      </Section>

      <Section title="Reliability Watchlists">
        <select
          className="rounded border border-slate-300 px-2 py-1 text-sm"
          value={watchlistName}
          onChange={(e) => setWatchlistName(e.target.value)}
        >
          {WATCHLIST_NAMES.map((name) => (
            <option key={name} value={name}>
              {name.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        {watchlistEntries && <div className="mt-3"><JsonView data={watchlistEntries} /></div>}
      </Section>

      <Section title="Executive Reliability Analytics">
        {executiveSummary && <JsonView data={executiveSummary} />}
      </Section>
    </div>
  );
}
