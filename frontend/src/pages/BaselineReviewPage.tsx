import { Link } from "react-router-dom";
import { CheckCircle2, ChevronRight } from "lucide-react";
import BaselineReviewQueue from "../components/BaselineReviewQueue";
import { Alert, AlertDescription } from "@/components/ui/alert";

export default function BaselineReviewPage() {
  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/" className="hover:text-slate-600">Dashboard</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-600 font-medium">Baseline Review Queue</span>
      </nav>

      {/* Page header */}
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100">
          <CheckCircle2 className="h-5 w-5 text-emerald-600" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Baseline Review Queue</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Vendor-submitted baselines awaiting hospital administrator approval before use in inspection scoring.
            Review each baseline against your facility's sterile processing standards.
          </p>
        </div>
      </div>

      {/* Role guidance */}
      <Alert variant="info">
        <AlertDescription>
          <strong>Hospital administrators:</strong> Review each baseline's acceptable condition notes and IFU reference
          before approving. Approved baselines will be used immediately in AI-assisted inspection scoring.
          Rejected baselines are logged in the audit trail.
        </AlertDescription>
      </Alert>

      {/* Component */}
      <BaselineReviewQueue />
    </div>
  );
}
