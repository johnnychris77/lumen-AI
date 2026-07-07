import { useEffect, useState } from "react";
import { ListChecks } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface QueueItem {
  inspection_id: number;
  instrument_type: string;
  facility_name: string | null;
  procedure_priority: string | null;
  workflow_state: string;
  risk_tier: string;
  priority_score: number;
  priority_tier: string;
  priority_reasons: string[];
  disposition: string;
  minutes_waiting: number | null;
  assigned_technician: string | null;
  is_vendor_tray: boolean;
  is_loaner_instrument: boolean;
  has_repeat_findings: boolean;
}

interface WorkQueue {
  pending_inspections: QueueItem[];
  high_risk_inspections: QueueItem[];
  or_priority_instruments: QueueItem[];
  vendor_trays: QueueItem[];
  loaner_instruments: QueueItem[];
  repeat_inspections: QueueItem[];
  supervisor_reviews: QueueItem[];
  repair_holds: QueueItem[];
  total_pending: number;
}

function priorityBadgeClass(tier: string): string {
  switch (tier) {
    case "Critical":
      return "bg-red-100 text-red-800";
    case "High":
      return "bg-orange-100 text-orange-800";
    case "Medium":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-slate-100 text-slate-600";
  }
}

function formatWait(minutes: number | null): string {
  if (minutes == null) return "—";
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const rem = minutes % 60;
  return `${hours}h ${rem}m`;
}

function QueueTable({ items }: { items: QueueItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-400 py-2">Nothing in this queue right now.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-400 text-xs">
            <th className="py-1 pr-3">Instrument</th>
            <th className="py-1 px-2">Procedure Priority</th>
            <th className="py-1 px-2">Status</th>
            <th className="py-1 px-2">Risk</th>
            <th className="py-1 px-2">Priority</th>
            <th className="py-1 px-2">Waiting</th>
            <th className="py-1 px-2">Assigned</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.inspection_id} className="border-t border-slate-100">
              <td className="py-1.5 pr-3 font-medium">
                #{item.inspection_id} — {item.instrument_type}
                {item.facility_name && <span className="text-slate-400"> · {item.facility_name}</span>}
              </td>
              <td className="py-1.5 px-2 capitalize">{item.procedure_priority?.replace(/_/g, " ") ?? "—"}</td>
              <td className="py-1.5 px-2">{item.workflow_state}</td>
              <td className="py-1.5 px-2">{item.risk_tier}</td>
              <td className="py-1.5 px-2">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${priorityBadgeClass(item.priority_tier)}`}>
                  {item.priority_tier} ({item.priority_score})
                </span>
              </td>
              <td className="py-1.5 px-2">{formatWait(item.minutes_waiting)}</td>
              <td className="py-1.5 px-2">{item.assigned_technician ?? "Unassigned"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Section({ title, count, children }: { title: string; count: number; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">{count}</span>
      </div>
      {children}
    </div>
  );
}

export default function InspectionWorkQueuePage() {
  const [queue, setQueue] = useState<WorkQueue | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<WorkQueue>("/api/inspection-work-queue")
      .then(setQueue)
      .catch(() => setError("Failed to load the inspection work queue."));
  }, []);

  if (error) return <div className="p-6 text-sm text-red-600">{error}</div>;
  if (!queue) return <div className="p-6 text-sm text-slate-500">Loading…</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
      <div className="flex items-center gap-2">
        <ListChecks className="h-6 w-6 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Smart Inspection Queue</h1>
          <p className="text-sm text-slate-500 mt-1">
            {queue.total_pending} inspection{queue.total_pending === 1 ? "" : "s"} pending, ranked by clinical risk,
            OR urgency, and supervisor workload.
          </p>
        </div>
      </div>

      <Section title="All Pending Inspections" count={queue.pending_inspections.length}>
        <QueueTable items={queue.pending_inspections} />
      </Section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Section title="High-Risk Inspections" count={queue.high_risk_inspections.length}>
          <QueueTable items={queue.high_risk_inspections} />
        </Section>
        <Section title="OR Priority Instruments" count={queue.or_priority_instruments.length}>
          <QueueTable items={queue.or_priority_instruments} />
        </Section>
        <Section title="Vendor Trays" count={queue.vendor_trays.length}>
          <QueueTable items={queue.vendor_trays} />
        </Section>
        <Section title="Loaner Instruments" count={queue.loaner_instruments.length}>
          <QueueTable items={queue.loaner_instruments} />
        </Section>
        <Section title="Repeat Inspections" count={queue.repeat_inspections.length}>
          <QueueTable items={queue.repeat_inspections} />
        </Section>
        <Section title="Supervisor Reviews" count={queue.supervisor_reviews.length}>
          <QueueTable items={queue.supervisor_reviews} />
        </Section>
        <Section title="Repair Holds" count={queue.repair_holds.length}>
          <QueueTable items={queue.repair_holds} />
        </Section>
      </div>
    </div>
  );
}
