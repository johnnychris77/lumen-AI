import { useState } from "react";
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  GraduationCap,
  HelpCircle,
  Layers,
  Play,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// ── Types ────────────────────────────────────────────────────────────────────

type TrackItem = {
  title: string;
  type: "guide" | "workflow" | "video" | "faq";
  duration: string;
  link?: string;
  description: string;
};

type TrainingTrack = {
  id: string;
  audience: string;
  icon: React.ElementType;
  color: string;
  items: TrackItem[];
};

// ── Data ─────────────────────────────────────────────────────────────────────

const TYPE_BADGE: Record<TrackItem["type"], { label: string; variant: "default" | "secondary" | "success" | "warning" }> = {
  guide:    { label: "Guide",    variant: "default" },
  workflow: { label: "Workflow", variant: "secondary" },
  video:    { label: "Demo",     variant: "warning" },
  faq:      { label: "FAQ",      variant: "success" },
};

const TRACKS: TrainingTrack[] = [
  {
    id: "technician",
    audience: "SPD Technician",
    icon: Users,
    color: "bg-blue-600",
    items: [
      { title: "Quick Start: Submitting Your First Inspection", type: "guide", duration: "5 min", link: "/inspection/new", description: "Step-by-step guide for new technicians — instrument selection, finding capture, barcode scan, and submission." },
      { title: "Understanding Finding Categories", type: "guide", duration: "3 min", description: "What each finding type means (blood, bone, tissue, debris, corrosion, crack, insulation damage) and how to identify them." },
      { title: "Barcode & QR Scanning Workflow", type: "workflow", duration: "4 min", link: "/vendor-intake", description: "How to scan instrument barcodes using a Zebra USB HID scanner. Visual confirmation, error states, and fallback entry." },
      { title: "Uploading Inspection Images", type: "workflow", duration: "3 min", link: "/inspection-image-upload", description: "Image resolution requirements (1080p min), lighting guidance, required angles, PHI warning." },
      { title: "Reading Your Risk Score", type: "guide", duration: "2 min", description: "What the risk score means (0–100 scale), badge colors, and when to escalate to your manager." },
      { title: "Technician FAQ", type: "faq", duration: "5 min", description: "Common questions: What if the scanner doesn't beep? What's the difference between debris and tissue? Can I submit without an image?" },
    ],
  },
  {
    id: "manager",
    audience: "SPD Manager",
    icon: Layers,
    color: "bg-indigo-600",
    items: [
      { title: "Review Queue Walkthrough", type: "workflow", duration: "6 min", link: "/findings", description: "How to review findings, approve/reject, and create CAPAs from the inspection review queue." },
      { title: "Baseline Approval Process", type: "workflow", duration: "5 min", link: "/baseline-review", description: "Reviewing vendor and manufacturer baseline submissions. Approval criteria, rejection workflow, and audit trail." },
      { title: "Dashboard & KPI Interpretation", type: "guide", duration: "4 min", link: "/", description: "Reading contamination KPIs, identifying trends, and responding to high-risk alerts." },
      { title: "CAPA Creation and Tracking", type: "workflow", duration: "5 min", link: "/capa", description: "Opening, assigning, and closing corrective actions. Linking CAPAs to instrument findings." },
      { title: "Instrument Passport Deep Dive", type: "guide", duration: "4 min", link: "/instrument-passport", description: "Using the Passport V2 to review instrument lifecycle history, risk trends, and recommended actions." },
      { title: "Manager FAQ", type: "faq", duration: "5 min", description: "How do I set up a new vendor? What triggers a Critical risk score? How do I export a report for Joint Commission?" },
    ],
  },
  {
    id: "vendor",
    audience: "Vendor / Manufacturer",
    icon: BookOpen,
    color: "bg-purple-600",
    items: [
      { title: "Vendor Baseline Submission Guide", type: "guide", duration: "5 min", link: "/vendor-baseline-portal", description: "How to submit baseline images via the Vendor Baseline Portal. Format, resolution, naming conventions, PHI requirements." },
      { title: "Image Capture Guidelines", type: "guide", duration: "3 min", link: "/baseline-image-upload", description: "JPEG/PNG format, 1080p minimum (4K preferred for borescope), 20 MB max, required angles, lighting setup." },
      { title: "Submission Status Tracking", type: "workflow", duration: "3 min", link: "/manufacturer-baselines", description: "How to track approval status of submitted baselines. Notification workflow and resubmission process." },
      { title: "Vendor FAQ", type: "faq", duration: "3 min", description: "What happens after I submit? How long does approval take? What if my image is rejected? Do you accept multi-image submissions?" },
    ],
  },
  {
    id: "executive",
    audience: "Executive / Quality Leader",
    icon: GraduationCap,
    color: "bg-emerald-600",
    items: [
      { title: "Executive Demo Walkthrough (10 stops)", type: "video", duration: "15 min", link: "/executive-command-center", description: "Full platform walkthrough for SPD Directors, CNOs, CFOs, and investors. See docs/demo/executive-demo-walkthrough.md." },
      { title: "Executive Command Center Overview", type: "guide", duration: "3 min", link: "/executive-command-center", description: "16 KPIs across 4 grids: Operational, Contamination, Instrument Health, Pilot Metrics." },
      { title: "Surgical Readiness Dashboard", type: "guide", duration: "3 min", link: "/surgical-readiness", description: "How composite readiness scores are computed. Dimension breakdown: facility, instrument, tray, inspection, baseline." },
      { title: "ROI Reporting for Renewals", type: "guide", duration: "4 min", link: "/roi-center", description: "Using the ROI Center to quantify time saved, findings detected, and estimated operational value for renewal conversations." },
      { title: "Executive FAQ", type: "faq", duration: "5 min", description: "Is LumenAI FDA cleared? How is data isolated between facilities? What does a 90-day ROI look like? How is risk score calibrated?" },
    ],
  },
];

