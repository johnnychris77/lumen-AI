/**
 * v4.0 — LumenAI OS: Project Genesis. Platform Launcher (Sections 4, 5, 6) —
 * unified navigation across every licensed and permitted module, global
 * search, and the universal activity feed. Every module tile links back
 * to its existing frontend route; nothing here duplicates those pages.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface PlatformModule {
  module_key: string;
  name: string;
  description: string;
  category: string;
  nav_icon: string;
  routes: string[];
}

interface LauncherView {
  modules: PlatformModule[];
  favorites: PlatformModule[];
  recent: PlatformModule[];
  notifications: { source: string; message: string; read: boolean; created_at: string }[];
  tasks: unknown[];
  notification_count: number;
  unread_task_count: number;
}

interface SearchResult {
  id: number | string;
  title: string;
  subtitle: string;
  module: string;
}

interface SearchResponse {
  query: string;
  results: Record<string, SearchResult[]>;
  total: number;
}

interface ActivityItem {
  id: number;
  action_type: string;
  actor: string;
  module: string;
  created_at: string;
}

const TABS = ["Launcher", "Global Search", "Activity Feed"] as const;
type Tab = (typeof TABS)[number];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

function ModuleTile({ m, onOpen }: { m: PlatformModule; onOpen: (m: PlatformModule) => void }) {
  return (
    <button
      onClick={() => onOpen(m)}
      className="text-left rounded-lg border border-slate-200 bg-white p-3 hover:border-slate-400 transition-colors"
    >
      <p className="font-semibold text-slate-900">{m.name}</p>
      <p className="text-xs text-slate-500 mt-1 line-clamp-2">{m.description}</p>
    </button>
  );
}

export default function PlatformLauncherDashboard() {
  const [tab, setTab] = useState<Tab>("Launcher");
  const [busy, setBusy] = useState(false);
  const [launcher, setLauncher] = useState<LauncherView | null>(null);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);

  async function loadLauncher() {
    setBusy(true);
    try {
      setLauncher(await api.get<LauncherView>("/api/platform/navigation/launcher"));
    } finally {
      setBusy(false);
    }
  }

  async function runSearch() {
    if (query.trim().length < 2) return;
    setBusy(true);
    try {
      setSearchResults(await api.get<SearchResponse>(`/api/platform/search?q=${encodeURIComponent(query)}`));
    } finally {
      setBusy(false);
    }
  }

  async function loadActivity() {
    setBusy(true);
    try {
      const result = await api.get<{ activity: ActivityItem[] }>("/api/platform/activity-feed");
      setActivity(result.activity);
    } finally {
      setBusy(false);
    }
  }

  async function openModule(m: PlatformModule) {
    await api.post("/api/platform/navigation/recent", { module_key: m.module_key });
    if (m.routes[0]) window.location.href = m.routes[0];
  }

  useEffect(() => {
    loadLauncher();
  }, []);

  function selectTab(t: Tab) {
    setTab(t);
    if (t === "Activity Feed") loadActivity();
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">LumenAI OS — Platform Launcher</h2>
        <p className="text-sm text-slate-500">
          Project Genesis — a modular operating system for sterile processing. You only see applications licensed
          and permitted for your role.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => selectTab(t)}
            className={`px-4 py-2 text-sm font-medium rounded-t-md ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {busy && <p className="text-sm text-slate-400">Loading…</p>}

      {tab === "Launcher" && launcher && (
        <div className="space-y-4">
          {launcher.favorites.length > 0 && (
            <Section title="Favorites">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {launcher.favorites.map((m) => <ModuleTile key={m.module_key} m={m} onOpen={openModule} />)}
              </div>
            </Section>
          )}
          {launcher.recent.length > 0 && (
            <Section title="Recent Applications">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {launcher.recent.map((m) => <ModuleTile key={m.module_key} m={m} onOpen={openModule} />)}
              </div>
            </Section>
          )}
          <Section title={`All Applications (${launcher.modules.length})`}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {launcher.modules.map((m) => <ModuleTile key={m.module_key} m={m} onOpen={openModule} />)}
            </div>
          </Section>
          <Section title={`Notifications (${launcher.notification_count}) · Tasks (${launcher.unread_task_count})`}>
            <ul className="space-y-1 text-sm">
              {launcher.notifications.map((n, i) => (
                <li key={i} className="flex items-center justify-between border-b border-slate-100 pb-1">
                  <span>{n.message}</span>
                  <span className="text-xs text-slate-500">{n.source}{n.read ? "" : " · unread"}</span>
                </li>
              ))}
              {launcher.notifications.length === 0 && <p className="text-slate-400">No notifications</p>}
            </ul>
          </Section>
        </div>
      )}

      {tab === "Global Search" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runSearch()}
              placeholder="Search Digital Twins, Inspections, Knowledge, Baselines, Users, Facilities…"
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <button onClick={runSearch} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white">
              Search
            </button>
          </div>
          {searchResults && (
            <Section title={`Results for "${searchResults.query}" (${searchResults.total})`}>
              <div className="space-y-3">
                {Object.entries(searchResults.results).map(([category, items]) => (
                  <div key={category}>
                    <p className="font-medium capitalize text-sm">{category.replace(/_/g, " ")}</p>
                    <ul className="ml-4 text-xs text-slate-500 list-disc">
                      {items.map((it) => <li key={`${category}-${it.id}`}>{it.title} — {it.subtitle} ({it.module})</li>)}
                    </ul>
                  </div>
                ))}
                {searchResults.total === 0 && <p className="text-slate-400 text-sm">No results</p>}
              </div>
            </Section>
          )}
        </div>
      )}

      {tab === "Activity Feed" && (
        <Section title="Universal Activity Feed">
          <ul className="space-y-1 text-sm">
            {activity.map((a) => (
              <li key={`${a.id}-${a.action_type}`} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{a.action_type}</span>
                <span className="text-xs text-slate-500">{a.actor} · {a.module}</span>
              </li>
            ))}
            {activity.length === 0 && <p className="text-slate-400">No activity yet</p>}
          </ul>
        </Section>
      )}
    </div>
  );
}
