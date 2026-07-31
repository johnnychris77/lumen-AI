import { useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  RotateCcw,
  Check,
  ShieldCheck,
  UserCheck,
  FileText,
} from "lucide-react";
import {
  DEMO_IMAGES,
  DEMO_INSTRUMENTS,
  DEMO_STEPS,
  DemoImage,
  DemoState,
  advance,
  back,
  buildDemoReport,
  canAdvance,
  computeDemoFinding,
  currentStep,
  reset,
} from "../lib/workflowDemo";
import { DemoDisclaimer } from "./DemoDisclaimer";
import { track } from "../lib/analytics";

const STEP_TITLES: Record<string, string> = {
  "select-instrument": "1 · Identify the instrument",
  "select-image": "2 · Choose a sample lumen image",
  metadata: "3 · Inspection metadata",
  analyze: "4 · Assistive analysis",
  compare: "5 · Baseline comparison",
  review: "6 · Review routing",
  record: "7 · Record evidence",
  report: "8 · Generated report",
};

/** Synthetic borescope view. No real image — purely illustrative. */
function BorescopeView({ image, size = 150 }: { image?: DemoImage; size?: number }) {
  const spots =
    image?.seed === "debris"
      ? [{ cx: 60, cy: 66, r: 9 }, { cx: 78, cy: 82, r: 5 }, { cx: 52, cy: 84, r: 4 }]
      : image?.seed === "corrosion"
        ? [{ cx: 88, cy: 60, r: 6 }, { cx: 96, cy: 72, r: 4 }]
        : [];
  const spotFill = image?.seed === "corrosion" ? "#b45309" : "#78716c";
  return (
    <svg width={size} height={size} viewBox="0 0 150 150" role="img" aria-label={image ? image.label : "No image selected"}>
      <defs>
        <radialGradient id="lumenWall" cx="50%" cy="45%" r="60%">
          <stop offset="0%" stopColor="#334155" />
          <stop offset="70%" stopColor="#1e293b" />
          <stop offset="100%" stopColor="#0f172a" />
        </radialGradient>
      </defs>
      <circle cx="75" cy="75" r="72" fill="#0f172a" />
      <circle cx="75" cy="75" r="60" fill="url(#lumenWall)" stroke="#475569" strokeWidth="1" />
      <circle cx="75" cy="75" r="22" fill="#020617" />
      {spots.map((s, i) => (
        <circle key={i} cx={s.cx} cy={s.cy} r={s.r} fill={spotFill} opacity="0.85" />
      ))}
      {!image && (
        <text x="75" y="80" textAnchor="middle" fontSize="10" fill="#94a3b8">
          select a sample
        </text>
      )}
    </svg>
  );
}

function Choice({
  active,
  onClick,
  title,
  subtitle,
}: {
  active: boolean;
  onClick: () => void;
  title: string;
  subtitle: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 ${
        active ? "border-primary bg-primary-subtle" : "border-slate-200 bg-white hover:bg-slate-50"
      }`}
    >
      <span
        aria-hidden
        className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
          active ? "border-primary bg-primary text-white" : "border-slate-300"
        }`}
      >
        {active ? <Check size={12} /> : null}
      </span>
      <span>
        <span className="block text-sm font-medium text-slate-900">{title}</span>
        <span className="block text-xs text-slate-500">{subtitle}</span>
      </span>
    </button>
  );
}

