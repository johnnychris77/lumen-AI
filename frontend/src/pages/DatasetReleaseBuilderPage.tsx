import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, PackageCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";

const RELEASE_ROLES = ["admin", "ai_researcher"];
const EXPORT_FORMATS = ["classification", "yolo", "coco", "pascal_voc", "segmentation", "csv", "json"];

interface ReleasePreview {
  candidate_count: number;
  candidate_annotation_ids: number[];
  ground_truth_versions: number[];
  distribution: { by_label: Record<string, number>; by_facility: Record<string, number>; by_manufacturer: Record<string, number>; by_instrument_family: Record<string, number> };
  duplicate_groups: { image_sha256: string; count: number; entry_ids: number[] }[];
  split_preview: { counts: Record<string, number>; leakage_free: boolean };
}

interface ExportPreview {
  export_format: string;
  record_count: number;
  excluded_count: number;
  class_distribution: Record<string, number>;
  missing_data_warnings: string[];
  dataset_versions: number[];
  ground_truth_versions: number[];
  export_timestamp: string;
}

interface DatasetVersionOption { id: number; version_label: string; frozen: boolean; }

function DistributionList({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return null;
  return (
    <div>
      <p className="text-xs font-medium text-slate-500 mb-1">{title}</p>
      <ul className="space-y-0.5">
        {entries.map(([k, v]) => (
          <li key={k} className="flex justify-between text-xs text-slate-700">
            <span>{k}</span><span className="font-mono">{v}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function DatasetReleaseBuilderPage() {
  const { role } = useAuth();
  const [preview, setPreview] = useState<ReleasePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [versions, setVersions] = useState<DatasetVersionOption[] | null>(null);
  const [versionId, setVersionId] = useState("");
  const [exportFormat, setExportFormat] = useState("classification");
  const [exportPreview, setExportPreview] = useState<ExportPreview | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"build" | "freeze" | null>(null);
  const [actionMsg, setActionMsg] = useState<{ type: "success" | "error"; message: string } | null>(null);

  function load() {
    apiFetch<ReleasePreview>("/api/dataset-release/preview")
      .then(setPreview)
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Failed to load the release preview."));
    apiFetch<{ versions: DatasetVersionOption[] }>("/api/dataset-registry/versions")
      .then((r) => {
        setVersions(r.versions);
        const usable = r.versions.find((v) => !v.frozen);
        if (usable) setVersionId(String(usable.id));
      })
      .catch(() => setVersions([]));
  }

  useEffect(load, []);

  useEffect(() => {
    setExportPreview(null);
    setExportError(null);
    apiFetch<ExportPreview>(`/api/dataset-release/export-preview?export_format=${exportFormat}`)
      .then(setExportPreview)
      .catch((e: unknown) => setExportError(e instanceof ApiError ? e.message : "Failed to load export preview."));
  }, [exportFormat]);

  async function buildTrainingDataset() {
    if (!versionId) return;
    setBusy("build");
    setActionMsg(null);
    try {
      await apiFetch(`/api/dataset-registry/versions/${versionId}/build-training-dataset`, { method: "POST" });
      setActionMsg({ type: "success", message: "Train/validation/test splits assigned for this dataset version." });
    } catch (e) {
      setActionMsg({ type: "error", message: e instanceof ApiError ? e.message : "Split assignment failed." });
    } finally {
      setBusy(null);
    }
  }

  async function freezeVersion() {
    if (!versionId) return;
    if (!window.confirm("Freezing this dataset version is permanent — no further images can be registered into it. Continue?")) return;
    setBusy("freeze");
    setActionMsg(null);
    try {
      await apiFetch(`/api/dataset-registry/versions/${versionId}/freeze`, { method: "POST" });
      setActionMsg({ type: "success", message: "Dataset version frozen." });
      load();
    } catch (e) {
      setActionMsg({ type: "error", message: e instanceof ApiError ? e.message : "Freeze failed." });
    } finally {
      setBusy(null);
    }
  }

  if (!RELEASE_ROLES.includes(role)) {
    return (
      <div role="alert" className="mx-auto mt-16 max-w-md rounded-lg border border-slate-200 bg-white p-8 text-center">
        <h2 className="text-lg font-semibold text-slate-900">Not authorized</h2>
        <p className="mt-2 text-sm text-slate-600">Dataset releases are restricted to AI Researcher and Administrator roles.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <PackageCheck className="h-6 w-6 text-blue-600" />
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Dataset Release Builder</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Inspect Ground-Truth-approved candidates, check for duplicates and split-leakage
            risk, then assign splits and freeze an immutable version.
          </p>
        </div>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" /><p>{error}</p>
        </div>
      )}

      {!preview && !error && (
        <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
          <Spinner className="h-5 w-5" /> <span className="text-sm">Loading release preview…</span>
        </div>
      )}

      {preview && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Release Candidates</CardTitle>
            <CardDescription>{preview.candidate_count} Ground-Truth-approved, gate-cleared image(s).</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <DistributionList title="By observation" data={preview.distribution.by_label} />
              <DistributionList title="By facility" data={preview.distribution.by_facility} />
              <DistributionList title="By manufacturer" data={preview.distribution.by_manufacturer} />
              <DistributionList title="By instrument family" data={preview.distribution.by_instrument_family} />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Duplicate groups detected:</span>
              <Badge variant={preview.duplicate_groups.length ? "destructive" : "success"}>{preview.duplicate_groups.length}</Badge>
            </div>

            <div className="flex items-center gap-4 flex-wrap text-xs text-slate-600">
              <span>Split preview — train: {preview.split_preview.counts.train ?? 0} · validation: {preview.split_preview.counts.validation ?? 0} · test: {preview.split_preview.counts.test ?? 0}</span>
              <Badge variant={preview.split_preview.leakage_free ? "success" : "destructive"}>
                {preview.split_preview.leakage_free ? "No leakage risk detected" : "Leakage risk detected"}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Assign Splits &amp; Freeze</CardTitle>
          <CardDescription>Freezing is permanent — a correction requires a new dataset version.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Select value={versionId} onChange={(e) => setVersionId(e.target.value)} className="max-w-xs">
            <option value="">Select a dataset version…</option>
            {(versions ?? []).map((v) => (
              <option key={v.id} value={v.id} disabled={v.frozen}>{v.version_label}{v.frozen ? " (frozen)" : ""}</option>
            ))}
          </Select>
          {actionMsg && (
            <div role="alert" className={`flex items-start gap-2 rounded-lg border p-2.5 text-sm ${actionMsg.type === "success" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-800"}`}>
              {actionMsg.type === "success" ? <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" /> : <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />}
              <p>{actionMsg.message}</p>
            </div>
          )}
          <div className="flex gap-3">
            <Button variant="outline" disabled={!versionId || busy !== null} onClick={buildTrainingDataset}>
              {busy === "build" && <Spinner className="h-4 w-4" />} Assign Train/Val/Test Splits
            </Button>
            <Button variant="destructive" disabled={!versionId || busy !== null} onClick={freezeVersion}>
              {busy === "freeze" && <Spinner className="h-4 w-4" />} Freeze Version
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Export Preview</CardTitle>
          <CardDescription>Region-dependent formats never fabricate a box or mask that wasn't stored.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Select value={exportFormat} onChange={(e) => setExportFormat(e.target.value)} className="max-w-xs">
            {EXPORT_FORMATS.map((f) => <option key={f} value={f}>{f}</option>)}
          </Select>

          {exportError && (
            <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-2.5 text-sm text-red-800">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" /><p>{exportError}</p>
            </div>
          )}
          {!exportPreview && !exportError && <Spinner className="h-5 w-5" />}
          {exportPreview && (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div><p className="text-slate-500">Records</p><p className="font-mono text-slate-800">{exportPreview.record_count}</p></div>
                <div><p className="text-slate-500">Excluded</p><p className="font-mono text-slate-800">{exportPreview.excluded_count}</p></div>
                <div><p className="text-slate-500">GT versions</p><p className="font-mono text-slate-800">{exportPreview.ground_truth_versions.join(", ") || "—"}</p></div>
                <div><p className="text-slate-500">Generated</p><p className="font-mono text-slate-800">{new Date(exportPreview.export_timestamp).toLocaleString()}</p></div>
              </div>
              <DistributionList title="Class distribution" data={exportPreview.class_distribution} />
              {exportPreview.missing_data_warnings.map((w, i) => (
                <p key={i} className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-2">{w}</p>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
