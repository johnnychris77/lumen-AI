import { Link } from "react-router-dom";
import { History, ChevronRight } from "lucide-react";
import EnterpriseIntakeHistoryPanel from "../components/EnterpriseIntakeHistoryPanel";
import InspectionResultsHistory from "../components/InspectionResultsHistory";
import { Alert, AlertDescription } from "@/components/ui/alert";

export default function IntakeHistoryPage() {
  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/" className="hover:text-slate-600">Dashboard</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-600 font-medium">Intake History</span>
      </nav>

      {/* Page header */}
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100">
          <History className="h-5 w-5 text-indigo-600" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Intake History</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Complete audit-ready record of all enterprise inspection intakes submitted through LumenAI.
            Each record includes instrument identification, AI finding, risk score, and workflow disposition.
          </p>
        </div>
      </div>

      {/* Role guidance */}
      <Alert variant="info">
        <AlertDescription>
          <strong>Executives and auditors:</strong> This history log is tamper-evident and exportable.
          Each intake is associated with a governance packet containing full audit evidence.
          Use the export options to prepare records for Joint Commission or FDA review.
        </AlertDescription>
      </Alert>

      {/* Inspection results from the New Inspection workflow */}
      <InspectionResultsHistory />

      {/* Enterprise governance intake history */}
      <EnterpriseIntakeHistoryPanel />
    </div>
  );
}
