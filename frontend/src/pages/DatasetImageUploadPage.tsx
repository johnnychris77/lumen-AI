import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, CheckCircle2, UploadCloud } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { apiFetch, ApiError } from "@/lib/api";
import { IMAGE_TYPES } from "@/lib/canvasTypes";

// Project Canvas — Sections 2, 3 & 4: Image Ingestion + Minimum Registration
// Form + Bulk Ingestion. Talks directly to the governed
// `/api/dataset-ingestion/images` (+ `/bulk`) endpoints — no client-side
// duplicate/metadata policy is re-implemented here; the backend is the
// single source of truth for what's accepted.

interface DatasetVersionOption {
  id: number;
  version_label: string;
  frozen: boolean;
}

const REQUIRED_MARK = <span className="text-red-500 ml-0.5">*</span>;

function FieldLabel({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <Label>
      {children}
      {required && REQUIRED_MARK}
    </Label>
  );
}

export default function DatasetImageUploadPage() {
  const navigate = useNavigate();
  const [versions, setVersions] = useState<DatasetVersionOption[] | null>(null);
  const [versionId, setVersionId] = useState<string>("");
  const [newVersionLabel, setNewVersionLabel] = useState("");
  const [creatingVersion, setCreatingVersion] = useState(false);
  const [dirty, setDirty] = useState(false);

  // Single-image form state
  const [file, setFile] = useState<File | null>(null);
  const [instrumentId, setInstrumentId] = useState("");
  const [instrumentFamily, setInstrumentFamily] = useState("");
  const [instrumentModel, setInstrumentModel] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [catalogNumber, setCatalogNumber] = useState("");
  const [anatomyZone, setAnatomyZone] = useState("");
  const [inspectionRegion, setInspectionRegion] = useState("");
  const [captureDevice, setCaptureDevice] = useState("");
  const [imageResolution, setImageResolution] = useState("");
  const [facility, setFacility] = useState("");
  const [operator, setOperator] = useState("");
  const [imageType, setImageType] = useState("");
  const [usageRights, setUsageRights] = useState("");
  const [reviewerNotes, setReviewerNotes] = useState("");
  const [consent, setConsent] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error" | "duplicate"; message: string } | null>(null);

  // Bulk upload state
  const [bulkFiles, setBulkFiles] = useState<FileList | null>(null);
  const [bulkCsv, setBulkCsv] = useState<File | null>(null);
  const [bulkSubmitting, setBulkSubmitting] = useState(false);
  const [bulkResult, setBulkResult] = useState<{
    success_count: number; error_count: number; duplicate_count: number;
    rows: { filename: string; success: boolean; duplicate: boolean; error: string | null; lcid: string | null }[];
  } | null>(null);
  const [bulkError, setBulkError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<{ count: number; versions: DatasetVersionOption[] }>("/api/dataset-registry/versions")
      .then((r) => {
        setVersions(r.versions);
        const usable = r.versions.find((v) => !v.frozen);
        if (usable) setVersionId(String(usable.id));
      })
      .catch(() => setVersions([]));
  }, []);

  // Warn before navigating away with unsaved single-image form work.
  useEffect(() => {
    function handler(e: BeforeUnloadEvent) {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    }
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  function markDirty() {
    setDirty(true);
    setResult(null);
  }

  async function createVersion() {
    if (!newVersionLabel.trim()) return;
    setCreatingVersion(true);
    try {
      const row = await apiFetch<DatasetVersionOption>("/api/dataset-registry/versions", {
        method: "POST",
        body: { version_label: newVersionLabel.trim() },
      });
      setVersions((v) => [row, ...(v ?? [])]);
      setVersionId(String(row.id));
      setNewVersionLabel("");
    } catch (e) {
      setResult({ type: "error", message: e instanceof ApiError ? e.message : "Failed to create dataset version." });
    } finally {
      setCreatingVersion(false);
    }
  }

  async function submitSingle(e: React.FormEvent) {
    e.preventDefault();
    setResult(null);
    if (!file) {
      setResult({ type: "error", message: "Choose an image file to upload." });
      return;
    }
    if (file.size === 0) {
      setResult({ type: "error", message: "The selected file is empty." });
      return;
    }
    if (!versionId) {
      setResult({ type: "error", message: "Select or create a dataset version first." });
      return;
    }
    if (!usageRights.trim()) {
      setResult({ type: "error", message: "A usage-rights status is required." });
      return;
    }
    if (!consent) {
      setResult({ type: "error", message: "Consent to retain this image is required before it can be registered." });
      return;
    }

    const form = new FormData();
    form.set("image", file);
    form.set("consent", String(consent));
    form.set("dataset_version_id", versionId);
    form.set("usage_rights", usageRights);
    form.set("instrument_id", instrumentId);
    form.set("instrument_family", instrumentFamily);
    form.set("instrument_model", instrumentModel);
    form.set("manufacturer", manufacturer);
    form.set("catalog_number", catalogNumber);
    form.set("anatomy_zone", anatomyZone);
    form.set("inspection_region", inspectionRegion);
    form.set("capture_device", captureDevice);
    form.set("image_resolution", imageResolution);
    form.set("facility", facility);
    form.set("operator", operator);
    form.set("image_type", imageType);
    form.set("reviewer_notes", reviewerNotes);

    setSubmitting(true);
    try {
      const res = await apiFetch<{
        duplicate: boolean;
        message?: string;
        entry?: { id: number; lcid: string };
        existing_entry?: { id: number; lcid: string };
      }>("/api/dataset-ingestion/images", { method: "POST", body: form });

      if (res.duplicate) {
        setResult({
          type: "duplicate",
          message: res.message || `Duplicate of an already-registered image (${res.existing_entry?.lcid}).`,
        });
      } else {
        setDirty(false);
        setResult({ type: "success", message: `Registered as ${res.entry?.lcid}.` });
        setTimeout(() => {
          if (res.entry?.id) navigate(`/dataset/images/${res.entry.id}`);
        }, 900);
      }
    } catch (e) {
      setResult({ type: "error", message: e instanceof ApiError ? e.message : "Upload failed." });
    } finally {
      setSubmitting(false);
    }
  }

  async function submitBulk(e: React.FormEvent) {
    e.preventDefault();
    setBulkError(null);
    setBulkResult(null);
    if (!bulkFiles || bulkFiles.length === 0) {
      setBulkError("Select one or more image files.");
      return;
    }
    if (!versionId) {
      setBulkError("Select or create a dataset version first.");
      return;
    }

    const form = new FormData();
    Array.from(bulkFiles).forEach((f) => form.append("images", f));
    form.set("consent", String(consent));
    form.set("dataset_version_id", versionId);
    form.set(
      "shared_metadata",
      JSON.stringify({
        usage_rights: usageRights, instrument_family: instrumentFamily, manufacturer,
        facility, operator, capture_device: captureDevice, image_resolution: imageResolution,
        image_type: imageType,
      })
    );
    if (bulkCsv) form.set("csv_metadata", bulkCsv);

    setBulkSubmitting(true);
    try {
      const res = await apiFetch<typeof bulkResult>("/api/dataset-ingestion/images/bulk", { method: "POST", body: form });
      setBulkResult(res);
    } catch (e) {
      setBulkError(e instanceof ApiError ? e.message : "Bulk upload failed.");
    } finally {
      setBulkSubmitting(false);
    }
  }

  const versionSelect = (
    <div className="flex flex-wrap items-end gap-3">
      <div className="min-w-56">
        <FieldLabel>Dataset version</FieldLabel>
        <Select value={versionId} onChange={(e) => { setVersionId(e.target.value); markDirty(); }}>
          <option value="">Select a version…</option>
          {(versions ?? []).filter((v) => !v.frozen).map((v) => (
            <option key={v.id} value={v.id}>{v.version_label}</option>
          ))}
        </Select>
      </div>
      <div className="flex items-end gap-2">
        <div>
          <FieldLabel>Or create a new version</FieldLabel>
          <Input
            value={newVersionLabel}
            onChange={(e) => setNewVersionLabel(e.target.value)}
            placeholder="e.g. canvas-intake-2026-07"
          />
        </div>
        <Button type="button" variant="outline" disabled={creatingVersion || !newVersionLabel.trim()} onClick={createVersion}>
          {creatingVersion ? <Spinner className="h-4 w-4" /> : "Create"}
        </Button>
      </div>
    </div>
  );

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Ingest Borescope Images</h2>
        <p className="text-sm text-slate-500 mt-1">
          Register a single image or a bulk batch into the governed dataset registry. Every
          image is deduplicated by content hash and validated against the required metadata
          before it receives a permanent LCID.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Dataset Version</CardTitle>
          <CardDescription>Images are always registered into a specific, versioned dataset.</CardDescription>
        </CardHeader>
        <CardContent>{versionSelect}</CardContent>
      </Card>

      {result && (
        <div
          role="alert"
          className={`flex items-start gap-3 rounded-lg p-4 border text-sm ${
            result.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : result.type === "duplicate"
              ? "bg-amber-50 border-amber-200 text-amber-800"
              : "bg-red-50 border-red-200 text-red-800"
          }`}
        >
          {result.type === "success" ? <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" /> : <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />}
          <p>{result.message}</p>
        </div>
      )}

      <form onSubmit={submitSingle} className="space-y-6" onChange={markDirty}>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Single Image Upload</CardTitle>
            <CardDescription>Accepted types: JPEG, PNG, WebP. Maximum 10 MB.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <FieldLabel required>Image file</FieldLabel>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                aria-label="Image file"
                onChange={(e) => { setFile(e.target.files?.[0] ?? null); markDirty(); }}
                className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-blue-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-blue-700"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <FieldLabel>Instrument ID</FieldLabel>
                <Input value={instrumentId} onChange={(e) => setInstrumentId(e.target.value)} placeholder="Serial / free-text ID" />
              </div>
              <div>
                <FieldLabel>Instrument family</FieldLabel>
                <Input value={instrumentFamily} onChange={(e) => setInstrumentFamily(e.target.value)} placeholder="e.g. laparoscope" />
              </div>
              <div>
                <FieldLabel>Instrument name / model</FieldLabel>
                <Input value={instrumentModel} onChange={(e) => setInstrumentModel(e.target.value)} placeholder="Optional" />
              </div>
              <div>
                <FieldLabel>Manufacturer</FieldLabel>
                <Input value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} placeholder="Optional if unknown" />
              </div>
              <div>
                <FieldLabel>Catalog number</FieldLabel>
                <Input value={catalogNumber} onChange={(e) => setCatalogNumber(e.target.value)} placeholder="Optional, where available" />
              </div>
              <div>
                <FieldLabel>Anatomy zone</FieldLabel>
                <Input value={anatomyZone} onChange={(e) => setAnatomyZone(e.target.value)} placeholder="Optional" />
              </div>
              <div>
                <FieldLabel>Inspection region</FieldLabel>
                <Input value={inspectionRegion} onChange={(e) => setInspectionRegion(e.target.value)} placeholder="Optional" />
              </div>
              <div>
                <FieldLabel>Capture device</FieldLabel>
                <Input value={captureDevice} onChange={(e) => setCaptureDevice(e.target.value)} placeholder="e.g. borescope_pro_3000" />
              </div>
              <div>
                <FieldLabel>Image resolution</FieldLabel>
                <Input value={imageResolution} onChange={(e) => setImageResolution(e.target.value)} placeholder="e.g. 1920x1080" />
              </div>
              <div>
                <FieldLabel>Facility / approved source</FieldLabel>
                <Input value={facility} onChange={(e) => setFacility(e.target.value)} placeholder="e.g. Test Hospital" />
              </div>
              <div>
                <FieldLabel>Reviewer / operator</FieldLabel>
                <Input value={operator} onChange={(e) => setOperator(e.target.value)} placeholder="Your identifier" />
              </div>
              <div>
                <FieldLabel required>Image type</FieldLabel>
                <Select value={imageType} onChange={(e) => setImageType(e.target.value)}>
                  <option value="">Select…</option>
                  {IMAGE_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </Select>
              </div>
              <div>
                <FieldLabel required>Usage rights</FieldLabel>
                <Input
                  value={usageRights}
                  onChange={(e) => setUsageRights(e.target.value)}
                  placeholder="e.g. internal_use_approved"
                />
              </div>
            </div>

            <div>
              <FieldLabel>Reviewer notes</FieldLabel>
              <Textarea value={reviewerNotes} onChange={(e) => setReviewerNotes(e.target.value)} rows={2} placeholder="Optional context for reviewers" />
            </div>

            <label className="flex items-start gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-0.5"
              />
              I confirm this image contains no patient-identifying information and consent is
              recorded to retain it in the governed dataset.
            </label>
          </CardContent>
        </Card>

        <div className="flex gap-3">
          <Button type="submit" disabled={submitting}>
            {submitting && <Spinner className="h-4 w-4" />}
            <UploadCloud className="h-4 w-4" /> Register Image
          </Button>
        </div>
      </form>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Bulk Ingestion</CardTitle>
          <CardDescription>
            Shared metadata above (instrument family, manufacturer, facility, operator, capture
            device, resolution, image type, usage rights) applies to every file unless a CSV
            override supplies a per-filename value. One bad file never fails the whole batch.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={submitBulk} className="space-y-4">
            <div>
              <FieldLabel required>Image files</FieldLabel>
              <input
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp"
                aria-label="Bulk image files"
                onChange={(e) => setBulkFiles(e.target.files)}
                className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-slate-200 file:px-4 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-300"
              />
            </div>
            <div>
              <FieldLabel>Per-filename CSV metadata override (optional)</FieldLabel>
              <input
                type="file"
                accept=".csv,text/csv"
                aria-label="CSV metadata override"
                onChange={(e) => setBulkCsv(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-slate-200 file:px-4 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-300"
              />
              <p className="text-xs text-slate-400 mt-1">
                Must include a <code className="bg-slate-100 px-1 rounded">filename</code> column;
                any registration-form field can be overridden per row.
              </p>
            </div>
            <Button type="submit" variant="outline" disabled={bulkSubmitting}>
              {bulkSubmitting && <Spinner className="h-4 w-4" />}
              Submit Batch
            </Button>
          </form>

          {bulkError && (
            <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <p>{bulkError}</p>
            </div>
          )}

          {bulkResult && (
            <div className="space-y-2">
              <p className="text-sm text-slate-700">
                <strong className="text-emerald-700">{bulkResult.success_count} registered</strong>
                {" · "}
                <strong className="text-amber-700">{bulkResult.duplicate_count} duplicate</strong>
                {" · "}
                <strong className="text-red-700">{bulkResult.error_count} failed</strong>
              </p>
              <div className="max-h-64 overflow-y-auto rounded-lg border border-slate-200">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-slate-500">
                    <tr>
                      <th className="text-left px-3 py-2">File</th>
                      <th className="text-left px-3 py-2">Status</th>
                      <th className="text-left px-3 py-2">Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bulkResult.rows.map((row, i) => (
                      <tr key={i} className="border-t border-slate-100">
                        <td className="px-3 py-1.5 font-mono">{row.filename}</td>
                        <td className="px-3 py-1.5">
                          {row.success ? (
                            <span className="text-emerald-700">Registered</span>
                          ) : row.duplicate ? (
                            <span className="text-amber-700">Duplicate</span>
                          ) : (
                            <span className="text-red-700">Failed</span>
                          )}
                        </td>
                        <td className="px-3 py-1.5 text-slate-500">{row.lcid || row.error || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
