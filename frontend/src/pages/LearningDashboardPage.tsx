import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Brain, TrendingDown, TrendingUp, Wrench } from "lucide-react";
import { apiFetch } from "@/lib/api";

// v2.4 — Clinical Memory & Predictive Intelligence ("Project Insight"),
// Section 8: Learning Dashboard. Tenant-wide rollup from
// /api/clinical-memory/learning-dashboard.

type InstrumentSummary = {
  instrument_identity: string;
  instrument_type: string;
  condition_trend: string;
  inspection_count: number;
  repair_count: number;
  corrosion_history_count: number;
};

type LearningDashboard = {
  tracked_instrument_count: number;
  recurring_findings: { finding_type: string; count: number }[];
  repeated_contamination_zones: { zone: string; count: number }[];
  most_improved_instruments: InstrumentSummary[];
  most_problematic_instruments: InstrumentSummary[];
  repeat_repair_candidates: InstrumentSummary[];
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

function InstrumentRow({ item }: { item: InstrumentSummary }) {
  const barcodeOrUdi = item.instrument_identity.split(":", 2)[1];
  return (
    <Link
      to={`/instrument-passport?instrument=${encodeURIComponent(barcodeOrUdi)}`}
      className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 hover:bg-slate-100 transition-colors"
    >
      <div className="min-w-0">
        <p className="text-sm text-slate-700 capitalize truncate">{item.instrument_type.replace(/_/g, " ")}</p>
        <p className="text-xs text-slate-400 font-mono truncate">{item.instrument_identity}</p>
      </div>
      <div className="text-right shrink-0 text-xs text-slate-500">
        <p>{item.inspection_count} inspections</p>
        {item.repair_count > 0 && <p className="text-red-600">{item.repair_count} repairs</p>}
      </div>
    </Link>
  );
}

export default function LearningDashboardPage() {
  const [data, setData] = useState<LearningDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<LearningDashboard>("/api/clinical-memory/learning-dashboard")
      .then(setData)
      .catch(() => setError("Failed to load the learning dashboard."));
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-5">
      <div className="flex items-center gap-2">
        <Brain className="h-6 w-6 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Learning Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            What the fleet's own history teaches — recurring findings, trending instruments, and repeat repair candidates.
          </p>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {!data && !error && <p className="text-sm text-slate-400">Loading…</p>}

      {data && (
        <>
          <p className="text-xs text-slate-400">
            {data.tracked_instrument_count} instrument{data.tracked_instrument_count !== 1 ? "s" : ""} with
            enough recorded history (2+ inspections) to trend.
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Section title="Recurring Findings">
              {data.recurring_findings.length === 0 ? (
                <p className="text-sm text-slate-400">No finding type has recurred yet.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {data.recurring_findings.map((f) => (
                    <span
                      key={f.finding_type}
                      className="text-xs font-medium px-2.5 py-1 rounded-full border border-amber-200 bg-amber-50 text-amber-800 capitalize"
                    >
                      {f.finding_type.replace(/_/g, " ")} × {f.count}
                    </span>
                  ))}
                </div>
              )}
            </Section>

            <Section title="Repeated Contamination Zones">
              {data.repeated_contamination_zones.length === 0 ? (
                <p className="text-sm text-slate-400">No anatomy zone has repeated contamination yet.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {data.repeated_contamination_zones.map((z) => (
                    <span
                      key={z.zone}
                      className="text-xs font-medium px-2.5 py-1 rounded-full border border-red-200 bg-red-50 text-red-800 capitalize"
                    >
                      {z.zone.replace(/_/g, " ")} × {z.count}
                    </span>
                  ))}
                </div>
              )}
            </Section>
          </div>

          <Section title="Most Improved Instruments">
            <div className="flex items-center gap-1.5 mb-2 text-xs text-emerald-600">
              <TrendingDown className="h-3.5 w-3.5" />
              <span>Declining finding rate over their own inspection history</span>
            </div>
            {data.most_improved_instruments.length === 0 ? (
              <p className="text-sm text-slate-400">No instrument shows a clear improving trend yet.</p>
            ) : (
              <div className="space-y-1.5">
                {data.most_improved_instruments.map((item) => (
                  <InstrumentRow key={item.instrument_identity} item={item} />
                ))}
              </div>
            )}
          </Section>

          <Section title="Most Problematic Instruments">
            <div className="flex items-center gap-1.5 mb-2 text-xs text-red-600">
              <TrendingUp className="h-3.5 w-3.5" />
              <span>Rising finding rate over their own inspection history</span>
            </div>
            {data.most_problematic_instruments.length === 0 ? (
              <p className="text-sm text-slate-400">No instrument shows a clear declining trend yet.</p>
            ) : (
              <div className="space-y-1.5">
                {data.most_problematic_instruments.map((item) => (
                  <InstrumentRow key={item.instrument_identity} item={item} />
                ))}
              </div>
            )}
          </Section>

          <Section title="Repeat Repair Candidates">
            <div className="flex items-center gap-1.5 mb-2 text-xs text-slate-500">
              <Wrench className="h-3.5 w-3.5" />
              <span>Removed from service / repaired 2 or more times</span>
            </div>
            {data.repeat_repair_candidates.length === 0 ? (
              <p className="text-sm text-slate-400">No instrument has been repaired more than once.</p>
            ) : (
              <div className="space-y-1.5">
                {data.repeat_repair_candidates.map((item) => (
                  <InstrumentRow key={item.instrument_identity} item={item} />
                ))}
              </div>
            )}
          </Section>

          <p className="text-xs text-slate-400 text-center pt-2">
            Clinical Memory reflects the fleet's own recorded history — a potential association,
            never a claim of causation. Human review required before clinical action.
          </p>
        </>
      )}
    </div>
  );
}
