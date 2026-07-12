/**
 * LumenAI AI Specialist — Project Sage, Section 11: Technician Learning
 * Center.
 *
 * Frontend route `/my-learning`, API prefix `/api/sage/my-learning`. Shows
 * only the authenticated user's OWN authorized learning information -- the
 * backend resolves the learner from the authenticated identity, never a
 * client-supplied parameter, so peer performance is never exposed here.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Json = Record<string, unknown>;

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {children}
    </div>
  );
}

function JsonView({ data }: { data: unknown }) {
  return <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(data, null, 2)}</pre>;
}

export default function MyLearningCenter() {
  const [data, setData] = useState<Json | null>(null);

  useEffect(() => {
    api.get("/api/sage/my-learning").then(setData).catch(() => {});
  }, []);

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">My Learning</h1>
      <p className="text-xs text-slate-400">
        Your own assigned education, due dates, completed modules, and competency status. This view never
        shows a coworker's performance.
      </p>

      <Section title="Assigned Modules">
        {data && <JsonView data={data.assigned_modules} />}
      </Section>

      <Section title="Due Dates">
        {data && <JsonView data={data.due_dates} />}
      </Section>

      <Section title="Completed Education">
        {data && <JsonView data={data.completed_education} />}
      </Section>

      <Section title="Competency Status">
        {data && <JsonView data={data.competency_status} />}
      </Section>

      <Section title="Supervisor Feedback">
        {data && <JsonView data={data.supervisor_feedback} />}
      </Section>

      <Section title="Assessments">
        {data && <JsonView data={data.assessments} />}
      </Section>
    </div>
  );
}
