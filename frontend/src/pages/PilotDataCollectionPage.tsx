import { useEffect, useState } from "react";
import { Database } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface IssueDetail {
  inspection_id: number;
  issues: { code: string; message: string }[];
  is_dataset_ready: boolean;
}

interface Summary {
  facility_name: string;
  department: string;
  inspections_collected: number;
  baseline_images_collected: number;
  inspection_images_collected: number;
  supervisor_reviews_completed: number;
  incomplete_inspections: number;
  incomplete_inspection_details: IssueDetail[];
  failed_uploads: number;
  missing_anatomy_zones: number;
  dataset_ready_images: number;
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-2xl font-bold text-slate-900">{value}</div>
    </div>
  );
}

export default function PilotDataCollectionPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<Summary>("/api/pilot-deployment/data-collection")
      .then(setSummary)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (error) {
    return (
      <div className="p-6 text-sm text-red-600">
        Failed to load pilot data collection status: {error}
        {error.includes("403") && (
          <p className="mt-1 text-slate-500">This dashboard is restricted to admins and SPD managers.</p>
        )}
      </div>
    );
  }
  if (!summary) return <div className="p-6 text-sm text-slate-500">Loading…</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
      <div className="flex items-center gap-2">
        <Database className="h-6 w-6 text-emerald-600" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Pilot Data Collection</h1>
          <p className="text-sm text-slate-500 mt-1">
            {summary.facility_name || "Facility not yet configured"}
            {summary.department && ` · ${summary.department}`} — dataset readiness for the pilot.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Inspections Collected" value={summary.inspections_collected} />
        <Stat label="Baseline Images Collected" value={summary.baseline_images_collected} />
        <Stat label="Inspection Images Collected" value={summary.inspection_images_collected} />
        <Stat label="Supervisor Reviews Completed" value={summary.supervisor_reviews_completed} />
        <Stat label="Dataset-Ready Inspections" value={summary.dataset_ready_images} />
        <Stat label="Incomplete Inspections" value={summary.incomplete_inspections} />
        <Stat label="Missing Anatomy Zones" value={summary.missing_anatomy_zones} />
        <Stat label="Failed Uploads" value={summary.failed_uploads} />
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">
          Incomplete Inspections ({summary.incomplete_inspection_details.length} shown)
        </p>
        {summary.incomplete_inspection_details.length === 0 ? (
          <p className="text-sm text-slate-400">Every inspection currently meets the site's data quality thresholds.</p>
        ) : (
          <div className="space-y-2 text-sm">
            {summary.incomplete_inspection_details.map((d) => (
              <div key={d.inspection_id} className="border-t border-slate-100 pt-2">
                <p className="font-medium">Inspection #{d.inspection_id}</p>
                <ul className="list-disc list-inside text-slate-500">
                  {d.issues.map((issue) => (
                    <li key={issue.code}>{issue.message}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
