import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Search,
  Filter,
  CreditCard,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ImageIcon,
  Upload,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  PILOT_IMAGES,
  getManifestSummary,
  type PilotImage,
  type ImageType,
  type FindingCategory,
} from "@/data/pilotImageManifest";

// ─── Metadata display maps ─────────────────────────────────────────────────────

const IMAGE_TYPE_META: Record<ImageType, { label: string; color: string }> = {
  baseline:   { label: "Baseline",   color: "bg-blue-50 text-blue-700 border-blue-200" },
  inspection: { label: "Inspection", color: "bg-slate-50 text-slate-700 border-slate-200" },
  borescope:  { label: "Borescope",  color: "bg-purple-50 text-purple-700 border-purple-200" },
  finding:    { label: "Finding",    color: "bg-red-50 text-red-700 border-red-200" },
};

const FINDING_META: Record<FindingCategory, { label: string; color: string }> = {
  blood:             { label: "Blood",            color: "bg-red-100 text-red-800 border-red-300" },
  bone:              { label: "Bone",             color: "bg-orange-100 text-orange-800 border-orange-300" },
  tissue:            { label: "Tissue",           color: "bg-pink-100 text-pink-800 border-pink-300" },
  debris:            { label: "Debris",           color: "bg-amber-100 text-amber-800 border-amber-300" },
  corrosion:         { label: "Corrosion",        color: "bg-yellow-100 text-yellow-800 border-yellow-300" },
  crack:             { label: "Crack",            color: "bg-slate-200 text-slate-800 border-slate-400" },
  insulation_damage: { label: "Insulation",       color: "bg-purple-100 text-purple-800 border-purple-300" },
  other:             { label: "Other",            color: "bg-slate-100 text-slate-700 border-slate-300" },
  none:              { label: "No Finding",       color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
};

const RISK_META = {
  low:      { label: "Low",      color: "text-emerald-700 bg-emerald-50" },
  medium:   { label: "Medium",   color: "text-amber-700 bg-amber-50" },
  high:     { label: "High",     color: "text-orange-700 bg-orange-50" },
  critical: { label: "Critical", color: "text-red-700 bg-red-50 font-bold" },
};

const BASELINE_STATUS_META = {
  approved:       { label: "Approved",       icon: CheckCircle2, color: "text-emerald-600" },
  pending_review: { label: "Pending Review", icon: Clock,        color: "text-amber-600" },
  rejected:       { label: "Rejected",       icon: AlertTriangle, color: "text-red-600" },
  draft:          { label: "Draft",          icon: ImageIcon,     color: "text-slate-400" },
};

// ─── Image card ───────────────────────────────────────────────────────────────

function PilotImageCard({ image }: { image: PilotImage }) {
  const [imgSrc, setImgSrc] = useState(image.available ? image.imageSrc : image.placeholderSrc);
  const [showingPlaceholder, setShowingPlaceholder] = useState(!image.available);

  const typeMeta     = IMAGE_TYPE_META[image.imageType];
  const findingMeta  = FINDING_META[image.findingCategory];
  const riskMeta     = RISK_META[image.riskLevel];
  const statusMeta   = BASELINE_STATUS_META[image.baselineStatus];
  const StatusIcon   = statusMeta.icon;

  return (
    <Card className="overflow-hidden flex flex-col hover:shadow-md transition-shadow">
      {/* Image area */}
      <div className="relative w-full h-44 bg-slate-100">
        <img
          src={imgSrc}
          alt={`${image.instrumentName} — ${typeMeta.label}`}
          className="w-full h-full object-cover"
          onError={() => {
            if (imgSrc !== image.placeholderSrc) {
              setImgSrc(image.placeholderSrc);
              setShowingPlaceholder(true);
            }
          }}
        />
        {showingPlaceholder && (
          <span className="absolute bottom-1.5 right-1.5 rounded bg-black/30 px-1.5 py-0.5 text-[10px] text-white/80 backdrop-blur-sm">
            placeholder
          </span>
        )}
        {image.riskLevel === "critical" && (
          <span className="absolute top-2 left-2 rounded-full bg-red-600 px-2 py-0.5 text-xs font-bold text-white flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" /> Critical
          </span>
        )}
      </div>

      <CardContent className="p-3 flex flex-col gap-2 flex-1">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-900 truncate">{image.instrumentName}</p>
            <p className="text-xs text-slate-500 truncate">{image.manufacturer} · {image.model}</p>
          </div>
          <span className={cn("shrink-0 text-xs px-2 py-0.5 rounded-full border font-medium", typeMeta.color)}>
            {typeMeta.label}
          </span>
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-1">
          {image.findingCategory !== "none" && (
            <span className={cn("text-xs px-1.5 py-0.5 rounded border font-medium", findingMeta.color)}>
              {findingMeta.label}
            </span>
          )}
          <span className={cn("text-xs px-1.5 py-0.5 rounded font-medium", riskMeta.color)}>
            {riskMeta.label}
          </span>
        </div>

        {/* Identifier + facility */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500 font-mono truncate">{image.identifier}</p>
          <p className="text-xs text-slate-400 truncate ml-2">{image.facility}</p>
        </div>

        {/* Notes */}
        <p className="text-xs text-slate-600 line-clamp-2 flex-1">{image.notes}</p>

        {/* Footer */}
        <div className="flex items-center justify-between mt-1 pt-2 border-t border-slate-100">
          <div className="flex items-center gap-1">
            <StatusIcon className={cn("h-3.5 w-3.5", statusMeta.color)} />
            <span className={cn("text-xs font-medium", statusMeta.color)}>{statusMeta.label}</span>
          </div>
          <Link
            to="/instrument-passport"
            className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
          >
            <CreditCard className="h-3 w-3" /> Passport
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Filter types ─────────────────────────────────────────────────────────────

const ALL_IMAGE_TYPES: Array<"all" | ImageType>      = ["all", "baseline", "inspection", "borescope", "finding"];
const ALL_FINDING_CATS: Array<"all" | FindingCategory> = [
  "all", "blood", "bone", "tissue", "debris", "corrosion", "crack", "insulation_damage", "none",
];
const ALL_FACILITIES: string[] = ["all", ...new Set(PILOT_IMAGES.map((i) => i.facility))];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DemoImageLibraryPage() {
  const [search, setSearch]           = useState("");
  const [typeFilter, setTypeFilter]   = useState<"all" | ImageType>("all");
  const [findingFilter, setFindingFilter] = useState<"all" | FindingCategory>("all");
  const [facilityFilter, setFacilityFilter] = useState("all");

  const summary = getManifestSummary();

  const filtered = PILOT_IMAGES.filter((img) => {
    const q = search.toLowerCase();
    const matchSearch =
      !q ||
      img.instrumentName.toLowerCase().includes(q) ||
      img.manufacturer.toLowerCase().includes(q) ||
      img.model.toLowerCase().includes(q) ||
      img.identifier.toLowerCase().includes(q) ||
      img.facility.toLowerCase().includes(q) ||
      img.notes.toLowerCase().includes(q);
    const matchType    = typeFilter === "all"    || img.imageType        === typeFilter;
    const matchFinding = findingFilter === "all" || img.findingCategory  === findingFilter;
    const matchFacility = facilityFilter === "all" || img.facility       === facilityFilter;
    return matchSearch && matchType && matchFinding && matchFacility;
  });

  const selectClass =
    "rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Pilot Image Library</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {summary.total} pilot instrument images · {summary.available} real photos loaded ·{" "}
            {summary.total - summary.available} placeholders remaining
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/baseline-image-upload"
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            <Upload className="h-4 w-4" /> Upload Baseline
          </Link>
          <Link
            to="/inspection-image-upload"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <Upload className="h-4 w-4" /> Upload Inspection
          </Link>
        </div>
      </div>

      {/* Placeholder notice */}
      {summary.available === 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3">
          <Info className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
          <p className="text-sm text-blue-800">
            No real pilot images are loaded yet. Showing placeholder cards.{" "}
            See{" "}
            <code className="font-mono text-xs bg-blue-100 px-1 rounded">
              docs/pilot/pilot-image-ingestion-guide.md
            </code>{" "}
            to load your images, then set{" "}
            <code className="font-mono text-xs bg-blue-100 px-1 rounded">available: true</code>{" "}
            in <code className="font-mono text-xs bg-blue-100 px-1 rounded">pilotImageManifest.ts</code>.
          </p>
        </div>
      )}

      {/* KPI summary strip */}
      <div className="grid grid-cols-4 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {[
          { label: "Total",      value: summary.total,           color: "text-slate-700" },
          { label: "Baselines",  value: summary.byType.baseline, color: "text-blue-700" },
          { label: "Inspections",value: summary.byType.inspection,color: "text-slate-600" },
          { label: "Borescope",  value: summary.byType.borescope,color: "text-purple-700" },
          { label: "Findings",   value: summary.byType.finding,  color: "text-red-700" },
          { label: "Approved",   value: summary.byStatus.approved, color: "text-emerald-600" },
          { label: "Pending",    value: summary.byStatus.pending, color: "text-amber-600" },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-white p-3 text-center">
            <p className={cn("text-2xl font-bold", color)}>{value}</p>
            <p className="text-xs text-slate-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search instrument, model, identifier, notes…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="h-4 w-4 text-slate-400" />
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as "all" | ImageType)} className={selectClass}>
            {ALL_IMAGE_TYPES.map((t) => (
              <option key={t} value={t}>{t === "all" ? "All Types" : IMAGE_TYPE_META[t].label}</option>
            ))}
          </select>
          <select value={findingFilter} onChange={(e) => setFindingFilter(e.target.value as "all" | FindingCategory)} className={selectClass}>
            {ALL_FINDING_CATS.map((c) => (
              <option key={c} value={c}>{c === "all" ? "All Findings" : FINDING_META[c].label}</option>
            ))}
          </select>
          <select value={facilityFilter} onChange={(e) => setFacilityFilter(e.target.value)} className={selectClass}>
            {ALL_FACILITIES.map((f) => (
              <option key={f} value={f}>{f === "all" ? "All Facilities" : f}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <ImageIcon className="h-10 w-10 text-slate-300 mb-3" />
          <p className="text-sm font-medium text-slate-600">No images match your filters</p>
          <button
            onClick={() => { setSearch(""); setTypeFilter("all"); setFindingFilter("all"); setFacilityFilter("all"); }}
            className="mt-3 text-xs text-blue-600 hover:underline"
          >
            Clear filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((img) => (
            <PilotImageCard key={img.id} image={img} />
          ))}
        </div>
      )}

      {/* Import note */}
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-center">
        <p className="text-sm font-medium text-slate-700">Loading Real Pilot Images</p>
        <p className="text-xs text-slate-500 mt-1 max-w-xl mx-auto">
          Copy your <code className="font-mono bg-white px-1 rounded">.jpg</code> files into{" "}
          <code className="font-mono bg-white px-1 rounded">frontend/public/demo-images/lumened-instruments/</code>{" "}
          using the naming convention in the manifest, then set{" "}
          <code className="font-mono bg-white px-1 rounded">available: true</code> for each entry.
          See{" "}
          <code className="font-mono bg-white px-1 rounded">docs/pilot/pilot-image-ingestion-guide.md</code>.
        </p>
      </div>
    </div>
  );
}
