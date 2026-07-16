import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertTriangle, FilePlus2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { apiFetch, ApiError } from "@/lib/api";
import type { AnnotationRecord } from "@/lib/canvasTypes";
import { NewAnnotationForm } from "@/components/canvas/NewAnnotationForm";

export default function AnnotationsListPage() {
  const [params] = useSearchParams();
  const retainedImageId = params.get("retained_image_id");
  const [annotations, setAnnotations] = useState<AnnotationRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [gtFilter, setGtFilter] = useState("all");

  function load() {
    setAnnotations(null);
    const qs = new URLSearchParams();
    if (retainedImageId) qs.set("retained_image_id", retainedImageId);
    apiFetch<{ count: number; annotations: AnnotationRecord[] }>(`/api/annotations?${qs.toString()}`)
      .then((r) => setAnnotations(r.annotations))
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Failed to load annotations."));
  }

  useEffect(load, [retainedImageId]);

  const filtered = (annotations ?? []).filter(
    (a) => gtFilter === "all" || a.ground_truth_status === gtFilter
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Annotations</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Every observation recorded against a registered image, its region data, and its
          current Ground Truth status.
        </p>
      </div>

      {retainedImageId && (
        <Card className="border-blue-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-3 text-sm font-medium text-slate-700">
              <FilePlus2 className="h-4 w-4 text-blue-600" /> New annotation for image #{retainedImageId}
            </div>
            <NewAnnotationForm retainedImageId={Number(retainedImageId)} onCreated={load} />
          </CardContent>
        </Card>
      )}

      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-500">Ground Truth status</span>
        <Select value={gtFilter} onChange={(e) => setGtFilter(e.target.value)} className="w-40">
          <option value="all">All</option>
          <option value="DRAFT">Draft</option>
          <option value="ACTIVE">Ground Truth (Active)</option>
        </Select>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {!annotations && !error && (
        <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
          <Spinner className="h-5 w-5" /> <span className="text-sm">Loading annotations…</span>
        </div>
      )}

      {annotations && filtered.length === 0 && (
        <p className="text-sm text-slate-500 text-center py-12">No annotations match this view.</p>
      )}

      {annotations && filtered.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs">
              <tr>
                <th className="text-left px-4 py-2">Annotation</th>
                <th className="text-left px-4 py-2">Observation</th>
                <th className="text-left px-4 py-2">Region</th>
                <th className="text-left px-4 py-2">Reviewer</th>
                <th className="text-left px-4 py-2">Ground Truth</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((a) => (
                <tr key={a.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-2">
                    <Link to={`/annotations/${a.id}`} className="font-mono text-blue-600 hover:underline">{a.ann_id}</Link>
                  </td>
                  <td className="px-4 py-2">{a.primary_observation || "—"}</td>
                  <td className="px-4 py-2 text-slate-500">{a.region_type.replace(/_/g, " ")}</td>
                  <td className="px-4 py-2 text-slate-500">{a.reviewer || "—"}</td>
                  <td className="px-4 py-2">
                    <Badge variant={a.ground_truth_status === "ACTIVE" ? "success" : "secondary"}>
                      {a.ground_truth_status === "ACTIVE" ? "Active" : "Draft"}
                    </Badge>
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
