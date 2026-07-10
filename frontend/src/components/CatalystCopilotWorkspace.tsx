/**
 * v4.4 — LumenAI OS: Project Catalyst — AI Copilot & Natural Language
 * Operations workspace.
 *
 * Frontend route `/copilot-workspace`, API prefix `/api/catalyst` —
 * deliberately distinct from the pre-existing P9 "Autonomous Inspection
 * Copilot" system (`/api/copilot`, a guided checklist wizard unrelated
 * to this conversational surface). See `app/models/catalyst_copilot.py`
 * for the full naming-disambiguation note.
 *
 * No chat-bubble component existed anywhere in this codebase before this
 * sprint — everything here is new. Panels: Conversation, Suggested
 * Actions, Evidence Panel, Related Knowledge, Open Tasks, Recent
 * Searches, Pinned Insights (Section 11).
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { getRole } from "@/lib/api";

interface EvidenceEnvelope {
  evidence_used: string[];
  knowledge_sources: string[];
  digital_twin_factors: string[];
  workflow_rules: string[];
  reasoning_path: string[];
  confidence: number;
  references: { source: string; [k: string]: unknown }[];
  human_review_required: boolean;
}

interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  message_type: string;
  content: string;
  intent: string;
  skill_used: string;
  confidence: number | null;
  evidence: EvidenceEnvelope;
  created_at: string;
}

interface ConversationSummary {
  id: number;
  title: string;
  persona: string;
  created_at: string;
  updated_at: string;
}

interface SuggestedAction {
  action_type: string;
  suggested_params: Record<string, unknown>;
}

interface PendingAction {
  confirm_token: string;
  action_type: string;
  summary: string;
  expires_at: string;
  created_at: string;
}

const PANELS = ["Suggested Actions", "Evidence", "Related Knowledge", "Open Tasks", "Recent Searches", "Pinned Insights"] as const;
type Panel = (typeof PANELS)[number];

const PERSONAS = ["technician", "supervisor", "executive"] as const;

function pinnedKey(conversationId: number) {
  return `catalyst_pinned_${conversationId}`;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <h3 className="mb-2 text-sm font-semibold text-slate-700">{title}</h3>
      {children}
    </div>
  );
}

export default function CatalystCopilotWorkspace() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [persona, setPersona] = useState<string>(() => {
    const role = getRole();
    if (["enterprise_admin", "hospital_admin", "facility_director", "market_director", "regional_administrator"].includes(role)) return "executive";
    if (["supervisor", "spd_manager", "admin"].includes(role)) return "supervisor";
    return "technician";
  });
  const [activePanel, setActivePanel] = useState<Panel>("Suggested Actions");
  const [suggestedAction, setSuggestedAction] = useState<SuggestedAction | null>(null);
  const [lastEvidence, setLastEvidence] = useState<EvidenceEnvelope | null>(null);
  const [lastData, setLastData] = useState<Record<string, unknown>>({});
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const [pinned, setPinned] = useState<ChatMessage[]>([]);
  const [confirmSummary, setConfirmSummary] = useState<{ token: string; summary: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const recentSearches = messages.filter((m) => m.role === "user").slice(-8).reverse();

  useEffect(() => {
    api.get<{ conversations: ConversationSummary[] }>("/api/catalyst/conversations").then((r) => setConversations(r.conversations)).catch(() => {});
    api.get<{ pending_actions: PendingAction[] }>("/api/catalyst/actions/pending").then((r) => setPendingActions(r.pending_actions)).catch(() => {});
  }, []);

  useEffect(() => {
    if (conversationId === null) {
      setMessages([]);
      setPinned([]);
      return;
    }
    api.get<{ messages: ChatMessage[] }>(`/api/catalyst/conversations/${conversationId}/messages`).then((r) => setMessages(r.messages)).catch(() => {});
    try {
      const raw = localStorage.getItem(pinnedKey(conversationId));
      setPinned(raw ? JSON.parse(raw) : []);
    } catch {
      setPinned([]);
    }
  }, [conversationId]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;
    setLoading(true);
    setInput("");
    try {
      const res = await api.post<{
        conversation_id: number; answer: string; intent: string; skill_used: string;
        data: Record<string, unknown>; evidence: EvidenceEnvelope; suggested_action: SuggestedAction | null;
      }>("/api/catalyst/chat", { message: text, conversation_id: conversationId, persona });
      setConversationId(res.conversation_id);
      setSuggestedAction(res.suggested_action);
      setLastEvidence(res.evidence);
      setLastData(res.data);
      const refreshed = await api.get<{ messages: ChatMessage[] }>(`/api/catalyst/conversations/${res.conversation_id}/messages`);
      setMessages(refreshed.messages);
      const convos = await api.get<{ conversations: ConversationSummary[] }>("/api/catalyst/conversations");
      setConversations(convos.conversations);
      if (res.suggested_action) setActivePanel("Suggested Actions");
    } finally {
      setLoading(false);
    }
  }

  async function proposeAction(actionType: string, params: Record<string, unknown>) {
    const res = await api.post<{ requires_confirmation: boolean; confirm_token?: string; summary?: string; result?: unknown }>(
      "/api/catalyst/actions/propose",
      { conversation_id: conversationId ?? 0, action_type: actionType, params },
    );
    if (res.requires_confirmation && res.confirm_token) {
      setConfirmSummary({ token: res.confirm_token, summary: res.summary ?? "" });
      const pending = await api.get<{ pending_actions: PendingAction[] }>("/api/catalyst/actions/pending");
      setPendingActions(pending.pending_actions);
    }
  }

  async function confirmPending(token: string) {
    await api.post("/api/catalyst/actions/confirm", { confirm_token: token });
    setConfirmSummary(null);
    const pending = await api.get<{ pending_actions: PendingAction[] }>("/api/catalyst/actions/pending");
    setPendingActions(pending.pending_actions);
  }

  async function cancelPending(token: string) {
    await api.post("/api/catalyst/actions/cancel", { confirm_token: token });
    setConfirmSummary(null);
    const pending = await api.get<{ pending_actions: PendingAction[] }>("/api/catalyst/actions/pending");
    setPendingActions(pending.pending_actions);
  }

  function togglePin(message: ChatMessage) {
    if (conversationId === null) return;
    const exists = pinned.some((p) => p.id === message.id);
    const next = exists ? pinned.filter((p) => p.id !== message.id) : [...pinned, message];
    setPinned(next);
    try {
      localStorage.setItem(pinnedKey(conversationId), JSON.stringify(next));
    } catch {
      /* localStorage unavailable — pin state stays session-only */
    }
  }

  return (
    <div className="flex h-[calc(100vh-6rem)] gap-3 p-4">
      {/* Conversation list */}
      <div className="w-56 shrink-0 overflow-y-auto rounded-lg border border-slate-200 bg-white p-2">
        <button
          className="mb-2 w-full rounded bg-indigo-600 px-2 py-1 text-sm text-white"
          onClick={() => setConversationId(null)}
        >
          + New conversation
        </button>
        <select className="mb-2 w-full rounded border border-slate-300 p-1 text-sm" value={persona} onChange={(e) => setPersona(e.target.value)}>
          {PERSONAS.map((p) => (
            <option key={p} value={p}>{p[0].toUpperCase() + p.slice(1)} Copilot</option>
          ))}
        </select>
        {conversations.map((c) => (
          <button
            key={c.id}
            onClick={() => setConversationId(c.id)}
            className={`mb-1 w-full truncate rounded p-1 text-left text-xs ${c.id === conversationId ? "bg-indigo-50 text-indigo-700" : "hover:bg-slate-50"}`}
          >
            {c.title}
          </button>
        ))}
      </div>

      {/* Chat */}
      <div className="flex flex-1 flex-col rounded-lg border border-slate-200 bg-white p-3">
        <div className="flex-1 overflow-y-auto space-y-2">
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${m.role === "user" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-800"}`}>
                <div>{m.content}</div>
                {m.role === "assistant" && (
                  <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                    {m.intent && <span>intent: {m.intent}</span>}
                    {m.confidence != null && <span>confidence: {(m.confidence * 100).toFixed(0)}%</span>}
                    <button className="underline" onClick={() => togglePin(m)}>
                      {pinned.some((p) => p.id === m.id) ? "unpin" : "pin"}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          <input
            className="flex-1 rounded border border-slate-300 p-2 text-sm"
            placeholder="Ask Catalyst about inspections, Digital Twins, findings, forecasts…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          />
          <button className="rounded bg-indigo-600 px-4 py-2 text-sm text-white disabled:opacity-50" disabled={loading} onClick={sendMessage}>
            Send
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          LumenAI Catalyst answers using only real LumenAI data and never executes a critical action without your explicit confirmation. Decision support only — human review required.
        </p>
      </div>

      {/* Side panels */}
      <div className="w-80 shrink-0 overflow-y-auto space-y-2">
        <div className="flex flex-wrap gap-1">
          {PANELS.map((p) => (
            <button
              key={p}
              onClick={() => setActivePanel(p)}
              className={`rounded px-2 py-1 text-xs ${activePanel === p ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}
            >
              {p}
            </button>
          ))}
        </div>

        {activePanel === "Suggested Actions" && (
          <Section title="Suggested Actions">
            {confirmSummary ? (
              <div className="space-y-2 text-sm">
                <p>{confirmSummary.summary}</p>
                <div className="flex gap-2">
                  <button className="rounded bg-emerald-600 px-2 py-1 text-xs text-white" onClick={() => confirmPending(confirmSummary.token)}>Confirm</button>
                  <button className="rounded bg-slate-200 px-2 py-1 text-xs" onClick={() => cancelPending(confirmSummary.token)}>Cancel</button>
                </div>
              </div>
            ) : suggestedAction ? (
              <button
                className="w-full rounded border border-indigo-300 bg-indigo-50 p-2 text-left text-xs text-indigo-700"
                onClick={() => proposeAction(suggestedAction.action_type, suggestedAction.suggested_params)}
              >
                {suggestedAction.action_type.replace(/_/g, " ")}
              </button>
            ) : (
              <p className="text-xs text-slate-400">No action suggested by the last message.</p>
            )}
          </Section>
        )}

        {activePanel === "Evidence" && (
          <Section title="Evidence Panel">
            {lastEvidence ? (
              <div className="space-y-1 text-xs text-slate-600">
                <div><b>Confidence:</b> {(lastEvidence.confidence * 100).toFixed(0)}%</div>
                <div><b>Evidence used:</b> {lastEvidence.evidence_used.join(", ") || "—"}</div>
                <div><b>Knowledge sources:</b> {lastEvidence.knowledge_sources.join(", ") || "—"}</div>
                <div><b>Digital Twin factors:</b> {lastEvidence.digital_twin_factors.join(", ") || "—"}</div>
                <div><b>Workflow rules:</b> {lastEvidence.workflow_rules.join(", ") || "—"}</div>
                <div><b>Reasoning path:</b> {lastEvidence.reasoning_path.join(" → ") || "—"}</div>
                <div className="text-amber-600"><b>Human review required.</b></div>
              </div>
            ) : (
              <p className="text-xs text-slate-400">Ask a question to see its evidence trace.</p>
            )}
          </Section>
        )}

        {activePanel === "Related Knowledge" && (
          <Section title="Related Knowledge">
            {(lastData.articles as unknown[] | undefined)?.length ? (
              <ul className="space-y-1 text-xs text-slate-600">
                {(lastData.articles as { title: string }[]).slice(0, 10).map((a, i) => <li key={i}>{a.title}</li>)}
              </ul>
            ) : (
              <p className="text-xs text-slate-400">No knowledge articles surfaced by the last query.</p>
            )}
          </Section>
        )}

        {activePanel === "Open Tasks" && (
          <Section title="Open Tasks">
            {pendingActions.length ? (
              <ul className="space-y-2 text-xs text-slate-600">
                {pendingActions.map((p) => (
                  <li key={p.confirm_token} className="rounded border border-slate-200 p-1">
                    <div>{p.summary}</div>
                    <div className="mt-1 flex gap-2">
                      <button className="rounded bg-emerald-600 px-1 text-white" onClick={() => confirmPending(p.confirm_token)}>Confirm</button>
                      <button className="rounded bg-slate-200 px-1" onClick={() => cancelPending(p.confirm_token)}>Cancel</button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400">No pending critical actions awaiting your confirmation.</p>
            )}
          </Section>
        )}

        {activePanel === "Recent Searches" && (
          <Section title="Recent Searches">
            {recentSearches.length ? (
              <ul className="space-y-1 text-xs text-slate-600">
                {recentSearches.map((m) => <li key={m.id}>{m.content}</li>)}
              </ul>
            ) : (
              <p className="text-xs text-slate-400">No searches yet in this conversation.</p>
            )}
          </Section>
        )}

        {activePanel === "Pinned Insights" && (
          <Section title="Pinned Insights">
            {pinned.length ? (
              <ul className="space-y-1 text-xs text-slate-600">
                {pinned.map((m) => <li key={m.id}>{m.content}</li>)}
              </ul>
            ) : (
              <p className="text-xs text-slate-400">Pin an assistant answer to keep it here.</p>
            )}
          </Section>
        )}
      </div>
    </div>
  );
}