export function WorkflowDemo() {
  const [state, setState] = useState<DemoState>(reset());
  const step = currentStep(state);
  const finding = useMemo(() => computeDemoFinding(state.image), [state.image]);
  const report = useMemo(
    () => (step === "report" ? buildDemoReport(state) : null),
    [step, state],
  );

  const goNext = () => {
    const next = advance(state);
    if (next !== state) {
      track("workflow_demo_step", { step: DEMO_STEPS[next.stepIndex] });
      if (currentStep(next) === "report") track("workflow_demo_complete");
      setState(next);
    }
  };

  const pct = Math.round(((state.stepIndex + 1) / DEMO_STEPS.length) * 100);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Interactive workflow demonstration</h3>
          <p className="text-xs text-slate-500">{STEP_TITLES[step]}</p>
        </div>
        <DemoDisclaimer />
      </div>

      {/* Progress */}
      <div className="px-4 pt-4">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-primary transition-all motion-reduce:transition-none" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div className="grid gap-6 p-4 md:grid-cols-[1fr_180px]">
        <div className="min-w-0">
          {step === "select-instrument" && (
            <div className="space-y-2">
              {DEMO_INSTRUMENTS.map((inst) => (
                <Choice
                  key={inst.id}
                  active={state.instrument?.id === inst.id}
                  onClick={() => setState({ ...state, instrument: inst })}
                  title={inst.name}
                  subtitle={`${inst.type} · ${inst.channelMm} mm channel · ${inst.id}`}
                />
              ))}
            </div>
          )}

          {step === "select-image" && (
            <div className="space-y-2">
              {DEMO_IMAGES.map((img) => (
                <Choice
                  key={img.id}
                  active={state.image?.id === img.id}
                  onClick={() => setState({ ...state, image: img })}
                  title={img.label}
                  subtitle="Synthetic sample"
                />
              ))}
            </div>
          )}

          {step === "metadata" && (
            <dl className="grid grid-cols-2 gap-3 text-sm">
              {[
                ["Instrument", state.instrument?.id ?? "—"],
                ["Tray", state.metadata.tray],
                ["Location", state.metadata.location],
                ["Technician", state.metadata.technician],
              ].map(([k, v]) => (
                <div key={k} className="rounded-lg bg-slate-50 p-3">
                  <dt className="text-xs uppercase tracking-wide text-slate-500">{k}</dt>
                  <dd className="mt-0.5 font-medium text-slate-900">{v}</dd>
                </div>
              ))}
              <p className="col-span-2 text-xs text-slate-500">
                Metadata makes an image into evidence. Prefilled here for the demonstration.
              </p>
            </dl>
          )}

          {step === "analyze" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
                <span className="text-sm font-medium text-slate-900">{finding.category}</span>
                <span className="text-xs font-semibold text-slate-500">
                  confidence {(finding.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full ${finding.reviewRequired ? "bg-warning" : "bg-success"}`}
                  style={{ width: `${finding.confidence * 100}%` }}
                />
              </div>
              <p className="rounded-md bg-info-subtle p-3 text-xs text-info">
                Assistive signal only. This is a non-validated demonstration scorer — a person confirms every finding.
              </p>
            </div>
          )}

          {step === "compare" && (
            <div className="grid grid-cols-2 gap-3">
              <figure className="rounded-lg border border-slate-200 p-2 text-center">
                <BorescopeView image={state.image} size={130} />
                <figcaption className="mt-1 text-xs font-medium text-slate-600">Current inspection</figcaption>
              </figure>
              <figure className="rounded-lg border border-slate-200 p-2 text-center">
                <BorescopeView image={DEMO_IMAGES[0]} size={130} />
                <figcaption className="mt-1 text-xs font-medium text-slate-600">Approved baseline</figcaption>
              </figure>
              <p className="col-span-2 text-center text-xs font-semibold text-slate-700">
                Baseline result:{" "}
                <span className={finding.baselineMatch === "match" ? "text-success" : "text-warning"}>
                  {finding.baselineMatch === "match" ? "consistent with baseline" : "deviation from baseline"}
                </span>
              </p>
            </div>
          )}

          {step === "review" && (
            <div className="space-y-3">
              <div
                className={`flex items-center gap-3 rounded-lg p-3 ${
                  finding.reviewRequired ? "bg-warning-subtle" : "bg-success-subtle"
                }`}
              >
                <UserCheck size={20} className={finding.reviewRequired ? "text-warning" : "text-success"} aria-hidden />
                <div>
                  <p className="text-sm font-semibold text-slate-900">
                    {finding.reviewRequired ? "Routed to human review" : "No mandatory review triggered"}
                  </p>
                  <p className="text-xs text-slate-600">
                    Ranking: <span className="font-medium">{finding.ranking.replace(/-/g, " ")}</span>
                  </p>
                </div>
              </div>
              <p className="text-xs leading-relaxed text-slate-600">{finding.rationale}</p>
            </div>
          )}

          {step === "record" && (
            <div className="space-y-2 text-sm">
              {[
                "Evidence image linked to instrument record",
                "Metadata + reviewer decision captured",
                "Rationale and timestamp written",
                "Event appended to hash-chained audit trail",
              ].map((t) => (
                <div key={t} className="flex items-center gap-2 rounded-md bg-slate-50 p-2.5">
                  <ShieldCheck size={16} className="text-success" aria-hidden />
                  <span className="text-slate-700">{t}</span>
                </div>
              ))}
            </div>
          )}

          {step === "report" && report && (
            <div className="rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 border-b border-slate-200 bg-slate-50 p-3">
                <FileText size={16} className="text-primary" aria-hidden />
                <span className="text-sm font-semibold text-slate-900">Sample inspection report</span>
              </div>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 p-3 text-sm">
                <dt className="text-slate-500">Report ID</dt>
                <dd className="font-mono text-xs text-slate-900">{report.reportId}</dd>
                <dt className="text-slate-500">Instrument</dt>
                <dd className="text-slate-900">{report.instrumentId}</dd>
                <dt className="text-slate-500">Finding</dt>
                <dd className="text-slate-900">{report.finding.category}</dd>
                <dt className="text-slate-500">Baseline</dt>
                <dd className="text-slate-900">{report.finding.baselineMatch.replace(/-/g, " ")}</dd>
                <dt className="text-slate-500">Ranking</dt>
                <dd className="text-slate-900">{report.finding.ranking.replace(/-/g, " ")}</dd>
                <dt className="text-slate-500">Human review</dt>
                <dd className="text-slate-900">{report.finding.reviewRequired ? "required" : "not mandatory"}</dd>
              </dl>
              <p className="border-t border-slate-200 p-3 text-[11px] font-semibold text-warning">{report.disclaimer}</p>
            </div>
          )}
        </div>

        {/* Live borescope preview panel (hidden on the two side-by-side steps) */}
        {step !== "compare" && (
          <aside className="hidden justify-self-center md:block">
            <BorescopeView image={state.image} />
            <p className="mt-2 text-center text-xs text-slate-500">
              {state.instrument ? state.instrument.id : "no instrument"}
            </p>
          </aside>
        )}
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-slate-200 p-4">
        <button
          type="button"
          onClick={() => setState(reset())}
          className="inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-sm text-slate-500 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <RotateCcw size={14} aria-hidden /> Restart
        </button>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setState(back(state))}
            disabled={state.stepIndex === 0}
            className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <ArrowLeft size={14} aria-hidden /> Back
          </button>
          <button
            type="button"
            onClick={goNext}
            disabled={!canAdvance(state)}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1"
          >
            {step === "report" ? "Done" : "Next"} <ArrowRight size={14} aria-hidden />
          </button>
        </div>
      </div>
    </div>
  );
}
