import { useState } from "react";
import {
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Factory,
  Store,
  Users,
  Layers,
  UserCheck,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// ── Types ────────────────────────────────────────────────────────────────────

type StepStatus = "complete" | "in-progress" | "pending";

type OnboardingStep = {
  id: string;
  label: string;
  description: string;
  status: StepStatus;
  action?: { label: string; to: string };
};

type OnboardingSection = {
  id: string;
  title: string;
  icon: React.ElementType;
  steps: OnboardingStep[];
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function sectionScore(steps: OnboardingStep[]) {
  const done = steps.filter((s) => s.status === "complete").length;
  return Math.round((done / steps.length) * 100);
}

function statusVariant(s: StepStatus) {
  return s === "complete" ? "success" : s === "in-progress" ? "warning" : "secondary";
}

function statusLabel(s: StepStatus) {
  return s === "complete" ? "Complete" : s === "in-progress" ? "In Progress" : "Pending";
}

// ── Hardcoded onboarding checklist (driven by real setup in future) ──────────

const SECTIONS: OnboardingSection[] = [
  {
    id: "facility",
    title: "Facility Setup",
    icon: Building2,
    steps: [
      { id: "facility-name", label: "Facility name configured", description: "Tenant name and facility ID registered.", status: "complete" },
      { id: "departments", label: "Departments added", description: "At least one SPD department created.", status: "in-progress", action: { label: "Manage Departments", to: "/settings" } },
      { id: "site-codes", label: "Site codes assigned", description: "Internal site identifiers for multi-location tracking.", status: "pending", action: { label: "Configure Sites", to: "/settings" } },
    ],
  },
  {
    id: "users",
    title: "User Setup",
    icon: Users,
    steps: [
      { id: "admin-created", label: "Admin account created", description: "At least one administrator is active.", status: "complete" },
      { id: "spd-managers", label: "SPD Manager accounts", description: "Managers assigned for each department.", status: "in-progress", action: { label: "Manage Users", to: "/users" } },
      { id: "technicians", label: "SPD Technician accounts", description: "Technicians trained and onboarded.", status: "pending", action: { label: "Add Users", to: "/users" } },
      { id: "roles", label: "Roles assigned", description: "RBAC roles configured for all users.", status: "in-progress", action: { label: "Manage Roles", to: "/roles" } },
    ],
  },
  {
    id: "vendors",
    title: "Vendor Setup",
    icon: Store,
    steps: [
      { id: "vendor-registered", label: "Primary vendor registered", description: "At least one reprocessing vendor added.", status: "complete" },
      { id: "vendor-baselines", label: "Vendor baselines submitted", description: "Vendor has submitted at least one baseline image.", status: "in-progress", action: { label: "Vendor Baselines", to: "/vendor-baseline-portal" } },
      { id: "vendor-approved", label: "Baseline approved", description: "At least one baseline approved by SPD Manager.", status: "in-progress", action: { label: "Review Baselines", to: "/baseline-review" } },
    ],
  },
  {
    id: "manufacturers",
    title: "Manufacturer Setup",
    icon: Factory,
    steps: [
      { id: "mfr-registered", label: "Manufacturers registered", description: "Instrument manufacturers added to registry.", status: "in-progress", action: { label: "Manufacturer Baselines", to: "/manufacturer-baselines" } },
      { id: "mfr-baselines", label: "Manufacturer baselines submitted", description: "Approved baseline images for instrument types.", status: "pending", action: { label: "Baseline Library", to: "/baseline-library" } },
    ],
  },
  {
    id: "instruments",
    title: "Instrument Registry",
    icon: Layers,
    steps: [
      { id: "instr-registered", label: "Pilot fleet registered", description: "Lumened scope fleet added to instrument registry.", status: "in-progress", action: { label: "Instrument Registry", to: "/infrastructure" } },
      { id: "barcodes", label: "Barcodes / UDIs captured", description: "All instruments have barcode or UDI identifiers.", status: "pending", action: { label: "Barcode Entry", to: "/vendor-intake" } },
    ],
  },
  {
    id: "training",
    title: "Training Completion",
    icon: UserCheck,
    steps: [
      { id: "tech-training", label: "Technician training complete", description: "All SPD technicians have completed workflow training.", status: "pending", action: { label: "Training Center", to: "/training-center" } },
      { id: "mgr-training", label: "Manager training complete", description: "SPD Managers completed review and CAPA training.", status: "pending", action: { label: "Training Center", to: "/training-center" } },
      { id: "first-inspection", label: "First live inspection submitted", description: "At least one real inspection submitted and reviewed.", status: "in-progress", action: { label: "New Inspection", to: "/inspection/new" } },
    ],
  },
];

// ── Sub-components ───────────────────────────────────────────────────────────

function StepRow({ step }: { step: OnboardingStep }) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-slate-50 last:border-0">
      <div className="mt-0.5 shrink-0">
        {step.status === "complete" ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        ) : step.status === "in-progress" ? (
          <div className="h-4 w-4 rounded-full border-2 border-amber-400 bg-amber-50" />
        ) : (
          <div className="h-4 w-4 rounded-full border-2 border-slate-200 bg-slate-50" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-sm font-medium ${step.status === "complete" ? "text-slate-500 line-through" : "text-slate-800"}`}>
            {step.label}
          </span>
          <Badge variant={statusVariant(step.status)} className="text-xs">{statusLabel(step.status)}</Badge>
        </div>
        <p className="text-xs text-slate-400 mt-0.5">{step.description}</p>
      </div>
      {step.action && step.status !== "complete" && (
        <Link
          to={step.action.to}
          className="shrink-0 flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700"
        >
          {step.action.label}
          <ArrowRight className="h-3 w-3" />
        </Link>
      )}
    </div>
  );
}

function SectionCard({ section }: { section: OnboardingSection }) {
  const [open, setOpen] = useState(true);
  const score = sectionScore(section.steps);
  const Icon = section.icon;
  const allDone = score === 100;

  return (
    <Card className={allDone ? "border-emerald-200 bg-emerald-50/30" : ""}>
      <CardHeader
        className="cursor-pointer select-none pb-2"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-3">
          <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${allDone ? "bg-emerald-100" : "bg-slate-100"}`}>
            <Icon className={`h-4 w-4 ${allDone ? "text-emerald-600" : "text-slate-500"}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm font-semibold text-slate-800">{section.title}</CardTitle>
              {allDone && <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <div className="flex-1 h-1.5 rounded-full bg-slate-200 overflow-hidden">
                <div
                  className={`h-full rounded-full ${allDone ? "bg-emerald-500" : score > 40 ? "bg-amber-400" : "bg-slate-400"}`}
                  style={{ width: `${score}%` }}
                />
              </div>
              <span className="text-xs font-medium text-slate-500 shrink-0">{score}%</span>
            </div>
          </div>
          {open ? <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" /> : <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />}
        </div>
      </CardHeader>
      {open && (
        <CardContent className="pt-0">
          {section.steps.map((step) => (
            <StepRow key={step.id} step={step} />
          ))}
        </CardContent>
      )}
    </Card>
  );
}

// ── Main ─────────────────────────────────────────────────────────────────────

export default function CustomerOnboardingPage() {
  const totalSteps = SECTIONS.flatMap((s) => s.steps).length;
  const completedSteps = SECTIONS.flatMap((s) => s.steps).filter((s) => s.status === "complete").length;
  const inProgressSteps = SECTIONS.flatMap((s) => s.steps).filter((s) => s.status === "in-progress").length;
  const overallScore = Math.round((completedSteps / totalSteps) * 100);

  const health =
    overallScore >= 80 ? { label: "On Track", variant: "success" as const, color: "text-emerald-600" }
    : overallScore >= 50 ? { label: "In Progress", variant: "warning" as const, color: "text-amber-600" }
    : { label: "Needs Attention", variant: "destructive" as const, color: "text-red-600" };

  const missingRequirements = SECTIONS.flatMap((s) =>
    s.steps.filter((step) => step.status === "pending").map((step) => ({ section: s.title, step: step.label, action: step.action }))
  );

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-600">
          <Building2 className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-slate-900">Customer Onboarding Center</h1>
          <p className="text-sm text-slate-500">Track facility setup, user configuration, and go-live readiness.</p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-5 text-center">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-1">Readiness Score</p>
            <p className={`text-4xl font-black tabular-nums ${health.color}`}>{overallScore}%</p>
            <Badge variant={health.variant} className="mt-2 text-xs">{health.label}</Badge>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5 text-center">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-1">Steps Complete</p>
            <p className="text-4xl font-black tabular-nums text-emerald-600">{completedSteps}</p>
            <p className="text-xs text-slate-400 mt-1">of {totalSteps} total steps</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5 text-center">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-1">In Progress</p>
            <p className="text-4xl font-black tabular-nums text-amber-500">{inProgressSteps}</p>
            <p className="text-xs text-slate-400 mt-1">steps active</p>
          </CardContent>
        </Card>
      </div>

      {/* Missing Requirements Alert */}
      {missingRequirements.length > 0 && (
        <Card className="border-amber-200 bg-amber-50">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              <CardTitle className="text-sm font-semibold text-amber-800">
                {missingRequirements.length} Pending Requirements
              </CardTitle>
            </div>
            <CardDescription className="text-amber-700 text-xs">
              Complete these steps before go-live.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-0 space-y-1.5">
            {missingRequirements.slice(0, 5).map((r, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-amber-800">
                <div className="h-1.5 w-1.5 rounded-full bg-amber-400 shrink-0" />
                <span className="text-amber-600">{r.section}:</span>
                <span>{r.step}</span>
                {r.action && (
                  <Link to={r.action.to} className="ml-auto text-blue-600 hover:underline flex items-center gap-0.5 shrink-0">
                    {r.action.label} <ArrowRight className="h-2.5 w-2.5" />
                  </Link>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Section Checklists */}
      <div className="space-y-4">
        {SECTIONS.map((section) => (
          <SectionCard key={section.id} section={section} />
        ))}
      </div>

      <p className="text-center text-xs text-slate-400 pb-4">
        Onboarding progress reflects current system configuration. All AI outputs require qualified human review.
      </p>
    </div>
  );
}
