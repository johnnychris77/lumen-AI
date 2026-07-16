import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ImageIcon, Search, Upload } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { AuthenticatedImage } from "@/components/ui/authenticated-image";
import { api, ApiError } from "@/lib/api";
import type { DatasetEntry } from "@/lib/canvasTypes";

export default function DatasetImageLibraryPage() {
  const [entries, setEntries] = useState<DatasetEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [reviewFilter, setReviewFilter] = useState("all");
  const [imageTypeFilter, setImageTypeFilter] = useState("all");
  const [manufacturerFilter, setManufacturerFilter] = useState("all");

  useEffect(() => {
    let cancelled = false;
    api
      .get<{ count: number; images: DatasetEntry[] }>("/api/dataset-registry/images")
      .then((res) => {
        if (!cancelled) setEntries(res.images);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof ApiError ? e.message : "Failed to load the image library.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const manufacturers = useMemo(
    () => ["all", ...new Set((entries ?? []).map((e) => e.manufacturer).filter(Boolean))],
    [entries]
  );

  const filtered = (entries ?? []).filter((e) => {
    const q = search.trim().toLowerCase();
    const matchesSearch =
      !q ||
      e.lcid.toLowerCase().includes(q) ||
      String(e.retained_image_id).includes(q) ||
      (e.digital_twin_id ?? "").toLowerCase().includes(q) ||
      e.instrument_family.toLowerCase().includes(q);
    const matchesReview = reviewFilter === "all" || e.review_status === reviewFilter;
    const matchesType = imageTypeFilter === "all" || e.image_type === imageTypeFilter;
    const matchesManufacturer = manufacturerFilter === "all" || e.manufacturer === manufacturerFilter;
    return matchesSearch && matchesReview && matchesType && matchesManufacturer;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Dataset Image Library</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Registered borescope images with LCID identity, review status, and Ground Truth
            state — drawn directly from the governed dataset registry.
          </p>
        </div>
        <Link
          to="/dataset/images/upload"
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          <Upload className="h-4 w-4" /> Ingest Image
        </Link>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-56">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            aria-label="Search by LCID, instrument family, or Digital Twin ID"
            placeholder="Search LCID, instrument family, Digital Twin ID…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select aria-label="Filter by review status" value={reviewFilter} onChange={(e) => setReviewFilter(e.target.value)} className="w-44">
          <option value="all">All review states</option>
          {["UNLABELED", "LABELED", "SECOND_REVIEW", "DISAGREEMENT", "ADJUDICATED", "APPROVED", "ARCHIVED"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </Select>
        <Select aria-label="Filter by image type" value={imageTypeFilter} onChange={(e) => setImageTypeFilter(e.target.value)} className="w-44">
          <option value="all">All image types</option>
          {["baseline_reference", "after_use", "after_cleaning", "after_recleaning", "post_repair", "unknown_context", "research_reference"].map((t) => (
            <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
          ))}
        </Select>
        <Select aria-label="Filter by manufacturer" value={manufacturerFilter} onChange={(e) => setManufacturerFilter(e.target.value)} className="w-44">
          {manufacturers.map((m) => (
            <option key={m} value={m}>{m === "all" ? "All manufacturers" : m}</option>
          ))}
        </Select>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {!entries && !error && (
        <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading image library…</span>
        </div>
      )}

      {entries && filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <ImageIcon className="h-10 w-10 text-slate-300 mb-3" />
          <p className="text-sm font-medium text-slate-600">
            {entries.length === 0 ? "No images registered yet." : "No images match your filters."}
          </p>
          {entries.length === 0 && (
            <Link to="/dataset/images/upload" className="mt-3 text-xs text-blue-600 hover:underline">
              Ingest the first image
            </Link>
          )}
        </div>
      )}

      {entries && filtered.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((entry) => (
            <Link key={entry.id} to={`/dataset/images/${entry.id}`}>
              <Card className="overflow-hidden flex flex-col hover:shadow-md transition-shadow h-full">
                <AuthenticatedImage
                  retainedImageId={entry.retained_image_id}
                  alt={`${entry.lcid} thumbnail`}
                  className="w-full h-36 object-cover"
                />
                <CardContent className="p-3 flex flex-col gap-1.5">
                  <p className="text-xs font-mono text-slate-500 truncate">{entry.lcid}</p>
                  <p className="text-sm font-medium text-slate-900 truncate">
                    {entry.instrument_family || "Unknown instrument"} · {entry.manufacturer || "Unknown mfr"}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    <Badge variant="outline">{entry.review_status}</Badge>
                    {entry.image_type && <Badge variant="secondary">{entry.image_type.replace(/_/g, " ")}</Badge>}
                    {entry.image_quality && <Badge variant="secondary">{entry.image_quality}</Badge>}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
