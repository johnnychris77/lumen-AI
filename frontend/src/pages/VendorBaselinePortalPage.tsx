import { Link } from "react-router-dom";
import { Store, ChevronRight } from "lucide-react";
import VendorBaselineSubscriptionPortal from "../components/VendorBaselineSubscriptionPortal";
import { Alert, AlertDescription } from "@/components/ui/alert";

export default function VendorBaselinePortalPage() {
  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/" className="hover:text-slate-600">Dashboard</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-600 font-medium">Vendor Baseline Portal</span>
      </nav>

      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-100">
          <Store className="h-5 w-5 text-teal-600" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Vendor Baseline Subscription Portal</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Manufacturers and vendors submit reference baselines for their instruments here.
            Once approved by a hospital administrator, baselines activate for AI-assisted inspection scoring.
          </p>
        </div>
      </div>

      <Alert variant="info">
        <AlertDescription>
          <strong>Vendor users:</strong> Submit one baseline per instrument model — include catalog number,
          barcode or QR value, IFU reference, and acceptable-condition notes. Hospital administrators will
          review and approve before it activates.{" "}
          <Link to="/baseline-review" className="underline text-blue-700 hover:text-blue-900">
            Track approval status →
          </Link>
        </AlertDescription>
      </Alert>

      <VendorBaselineSubscriptionPortal />
    </div>
  );
}