// ── Sub-components ───────────────────────────────────────────────────────────

function TrackCard({ track }: { track: TrainingTrack }) {
  const [open, setOpen] = useState(true);
  const Icon = track.icon;

  return (
    <Card>
      <CardHeader
        className="cursor-pointer select-none pb-2"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-3">
          <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${track.color}`}>
            <Icon className="h-4 w-4 text-white" />
          </div>
          <CardTitle className="text-sm font-semibold text-slate-800 flex-1">{track.audience} Training</CardTitle>
          <Badge variant="secondary" className="text-xs">{track.items.length} modules</Badge>
          {open ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
        </div>
      </CardHeader>
      {open && (
        <CardContent className="pt-0 divide-y divide-slate-50">
          {track.items.map((item, i) => {
            const tb = TYPE_BADGE[item.type];
            return (
              <div key={i} className="py-3 flex items-start gap-3">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-100 mt-0.5">
                  {item.type === "video" ? <Play className="h-3.5 w-3.5 text-slate-500" /> : item.type === "faq" ? <HelpCircle className="h-3.5 w-3.5 text-slate-500" /> : <BookOpen className="h-3.5 w-3.5 text-slate-500" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-slate-800">{item.title}</span>
                    <Badge variant={tb.variant} className="text-xs">{tb.label}</Badge>
                    <span className="text-xs text-slate-400">{item.duration}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">{item.description}</p>
                </div>
                {item.link && (
                  <Link to={item.link} className="shrink-0 flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 mt-0.5">
                    Open <ExternalLink className="h-3 w-3" />
                  </Link>
                )}
              </div>
            );
          })}
        </CardContent>
      )}
    </Card>
  );
}

// ── Main ─────────────────────────────────────────────────────────────────────

export default function TrainingCenterPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-600">
          <GraduationCap className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-slate-900">Training Center</h1>
          <p className="text-sm text-slate-500">Role-based training tracks for SPD Technicians, Managers, Vendors, and Executives.</p>
        </div>
      </div>

      {/* Track Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {TRACKS.map((track) => {
          const Icon = track.icon;
          return (
            <div key={track.id} className="flex flex-col items-center text-center p-4 rounded-xl border border-slate-200 bg-white">
              <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${track.color} mb-2`}>
                <Icon className="h-4 w-4 text-white" />
              </div>
              <p className="text-xs font-semibold text-slate-700">{track.audience}</p>
              <p className="text-xs text-slate-400 mt-0.5">{track.items.length} modules</p>
            </div>
          );
        })}
      </div>

      {/* Training Tracks */}
      <div className="space-y-4">
        {TRACKS.map((track) => (
          <TrackCard key={track.id} track={track} />
        ))}
      </div>

      <p className="text-center text-xs text-slate-400 pb-4">
        Training completion tracking will be automated in a future release. All clinical decisions require qualified human review.
      </p>
    </div>
  );
}
