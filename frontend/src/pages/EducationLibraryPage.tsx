import { useState, useEffect } from "react";
import { BookOpen } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface Article {
  finding: string;
  finding_type: string;
  definition: string;
  clinical_importance: string;
  typical_anatomy_locations: string[];
  inspection_tips: string;
  cleaning_considerations: string;
  corrective_actions: string[];
  reference: string;
}

export default function EducationLibraryPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiFetch<{ articles: Article[] }>("/api/mentor/education");
        setArticles(data.articles);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <div className="p-6 text-sm text-slate-500">Loading education library…</div>;
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-4">
      <div className="flex items-center gap-2">
        <BookOpen className="h-6 w-6 text-indigo-600" />
        <h1 className="text-xl font-bold text-slate-900">SPD Education Library</h1>
      </div>
      <p className="text-sm text-slate-500">
        Structured reference for every contamination and condition category LumenAI recognizes —
        definition, clinical importance, typical anatomy locations, inspection tips, cleaning
        considerations, and corrective actions.
      </p>

      <div className="space-y-2">
        {articles.map((a) => (
          <div key={a.finding_type} className="rounded-lg border border-slate-200 bg-white">
            <button
              onClick={() => setOpen(open === a.finding_type ? null : a.finding_type)}
              className="w-full flex items-center justify-between px-4 py-3 text-left"
            >
              <span className="font-semibold capitalize text-slate-800">{a.finding.replace(/_/g, " ")}</span>
              <span className="text-xs text-slate-400">{open === a.finding_type ? "Hide" : "View"}</span>
            </button>
            {open === a.finding_type && (
              <div className="px-4 pb-4 space-y-2 text-sm text-slate-700">
                <p><span className="font-medium text-slate-500">Definition:</span> {a.definition}</p>
                <p><span className="font-medium text-slate-500">Clinical importance:</span> {a.clinical_importance}</p>
                <p><span className="font-medium text-slate-500">Typical anatomy locations:</span> {a.typical_anatomy_locations.join(", ")}</p>
                <p><span className="font-medium text-slate-500">Inspection tips:</span> {a.inspection_tips}</p>
                <p><span className="font-medium text-slate-500">Cleaning considerations:</span> {a.cleaning_considerations}</p>
                <div>
                  <span className="font-medium text-slate-500">Corrective actions:</span>
                  <ul className="mt-1 space-y-0.5">
                    {a.corrective_actions.map((s, i) => <li key={i}>• {s}</li>)}
                  </ul>
                </div>
                <p className="text-xs text-slate-400">{a.reference}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
