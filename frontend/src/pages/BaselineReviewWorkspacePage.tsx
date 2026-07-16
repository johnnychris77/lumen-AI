import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, ClipboardCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api";
import { baselineLibraryApi, type BaselineImageLink } from "@/lib/baselineLibraryApi";

export default function BaselineReviewWorkspacePage() {
  const [images, setImages] = useState<BaselineImageLink[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    baselineLibraryApi
      .listImages({ lifecycle_status: "PENDING_REVIEW" })
      .then((res) => setImages(res.images))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load the review queue."));
  }, []);

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/baselines/library" className="hover:text-slate-600">Baseline Library</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-600 font-medium">Review queue</span>
      </nav>

      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100">
          <ClipboardCheck className="h-5 w-5 text-emerald-600" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Baseline Image Review Queue</h2>
          <p className="text-sm text-slate-500 mt-0.5 max-w-2xl">
            Baseline images awaiting a real review decision before they can be activated. Every approval
            here requires a rationale and, for manufacturer-sourced images, real supporting provenance —
            never a bare status change.
          </p>
        </div>
      </div>

      <Alert variant="info">
        <AlertDescription>
          <strong>Clinical reviewers / SPD managers:</strong> Open each baseline image below to confirm
          anatomy-zone compatibility and image quality before approving or rejecting.
        </AlertDescription>
      </Alert>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {!images && !error && (
        <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading pending baseline images…</span>
        </div>
      )}

      {images && images.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
          Nothing is pending review right now.
        </div>
      )}

      {images && images.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="text-left px-3 py-2 font-medium">Link</th>
                <th className="text-left px-3 py-2 font-medium">Baseline entry</th>
                <th className="text-left px-3 py-2 font-medium">Manufacturer / model</th>
                <th className="text-left px-3 py-2 font-medium">Anatomy zone</th>
                <th className="text-left px-3 py-2 font-medium">Source type</th>
                <th className="text-left px-3 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {images.map((img) => (
                <tr key={img.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-2 font-medium text-slate-900">#{img.id}</td>
                  <td className="px-3 py-2 text-slate-600">#{img.baseline_library_entry_id}</td>
                  <td className="px-3 py-2 text-slate-600">{img.manufacturer || "—"} {img.model_name}</td>
                  <td className="px-3 py-2 text-slate-600">{img.anatomy_zone || "—"}</td>
                  <td className="px-3 py-2">
                    <Badge variant={img.source_type === "manufacturer_reference" ? "warning" : "outline"}>
                      {img.source_type.replace(/_/g, " ")}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Link to={`/baselines/library/${img.id}`} className="text-blue-600 hover:underline font-medium">Review →</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
