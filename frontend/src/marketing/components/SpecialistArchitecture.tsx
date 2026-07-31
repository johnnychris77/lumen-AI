import { SPECIALISTS } from "../lib/content";
import { CheckCircle2, XCircle, UserCheck, Info } from "lucide-react";

export function SpecialistBoundaries() {
  return (
    <div className="rounded-xl border border-primary/20 bg-primary-subtle p-5">
      <h3 className="text-sm font-semibold text-slate-900">The boundary that never moves</h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-700">
        Specialists analyze, compare, and recommend. They do not diagnose, do not act, and do not
        finalize clinical decisions. Veritas assures evidence only. Vulcan assesses instrument
        reliability only. Council supports decisions only. The execution layer carries out
        already-approved actions only. A qualified human owns every disposition.
      </p>
    </div>
  );
}

export function SpecialistGrid() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {SPECIALISTS.map((s) => (
        <article key={s.name} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="text-base font-semibold text-slate-900">{s.name}</h3>
            <span className="text-xs font-medium text-primary">{s.role}</span>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">{s.purpose}</p>

          <dl className="mt-3 space-y-1.5 text-xs">
            <div className="flex gap-2">
              <dt className="w-16 shrink-0 font-semibold text-slate-500">Inputs</dt>
              <dd className="text-slate-600">{s.inputs}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-16 shrink-0 font-semibold text-slate-500">Outputs</dt>
              <dd className="text-slate-600">{s.outputs}</dd>
            </div>
          </dl>

          <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
            <div className="flex items-start gap-1.5 rounded-md bg-success-subtle p-2">
              <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-success" aria-hidden />
              <span className="text-slate-700"><span className="font-semibold">Allowed:</span> {s.allowed}</span>
            </div>
            <div className="flex items-start gap-1.5 rounded-md bg-danger-subtle p-2">
              <XCircle size={13} className="mt-0.5 shrink-0 text-danger" aria-hidden />
              <span className="text-slate-700"><span className="font-semibold">Not allowed:</span> {s.notAllowed}</span>
            </div>
          </div>

          <p className="mt-2 flex items-start gap-1.5 text-xs text-slate-600">
            <UserCheck size={13} className="mt-0.5 shrink-0 text-primary" aria-hidden />
            {s.humanReview}
          </p>

          {s.note && (
            <p className="mt-2 flex items-start gap-1.5 rounded-md bg-slate-50 p-2 text-[11px] text-slate-500">
              <Info size={12} className="mt-0.5 shrink-0" aria-hidden />
              {s.note}
            </p>
          )}
        </article>
      ))}
    </div>
  );
}
