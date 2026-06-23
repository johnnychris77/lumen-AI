import { FileText, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

export default function AuditEvidencePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[420px] text-center px-4">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 mb-5">
        <FileText className="h-7 w-7 text-emerald-500" />
      </div>
      <h2 className="text-lg font-semibold text-slate-900 mb-2">Audit Evidence</h2>
      <p className="text-sm text-slate-500 max-w-md mb-6">
        Compile and export tamper-evident evidence bundles for accreditation, compliance
        audits, and regulatory review. Evidence packages include inspection records, CAPA
        trails, and baseline change history.
      </p>
      <div className="flex gap-3">
        <Link
          to="/accreditation"
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 transition-colors"
        >
          Accreditation Console
          <ArrowRight className="h-4 w-4" />
        </Link>
        <Link
          to="/capa"
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
        >
          CAPA Workflow
        </Link>
      </div>
    </div>
  );
}
