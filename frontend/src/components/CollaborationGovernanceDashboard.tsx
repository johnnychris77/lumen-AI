/**
 * v3.5 — Project Beacon, Section 9: Collaboration Governance —
 * participation agreements, knowledge approval, evidence review,
 * contribution history, access control, version management, and audit
 * trails for the Industry Collaboration Hub. Mirrors Project Horizon's
 * `GovernanceCenterDashboard.tsx` pattern.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Participation {
  organization_type: string;
  membership_tier: string;
  membership_status: string;
}

interface PendingContribution {
  id: number;
  title: string;
  contribution_type: string;
  category: string;
}

interface AuditEntry {
  id: number;
  action_type: string;
  actor_email: string;
}

interface GovernanceOverview {
  participation: Participation | null;
  own_contribution_history: PendingContribution[];
  own_pending_approvals: PendingContribution[];
  audit_trail: AuditEntry[];
  disclaimer: string;
}

const TABS = ["Overview", "Pending Approvals", "Audit Trail"] as const;
type Tab = (typeof TABS)[number];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

export default function CollaborationGovernanceDashboard() {
  const [tab, setTab] = useState<Tab>("Overview");
  const [busy, setBusy] = useState(false);
  const [overview, setOverview] = useState<GovernanceOverview | null>(null);
  const [pending, setPending] = useState<PendingContribution[]>([]);

  async function loadOverview() {
    setBusy(true);
    try {
      setOverview(await api.get<GovernanceOverview>("/api/beacon/governance/overview"));
    } finally {
      setBusy(false);
    }
  }

  async function loadPending() {
    setBusy(true);
    try {
      const result = await api.get<{ pending: PendingContribution[] }>("/api/beacon/governance/pending-approvals");
      setPending(result.pending);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadOverview();
  }, []);

  function selectTab(t: Tab) {
    setTab(t);
    if (t === "Pending Approvals") loadPending();
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Collaboration Governance</h2>
        <p className="text-sm text-slate-500">
          Participation agreements, knowledge approval, evidence review, contribution history, access control,
          version management, and audit trails for the Industry Collaboration Hub.
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

      {tab === "Overview" && overview && (
        <div className="space-y-4">
          <Section title="Participation Status">
            {overview.participation ? (
              <div className="text-sm text-slate-700 space-y-1">
                <p>Organization type: <span className="font-medium">{overview.participation.organization_type}</span></p>
                <p>Membership tier: <span className="font-medium">{overview.participation.membership_tier}</span></p>
                <p>Status: <span className="font-medium">{overview.participation.membership_status}</span></p>
              </div>
            ) : (
              <p className="text-sm text-slate-400">
                Not yet enrolled as a consortium participant. Enroll via the Standards Center consortium enrollment endpoint.
              </p>
            )}
          </Section>
          <Section title="Contribution History">
            <ul className="space-y-1 text-sm">
              {overview.own_contribution_history.map((c) => (
                <li key={c.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                  <span className="font-medium">{c.title}</span>
                  <span className="text-xs text-slate-500">{c.contribution_type.replace(/_/g, " ")}</span>
                </li>
              ))}
              {overview.own_contribution_history.length === 0 && <p className="text-slate-400">No contributions submitted yet</p>}
            </ul>
          </Section>
          <p className="text-xs text-slate-400 italic">{overview.disclaimer}</p>
        </div>
      )}

      {tab === "Pending Approvals" && (
        <Section title="Governance-Wide Pending Knowledge Approvals">
          <ul className="space-y-1 text-sm">
            {pending.map((c) => (
              <li key={c.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{c.title}</span>
                <span className="text-xs text-slate-500">{c.contribution_type.replace(/_/g, " ")} · {c.category}</span>
              </li>
            ))}
            {pending.length === 0 && <p className="text-slate-400">No contributions awaiting approval</p>}
          </ul>
        </Section>
      )}

      {tab === "Audit Trail" && overview && (
        <Section title="Governance Audit Trail">
          <ul className="space-y-1 text-sm">
            {overview.audit_trail.map((a) => (
              <li key={a.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{a.action_type}</span>
                <span className="text-xs text-slate-500">{a.actor_email}</span>
              </li>
            ))}
            {overview.audit_trail.length === 0 && <p className="text-slate-400">No beacon governance actions recorded yet</p>}
          </ul>
        </Section>
      )}
    </div>
  );
}
