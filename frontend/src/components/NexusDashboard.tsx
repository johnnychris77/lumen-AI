/**
 * v3.2 — Project Nexus: Connected Healthcare Intelligence Platform.
 * Integration monitoring dashboard (Section 8) — connector status, last
 * sync, health, errors, retries, latency, version, and authentication
 * status for every connector this tenant has registered. LumenAI enriches
 * external data with anatomy-aware clinical intelligence; it does not
 * become the system of record for every workflow.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface CatalogEntry {
  connector_key: string;
  display_name: string;
  category: string;
  default_auth_type: string;
  default_version: string;
}

interface ConnectorRow {
  connector_id: number;
  connector_key: string;
  display_name: string;
  category: string;
  status: string;
  version: string;
  auth_type: string;
  health_status: string;
  last_sync_at: string | null;
  last_health_check_at: string | null;
  consecutive_errors: number;
  total_errors: number;
  retry_count: number;
  latency_ms: number | null;
  authentication_status: string;
}

interface NexusEvent {
  id: number;
  event_type: string;
  published_at: string;
  actor: string;
  subscriber_delivery_count: number;
}

const TABS = ["Connector Monitoring", "Catalog", "Event Bus"] as const;
type Tab = (typeof TABS)[number];

function healthColor(status: string): string {
  switch (status) {
    case "healthy": return "bg-emerald-100 text-emerald-800";
    case "degraded": return "bg-amber-100 text-amber-800";
    case "error": return "bg-red-100 text-red-800";
    default: return "bg-slate-100 text-slate-600";
  }
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

export default function NexusDashboard() {
  const [tab, setTab] = useState<Tab>("Connector Monitoring");
  const [busy, setBusy] = useState(false);

  const [connectors, setConnectors] = useState<ConnectorRow[]>([]);
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [events, setEvents] = useState<NexusEvent[]>([]);

  async function loadDashboard() {
    setBusy(true);
    try {
      const result = await api.get<{ connectors: ConnectorRow[] }>("/api/nexus/dashboard");
      setConnectors(result.connectors);
    } finally {
      setBusy(false);
    }
  }

  async function loadCatalog() {
    setBusy(true);
    try {
      const result = await api.get<{ catalog: CatalogEntry[] }>("/api/nexus/catalog");
      setCatalog(result.catalog);
    } finally {
      setBusy(false);
    }
  }

  async function registerConnector(connectorKey: string) {
    setBusy(true);
    try {
      await api.post("/api/nexus/connectors", { connector_key: connectorKey });
      await loadDashboard();
    } finally {
      setBusy(false);
    }
  }

  async function loadEvents() {
    setBusy(true);
    try {
      const result = await api.get<{ events: NexusEvent[] }>("/api/nexus/events");
      setEvents(result.events);
    } finally {
      setBusy(false);
    }
  }

  async function runHealthCheck(connectorId: number) {
    setBusy(true);
    try {
      await api.post(`/api/nexus/connectors/${connectorId}/health-check`);
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
        <h2 className="text-xl font-bold text-slate-900">Project Nexus</h2>
        <p className="text-sm text-slate-500">
          Connected Healthcare Intelligence Platform — securely connects with hospital systems (CensiTrac, SPM,
          Epic, Cerner, Oracle ERP, SAP, CMMS, Active Directory, SSO) while preserving tenant isolation,
          auditability, and clinical governance. LumenAI enriches external data; it does not become the system
          of record for every workflow.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              if (t === "Catalog") loadCatalog();
              if (t === "Event Bus") loadEvents();
            }}
            className={`px-4 py-2 text-sm font-medium rounded-t-md ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Connector Monitoring" && (
        <Section title={`Registered Connectors (${connectors.length})`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 uppercase">
                  <th className="pb-2 pr-4">Connector</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Health</th>
                  <th className="pb-2 pr-4">Version</th>
                  <th className="pb-2 pr-4">Auth</th>
                  <th className="pb-2 pr-4">Last Sync</th>
                  <th className="pb-2 pr-4">Errors</th>
                  <th className="pb-2 pr-4">Retries</th>
                  <th className="pb-2 pr-4">Latency</th>
                  <th className="pb-2"></th>
                </tr>
              </thead>
              <tbody>
                {connectors.map((c) => (
                  <tr key={c.connector_id} className="border-t border-slate-100">
                    <td className="py-1.5 pr-4 font-medium">{c.display_name}</td>
                    <td className="py-1.5 pr-4 capitalize">{c.status}</td>
                    <td className="py-1.5 pr-4">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${healthColor(c.health_status)}`}>{c.health_status}</span>
                    </td>
                    <td className="py-1.5 pr-4">{c.version}</td>
                    <td className="py-1.5 pr-4">{c.authentication_status}</td>
                    <td className="py-1.5 pr-4">{c.last_sync_at ? new Date(c.last_sync_at).toLocaleString() : "never"}</td>
                    <td className="py-1.5 pr-4">{c.total_errors}</td>
                    <td className="py-1.5 pr-4">{c.retry_count}</td>
                    <td className="py-1.5 pr-4">{c.latency_ms ?? "—"}ms</td>
                    <td className="py-1.5">
                      <button onClick={() => runHealthCheck(c.connector_id)} disabled={busy} className="rounded-md bg-slate-700 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50">
                        Check
                      </button>
                    </td>
                  </tr>
                ))}
                {connectors.length === 0 && (
                  <tr><td colSpan={10} className="py-2 text-slate-400">No connectors registered yet — see the Catalog tab.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {tab === "Catalog" && (
        <Section title="Connector Catalog">
          <ul className="space-y-1 text-sm">
            {catalog.map((c) => (
              <li key={c.connector_key} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span>
                  <span className="font-medium">{c.display_name}</span>{" "}
                  <span className="text-xs text-slate-500">({c.category.replace(/_/g, " ")}, {c.default_auth_type})</span>
                </span>
                <button onClick={() => registerConnector(c.connector_key)} disabled={busy} className="rounded-md bg-slate-900 px-3 py-1 text-xs font-semibold text-white disabled:opacity-50">
                  Register
                </button>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {tab === "Event Bus" && (
        <Section title="Recent Events">
          <ul className="space-y-1 text-sm">
            {events.map((e) => (
              <li key={e.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{e.event_type}</span>
                <span className="text-xs text-slate-500">{e.actor} · {new Date(e.published_at).toLocaleString()} · {e.subscriber_delivery_count} delivered</span>
              </li>
            ))}
            {events.length === 0 && <p className="text-slate-400">No events published yet</p>}
          </ul>
        </Section>
      )}

      <p className="text-xs text-slate-400 italic">
        Project Nexus synchronizes and links data already present in connected systems — it never fabricates
        instrument, work-queue, or identity records that a connector hasn't actually supplied. No external
        integration bypasses RBAC, audit logging, or supervisor validation.
      </p>
    </div>
  );
}
