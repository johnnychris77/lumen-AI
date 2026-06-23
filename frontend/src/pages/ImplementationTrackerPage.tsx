import { useState } from "react";
import { CheckCircle2, AlertTriangle, Clock, ChevronDown, ChevronUp, User } from "lucide-react";

type TaskStatus = "complete" | "in-progress" | "blocked" | "pending";

interface ImplementationTask {
  id: string;
  label: string;
  owner: string;
  status: TaskStatus;
  dueOffset: string;
  notes?: string;
}

interface Phase {
  id: string;
  label: string;
  weekRange: string;
  tasks: ImplementationTask[];
}

const PHASES: Phase[] = [
  {
    id: "planning",
    label: "Planning",
    weekRange: "Week –2 to –1",
    tasks: [
      { id: "p1", label: "Kick-off meeting with SPD Director and IT lead", owner: "CS Lead", status: "complete", dueOffset: "Day –10" },
      { id: "p2", label: "Confirm tenant_id and facility name", owner: "CS Lead", status: "complete", dueOffset: "Day –8" },
      { id: "p3", label: "Define RBAC roles and user list", owner: "CS Lead + Customer IT", status: "complete", dueOffset: "Day –7" },
      { id: "p4", label: "Identify scope types in active fleet", owner: "SPD Manager", status: "complete", dueOffset: "Day –5" },
      { id: "p5", label: "Select vendor contacts for baseline submission", owner: "SPD Manager", status: "complete", dueOffset: "Day –5" },
      { id: "p6", label: "Confirm borescope / imaging hardware available", owner: "Customer IT", status: "in-progress", dueOffset: "Day –3" },
    ],
  },
  {
    id: "configuration",
    label: "Configuration",
    weekRange: "Week –1",
    tasks: [
      { id: "c1", label: "Provision tenant in production database", owner: "LumenAI DevOps", status: "complete", dueOffset: "Day –5" },
      { id: "c2", label: "Generate and deliver admin API key (SHA-256 stored)", owner: "LumenAI DevOps", status: "complete", dueOffset: "Day –5" },
      { id: "c3", label: "Create user accounts (admin, spd_manager, spd_technician)", owner: "CS Lead", status: "complete", dueOffset: "Day –3" },
      { id: "c4", label: "Configure SMTP for approval notifications", owner: "Customer IT", status: "in-progress", dueOffset: "Day –2", notes: "Awaiting IT firewall approval" },
      { id: "c5", label: "Verify VITE_API_BASE_URL in frontend build", owner: "LumenAI DevOps", status: "complete", dueOffset: "Day –2" },
      { id: "c6", label: "Confirm ENABLE_DEV_AUTH=false in production", owner: "LumenAI DevOps", status: "complete", dueOffset: "Day –1" },
    ],
  },
  {
    id: "training",
    label: "Training",
    weekRange: "Days 1–5",
    tasks: [
      { id: "t1", label: "SPD Technician training session (new inspection + image capture)", owner: "CS Lead", status: "complete", dueOffset: "Day 1" },
      { id: "t2", label: "SPD Manager training session (review queue + CAPA + findings)", owner: "CS Lead", status: "complete", dueOffset: "Day 2" },
      { id: "t3", label: "Vendor/Manufacturer training (baseline submission portal)", owner: "CS Lead", status: "in-progress", dueOffset: "Day 3" },
      { id: "t4", label: "Executive training (Command Center + ROI Center)", owner: "CS Lead", status: "pending", dueOffset: "Day 5" },
      { id: "t5", label: "Training completion confirmed via /training-compliance", owner: "CS Lead", status: "pending", dueOffset: "Day 5" },
    ],
  },
  {
    id: "data-collection",
    label: "Data Collection",
    weekRange: "Days 1–14",
    tasks: [
      { id: "d1", label: "Vendor submits baseline images for top 3 scope types", owner: "Vendor", status: "in-progress", dueOffset: "Day 5" },
      { id: "d2", label: "SPD Manager approves ≥1 baseline per scope type", owner: "SPD Manager", status: "pending", dueOffset: "Day 7" },
      { id: "d3", label: "First 10 live inspections completed by technicians", owner: "SPD Technicians", status: "in-progress", dueOffset: "Day 7" },
      { id: "d4", label: "Reach ≥50% baseline coverage (instrument fleet)", owner: "SPD Manager + Vendor", status: "pending", dueOffset: "Day 14" },
      { id: "d5", label: "First critical finding reviewed and CAPA opened (if applicable)", owner: "SPD Manager", status: "pending", dueOffset: "Day 14" },
    ],
  },
  {
    id: "validation",
    label: "Validation",
    weekRange: "Days 14–21",
    tasks: [
      { id: "v1", label: "Reach ≥50 inspections", owner: "SPD Technicians", status: "pending", dueOffset: "Day 21" },
      { id: "v2", label: "Customer Health Score ≥ 50 (Yellow or Green)", owner: "CS Lead", status: "pending", dueOffset: "Day 21" },
      { id: "v3", label: "Audit evidence bundle generated and reviewed", owner: "SPD Manager", status: "pending", dueOffset: "Day 21" },
      { id: "v4", label: "Data completeness ≥ 70% across inspection records", owner: "CS Lead", status: "pending", dueOffset: "Day 21" },
    ],
  },
  {
    id: "go-live",
    label: "Go-Live",
    weekRange: "Day 21",
    tasks: [
      { id: "g1", label: "Go-Live Readiness Score ≥ 75 confirmed at /go-live-center", owner: "CS Lead", status: "pending", dueOffset: "Day 21" },
      { id: "g2", label: "Executive Command Center demo with SPD Director", owner: "CS Lead", status: "pending", dueOffset: "Day 21" },
      { id: "g3", label: "Incident escalation path confirmed (engineering SLA)", owner: "CS Lead + LumenAI", status: "pending", dueOffset: "Day 21" },
    ],
  },
  {
    id: "post-go-live",
    label: "Post Go-Live",
    weekRange: "Days 22–90",
    tasks: [
      { id: "pg1", label: "30-day health check — Customer Health Score + adoption review", owner: "CS Lead", status: "pending", dueOffset: "Day 30" },
      { id: "pg2", label: "60-day ROI preliminary report generated at /roi-center", owner: "CS Lead", status: "pending", dueOffset: "Day 60" },
      { id: "pg3", label: "90-day QBR with SPD Director + executive sponsor", owner: "CS Lead + Account Exec", status: "pending", dueOffset: "Day 90" },
      { id: "pg4", label: "Renewal conversation initiated (if Green health score)", owner: "Account Exec", status: "pending", dueOffset: "Day 75" },
      { id: "pg5", label: "Reference story drafted (with customer permission)", owner: "CS Lead", status: "pending", dueOffset: "Day 90" },
    ],
  },
];

