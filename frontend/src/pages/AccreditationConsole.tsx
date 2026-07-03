import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch, API_BASE } from "@/lib/api";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchJSON(path: string) {
  const res = await apiFetch(`${path}`, { raw: true, headers: authHeaders() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function postJSON(path: string, body: object) {
  const res = await apiFetch(`${path}`, { raw: true,
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

const ACCREDITORS = [
  { value: "joint_commission", label: "Joint Commission" },
  { value: "dnv", label: "DNV" },
  { value: "cms", label: "CMS" },
  { value: "hfap", label: "HFAP" },
  { value: "state", label: "State Survey" },
];

const STATUS_VARIANT: Record<string, "success" | "warning" | "destructive"> = {
  ready: "success",
  approaching: "warning",
  not_ready: "destructive",
};

interface Readiness {
  total_items: number;
  readiness_score: number;
  evidence_completeness_score: number;
  risk_score: number;
  readiness_status: string;
  open_critical_items: number;
  breakdown: { missing: number; in_progress: number; complete: number };
}

interface EvidenceItem {
  id: number;
  standard_ref: string;
  category: string;
  title: string;
  status: string;
  is_critical: boolean;
}

export default function AccreditationConsole() {
  const [tenantId, setTenantId] = useState(localStorage.getItem("tenant_id") || "default-tenant");
  const [facilityId, setFacilityId] = useState("F1");
  const [accreditor, setAccreditor] = useState("joint_commission");
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [items, setItems] = useState<EvidenceItem[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function load() {
    setErr(null);
    try {
      const qs = `tenant_id=${encodeURIComponent(tenantId)}&facility_id=${encodeURIComponent(facilityId)}&accreditor=${accreditor}`;
      const [r, ev] = await Promise.all([
        fetchJSON(`/api/accreditation/readiness?${qs}`),
        fetchJSON(`/api/accreditation/evidence-items?tenant_id=${encodeURIComponent(tenantId)}&facility_id=${encodeURIComponent(facilityId)}&accreditor=${accreditor}`),
      ]);
      setReadiness(r);
      setItems(ev.evidence_items || []);
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setMsg(null);
    setErr(null);
    try {
      await fn();
      await load();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  const seed = () => action(async () => {
    const r = await postJSON("/api/accreditation/evidence-items/seed",
      { tenant_id: tenantId, facility_id: facilityId, accreditor });
    setMsg(`Seeded ${r.created} item(s) (${r.skipped_existing} already present).`);
  });

  const snapshot = () => action(async () => {
    await postJSON("/api/accreditation/readiness/snapshot",
      { tenant_id: tenantId, facility_id: facilityId, accreditor });
    setMsg("Readiness snapshot saved.");
  });

  const createCapas = () => action(async () => {
    const r = await postJSON("/api/accreditation/readiness/create-capas",
      { tenant_id: tenantId, facility_id: facilityId, accreditor });
    setMsg(`${r.capas_created} CAPA(s) created from ${r.open_critical_gaps} open critical gap(s).`);
  });

  const generateBinder = () => action(async () => {
    const r = await postJSON("/api/accreditation/survey-evidence/generate",
      { tenant_id: tenantId, facility_id: facilityId, accreditor, package_type: "binder" });
    window.open(`${API_BASE}/api/accreditation/survey-evidence/${r.id}/export`, "_blank");
    setMsg("Survey binder generated (opened for print/PDF).");
  });

  async function setItemStatus(id: number, status: string) {
    await action(async () => {
      await postJSON(`/api/accreditation/evidence-items/${id}?status=${status}`, {});
    });
  }

  return (
    <div className="space-y-6">
      {/* Context selector */}
      <Card>
        <CardContent className="flex flex-wrap items-end gap-3 pt-6">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-500">Tenant</label>
            <Input value={tenantId} onChange={(e) => setTenantId(e.target.value)} className="w-44" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-500">Facility</label>
            <Input value={facilityId} onChange={(e) => setFacilityId(e.target.value)} className="w-28" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-500">Accreditor</label>
            <select
              className="h-9 rounded-md border border-slate-300 px-2 text-sm"
              value={accreditor}
              onChange={(e) => setAccreditor(e.target.value)}
            >
              {ACCREDITORS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
            </select>
          </div>
          <Button onClick={load} disabled={busy}>Load</Button>
          <Button variant="outline" onClick={seed} disabled={busy}>Seed checklist</Button>
        </CardContent>
      </Card>

      {err && <p className="text-sm text-red-600">{err}</p>}
      {msg && <p className="text-sm text-emerald-700">{msg}</p>}

      {/* Readiness scorecard */}
      {readiness && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Readiness</CardTitle>
            <Badge variant={STATUS_VARIANT[readiness.readiness_status] || "secondary"}>
              {readiness.readiness_status.replace("_", " ")}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Metric label="Readiness" value={readiness.readiness_score} />
              <Metric label="Evidence completeness" value={readiness.evidence_completeness_score} />
              <Metric label="Risk" value={readiness.risk_score} invert />
              <Metric label="Open critical items" value={readiness.open_critical_items} raw />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="outline" onClick={snapshot} disabled={busy}>Save snapshot</Button>
              <Button variant="outline" onClick={createCapas} disabled={busy || readiness.open_critical_items === 0}>
                Create CAPAs from gaps
              </Button>
              <Button onClick={generateBinder} disabled={busy}>Generate survey binder</Button>
            </div>
            <p className="mt-3 text-xs text-slate-400">
              Decision-support indicator requiring human review. Does not guarantee accreditation.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Evidence checklist */}
      <Card>
        <CardHeader>
          <CardTitle>Evidence Checklist ({items.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <p className="text-sm text-slate-500">No evidence items. Use “Seed checklist” to start.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs uppercase text-slate-400">
                    <th className="py-2 pr-3">Standard</th>
                    <th className="py-2 pr-3">Title</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Set</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <tr key={it.id} className="border-b last:border-0">
                      <td className="py-2 pr-3 font-medium">
                        {it.standard_ref}
                        {it.is_critical && <Badge variant="destructive" className="ml-2">critical</Badge>}
                      </td>
                      <td className="py-2 pr-3 text-slate-600">{it.title}</td>
                      <td className="py-2 pr-3">
                        <Badge variant={it.status === "complete" ? "success" : it.status === "in_progress" ? "warning" : "secondary"}>
                          {it.status.replace("_", " ")}
                        </Badge>
                      </td>
                      <td className="py-2 pr-3">
                        <select
                          className="h-7 rounded border border-slate-300 px-1 text-xs"
                          value={it.status}
                          onChange={(e) => setItemStatus(it.id, e.target.value)}
                          disabled={busy}
                        >
                          <option value="missing">missing</option>
                          <option value="in_progress">in_progress</option>
                          <option value="complete">complete</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value, invert, raw }: { label: string; value: number; invert?: boolean; raw?: boolean }) {
  const color = raw
    ? (value > 0 ? "text-red-600" : "text-emerald-600")
    : invert
      ? (value >= 50 ? "text-red-600" : value >= 25 ? "text-amber-600" : "text-emerald-600")
      : (value >= 85 ? "text-emerald-600" : value >= 65 ? "text-amber-600" : "text-red-600");
  return (
    <div className="rounded-lg border p-3">
      <div className={`text-2xl font-bold ${color}`}>{value}{raw ? "" : ""}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}
