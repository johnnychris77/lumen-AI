import { WORKFLOW_STEPS, WorkflowStepInfo } from "../lib/content";
import { Camera, ScanSearch, GitCompareArrows, UserCheck, ShieldCheck, BarChart3 } from "lucide-react";

const KIND_META: Record<WorkflowStepInfo["kind"], { label: string; className: string; Icon: typeof Camera }> = {
  capture: { label: "Capture", className: "bg-primary-subtle text-primary", Icon: Camera },
  analyze: { label: "Automated analysis", className: "bg-info-subtle text-info", Icon: ScanSearch },
  compare: { label: "Baseline comparison", className: "bg-info-subtle text-info", Icon: GitCompareArrows },
  review: { label: "Human review", className: "bg-warning-subtle text-warning", Icon: UserCheck },
  govern: { label: "Evidence governance", className: "bg-success-subtle text-success", Icon: ShieldCheck },
  report: { label: "Reporting & analytics", className: "bg-slate-100 text-slate-700", Icon: BarChart3 },
};

export function WorkflowLegend() {
  return (
    <ul className="flex flex-wrap gap-2" aria-label="Workflow stage types">
      {Object.entries(KIND_META).map(([kind, m]) => (
        <li
          key={kind}
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${m.className}`}
        >
          <m.Icon size={13} aria-hidden />
          {m.label}
        </li>
      ))}
    </ul>
  );
}

export function WorkflowDiagram() {
  return (
    <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-2" aria-label="LumenAI inspection workflow, ten steps">
      {WORKFLOW_STEPS.map((step) => {
        const meta = KIND_META[step.kind];
        return (
          <li key={step.n} className="flex gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col items-center">
              <span
                aria-hidden
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold ${meta.className}`}
              >
                {step.n}
              </span>
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-semibold text-slate-900">{step.title}</h3>
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${meta.className}`}>
                  <meta.Icon size={11} aria-hidden /> {meta.label}
                </span>
              </div>
              <p className="mt-1 text-sm leading-relaxed text-slate-600">{step.detail}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
