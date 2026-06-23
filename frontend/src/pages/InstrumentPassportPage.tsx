import { CreditCard, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

export default function InstrumentPassportPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[420px] text-center px-4">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 mb-5">
        <CreditCard className="h-7 w-7 text-indigo-500" />
      </div>
      <h2 className="text-lg font-semibold text-slate-900 mb-2">Instrument Passport</h2>
      <p className="text-sm text-slate-500 max-w-md mb-6">
        The Instrument Passport records the full lifecycle event log for each surgical
        instrument — verifications, maintenance events, findings, and readiness scores.
        Access passport records via the Instrument Registry.
      </p>
      <Link
        to="/infrastructure"
        className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
      >
        Open Instrument Registry
        <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