function statusIcon(s: TaskStatus) {
  if (s === "complete") return <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0" />;
  if (s === "in-progress") return <Clock className="h-4 w-4 text-blue-500 flex-shrink-0" />;
  if (s === "blocked") return <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" />;
  return <div className="h-4 w-4 rounded-full border-2 border-slate-300 flex-shrink-0" />;
}

function phasePct(phase: Phase) {
  const done = phase.tasks.filter(t => t.status === "complete").length;
  return Math.round((done / phase.tasks.length) * 100);
}

function PhaseCard({ phase }: { phase: Phase }) {
  const [open, setOpen] = useState(phase.tasks.some(t => t.status === "in-progress" || t.status === "blocked"));
  const pct = phasePct(phase);
  const blocked = phase.tasks.filter(t => t.status === "blocked");
  const inProgress = phase.tasks.filter(t => t.status === "in-progress");

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <button
        className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-slate-50 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-slate-800">{phase.label}</span>
            <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">{phase.weekRange}</span>
            {blocked.length > 0 && (
              <span className="text-xs text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
                {blocked.length} blocked
              </span>
            )}
            {inProgress.length > 0 && blocked.length === 0 && (
              <span className="text-xs text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
                {inProgress.length} in progress
              </span>
            )}
          </div>
          <div className="mt-2 flex items-center gap-3">
            <div className="flex-1 bg-slate-100 rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full transition-all ${pct === 100 ? "bg-emerald-500" : pct >= 50 ? "bg-blue-500" : "bg-slate-300"}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs font-medium text-slate-600 flex-shrink-0">{pct}%</span>
          </div>
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
      </button>

      {open && (
        <div className="border-t border-slate-100 divide-y divide-slate-50">
          {phase.tasks.map(task => (
            <div key={task.id} className={`flex items-start gap-3 px-5 py-3 ${task.status === "blocked" ? "bg-red-50" : ""}`}>
              <div className="mt-0.5">{statusIcon(task.status)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-0.5">
                  <span className={`text-sm ${task.status === "complete" ? "text-slate-500 line-through" : "text-slate-800"}`}>
                    {task.label}
                  </span>
                  <span className="text-xs text-slate-400 flex-shrink-0">{task.dueOffset}</span>
                </div>
                <div className="flex items-center gap-1 mt-0.5">
                  <User className="h-3 w-3 text-slate-400" />
                  <span className="text-xs text-slate-500">{task.owner}</span>
                </div>
                {task.notes && (
                  <div className="mt-1 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                    {task.notes}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ImplementationTrackerPage() {
  const allTasks = PHASES.flatMap(p => p.tasks);
  const completedCount = allTasks.filter(t => t.status === "complete").length;
  const blockedCount = allTasks.filter(t => t.status === "blocked").length;
  const inProgressCount = allTasks.filter(t => t.status === "in-progress").length;
  const overallPct = Math.round((completedCount / allTasks.length) * 100);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Implementation Tracker</h1>
        <p className="text-sm text-slate-500 mt-1">First customer deployment progress across all phases</p>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Overall Progress", value: `${overallPct}%`, color: "text-indigo-700 bg-indigo-50 border-indigo-200" },
          { label: "Completed", value: completedCount, color: "text-emerald-700 bg-emerald-50 border-emerald-200" },
          { label: "In Progress", value: inProgressCount, color: "text-blue-700 bg-blue-50 border-blue-200" },
          { label: "Blocked", value: blockedCount, color: blockedCount > 0 ? "text-red-700 bg-red-50 border-red-200" : "text-slate-500 bg-slate-50 border-slate-200" },
        ].map(s => (
          <div key={s.label} className={`rounded-lg border p-4 text-center ${s.color}`}>
            <div className="text-2xl font-bold">{s.value}</div>
            <div className="text-xs font-medium mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Phase cards */}
      <div className="space-y-3">
        {PHASES.map(phase => <PhaseCard key={phase.id} phase={phase} />)}
      </div>
    </div>
  );
}
