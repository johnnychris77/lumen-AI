import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, Plus, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import {
  baselineLibraryApi,
  formatLifecycleLabel,
  type BaselineImageLink,
} from "@/lib/baselineLibraryApi";

const REVIEW_ROLES = new Set(["admin", "spd_manager", "clinical_reviewer"]);
const LEGACY_REPORT_ROLES = new Set(["admin", "spd_manager"]);

function statusVariant(status: string): "success" | "warning" | "destructive" | "secondary" | "outline" {
  if (status === "ACTIVE") return "success";
  if (status === "PENDING_REVIEW" || status === "SUSPENDED") return "warning";
  if (status === "REJECTED") return "destructive";
  if (status === "SUPERSEDED" || status === "ARCHIVED") return "secondary";
  return "outline";
}

export default function BaselineLibraryPage() {
  const { role } = useAuth();
  const [images, setImages] = useState<BaselineImageLink[] | null>(null);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  async function load() {
    setError("");
    try {
      const res = await baselineLibraryApi.listImages(statusFilter ? { lifecycle_status: statusFilter } : undefined);
      setImages(res.images);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load the baseline image library.");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
            <BookOpen className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-slate-900">Baseline Image Library</h2>
            <p className="text-sm text-slate-500 mt-0.5 max-w-2xl">
              Governed image evidence linked to existing baseline entries — every image below is a real
              LCID-registered image, never a duplicated copy, and only an <strong>ACTIVE</strong>, approved
              image may influence live inspection comparison.
            </p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          {REVIEW_ROLES.has(role) && (
            <Link to="/baselines/review">
              <Button variant="outline">
                <ShieldCheck className="h-4 w-4 mr-1.5" /> Review queue
              </Button>
            </Link>
          )}
          <Link to="/baselines/library/new">
            <Button>
              <Plus className="h-4 w-4 mr-1.5" /> Link new baseline image
            </Button>
          </Link>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap text-sm">
        <span className="text-slate-500">Filter by status:</span>
        <button
          onClick={() => setStatusFilter("")}
          className={`px-2.5 py-1 rounded-full border ${!statusFilter ? "bg-slate-900 text-white border-slate-900" : "border-slate-300 text-slate-600"}`}
        >
          All
        </button>
        {["DRAFT", "PENDING_REVIEW", "APPROVED", "ACTIVE", "SUSPENDED", "SUPERSEDED", "REJECTED", "ARCHIVED"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-2.5 py-1 rounded-full border ${statusFilter === s ? "bg-slate-900 text-white border-slate-900" : "border-slate-300 text-slate-600"}`}
          >
            {formatLifecycleLabel(s)}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {!images && !error && (
        <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading baseline image links…</span>
        </div>
      )}

      {images && images.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
          No baseline image links match this filter yet. Link an existing LCID image to a baseline entry to begin.
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
                <th className="text-left px-3 py-2 font-medium">View</th>
                <th className="text-left px-3 py-2 font-medium">Source type</th>
                <th className="text-left px-3 py-2 font-medium">Version</th>
                <th className="text-left px-3 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {images.map((img) => (
                <tr key={img.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-2">
                    <Link to={`/baselines/library/${img.id}`} className="font-medium text-blue-600 hover:underline">
                      #{img.id}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-slate-600">#{img.baseline_library_entry_id}</td>
                  <td className="px-3 py-2 text-slate-600">
                    {img.manufacturer || "—"} {img.model_name ? `/ ${img.model_name}` : ""}
                  </td>
                  <td className="px-3 py-2 text-slate-600">{img.anatomy_zone || "—"}</td>
                  <td className="px-3 py-2 text-slate-600">{img.inspection_view || "—"}</td>
                  <td className="px-3 py-2 text-slate-600">{img.source_type.replace(/_/g, " ") || "—"}</td>
                  <td className="px-3 py-2 text-slate-600">{img.baseline_version || "—"}</td>
                  <td className="px-3 py-2">
                    <Badge variant={statusVariant(img.lifecycle_status)}>{formatLifecycleLabel(img.lifecycle_status)}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center justify-between gap-3 flex-wrap pt-2 border-t border-slate-100 text-xs text-slate-400">
        <span>
          Legacy manufacturer/vendor baseline workflows remain available at{" "}
          <Link to="/manufacturer-baselines" className="underline hover:text-slate-600">Manufacturer Baselines</Link>
          {" "}and{" "}
          <Link to="/vendor-baseline-portal" className="underline hover:text-slate-600">Vendor Baselines</Link>
          {" "}— this library governs image-backed evidence specifically.
        </span>
        {LEGACY_REPORT_ROLES.has(role) && (
          <Link to="/baselines/library?report=1" className="underline hover:text-slate-600 whitespace-nowrap">
            View legacy migration report
          </Link>
        )}
      </div>

      {LEGACY_REPORT_ROLES.has(role) && new URLSearchParams(window.location.search).get("report") === "1" && (
        <LegacyReportPanel />
      )}
    </div>
  );
}

function LegacyReportPanel() {
  const [report, setReport] = useState<Awaited<ReturnType<typeof baselineLibraryApi.legacyReport>> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    baselineLibraryApi
      .legacyReport()
      .then(setReport)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load the legacy migration report."));
  }, []);

  if (error) return <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>;
  if (!report) return <div className="text-sm text-slate-500">Loading legacy migration report…</div>;

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-2">
      <h3 className="text-sm font-semibold text-slate-900">Legacy Baseline Migration Report (Section 15)</h3>
      <p className="text-xs text-slate-500">
        Every pre-existing metadata-only baseline entry without an ACTIVE linked image is marked{" "}
        <code className="font-mono">{report.missing_image_evidence_marker}</code> and cannot participate in
        image-based comparison.
      </p>
      <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
        <div><dt className="text-slate-400">Total entries</dt><dd className="font-semibold text-slate-900">{report.total_baseline_entries}</dd></div>
        <div><dt className="text-slate-400">With active image</dt><dd className="font-semibold text-green-700">{report.with_active_image.length}</dd></div>
        <div><dt className="text-slate-400">Missing image evidence</dt><dd className="font-semibold text-amber-700">{report.missing_image_evidence.length}</dd></div>
        <div><dt className="text-slate-400">Missing anatomy zone</dt><dd className="font-semibold text-amber-700">{report.missing_anatomy_zone.length}</dd></div>
        <div><dt className="text-slate-400">Missing usage rights</dt><dd className="font-semibold text-amber-700">{report.missing_usage_rights.length}</dd></div>
        <div><dt className="text-slate-400">Needing review</dt><dd className="font-semibold text-amber-700">{report.needing_review.length}</dd></div>
      </dl>
    </div>
  );
}
