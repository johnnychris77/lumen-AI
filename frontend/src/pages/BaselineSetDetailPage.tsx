import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronRight, ShieldAlert, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api";
import { baselineLibraryApi, formatLifecycleLabel, type BaselineSet } from "@/lib/baselineLibraryApi";

export default function BaselineSetDetailPage() {
  const { baselineSetId } = useParams<{ baselineSetId: string }>();
  const [set, setSet] = useState<BaselineSet | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!baselineSetId) return;
    baselineLibraryApi
      .getSet(Number(baselineSetId))
      .then(setSet)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load this baseline set."));
  }, [baselineSetId]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center" role="alert">
        <ShieldAlert className="h-8 w-8 text-red-400" />
        <p className="text-sm text-slate-600">{error}</p>
        <Link to="/baselines/library" className="text-sm text-blue-600 hover:underline">Back to Baseline Library</Link>
      </div>
    );
  }

  if (!set) {
    return (
      <div className="flex items-center justify-center gap-3 py-20 text-slate-500">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading baseline set…</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/baselines/library" className="hover:text-slate-600">Baseline Library</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-600 font-medium">Baseline set #{set.id}</span>
      </nav>

      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100">
          <Layers className="h-5 w-5 text-indigo-600" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-slate-900">
            Baseline set #{set.id} <Badge variant={set.active ? "success" : "secondary"} className="ml-2 align-middle">{set.active ? "Active" : formatLifecycleLabel(set.lifecycle_status)}</Badge>
          </h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {set.manufacturer || "Any manufacturer"} {set.model_name} · {set.instrument_family} ·{" "}
            {set.anatomy_zone || "no anatomy zone"} · version {set.version}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Governance Scope</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
          <Row label="View protocol" value={set.view_protocol} />
          <Row label="Orientation protocol" value={set.orientation_protocol} />
          <Row label="Effective date" value={set.effective_date ? new Date(set.effective_date).toLocaleDateString() : "—"} />
          {set.supersedes_set_id && (
            <Row label="Supersedes" value={<Link className="text-blue-600 hover:underline" to={`/baselines/sets/${set.supersedes_set_id}`}>#{set.supersedes_set_id}</Link>} />
          )}
          {set.limitations && (
            <div className="sm:col-span-2 mt-2 pt-2 border-t border-slate-100">
              <p className="text-xs font-medium text-slate-500 mb-1">Limitations</p>
              <p className="text-sm text-slate-700">{set.limitations}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Member Baseline Images ({set.baseline_image_link_ids.length})</CardTitle></CardHeader>
        <CardContent>
          {set.baseline_image_link_ids.length === 0 && (
            <p className="text-sm text-slate-400">No baseline images are grouped into this set yet.</p>
          )}
          <ul className="space-y-1.5">
            {set.baseline_image_link_ids.map((id) => (
              <li key={id}>
                <Link to={`/baselines/library/${id}`} className="text-sm text-blue-600 hover:underline">Baseline image #{id}</Link>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3 text-sm py-1">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-900 font-medium text-right">{value ?? "—"}</span>
    </div>
  );
}
