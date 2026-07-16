import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { apiFetch, ApiError } from "@/lib/api";
import type { DatasetEntry } from "@/lib/canvasTypes";
import {
  baselineLibraryApi,
  BASELINE_IMAGE_TYPES,
  BASELINE_SOURCE_TYPES,
  SOURCE_TYPES_REQUIRING_PROVENANCE,
} from "@/lib/baselineLibraryApi";

export default function BaselineImageNewPage() {
  const navigate = useNavigate();
  const [lcidImages, setLcidImages] = useState<DatasetEntry[]>([]);
  const [loadError, setLoadError] = useState("");

  const [baselineLibraryEntryId, setBaselineLibraryEntryId] = useState("");
  const [lcidImageId, setLcidImageId] = useState("");
  const [anatomyZone, setAnatomyZone] = useState("");
  const [inspectionView, setInspectionView] = useState("");
  const [orientation, setOrientation] = useState("");
  const [imageType, setImageType] = useState(BASELINE_IMAGE_TYPES[0]);
  const [sourceType, setSourceType] = useState(BASELINE_SOURCE_TYPES[0]);
  const [sourceOrganization, setSourceOrganization] = useState("");
  const [sourceReference, setSourceReference] = useState("");
  const [baselineVersion, setBaselineVersion] = useState("1.0");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<{ count: number; images: DatasetEntry[] }>("/api/dataset-registry/images")
      .then((res) => setLcidImages(res.images))
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : "Failed to load LCID-registered images."));
  }, []);

  const requiresProvenance = SOURCE_TYPES_REQUIRING_PROVENANCE.has(sourceType);
  const selectedImage = lcidImages.find((img) => String(img.id) === lcidImageId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const parsedBaselineId = Number(baselineLibraryEntryId);
    const parsedLcidId = Number(lcidImageId);
    if (!parsedBaselineId || !parsedLcidId) {
      setError("Enter a valid baseline library entry ID and select an LCID image.");
      return;
    }
    if (!anatomyZone.trim() || !inspectionView.trim()) {
      setError("Anatomy zone and inspection view are required — a baseline image must document both.");
      return;
    }
    if (requiresProvenance && !(sourceOrganization.trim() && sourceReference.trim())) {
      setError(
        "Manufacturer-reference source requires real supporting provenance (source organization and a " +
          "source reference such as a document ID) — it cannot be marked manufacturer-approved from a dropdown alone."
      );
      return;
    }

    setSubmitting(true);
    try {
      const link = await baselineLibraryApi.createImage({
        baseline_library_entry_id: parsedBaselineId,
        lcid_image_id: parsedLcidId,
        anatomy_zone: anatomyZone,
        inspection_view: inspectionView,
        orientation,
        image_type: imageType,
        source_type: sourceType,
        source_organization: sourceOrganization,
        source_reference: sourceReference,
        baseline_version: baselineVersion,
      });
      navigate(`/baselines/library/${link.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to link this baseline image.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/baselines/library" className="hover:text-slate-600">Baseline Library</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-600 font-medium">Link new baseline image</span>
      </nav>

      <div>
        <h2 className="text-xl font-semibold text-slate-900">Link a governed baseline image</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          This links an existing LCID-registered image to an existing baseline entry — it never
          re-uploads or duplicates image bytes. The new link starts in <strong>DRAFT</strong> and must
          pass review and activation before it can influence any comparison.
        </p>
      </div>

      {loadError && <Alert variant="destructive"><AlertDescription>{loadError}</AlertDescription></Alert>}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader><CardTitle className="text-base">1. Select the baseline entry and LCID image</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <Field label="Baseline library entry ID">
              <input
                type="number"
                min={1}
                value={baselineLibraryEntryId}
                onChange={(e) => setBaselineLibraryEntryId(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g. 12"
              />
              <p className="text-xs text-slate-400 mt-1">
                The existing metadata-only baseline entry (see the Manufacturer Baselines / Baseline
                Review pages, or the network baseline registry) that this image will provide evidence for.
              </p>
            </Field>

            <Field label="LCID-registered image">
              <select value={lcidImageId} onChange={(e) => setLcidImageId(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">Select a governed LCID image…</option>
                {lcidImages.map((img) => (
                  <option key={img.id} value={img.id}>
                    #{img.id} · {img.lcid} · {img.manufacturer || "Unknown"} {img.instrument_model || ""} ·{" "}
                    {img.anatomy_zone || "no zone recorded"}
                  </option>
                ))}
              </select>
              {selectedImage && (
                <p className="text-xs text-slate-400 mt-1">
                  Quality: {selectedImage.image_quality || "unrecorded"} · Usage rights:{" "}
                  {selectedImage.usage_rights || "unrecorded"} · PHI review: {selectedImage.phi_verification || "unrecorded"} ·
                  Digital Twin: {selectedImage.digital_twin_id || "untracked"}
                </p>
              )}
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">2. Document what this image represents</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Anatomy zone">
                <input value={anatomyZone} onChange={(e) => setAnatomyZone(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="e.g. distal_tip" />
              </Field>
              <Field label="Inspection view">
                <input value={inspectionView} onChange={(e) => setInspectionView(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="e.g. lateral" />
              </Field>
              <Field label="Orientation (optional)">
                <input value={orientation} onChange={(e) => setOrientation(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="e.g. 0_degree" />
              </Field>
              <Field label="Baseline version">
                <input value={baselineVersion} onChange={(e) => setBaselineVersion(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </Field>
            </div>

            <Field label="Baseline image type">
              <select value={imageType} onChange={(e) => setImageType(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500">
                {BASELINE_IMAGE_TYPES.map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                ))}
              </select>
              <p className="text-xs text-slate-400 mt-1">
                A baseline entry may hold multiple images for different anatomy zones, depths, orientations,
                and views — this is one such image, not a claim that it represents the entire instrument.
              </p>
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">3. Source provenance</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <Field label="Source type">
              <select value={sourceType} onChange={(e) => setSourceType(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500">
                {BASELINE_SOURCE_TYPES.map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                ))}
              </select>
            </Field>

            {requiresProvenance && (
              <Alert variant="warning">
                <AlertDescription>
                  Manufacturer-reference status requires real evidence of source — a dropdown selection
                  alone is never sufficient. Provide the supplying organization and a verifiable reference
                  (document ID, purchase order, vendor-portal submission ID).
                </AlertDescription>
              </Alert>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label={`Source organization${requiresProvenance ? " (required)" : ""}`}>
                <input value={sourceOrganization} onChange={(e) => setSourceOrganization(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </Field>
              <Field label={`Source reference${requiresProvenance ? " (required)" : ""}`}>
                <input value={sourceReference} onChange={(e) => setSourceReference(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </Field>
            </div>
          </CardContent>
        </Card>

        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

        <div className="flex justify-end gap-3">
          <Link to="/baselines/library"><Button type="button" variant="outline">Cancel</Button></Link>
          <Button type="submit" disabled={submitting}>{submitting ? "Linking…" : "Create baseline image link"}</Button>
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600 mb-1 block">{label}</span>
      {children}
    </label>
  );
}
