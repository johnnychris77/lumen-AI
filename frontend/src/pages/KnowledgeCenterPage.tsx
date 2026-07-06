import { useEffect, useState } from "react";
import { BookMarked } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface Article {
  id: number;
  category: string;
  title: string;
  body: string;
  author: string;
  reviewer: string;
  approval_status: string;
  version: number;
  applicable_instruments: string[];
  applicable_findings: string[];
  view_count: number;
}

interface Case {
  id: number;
  inspection_id: number;
  instrument_type: string;
  finding_type: string;
  title: string;
  supervisor_corrections: string;
  final_disposition: string;
  educational_notes: string;
  outcome: string;
}

interface Standard {
  id: number;
  standard_type: string;
  title: string;
  description: string;
  created_by: string;
}

interface SearchResult {
  matched_findings: string[];
  matched_instrument_families: string[];
  articles: Article[];
  cases: Case[];
}

interface AssistantResult {
  answer: string;
  sources: string[];
}

interface Analytics {
  most_viewed_articles: { id: number; title: string; view_count: number }[];
  most_common_questions: { query: string; count: number }[];
  knowledge_gaps: { finding_type: string; clinical_case_count: number }[];
  training_opportunities: { technician: string; finding_type: string }[];
}

const TABS = ["Search", "Articles", "Cases", "Standards", "Assistant", "Analytics"] as const;
type Tab = (typeof TABS)[number];

const CATEGORIES = [
  "best_practice", "local_standard", "approved_workflow", "clinical_pearl",
  "lesson_learned", "faq", "competency_guidance", "manufacturer_clarification",
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "approved" ? "bg-emerald-100 text-emerald-800"
    : status === "pending_review" ? "bg-amber-100 text-amber-800"
    : status === "rejected" ? "bg-red-100 text-red-800"
    : status === "archived" ? "bg-slate-200 text-slate-500"
    : "bg-slate-100 text-slate-600";
  return <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>{status.replace(/_/g, " ")}</span>;
}

