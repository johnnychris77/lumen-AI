import { BookOpen } from "lucide-react";
import { Link } from "react-router-dom";

export default function BaselineLibraryPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[420px] text-center px-4">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 mb-5">
        <BookOpen className="h-7 w-7 text-blue-500" />
      </div>
      <h2 className="text-lg font-semibold text-slate-900 mb-2">Baseline Library</h2>
      <p className="text-sm text-slate-500 max-w-md mb-6">
        The shared baseline library consolidates manufacturer and vendor baselines into a
        searchable reference catalogue. Full search and filtering will be available in the
        next release.
      </p>
      <div className="flex gap-3">
        <Link
          to="/manufacturer-baselines"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          Manufacturer Baselines
        </Link>
        <Link
          to="/vendor-baseline-portal"
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
        >
          Vendor Baselines
        </Link>
      </div>
    </div>
  );
}
