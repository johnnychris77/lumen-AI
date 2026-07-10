/**
 * v3.4 — Project Horizon: Federated Clinical Intelligence & Global
 * Learning Network. Governance Center (Section 9) — participation
 * agreements, contribution approval, version history, audit trail, and
 * data sharing preferences. Human oversight and organizational
 * governance remain central to all shared knowledge.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Participation {
  enrolled: boolean;
  participant: { enrollment_status: string; participant_type: string; region: string; contribution_categories: string } | null;
  sharing_agreement: { status: string; sharing_scope: string } | null;
}

interface Contribution {
  id: number;
  contribution_ref: string;
  contribution_type: string;
  title: string;
  approval_status: string;
  version: number;
}

interface AuditEntry {
  id: number;
  action_type: string;
  actor_email: string;
  created_at?: string;
}

const TABS = ["Participation", "Pending Approvals", "Audit Trail"] as const;
type Tab = (typeof TABS)[number];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">{title}</p>
      {children}
    </div>
  );
}

export default function GovernanceCenterDashboard() {
  const [tab, setTab] = useState<Tab>("Participation");
  const [busy, setBusy] = useState(false);
  const [participation, setParticipation] = useState<Participation | null>(null);
  const [pending, setPending] = useState<Contribution[]>([]);
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>([]);

  async function loadParticipation() {
    setBusy(true);
    try {
      const result = await api.get<Participation>("/api/horizon/participation/status");
      setParticipation(result);
    } finally {
      setBusy(false);
    }
  }

  async function loadPending() {
    setBusy(true);
    try {
      const result = await api.get<{ pending: Contribution[] }>("/api/horizon/governance/pending-approvals");
      setPending(result.pending);
    } finally {
      setBusy(false);
    }
  }

  async function loadAuditTrail() {
    setBusy(true);
    try {
      const result = await api.get<{ audit_trail: AuditEntry[] }>("/api/horizon/governance/overview");
      setAuditTrail(result.audit_trail);
    } finally {
      setBusy(false);
    }
  }

  async function approve(id: number) {
    setBusy(true);
    try {
      await api.post(`/api/horizon/contributions/${id}/approve`);
      await loadPending();
    } finally {
      setBusy(false);
    }
  }

  async function enroll() {
    setBusy(true);
    try {
      await api.post("/api/horizon/participation/enroll", {
        participant_type: "hospital", region: "north_america", contribution_categories: ["benchmark", "research"],
      });
      await loadParticipation();
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadParticipation();
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Governance Center</h2>
        <p className="text-sm text-slate-500">
          Participation agreements, contribution approval, knowledge review, version history, and audit trail for
          Project Horizon's federated clinical intelligence network. Every participant's opt-in is reversible.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              if (t === "Pending Approvals") loadPending();
              if (t === "Audit Trail") loadAuditTrail();
            }}
            className={`px-4 py-2 text-sm font-medium rounded-t-md ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Participation" && (
        <Section title="Federated Network Participation">
          {participation?.enrolled ? (
            <div className="text-sm text-slate-700 space-y-1">
              <p>Enrollment status: <span className="font-medium">{participation.participant?.enrollment_status}</span></p>
              <p>Sharing agreement: <span className="font-medium">{participation.sharing_agreement?.status}</span> ({participation.sharing_agreement?.sharing_scope})</p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-slate-400">Not yet enrolled in the federated network.</p>
              <button onClick={enroll} disabled={busy} className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
                Enroll Organization
              </button>
            </div>
          )}
        </Section>
      )}

      {tab === "Pending Approvals" && (
        <Section title="Pending Contribution Approvals">
          <ul className="space-y-2 text-sm">
            {pending.map((c) => (
              <li key={c.id} className="flex items-center justify-between border-b border-slate-100 pb-2">
                <span>
                  <span className="font-medium">{c.title}</span>{" "}
                  <span className="text-xs text-slate-500">({c.contribution_type.replace(/_/g, " ")}, v{c.version})</span>
                </span>
                <button onClick={() => approve(c.id)} disabled={busy} className="rounded-md bg-slate-700 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50">
                  Approve
                </button>
              </li>
            ))}
            {pending.length === 0 && <p className="text-slate-400">No contributions awaiting approval</p>}
          </ul>
        </Section>
      )}

      {tab === "Audit Trail" && (
        <Section title="Governance Audit Trail">
          <ul className="space-y-1 text-sm">
            {auditTrail.map((a) => (
              <li key={a.id} className="flex items-center justify-between border-b border-slate-100 pb-1">
                <span className="font-medium">{a.action_type}</span>
                <span className="text-xs text-slate-500">{a.actor_email}</span>
              </li>
            ))}
            {auditTrail.length === 0 && <p className="text-slate-400">No horizon governance actions recorded yet</p>}
          </ul>
        </Section>
      )}
    </div>
  );
}