export default function KnowledgeCenterPage() {
  const { role } = useAuth();
  const isLeadership = role === "admin" || role === "spd_manager";
  const [tab, setTab] = useState<Tab>("Search");

  const [query, setQuery] = useState("");
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);

  const [articles, setArticles] = useState<Article[]>([]);
  const [newArticle, setNewArticle] = useState({ category: "best_practice", title: "", body: "" });

  const [cases, setCases] = useState<Case[]>([]);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [newStandard, setNewStandard] = useState({ standard_type: "coverage_requirement", title: "", description: "" });

  const [question, setQuestion] = useState("");
  const [assistantResult, setAssistantResult] = useState<AssistantResult | null>(null);

  const [analytics, setAnalytics] = useState<Analytics | null>(null);

  function loadArticles() {
    api.get<{ articles: Article[] }>("/api/knowledge/articles").then((d) => setArticles(d.articles));
  }
  function loadCases() {
    api.get<{ cases: Case[] }>("/api/knowledge/cases").then((d) => setCases(d.cases));
  }
  function loadStandards() {
    api.get<{ standards: Standard[] }>("/api/knowledge/standards").then((d) => setStandards(d.standards));
  }
  function loadAnalytics() {
    if (isLeadership) api.get<Analytics>("/api/knowledge/analytics").then(setAnalytics);
  }

  useEffect(() => {
    if (tab === "Articles") loadArticles();
    if (tab === "Cases") loadCases();
    if (tab === "Standards") loadStandards();
    if (tab === "Analytics") loadAnalytics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  async function runSearch() {
    if (!query.trim()) return;
    const result = await api.post<SearchResult>("/api/knowledge/search", { query });
    setSearchResult(result);
  }

  async function submitArticle() {
    if (!newArticle.title.trim() || !newArticle.body.trim()) return;
    await api.post("/api/knowledge/articles", newArticle);
    setNewArticle({ category: "best_practice", title: "", body: "" });
    loadArticles();
  }

  async function approveArticle(id: number) {
    await api.post(`/api/knowledge/articles/${id}/approve`);
    loadArticles();
  }
  async function archiveArticle(id: number) {
    await api.post(`/api/knowledge/articles/${id}/archive`);
    loadArticles();
  }

  async function submitStandard() {
    if (!newStandard.title.trim() || !newStandard.description.trim()) return;
    await api.post("/api/knowledge/standards", newStandard);
    setNewStandard({ standard_type: "coverage_requirement", title: "", description: "" });
    loadStandards();
  }

  async function askAssistant() {
    if (!question.trim()) return;
    const result = await api.post<AssistantResult>("/api/knowledge/assistant", { question });
    setAssistantResult(result);
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
      <div className="flex items-center gap-2">
        <BookMarked className="h-6 w-6 text-purple-600" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Institutional Knowledge Center</h1>
          <p className="text-sm text-slate-500 mt-1">
            The organization's permanent clinical memory — searchable, governed, and reusable.
          </p>
        </div>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {TABS.filter((t) => t !== "Analytics" || isLeadership).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === t ? "border-purple-600 text-purple-700" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Search" && (
        <Section title="Smart Knowledge Search">
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              placeholder='e.g. "show all blood findings in Kerrisons"'
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runSearch()}
              className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm"
            />
            <button onClick={runSearch} className="text-xs font-semibold px-3 py-1.5 rounded bg-purple-600 text-white">
              Search
            </button>
          </div>
          {searchResult && (
            <div className="space-y-3 text-sm">
              <div className="flex flex-wrap gap-2">
                {searchResult.matched_findings.map((f) => (
                  <span key={f} className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">finding: {f}</span>
                ))}
                {searchResult.matched_instrument_families.map((f) => (
                  <span key={f} className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">family: {f}</span>
                ))}
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500 mb-1">Articles ({searchResult.articles.length})</p>
                {searchResult.articles.map((a) => (
                  <div key={a.id} className="border-t border-slate-100 py-1.5">
                    <span className="font-medium">{a.title}</span> — <span className="text-slate-500">{a.body}</span>
                  </div>
                ))}
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500 mb-1">Cases ({searchResult.cases.length})</p>
                {searchResult.cases.map((c) => (
                  <div key={c.id} className="border-t border-slate-100 py-1.5">
                    <span className="font-medium">{c.title}</span>
                    {c.final_disposition && <span className="text-slate-500"> — {c.final_disposition}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Section>
      )}

      {tab === "Articles" && (
        <div className="space-y-4">
          <Section title="Contribute Knowledge">
            <div className="space-y-2">
              <select
                value={newArticle.category}
                onChange={(e) => setNewArticle({ ...newArticle, category: e.target.value })}
                className="rounded border border-slate-300 px-2 py-1.5 text-sm"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
                ))}
              </select>
              <input
                type="text" placeholder="Title" value={newArticle.title}
                onChange={(e) => setNewArticle({ ...newArticle, title: e.target.value })}
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
              />
              <textarea
                placeholder="Body" value={newArticle.body}
                onChange={(e) => setNewArticle({ ...newArticle, body: e.target.value })}
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" rows={3}
              />
              <button onClick={submitArticle} className="text-xs font-semibold px-3 py-1.5 rounded bg-purple-600 text-white">
                Submit for Review
              </button>
            </div>
          </Section>
          <Section title={`Articles (${articles.length})`}>
            <div className="space-y-2 text-sm">
              {articles.map((a) => (
                <div key={a.id} className="border-t border-slate-100 pt-2 flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{a.title} <span className="text-slate-400 text-xs">v{a.version}</span></p>
                    <p className="text-slate-500 text-xs">{a.category.replace(/_/g, " ")} · by {a.author || "unknown"}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusBadge status={a.approval_status} />
                    {isLeadership && a.approval_status === "pending_review" && (
                      <button onClick={() => approveArticle(a.id)} className="text-xs text-emerald-700 underline">Approve</button>
                    )}
                    {isLeadership && a.approval_status === "approved" && (
                      <button onClick={() => archiveArticle(a.id)} className="text-xs text-slate-500 underline">Archive</button>
                    )}
                  </div>
                </div>
              ))}
              {articles.length === 0 && <p className="text-slate-400">No articles yet.</p>}
            </div>
          </Section>
        </div>
      )}

      {tab === "Cases" && (
        <Section title={`Clinical Case Library (${cases.length})`}>
          <div className="space-y-2 text-sm">
            {cases.map((c) => (
              <div key={c.id} className="border-t border-slate-100 pt-2">
                <p className="font-medium">{c.title}</p>
                <p className="text-slate-500 text-xs">
                  Inspection #{c.inspection_id} · {c.final_disposition || "no disposition yet"}
                  {c.outcome && ` · ${c.outcome}`}
                </p>
                {c.educational_notes && <p className="text-xs mt-1">{c.educational_notes}</p>}
              </div>
            ))}
            {cases.length === 0 && <p className="text-slate-400">No significant cases recorded yet.</p>}
          </div>
        </Section>
      )}

      {tab === "Standards" && (
        <div className="space-y-4">
          {isLeadership && (
            <Section title="Define Organization Standard">
              <div className="space-y-2">
                <select
                  value={newStandard.standard_type}
                  onChange={(e) => setNewStandard({ ...newStandard, standard_type: e.target.value })}
                  className="rounded border border-slate-300 px-2 py-1.5 text-sm"
                >
                  {["inspection_standard", "photography_standard", "coverage_requirement", "supervisor_approval_threshold", "competency_requirement"].map((s) => (
                    <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
                  ))}
                </select>
                <input
                  type="text" placeholder="Title" value={newStandard.title}
                  onChange={(e) => setNewStandard({ ...newStandard, title: e.target.value })}
                  className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                />
                <textarea
                  placeholder="Description" value={newStandard.description}
                  onChange={(e) => setNewStandard({ ...newStandard, description: e.target.value })}
                  className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" rows={2}
                />
                <button onClick={submitStandard} className="text-xs font-semibold px-3 py-1.5 rounded bg-purple-600 text-white">
                  Add Standard
                </button>
              </div>
            </Section>
          )}
          <Section title={`Organization Standards (${standards.length})`}>
            <div className="space-y-2 text-sm">
              {standards.map((s) => (
                <div key={s.id} className="border-t border-slate-100 pt-2">
                  <p className="font-medium">{s.title} <span className="text-slate-400 text-xs">({s.standard_type.replace(/_/g, " ")})</span></p>
                  <p className="text-slate-500 text-xs">{s.description}</p>
                </div>
              ))}
              {standards.length === 0 && <p className="text-slate-400">No local standards defined yet — manufacturer IFUs apply.</p>}
            </div>
          </Section>
        </div>
      )}

      {tab === "Assistant" && (
        <Section title="AI Knowledge Assistant">
          <div className="flex gap-2 mb-3">
            <input
              type="text" placeholder='e.g. "why is this finding important?"' value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && askAssistant()}
              className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm"
            />
            <button onClick={askAssistant} className="text-xs font-semibold px-3 py-1.5 rounded bg-purple-600 text-white">
              Ask
            </button>
          </div>
          {assistantResult && (
            <div className="text-sm space-y-2">
              <p>{assistantResult.answer}</p>
              <div className="flex flex-wrap gap-1.5">
                {assistantResult.sources.map((s, i) => (
                  <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">{s}</span>
                ))}
              </div>
            </div>
          )}
        </Section>
      )}

      {tab === "Analytics" && isLeadership && analytics && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Section title="Most Viewed Articles">
            {analytics.most_viewed_articles.map((a) => (
              <p key={a.id} className="text-sm py-0.5">{a.title} — {a.view_count} views</p>
            ))}
            {analytics.most_viewed_articles.length === 0 && <p className="text-sm text-slate-400">No views yet.</p>}
          </Section>
          <Section title="Most Common Questions">
            {analytics.most_common_questions.map((q, i) => (
              <p key={i} className="text-sm py-0.5">"{q.query}" — {q.count}×</p>
            ))}
            {analytics.most_common_questions.length === 0 && <p className="text-sm text-slate-400">No questions logged yet.</p>}
          </Section>
          <Section title="Knowledge Gaps">
            {analytics.knowledge_gaps.map((g, i) => (
              <p key={i} className="text-sm py-0.5">{g.finding_type} — {g.clinical_case_count} case(s), no approved guidance</p>
            ))}
            {analytics.knowledge_gaps.length === 0 && <p className="text-sm text-slate-400">No gaps detected.</p>}
          </Section>
          <Section title="Training Opportunities">
            {analytics.training_opportunities.map((t, i) => (
              <p key={i} className="text-sm py-0.5">{t.technician} — repeated {t.finding_type} errors</p>
            ))}
            {analytics.training_opportunities.length === 0 && <p className="text-sm text-slate-400">None detected.</p>}
          </Section>
        </div>
      )}
    </div>
  );
}
