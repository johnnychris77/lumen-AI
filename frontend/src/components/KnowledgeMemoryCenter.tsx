/**
 * v4.8 — LumenAI OS: Project Athena — Healthcare Knowledge Intelligence &
 * Institutional Memory.
 *
 * Frontend route `/knowledge-memory`, API prefix `/api/athena` —
 * deliberately distinct from the pre-existing `/api/knowledge` (v1.8) and
 * `/api/knowledge-graph` (see `app/models/athena_knowledge.py` for the
 * naming-disambiguation note). Athena's routes require real tenant
 * membership (`require_tenant_roles`), a stricter check than most other
 * modules in this app use today.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const TABS = [
  "Memory Engine", "Expert Capture", "Experience Graph", "Timeline", "Playbooks",
  "Curator", "Search", "Trust Score", "Assistant", "Preservation",
] as const;
type Tab = (typeof TABS)[number];

const PLAYBOOK_CATEGORIES = [
  "blood_detection_investigation", "corrosion_investigation", "loaner_instrument",
  "joint_commission_preparation", "vendor_tray", "robotic_instrument",
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {children}
    </div>
  );
}

function Json({ data }: { data: unknown }) {
  return <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(data, null, 2)}</pre>;
}

export default function KnowledgeMemoryCenter() {
  const [activeTab, setActiveTab] = useState<Tab>("Memory Engine");

  const [memorySummary, setMemorySummary] = useState<Record<string, unknown> | null>(null);
  const [contributionForm, setContributionForm] = useState({ category: "best_practice", title: "", body: "" });

  const [personQuery, setPersonQuery] = useState("");
  const [graphResult, setGraphResult] = useState<Record<string, unknown> | null>(null);
  const [chainForm, setChainForm] = useState({ person: "", experience_label: "", instrument_type: "", finding_type: "" });

  const [timelineFinding, setTimelineFinding] = useState("blood");
  const [timeline, setTimeline] = useState<Record<string, unknown> | null>(null);

  const [playbooks, setPlaybooks] = useState<Record<string, unknown>[] | null>(null);

  const [curatorSummary, setCuratorSummary] = useState<Record<string, unknown> | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Record<string, unknown> | null>(null);

  const [trustArticles, setTrustArticles] = useState<Record<string, unknown>[] | null>(null);

  const [assistantQuestion, setAssistantQuestion] = useState("");
  const [assistantAnswer, setAssistantAnswer] = useState<Record<string, unknown> | null>(null);

  const [sessions, setSessions] = useState<Record<string, unknown>[] | null>(null);
  const [sessionForm, setSessionForm] = useState({ subject_name: "", session_type: "exit_interview", summary: "" });

  useEffect(() => {
    api.get("/api/athena/memory/summary").then(setMemorySummary).catch(() => {});
  }, []);

  useEffect(() => {
    if (activeTab === "Playbooks") api.get("/api/athena/playbooks").then((r: Record<string, unknown>) => setPlaybooks(r.playbooks as Record<string, unknown>[])).catch(() => {});
    if (activeTab === "Curator") api.get("/api/athena/curator/summary").then(setCuratorSummary).catch(() => {});
    if (activeTab === "Trust Score") api.get("/api/athena/trust/articles").then((r: Record<string, unknown>) => setTrustArticles(r.articles as Record<string, unknown>[])).catch(() => {});
    if (activeTab === "Preservation") api.get("/api/athena/preservation/sessions").then((r: Record<string, unknown>) => setSessions(r.sessions as Record<string, unknown>[])).catch(() => {});
  }, [activeTab]);

  async function submitContribution() {
    if (!contributionForm.title.trim()) return;
    await api.post("/api/athena/expert-contributions", contributionForm);
    setContributionForm({ category: "best_practice", title: "", body: "" });
  }

  async function submitChain() {
    if (!chainForm.person.trim() || !chainForm.finding_type.trim()) return;
    const res = await api.post<Record<string, unknown>>("/api/athena/experience-graph/chains", chainForm);
    setGraphResult(res);
  }

  async function lookupPerson() {
    if (!personQuery.trim()) return;
    const res = await api.get<Record<string, unknown>>(`/api/athena/experience-graph/person/${encodeURIComponent(personQuery)}`);
    setGraphResult(res);
  }

  async function loadTimeline() {
    const res = await api.get<Record<string, unknown>>(`/api/athena/timeline?finding_type=${encodeURIComponent(timelineFinding)}`);
    setTimeline(res);
  }

  async function runSearch() {
    if (!searchQuery.trim()) return;
    const res = await api.get<Record<string, unknown>>(`/api/athena/search?q=${encodeURIComponent(searchQuery)}`);
    setSearchResults(res);
  }

  async function askAssistant() {
    if (!assistantQuestion.trim()) return;
    const res = await api.post<Record<string, unknown>>("/api/athena/assistant/ask", { question: assistantQuestion });
    setAssistantAnswer(res);
  }

  async function createSession() {
    if (!sessionForm.subject_name.trim()) return;
    await api.post("/api/athena/preservation/sessions", sessionForm);
    setSessionForm({ subject_name: "", session_type: "exit_interview", summary: "" });
    api.get("/api/athena/preservation/sessions").then((r: Record<string, unknown>) => setSessions(r.sessions as Record<string, unknown>[])).catch(() => {});
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Knowledge Memory Center</h1>
      <p className="text-xs text-slate-400">
        LumenAI's permanent organizational memory — institutional knowledge, the Experience Graph, clinical
        playbooks, the AI Knowledge Curator, organizational search, Knowledge Trust Scores, the Athena
        Assistant, and knowledge preservation. Clinical expertise no longer depends on individual memory.
      </p>

      <div className="flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`rounded px-3 py-1 text-sm ${activeTab === t ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {activeTab === "Memory Engine" && (
        <Section title="Institutional Memory Summary">{memorySummary && <Json data={memorySummary} />}</Section>
      )}

      {activeTab === "Expert Capture" && (
        <Section title="Submit Expert Contribution">
          <div className="space-y-2 text-sm">
            <select className="w-full rounded border border-slate-300 p-2" value={contributionForm.category}
              onChange={(e) => setContributionForm({ ...contributionForm, category: e.target.value })}>
              <option value="best_practice">Best Practice</option>
              <option value="clinical_pearl">Clinical Pearl</option>
              <option value="lesson_learned">Lesson Learned</option>
              <option value="teaching_point">Teaching Point</option>
              <option value="supervisor_experience">Supervisor Experience</option>
              <option value="vendor_observation">Vendor Observation</option>
              <option value="repair_observation">Repair Observation</option>
            </select>
            <input className="w-full rounded border border-slate-300 p-2" placeholder="Title" value={contributionForm.title}
              onChange={(e) => setContributionForm({ ...contributionForm, title: e.target.value })} />
            <textarea className="w-full rounded border border-slate-300 p-2" placeholder="Body" value={contributionForm.body}
              onChange={(e) => setContributionForm({ ...contributionForm, body: e.target.value })} />
            <button className="rounded bg-indigo-600 px-4 py-2 text-white" onClick={submitContribution}>Submit for Review</button>
          </div>
        </Section>
      )}

      {activeTab === "Experience Graph" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Record an Experience Chain">
            <div className="space-y-2 text-sm">
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Person" value={chainForm.person}
                onChange={(e) => setChainForm({ ...chainForm, person: e.target.value })} />
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Experience label" value={chainForm.experience_label}
                onChange={(e) => setChainForm({ ...chainForm, experience_label: e.target.value })} />
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Instrument type" value={chainForm.instrument_type}
                onChange={(e) => setChainForm({ ...chainForm, instrument_type: e.target.value })} />
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Finding type (e.g. blood)" value={chainForm.finding_type}
                onChange={(e) => setChainForm({ ...chainForm, finding_type: e.target.value })} />
              <button className="rounded bg-indigo-600 px-4 py-2 text-white" onClick={submitChain}>Build Chain</button>
            </div>
          </Section>
          <Section title="Look Up a Person's Graph">
            <div className="mb-3 flex gap-2">
              <input className="flex-1 rounded border border-slate-300 p-2 text-sm" placeholder="Person name" value={personQuery}
                onChange={(e) => setPersonQuery(e.target.value)} />
              <button className="rounded bg-indigo-600 px-4 py-1 text-sm text-white" onClick={lookupPerson}>Look Up</button>
            </div>
            {graphResult && <Json data={graphResult} />}
          </Section>
        </div>
      )}

      {activeTab === "Timeline" && (
        <Section title="Institutional Memory Timeline">
          <div className="mb-3 flex gap-2">
            <input className="flex-1 rounded border border-slate-300 p-2 text-sm" placeholder="Finding type" value={timelineFinding}
              onChange={(e) => setTimelineFinding(e.target.value)} />
            <button className="rounded bg-indigo-600 px-4 py-1 text-sm text-white" onClick={loadTimeline}>Load Timeline</button>
          </div>
          {timeline && <Json data={timeline.timeline} />}
        </Section>
      )}

      {activeTab === "Playbooks" && (
        <Section title="Clinical Playbooks">
          <p className="mb-2 text-xs text-slate-400">Categories: {PLAYBOOK_CATEGORIES.join(", ")}</p>
          {playbooks?.map((p) => (
            <div key={String(p.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              <span className="font-medium">{String(p.name)}</span> — {String(p.category)} (v{String(p.version)}, {String(p.status)})
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Curator" && (
        <Section title="AI Knowledge Curator">{curatorSummary && <Json data={curatorSummary} />}</Section>
      )}

      {activeTab === "Search" && (
        <Section title="Organizational Search">
          <div className="mb-3 flex gap-2">
            <input className="flex-1 rounded border border-slate-300 p-2 text-sm" placeholder="Search everything..." value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && runSearch()} />
            <button className="rounded bg-indigo-600 px-4 py-1 text-sm text-white" onClick={runSearch}>Search</button>
          </div>
          {searchResults && <Json data={searchResults} />}
        </Section>
      )}

      {activeTab === "Trust Score" && (
        <Section title="Knowledge Trust Scores">
          {trustArticles?.map((a) => (
            <div key={String(a.article_id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              <span className="font-medium">{String(a.title)}</span> — Trust: {String(a.overall_trust_score)}/100
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Assistant" && (
        <Section title="Athena Assistant">
          <div className="mb-3 flex gap-2">
            <input
              className="flex-1 rounded border border-slate-300 p-2 text-sm"
              placeholder='e.g. "Show me how we handled recurring corrosion in orthopedic drills."'
              value={assistantQuestion}
              onChange={(e) => setAssistantQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && askAssistant()}
            />
            <button className="rounded bg-indigo-600 px-4 py-2 text-sm text-white" onClick={askAssistant}>Ask</button>
          </div>
          {assistantAnswer && <Json data={assistantAnswer} />}
        </Section>
      )}

      {activeTab === "Preservation" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Preservation Sessions">
            {sessions?.map((s) => (
              <div key={String(s.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
                <span className="font-medium">{String(s.subject_name)}</span> — {String(s.session_type)} ({String(s.status)})
              </div>
            ))}
          </Section>
          <Section title="Capture a New Session">
            <div className="space-y-2 text-sm">
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Subject name" value={sessionForm.subject_name}
                onChange={(e) => setSessionForm({ ...sessionForm, subject_name: e.target.value })} />
              <select className="w-full rounded border border-slate-300 p-2" value={sessionForm.session_type}
                onChange={(e) => setSessionForm({ ...sessionForm, session_type: e.target.value })}>
                <option value="exit_interview">Exit Interview</option>
                <option value="video_capture">Video Capture</option>
                <option value="voice_transcription">Voice Transcription</option>
                <option value="workflow_recording">Workflow Recording</option>
                <option value="procedure_demonstration">Procedure Demonstration</option>
              </select>
              <textarea className="w-full rounded border border-slate-300 p-2" placeholder="Summary" value={sessionForm.summary}
                onChange={(e) => setSessionForm({ ...sessionForm, summary: e.target.value })} />
              <button className="rounded bg-indigo-600 px-4 py-2 text-white" onClick={createSession}>Capture Session</button>
            </div>
          </Section>
        </div>
      )}
    </div>
  );
}
