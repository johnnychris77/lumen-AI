import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Search,
  Filter,
  CreditCard,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ImageIcon,
  Upload,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type ImageType = "baseline" | "inspection" | "borescope" | "finding";
type FindingCategory =
  | "blood"
  | "bone"
  | "tissue"
  | "debris"
  | "corrosion"
  | "crack"
  | "insulation_damage"
  | "other"
  | "none";
type RiskLevel = "low" | "medium" | "high" | "critical";
type BaselineStatus = "approved" | "pending_review" | "rejected" | "draft";
type ImageQuality = "high" | "medium" | "low";

interface DemoImage {
  id: string;
  instrumentName: string;
  manufacturer: string;
  model: string;
  identifier: string;
  identifierType: "keydot" | "qr" | "barcode" | "manual";
  imageType: ImageType;
  findingCategory: FindingCategory;
  baselineStatus: BaselineStatus;
  riskLevel: RiskLevel;
  imageQuality: ImageQuality;
  captureDate: string;
  captureDevice: string;
  captureAngle: string;
  notes: string;
  placeholderLabel: string;
}

// ─── Demo dataset — replace src values with real pilot images ─────────────────

const DEMO_IMAGES: DemoImage[] = [
  {
    id: "demo-001",
    instrumentName: "Laparoscopic Grasper",
    manufacturer: "Storz",
    model: "26173KA",
    identifier: "keydot-127",
    identifierType: "keydot",
    imageType: "baseline",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-01-15",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "distal tip, 0°",
    notes: "Clean. No visible tissue residue. Jaws close flush.",
    placeholderLabel: "Baseline — Distal Tip",
  },
  {
    id: "demo-002",
    instrumentName: "Laparoscopic Grasper",
    manufacturer: "Storz",
    model: "26173KA",
    identifier: "keydot-127",
    identifierType: "keydot",
    imageType: "finding",
    findingCategory: "tissue",
    baselineStatus: "approved",
    riskLevel: "high",
    imageQuality: "high",
    captureDate: "2026-03-10",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "distal tip, 0°",
    notes: "Tissue fragment visible at jaw hinge. Requires re-cleaning.",
    placeholderLabel: "Finding — Tissue",
  },
  {
    id: "demo-003",
    instrumentName: "Needle Driver",
    manufacturer: "Olympus",
    model: "MAJ-1262",
    identifier: "barcode-A04421",
    identifierType: "barcode",
    imageType: "baseline",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-01-20",
    captureDevice: "USB Macro Camera",
    captureAngle: "full instrument, lateral",
    notes: "Reference baseline. Tungsten carbide inserts intact.",
    placeholderLabel: "Baseline — Full View",
  },
  {
    id: "demo-004",
    instrumentName: "Needle Driver",
    manufacturer: "Olympus",
    model: "MAJ-1262",
    identifier: "barcode-A04421",
    identifierType: "barcode",
    imageType: "finding",
    findingCategory: "corrosion",
    baselineStatus: "approved",
    riskLevel: "medium",
    imageQuality: "medium",
    captureDate: "2026-04-02",
    captureDevice: "USB Macro Camera",
    captureAngle: "jaw box",
    notes: "Early-stage corrosion at box joint. Quality review recommended.",
    placeholderLabel: "Finding — Corrosion",
  },
  {
    id: "demo-005",
    instrumentName: "Hemostatic Forceps",
    manufacturer: "Aesculap",
    model: "BH741R",
    identifier: "qr-4892-B",
    identifierType: "qr",
    imageType: "baseline",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-01-22",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "ratchet mechanism",
    notes: "Ratchet engages cleanly through all positions.",
    placeholderLabel: "Baseline — Ratchet",
  },
  {
    id: "demo-006",
    instrumentName: "Hemostatic Forceps",
    manufacturer: "Aesculap",
    model: "BH741R",
    identifier: "qr-4892-B",
    identifierType: "qr",
    imageType: "finding",
    findingCategory: "blood",
    baselineStatus: "approved",
    riskLevel: "critical",
    imageQuality: "high",
    captureDate: "2026-05-14",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "ratchet interior",
    notes: "Blood residue in ratchet channel. Immediate re-cleaning required.",
    placeholderLabel: "Finding — Blood",
  },
  {
    id: "demo-007",
    instrumentName: "Bone Rongeur",
    manufacturer: "Codman",
    model: "10-0006",
    identifier: "keydot-088",
    identifierType: "keydot",
    imageType: "finding",
    findingCategory: "bone",
    baselineStatus: "approved",
    riskLevel: "high",
    imageQuality: "medium",
    captureDate: "2026-04-28",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "cup jaw interior",
    notes: "Bone fragment in cup recess. Investigation candidate.",
    placeholderLabel: "Finding — Bone",
  },
  {
    id: "demo-008",
    instrumentName: "Bipolar Forceps",
    manufacturer: "Erbe",
    model: "VIO 300D",
    identifier: "keydot-219",
    identifierType: "keydot",
    imageType: "inspection",
    findingCategory: "insulation_damage",
    baselineStatus: "pending_review",
    riskLevel: "high",
    imageQuality: "high",
    captureDate: "2026-05-01",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "shaft insulation, mid-point",
    notes: "Possible insulation thinning at 120 mm. Electrical safety check required.",
    placeholderLabel: "Inspection — Insulation",
  },
  {
    id: "demo-009",
    instrumentName: "Retractor",
    manufacturer: "Thompson",
    model: "M-3760",
    identifier: "manual-R9921",
    identifierType: "manual",
    imageType: "borescope",
    findingCategory: "debris",
    baselineStatus: "approved",
    riskLevel: "medium",
    imageQuality: "medium",
    captureDate: "2026-05-08",
    captureDevice: "Rigid Borescope 4 mm",
    captureAngle: "inner channel",
    notes: "Debris / bioburden accumulation in inner channel.",
    placeholderLabel: "Borescope — Debris",
  },
  {
    id: "demo-010",
    instrumentName: "Scissors — Metzenbaum",
    manufacturer: "Jarit",
    model: "110-218",
    identifier: "keydot-341",
    identifierType: "keydot",
    imageType: "finding",
    findingCategory: "crack",
    baselineStatus: "approved",
    riskLevel: "critical",
    imageQuality: "high",
    captureDate: "2026-05-12",
    captureDevice: "USB Macro Camera",
    captureAngle: "blade edge",
    notes: "Hairline crack at blade pivot. Remove from service immediately.",
    placeholderLabel: "Finding — Crack",
  },
  {
    id: "demo-011",
    instrumentName: "Suction Irrigator",
    manufacturer: "Medtronic",
    model: "REF-0090",
    identifier: "qr-7731-C",
    identifierType: "qr",
    imageType: "baseline",
    findingCategory: "none",
    baselineStatus: "draft",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-05-18",
    captureDevice: "Borescope Pro 3000",
    captureAngle: "lumen, distal",
    notes: "Draft baseline pending SPD manager approval.",
    placeholderLabel: "Baseline — Lumen",
  },
  {
    id: "demo-012",
    instrumentName: "Trocar — 12 mm",
    manufacturer: "Applied Medical",
    model: "G35012",
    identifier: "keydot-455",
    identifierType: "keydot",
    imageType: "inspection",
    findingCategory: "none",
    baselineStatus: "approved",
    riskLevel: "low",
    imageQuality: "high",
    captureDate: "2026-05-20",
    captureDevice: "Rigid Borescope 4 mm",
    captureAngle: "valve channel",
    notes: "Routine inspection. Valve seals intact. No findings.",
    placeholderLabel: "Inspection — Pass",
  },
];

