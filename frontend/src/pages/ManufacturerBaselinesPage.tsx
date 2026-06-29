import { Link } from "react-router-dom";
import { Package, ChevronRight } from "lucide-react";
import ManufacturerBaselinePanel from "../components/ManufacturerBaselinePanel";
import CreateManufacturerBaseline from "../components/CreateManufacturerBaseline";
import { Alert, AlertDescription } from "@/components/ui/alert";

export default function ManufacturerBaselinesPage() {
  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/" className="hover:text-slate-600">Dashboard</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-600 font-medium">Manufacturer Baselines</span>
      </nav>

      {/* Page header */}
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
          <Package className="h-5 w-5 text-blue-600" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Manufacturer Baselines</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Reference baselines for each instrument model, uploaded by manufacturers and approved by hospital administrators.
            These baselines define the known-normal condition for AI inspection scoring and comparison.
          </p>
        </div>
      </div>

      {/* Role guidance */}
      <Alert variant="info">
        <AlertDescription>
          <strong>SPD managers:</strong> Use this panel to view approved manufacturer baselines, track approval status,
          and compare instrument condition against the manufacturer's IFU reference.
          Contact your vendor to submit new baselines via the{" "}
          <Link to="/vendor-baseline-portal" className="underline text-blue-700 hover:text-blue-900">
            Vendor Baseline Portal
          </Link>.
        </AlertDescription>
      </Alert>

      {/* Create a new approved baseline (instrument + image) */}
      <CreateManufacturerBaseline />

      {/* Component */}
      <ManufacturerBaselinePanel />
    </div>
  );
}
