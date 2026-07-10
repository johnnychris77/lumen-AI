/**
 * v4.0 — LumenAI OS: Project Genesis, Section 9 — Platform Administration.
 * Composes Organizations, Licenses, Modules, Users, Roles, Feature Flags,
 * API Keys, Integrations, and Audit Logs into one admin console. Every
 * section reads from the system that already owns that data — this page
 * adds no second source of truth.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface AdminDashboard {
  organizations: { counts: Record<string, number> };
  modules: { module_key: string; name: string; release_channel: string }[];
  licenses: Record<string, { status: string; implicit?: boolean }>;
  roles: string[];
  feature_flags: { id: number; flag_key: string; is_enabled: boolean }[];
  api_keys: { id: number; consumer_type: string; status: string; scopes: string }[];
  integrations: { id: number; connector_key: string; status: string }[];
  plugins: { plugin_key: string; name: string; status: string; version: string }[];
  recent_audit_logs: { id: number; action_type: string; actor_email: string }[];
}

const TABS = [
  "Overview", "Modules & Licenses", "Roles", "Feature Flags", "API Keys", "Integrations", "Plugins", "Audit Logs",
] as const;
type Tab = (typeof TABS)[number];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

export default function PlatformAdminDashboard() {
  const [tab, setTab] = useState<Tab>("Overview");
  const [busy, setBusy] = useState(false);
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);

  async function loadDashboard() {
    setBusy(true);
    try {
      setDashboard(await api.get<AdminDashboard>("/api/platform/admin/dashboard"));
    } finally {
      setBusy(false);
    }
  }

  async function setLicense(moduleKey: string, status: string) {
    setBusy(true);
    try {
      await api.post("/api/platform/licenses", { module_key: moduleKey, status });
      await loadDashboard();
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Platform Administration</h2>
        <p className="text-sm text-slate-500">
          Organizations, licenses, modules, users, roles, feature flags, API keys, integrations, and audit logs — one
          governed admin console composing every existing platform system.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium rounded-t-md ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {busy && <p className="text-sm text-slate-400">Loading…</p>}

      {tab === "Overview" && dashboard && (
        <Section title="Organization Counts">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
            {Object.entries(dashboard.organizations.counts).map(([k, v]) => (
              <div key={k} className="rounded-md border border-slate-100 p-2 text-center">
                <p className="text-lg font-bold">{v}</p>
                <p className="text-xs text-slate-500 capitalize">{k.replace(/_/g, " ")}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {tab === "Modules & Licenses" && dashboard && (
        <Section title="Modules">
          <ul className="space-y-2 text-sm">
            {dashboard.modules.map((m) => {
              const license = dashboard.licenses[m.module_key];
              return (
                <li key={m.module_key} className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="font-medium">{m.name} <span className="text-xs text-slate-400">({m.release_channel})</span></span>
                  <span className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">{license?.status ?? "enabled"}{license?.implicit ? " (default)" : ""}</span>
                    <button onClick={() => setLicense(m.module_key, "disabled")} disabled={busy} className="rounded-md bg-slate-200 px-2 py-1 text-xs font-semibold disabled:opacity-50">
                      Disable
                    </button>
                    <button onClick={() => setLicense(m.module_key, "enabled")} disabled={busy} className="rounded-md bg-slate-900 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50">
                      Enable
                    </button>
                  </span>
                </li>
              );
            })}
          </ul>
        </Section>
      )}

      {tab === "Roles" && dashboard && (
        <Section title="Canonical Role Catalog">
          <div className="flex flex-wrap gap-2">
            {dashboard.roles.map((r) => (
              <span key={r} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium">{r}</span>
            ))}
          </div>
        </Section>
      )}

      {tab === "Feature Flags" && dashboard && (
        <Section title="Feature Flags">
          <ul className="space-y-1 text-sm">
            {dashboard.feature_flags.map((f) => (
              <li key={f.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{f.flag_key}</span>
                <span className="text-xs text-slate-500">{f.is_enabled ? "enabled" : "disabled"}</span>
              </li>
            ))}
            {dashboard.feature_flags.length === 0 && <p className="text-slate-400">No feature flags set</p>}
          </ul>
        </Section>
      )}

      {tab === "API Keys" && dashboard && (
        <Section title="API Keys (hashes never shown)">
          <ul className="space-y-1 text-sm">
            {dashboard.api_keys.map((k) => (
              <li key={k.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{k.consumer_type}</span>
                <span className="text-xs text-slate-500">{k.status}</span>
              </li>
            ))}
            {dashboard.api_keys.length === 0 && <p className="text-slate-400">No API keys issued</p>}
          </ul>
        </Section>
      )}

      {tab === "Integrations" && dashboard && (
        <Section title="Connected Integrations">
          <ul className="space-y-1 text-sm">
            {dashboard.integrations.map((i) => (
              <li key={i.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{i.connector_key}</span>
                <span className="text-xs text-slate-500">{i.status}</span>
              </li>
            ))}
            {dashboard.integrations.length === 0 && <p className="text-slate-400">No integrations connected</p>}
          </ul>
        </Section>
      )}

      {tab === "Plugins" && dashboard && (
        <Section title="Registered Plugins">
          <ul className="space-y-1 text-sm">
            {dashboard.plugins.map((p) => (
              <li key={p.plugin_key} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{p.name} <span className="text-xs text-slate-400">v{p.version}</span></span>
                <span className="text-xs text-slate-500">{p.status}</span>
              </li>
            ))}
            {dashboard.plugins.length === 0 && <p className="text-slate-400">No plugins registered</p>}
          </ul>
        </Section>
      )}

      {tab === "Audit Logs" && dashboard && (
        <Section title="Recent Audit Log Entries">
          <ul className="space-y-1 text-sm">
            {dashboard.recent_audit_logs.map((a) => (
              <li key={a.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{a.action_type}</span>
                <span className="text-xs text-slate-500">{a.actor_email}</span>
              </li>
            ))}
            {dashboard.recent_audit_logs.length === 0 && <p className="text-slate-400">No audit log entries yet</p>}
          </ul>
        </Section>
      )}
    </div>
  );
}
