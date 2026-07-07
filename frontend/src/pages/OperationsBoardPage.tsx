import { useEffect, useState } from "react";
import { ClipboardList } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface QueueItem {
  inspection_id: number;
  instrument_type: string;
  workflow_state: string;
  risk_tier: string;
  priority_tier: string;
  minutes_waiting: number | null;
  assigned_technician: string | null;
}

interface TechnicianWorkload {
  technician: string;
  open_inspections: number;
  completed_inspections: number;
  workload: number;
  avg_inspection_time_minutes: number | null;
}

interface OperationsBoard {
  technician_workload: TechnicianWorkload[];
  supervisor_queue: QueueItem[];
  pending_approvals: QueueItem[];
  high_risk_findings: QueueItem[];
  repair_queue: QueueItem[];
  or_urgent_items: QueueItem[];
  vendor_instruments: QueueItem[];
}

function MiniList({ items }: { items: QueueItem[] }) {
  if (items.length === 0) return <p className="text-sm text-slate-400 py-1">None right now.</p>;
  return (
    <ul className="space-y-1.5 text-sm">
      {items.map((item) => (
        <li key={item.inspection_id} className="flex items-center justify-between">
          <span>
            #{item.inspection_id} — {item.instrument_type}{" "}
            <span className="text-slate-400">({item.workflow_state})</span>
          </span>
          <span className="text-xs text-slate-500">{item.assigned_technician ?? "Unassigned"}</span>
        </li>
      ))}
    </ul>
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

export default function OperationsBoardPage() {
  const [board, setBoard] = useState<OperationsBoard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<OperationsBoard>("/api/operations-board")
      .then(setBoard)
      .catch(() => setError("You may not have access to the Supervisor Operations Board, or it failed to load."));
  }, []);

  if (error) return <div className="p-6 text-sm text-red-600">{error}</div>;
  if (!board) return <div className="p-6 text-sm text-slate-500">Loading…</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
      <div className="flex items-center gap-2">
        <ClipboardList className="h-6 w-6 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Supervisor Operations Board</h1>
          <p className="text-sm text-slate-500 mt-1">
            Technician workload, pending approvals, and clinical-risk queues for the shift.
          </p>
        </div>
      </div>

      <Section title="Technician Workload" count={board.technician_workload.length}>
        {board.technician_workload.length === 0 ? (
          <p className="text-sm text-slate-400 py-1">No technicians currently assigned.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-400 text-xs">
                <th className="py-1 pr-3">Technician</th>
                <th className="py-1 px-2">Open</th>
                <th className="py-1 px-2">Completed</th>
                <th className="py-1 px-2">Avg. Inspection Time</th>
              </tr>
            </thead>
            <tbody>
              {board.technician_workload.map((t) => (
                <tr key={t.technician} className="border-t border-slate-100">
                  <td className="py-1.5 pr-3 font-medium">{t.technician}</td>
                  <td className="py-1.5 px-2">{t.open_inspections}</td>
                  <td className="py-1.5 px-2">{t.completed_inspections}</td>
                  <td className="py-1.5 px-2">
                    {t.avg_inspection_time_minutes == null ? "—" : `${Math.round(t.avg_inspection_time_minutes)}m`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Section title="Supervisor Queue" count={board.supervisor_queue.length}>
          <MiniList items={board.supervisor_queue} />
        </Section>
        <Section title="High-Risk Findings" count={board.high_risk_findings.length}>
          <MiniList items={board.high_risk_findings} />
        </Section>
        <Section title="Repair Queue" count={board.repair_queue.length}>
          <MiniList items={board.repair_queue} />
        </Section>
        <Section title="OR Urgent Items" count={board.or_urgent_items.length}>
          <MiniList items={board.or_urgent_items} />
        </Section>
        <Section title="Vendor Instruments" count={board.vendor_instruments.length}>
          <MiniList items={board.vendor_instruments} />
        </Section>
      </div>
    </div>
  );
}
