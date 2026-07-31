import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  LineChart,
  Line,
  CartesianGrid,
} from "recharts";
import { DemoDisclaimer } from "./DemoDisclaimer";

// All figures are SYNTHETIC and illustrative.
const FINDING_CATEGORIES = [
  { name: "Debris", value: 34 },
  { name: "Corrosion", value: 18 },
  { name: "Residue", value: 12 },
  { name: "Scratch", value: 9 },
  { name: "Clear", value: 121 },
];

const TREND = [
  { week: "W1", reviewRate: 22 },
  { week: "W2", reviewRate: 19 },
  { week: "W3", reviewRate: 24 },
  { week: "W4", reviewRate: 16 },
  { week: "W5", reviewRate: 14 },
  { week: "W6", reviewRate: 15 },
];

const STATS = [
  { label: "Inspections completed", value: "194" },
  { label: "Review-required cases", value: "31" },
  { label: "Baseline availability", value: "78%" },
  { label: "Evidence completeness", value: "96%" },
];

export function DashboardPreview() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-900">Concept quality dashboard</h3>
        <DemoDisclaimer />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {STATS.map((s) => (
          <div key={s.label} className="rounded-lg bg-slate-50 p-3">
            <div className="text-2xl font-bold tracking-tight text-slate-900">{s.value}</div>
            <div className="mt-0.5 text-xs text-slate-500">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Finding categories</p>
          <div className="h-56" aria-label="Bar chart of synthetic finding categories">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={FINDING_CATEGORIES}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: "#eef2ff" }} />
                <Bar dataKey="value" fill="#4f46e5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Review-required rate over time (%)
          </p>
          <div className="h-56" aria-label="Line chart of synthetic review-required rate over six weeks">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={TREND}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="week" tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
                <Tooltip />
                <Line type="monotone" dataKey="reviewRate" stroke="#0284c7" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
