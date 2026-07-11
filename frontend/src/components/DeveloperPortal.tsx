/**
 * v5.0 — LumenAI OS: Project Infinity — Developer Portal.
 *
 * Frontend route `/developers`, API prefix `/api/infinity`. Third-party
 * developer accounts are admin-provisioned ("trusted third parties"),
 * not open self-service — this portal's account/key management tabs are
 * for internal platform admins curating the developer ecosystem.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const TABS = ["API Explorer", "Rate Limits", "Tutorials", "Developer Accounts", "Plugins", "Sandbox"] as const;
type Tab = (typeof TABS)[number];

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

export default function DeveloperPortal() {
  const [activeTab, setActiveTab] = useState<Tab>("API Explorer");

  const [apiExplorer, setApiExplorer] = useState<Record<string, unknown>[] | null>(null);
  const [rateLimits, setRateLimits] = useState<Record<string, unknown> | null>(null);
  const [tutorials, setTutorials] = useState<Record<string, unknown>[] | null>(null);
  const [accounts, setAccounts] = useState<Record<string, unknown>[] | null>(null);
  const [accountForm, setAccountForm] = useState({ email: "", organization_name: "", developer_type: "hospital" });
  const [plugins, setPlugins] = useState<Record<string, unknown>[] | null>(null);

  useEffect(() => {
    if (activeTab === "API Explorer") api.get("/api/infinity/developer-portal/api-explorer").then((r: Record<string, unknown>) => setApiExplorer(r.endpoints as Record<string, unknown>[])).catch(() => {});
    if (activeTab === "Rate Limits") api.get("/api/infinity/developer-portal/rate-limits").then(setRateLimits).catch(() => {});
    if (activeTab === "Tutorials") api.get("/api/infinity/developer-portal/tutorials").then((r: Record<string, unknown>) => setTutorials(r.tutorials as Record<string, unknown>[])).catch(() => {});
    if (activeTab === "Developer Accounts") api.get("/api/infinity/developer-accounts").then((r: Record<string, unknown>) => setAccounts(r.accounts as Record<string, unknown>[])).catch(() => {});
    if (activeTab === "Plugins") api.get("/api/infinity/plugins").then((r: Record<string, unknown>) => setPlugins(r.plugins as Record<string, unknown>[])).catch(() => {});
  }, [activeTab]);

  async function createAccount() {
    if (!accountForm.email.trim()) return;
    await api.post("/api/infinity/developer-accounts", accountForm);
    setAccountForm({ email: "", organization_name: "", developer_type: "hospital" });
    api.get("/api/infinity/developer-accounts").then((r: Record<string, unknown>) => setAccounts(r.accounts as Record<string, unknown>[])).catch(() => {});
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Developer Portal</h1>
      <p className="text-xs text-slate-400">
        Documentation, SDKs, the API Explorer, sample apps, tutorials, authentication, rate limits, and a
        sandbox environment for trusted third-party developers and partner organizations.
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

      {activeTab === "API Explorer" && (
        <Section title="Public Platform API — /api/v1/*">
          {apiExplorer?.map((e) => (
            <div key={String(e.path)} className="mb-1 text-sm">
              <code className="text-indigo-600">{String(e.path)}</code> — {String(e.system)}
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Rate Limits" && (
        <Section title="Rate Limit Policy">{rateLimits && <Json data={rateLimits} />}</Section>
      )}

      {activeTab === "Tutorials" && (
        <Section title="Tutorials">
          {tutorials?.map((t) => (
            <div key={String(t.title)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              <span className="font-medium">{String(t.title)}</span> — {String(t.topic)}
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Developer Accounts" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Section title="Registered Developer Accounts">
            {accounts?.map((a) => (
              <div key={String(a.id)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
                <span className="font-medium">{String(a.organization_name)}</span> — {String(a.developer_type)} ({String(a.status)})
              </div>
            ))}
          </Section>
          <Section title="Provision a Developer Account">
            <div className="space-y-2 text-sm">
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Email" value={accountForm.email}
                onChange={(e) => setAccountForm({ ...accountForm, email: e.target.value })} />
              <input className="w-full rounded border border-slate-300 p-2" placeholder="Organization name" value={accountForm.organization_name}
                onChange={(e) => setAccountForm({ ...accountForm, organization_name: e.target.value })} />
              <select className="w-full rounded border border-slate-300 p-2" value={accountForm.developer_type}
                onChange={(e) => setAccountForm({ ...accountForm, developer_type: e.target.value })}>
                <option value="hospital">Hospital</option><option value="manufacturer">Manufacturer</option>
                <option value="repair_vendor">Repair Vendor</option><option value="academic">Academic</option>
                <option value="research">Research</option><option value="enterprise">Enterprise</option>
                <option value="consulting">Consulting</option>
              </select>
              <button className="rounded bg-indigo-600 px-4 py-2 text-white" onClick={createAccount}>Create Account</button>
            </div>
          </Section>
        </div>
      )}

      {activeTab === "Plugins" && (
        <Section title="Registered Plugins">
          {plugins?.map((p) => (
            <div key={String(p.plugin_key)} className="mb-2 border-b border-slate-100 pb-2 text-sm">
              <span className="font-medium">{String(p.name)}</span> — v{String(p.version)} ({String(p.status)})
            </div>
          ))}
        </Section>
      )}

      {activeTab === "Sandbox" && (
        <Section title="Developer Sandbox">
          <p className="text-xs text-slate-400">
            Isolated development, testing, validation, and certification sessions scoped to a synthetic
            sandbox tenant — no production impact. Manage sessions from the Developer Accounts tab's
            provisioning flow.
          </p>
        </Section>
      )}
    </div>
  );
}
