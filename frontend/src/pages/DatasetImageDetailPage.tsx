import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, Minus, Plus, RotateCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { AuthenticatedImage } from "@/components/ui/authenticated-image";
import { apiFetch, ApiError } from "@/lib/api";
import type { AnnotationRecord, DatasetEntry } from "@/lib/canvasTypes";

interface BaselineComparison {
  found: boolean;
  any_baseline_available: boolean;
  baselines: Record<string, { available: boolean; reason?: string; source?: Record<string, unknown> }>;
}

interface TwinHistory {
  digital_twin_id: string;
  is_tracked: boolean;
  historical_image_count: number;
  inspection_history_count: number;
  repair_history_count: number;
  timeline: { id: number; lcid: string; image_type: string; capture_date: string | null; review_status: string }[];
}

function ContextRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3 text-sm py-1">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-900 font-medium text-right">{value ?? "—"}</span>
    </div>
  );
}

export default function DatasetImageDetailPage() {
  const { imageId } = useParams<{ imageId: string }>();
  const [entry, setEntry] = useState<DatasetEntry | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [annotations, setAnnotations] = useState<AnnotationRecord[]>([]);
  const [baseline, setBaseline] = useState<BaselineComparison | null>(null);
  const [twin, setTwin] = useState<TwinHistory | null>(null);

  useEffect(() => {
    if (!imageId) return;
    let cancelled = false;
    setEntry(null);
    setLoadError(null);

    apiFetch<{ count: number; images: DatasetEntry[] }>("/api/dataset-registry/images")
      .then((res) => {
        if (cancelled) return;
        const found = res.images.find((e) => String(e.id) === imageId) ?? null;
        if (!found) {
          setLoadError("Image not found in this tenant's dataset registry.");
          return;
        }
        setEntry(found);

        apiFetch<{ count: number; annotations: AnnotationRecord[] }>(
          `/api/annotations?retained_image_id=${found.retained_image_id}`
        )
          .then((r) => !cancelled && setAnnotations(r.annotations))
          .catch(() => {});

        apiFetch<BaselineComparison>(`/api/dataset-registry/images/${found.id}/baseline-comparison`)
          .then((r) => !cancelled && setBaseline(r))
          .catch(() => {});

        if (found.digital_twin_id) {
          apiFetch<TwinHistory>(`/api/dataset-registry/digital-twin/${encodeURIComponent(found.digital_twin_id)}/history`)
            .then((r) => !cancelled && setTwin(r))
            .catch(() => {});
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setLoadError(e instanceof ApiError ? e.message : "Failed to load this image.");
      });

    return () => {
      cancelled = true;
    };
  }, [imageId]);

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center" role="alert">
        <AlertTriangle className="h-8 w-8 text-red-400" />
        <p className="text-sm text-slate-600">{loadError}</p>
        <Link to="/dataset/images" className="text-sm text-blue-600 hover:underline">Back to image library</Link>
      </div>
    );
  }

  if (!entry) {
    return (
      <div className="flex items-center justify-center gap-3 py-20 text-slate-500">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading image…</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold text-slate-900 font-mono">{entry.lcid}</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {entry.instrument_family || "Unknown instrument"} · {entry.manufacturer || "Unknown manufacturer"}
          </p>
        </div>
        <Link to={`/annotations?retained_image_id=${entry.retained_image_id}`}>
          <Button>Annotate this image</Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* (A) Image Viewer */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">Image Viewer</CardTitle>
            <div className="flex items-center gap-1">
              <Button size="icon" variant="ghost" aria-label="Zoom out" onClick={() => setZoom((z) => Math.max(1, z - 0.25))}>
                <Minus className="h-4 w-4" />
              </Button>
              <Button size="icon" variant="ghost" aria-label="Zoom in" onClick={() => setZoom((z) => Math.min(4, z + 0.25))}>
                <Plus className="h-4 w-4" />
              </Button>
              <Button size="icon" variant="ghost" aria-label="Reset zoom" onClick={() => setZoom(1)}>
                <RotateCcw className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="w-full h-80 overflow-auto rounded-lg border border-slate-200 bg-slate-950 flex items-center justify-center">
              <div style={{ transform: `scale(${zoom})`, transformOrigin: "center" }} className="transition-transform">
                <AuthenticatedImage
                  retainedImageId={entry.retained_image_id}
                  alt={`${entry.lcid} full resolution`}
                  className="max-h-80 max-w-full object-contain"
                />
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-2">
              Zoom {(zoom * 100).toFixed(0)}%. Brightness/contrast adjustment is view-only and
              never alters the stored source image (not yet implemented in this release).
            </p>
          </CardContent>
        </Card>

        {/* (B) Instrument Context */}
        <Card>
          <CardHeader><CardTitle className="text-base">Instrument Context</CardTitle></CardHeader>
          <CardContent>
            <ContextRow label="Instrument ID" value={entry.instrument_id} />
            <ContextRow label="Family" value={entry.instrument_family} />
            <ContextRow label="Model" value={entry.instrument_model} />
            <ContextRow label="Manufacturer" value={entry.manufacturer} />
            <ContextRow label="Catalog number" value={entry.catalog_number} />
            <ContextRow label="Anatomy zone" value={entry.anatomy_zone} />
            <ContextRow label="Inspection region" value={entry.inspection_region} />
            <ContextRow
              label="Digital Twin"
              value={
                entry.digital_twin_id ? (
                  <span className="font-mono text-xs">{entry.digital_twin_id}</span>
                ) : "Untracked"
              }
            />
            {twin && (
              <div className="mt-3 pt-3 border-t border-slate-100 space-y-2">
                <p className="text-xs text-slate-500">
                  {twin.historical_image_count} linked image(s) · {twin.inspection_history_count} inspection(s) ·{" "}
                  {twin.repair_history_count} repair event(s)
                  {!twin.is_tracked && " (untracked — no barcode/UDI captured for this instrument)"}
                </p>
                {twin.timeline.length > 0 && (
                  <ol className="space-y-1">
                    {twin.timeline.map((t) => (
                      <li key={t.id} className="flex items-center justify-between gap-2 text-xs">
                        <Link to={`/dataset/images/${t.id}`} className="font-mono text-blue-600 hover:underline">{t.lcid}</Link>
                        <span className="text-slate-500">{(t.image_type || "unknown").replace(/_/g, " ")}</span>
                        <span className="text-slate-400">{t.capture_date ? new Date(t.capture_date).toLocaleDateString() : "—"}</span>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* (C) Baseline Context */}
        <Card>
          <CardHeader><CardTitle className="text-base">Baseline Context</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {!baseline && <p className="text-xs text-slate-400">Loading baseline comparison…</p>}
            {baseline && !baseline.any_baseline_available && (
              <p className="text-sm text-slate-500">
                No approved baseline is currently resolved for this instrument — comparison is
                unavailable rather than presented as authoritative.
              </p>
            )}
            {baseline &&
              Object.entries(baseline.baselines).map(([type, info]) => (
                <div key={type} className="flex items-start justify-between gap-2 text-sm">
                  <span className="capitalize text-slate-600">{type.replace(/_/g, " ")}</span>
                  {info.available ? (
                    <Badge variant="success">Available</Badge>
                  ) : (
                    <span className="text-xs text-slate-400 text-right max-w-[60%]">{info.reason}</span>
                  )}
                </div>
              ))}
          </CardContent>
        </Card>

        {/* (D) Review Context */}
        <Card>
          <CardHeader><CardTitle className="text-base">Review Context</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <ContextRow label="Registry review status" value={<Badge variant="outline">{entry.review_status}</Badge>} />
            <ContextRow label="Usage rights" value={entry.usage_rights || "Not recorded"} />
            <ContextRow label="PHI verification" value={entry.phi_verification} />
            <div className="pt-2 border-t border-slate-100">
              <p className="text-xs font-medium text-slate-500 mb-1.5">Annotations ({annotations.length})</p>
              {annotations.length === 0 && <p className="text-xs text-slate-400">No annotations recorded yet.</p>}
              <ul className="space-y-1.5">
                {annotations.map((a) => (
                  <li key={a.id} className="flex items-center justify-between gap-2 text-xs">
                    <Link to={`/annotations/${a.id}`} className="font-mono text-blue-600 hover:underline">{a.ann_id}</Link>
                    <span className="text-slate-500 truncate">{a.primary_observation || "unclassified"}</span>
                    <Badge variant={a.ground_truth_status === "ACTIVE" ? "success" : "secondary"}>
                      {a.ground_truth_status === "ACTIVE" ? "Ground Truth" : "Draft"}
                    </Badge>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