// ─── Metadata maps ─────────────────────────────────────────────────────────────

const IMAGE_TYPE_META: Record<ImageType, { label: string; color: string }> = {
  baseline: { label: "Baseline", color: "bg-blue-50 text-blue-700 border-blue-200" },
  inspection: { label: "Inspection", color: "bg-slate-50 text-slate-700 border-slate-200" },
  borescope: { label: "Borescope", color: "bg-purple-50 text-purple-700 border-purple-200" },
  finding: { label: "Finding", color: "bg-red-50 text-red-700 border-red-200" },
};

const FINDING_META: Record<FindingCategory, { label: string; color: string }> = {
  blood: { label: "Blood", color: "bg-red-100 text-red-800 border-red-300" },
  bone: { label: "Bone", color: "bg-orange-100 text-orange-800 border-orange-300" },
  tissue: { label: "Tissue", color: "bg-pink-100 text-pink-800 border-pink-300" },
  debris: { label: "Debris", color: "bg-amber-100 text-amber-800 border-amber-300" },
  corrosion: { label: "Corrosion", color: "bg-yellow-100 text-yellow-800 border-yellow-300" },
  crack: { label: "Crack", color: "bg-slate-200 text-slate-800 border-slate-400" },
  insulation_damage: { label: "Insulation", color: "bg-purple-100 text-purple-800 border-purple-300" },
  other: { label: "Other", color: "bg-slate-100 text-slate-700 border-slate-300" },
  none: { label: "No Finding", color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
};

const RISK_META: Record<RiskLevel, { label: string; color: string }> = {
  low: { label: "Low Risk", color: "text-emerald-700 bg-emerald-50" },
  medium: { label: "Medium Risk", color: "text-amber-700 bg-amber-50" },
  high: { label: "High Risk", color: "text-orange-700 bg-orange-50" },
  critical: { label: "Critical", color: "text-red-700 bg-red-50 font-bold" },
};

const BASELINE_STATUS_META: Record<BaselineStatus, { label: string; icon: React.ElementType; color: string }> = {
  approved: { label: "Approved", icon: CheckCircle2, color: "text-emerald-600" },
  pending_review: { label: "Pending Review", icon: Clock, color: "text-amber-600" },
  rejected: { label: "Rejected", icon: AlertTriangle, color: "text-red-600" },
  draft: { label: "Draft", icon: ImageIcon, color: "text-slate-400" },
};

const QUALITY_COLOR: Record<ImageQuality, string> = {
  high: "text-emerald-600",
  medium: "text-amber-600",
  low: "text-red-600",
};

// ─── Placeholder image card ────────────────────────────────────────────────────

const PLACEHOLDER_COLORS: Record<ImageType, string> = {
  baseline: "from-blue-100 to-blue-200",
  inspection: "from-slate-100 to-slate-200",
  borescope: "from-purple-100 to-purple-200",
  finding: "from-red-100 to-red-200",
};

function PlaceholderImage({ image }: { image: DemoImage }) {
  return (
    <div
      className={cn(
        "w-full h-40 flex flex-col items-center justify-center rounded-t-lg bg-gradient-to-br",
        PLACEHOLDER_COLORS[image.imageType]
      )}
    >
      <ImageIcon className="h-10 w-10 text-slate-400 mb-2" />
      <span className="text-xs font-medium text-slate-500 px-3 text-center leading-tight">
        {image.placeholderLabel}
      </span>
      <span className="text-[10px] text-slate-400 mt-1 px-2 py-0.5 rounded bg-white/60">
        Replace with pilot image
      </span>
    </div>
  );
}

// ─── Image card ───────────────────────────────────────────────────────────────

function ImageCard({ image }: { image: DemoImage }) {
  const typeMeta = IMAGE_TYPE_META[image.imageType];
  const findingMeta = FINDING_META[image.findingCategory];
  const riskMeta = RISK_META[image.riskLevel];
  const statusMeta = BASELINE_STATUS_META[image.baselineStatus];
  const StatusIcon = statusMeta.icon;

  return (
    <Card className="overflow-hidden flex flex-col hover:shadow-md transition-shadow">
      <PlaceholderImage image={image} />
      <CardContent className="p-3 flex flex-col gap-2 flex-1">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-900 truncate">{image.instrumentName}</p>
            <p className="text-xs text-slate-500 truncate">{image.manufacturer} · {image.model}</p>
          </div>
          <span className={cn("shrink-0 text-xs px-2 py-0.5 rounded-full border font-medium", typeMeta.color)}>
            {typeMeta.label}
          </span>
        </div>

        {/* Badges row */}
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

        {/* Identifier */}
        <p className="text-xs text-slate-500 font-mono truncate">{image.identifier}</p>

        {/* Notes */}
        <p className="text-xs text-slate-600 line-clamp-2 flex-1">{image.notes}</p>

        {/* Footer */}
        <div className="flex items-center justify-between mt-1 pt-2 border-t border-slate-100">
          <div className="flex items-center gap-1">
            <StatusIcon className={cn("h-3.5 w-3.5", statusMeta.color)} />
            <span className={cn("text-xs font-medium", statusMeta.color)}>{statusMeta.label}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={cn("text-xs font-medium capitalize", QUALITY_COLOR[image.imageQuality])}>
              {image.imageQuality} quality
            </span>
            <Link
              to="/instrument-passport"
              className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
            >
              <CreditCard className="h-3 w-3" /> Passport
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Filters ──────────────────────────────────────────────────────────────────

const ALL_IMAGE_TYPES: Array<"all" | ImageType> = ["all", "baseline", "inspection", "borescope", "finding"];
const ALL_FINDING_CATS: Array<"all" | FindingCategory> = [
  "all", "blood", "bone", "tissue", "debris", "corrosion", "crack", "insulation_damage", "none",
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DemoImageLibraryPage() {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | ImageType>("all");
  const [findingFilter, setFindingFilter] = useState<"all" | FindingCategory>("all");

  const filtered = DEMO_IMAGES.filter((img) => {
    const q = search.toLowerCase();
    const matchSearch =
      !q ||
      img.instrumentName.toLowerCase().includes(q) ||
      img.manufacturer.toLowerCase().includes(q) ||
      img.model.toLowerCase().includes(q) ||
      img.identifier.toLowerCase().includes(q) ||
      img.notes.toLowerCase().includes(q);
    const matchType = typeFilter === "all" || img.imageType === typeFilter;
    const matchFinding = findingFilter === "all" || img.findingCategory === findingFilter;
    return matchSearch && matchType && matchFinding;
  });

  // Summary counts
  const counts = {
    total: DEMO_IMAGES.length,
    baseline: DEMO_IMAGES.filter((i) => i.imageType === "baseline").length,
    inspection: DEMO_IMAGES.filter((i) => i.imageType === "inspection").length,
    borescope: DEMO_IMAGES.filter((i) => i.imageType === "borescope").length,
    finding: DEMO_IMAGES.filter((i) => i.imageType === "finding").length,
    pending: DEMO_IMAGES.filter((i) => i.baselineStatus === "pending_review").length,
    approved: DEMO_IMAGES.filter((i) => i.baselineStatus === "approved").length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Demo Image Library</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {counts.total} pilot demo images · placeholder cards will be replaced with real instrument photos
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

      {/* KPI summary strip */}
      <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {[
          { label: "Total", value: counts.total, color: "text-slate-700" },
          { label: "Baselines", value: counts.baseline, color: "text-blue-700" },
          { label: "Inspections", value: counts.inspection, color: "text-slate-600" },
          { label: "Borescope", value: counts.borescope, color: "text-purple-700" },
          { label: "Findings", value: counts.finding, color: "text-red-700" },
          { label: "Pending", value: counts.pending, color: "text-amber-600" },
          { label: "Approved", value: counts.approved, color: "text-emerald-600" },
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
            placeholder="Search instruments, manufacturer, model…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as "all" | ImageType)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {ALL_IMAGE_TYPES.map((t) => (
              <option key={t} value={t}>{t === "all" ? "All Types" : IMAGE_TYPE_META[t].label}</option>
            ))}
          </select>
          <select
            value={findingFilter}
            onChange={(e) => setFindingFilter(e.target.value as "all" | FindingCategory)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {ALL_FINDING_CATS.map((c) => (
              <option key={c} value={c}>{c === "all" ? "All Findings" : FINDING_META[c].label}</option>
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
            onClick={() => { setSearch(""); setTypeFilter("all"); setFindingFilter("all"); }}
            className="mt-3 text-xs text-blue-600 hover:underline"
          >
            Clear filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((img) => (
            <ImageCard key={img.id} image={img} />
          ))}
        </div>
      )}

      {/* Import note */}
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-center">
        <p className="text-sm font-medium text-slate-700">Pilot Image Import</p>
        <p className="text-xs text-slate-500 mt-1 max-w-lg mx-auto">
          See <code className="font-mono bg-white px-1 rounded">docs/pilot/pilot-image-library-import-guide.md</code> for
          the file naming convention and metadata CSV structure to load your 100 pilot images.
        </p>
      </div>
    </div>
  );
}
