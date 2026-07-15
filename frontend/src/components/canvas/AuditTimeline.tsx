import { useEffect, useState } from "react";
import { History } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";

interface AuditLogRow {
  id: number;
  action_type: string;
  resource_type: string;
  resource_id: string;
  actor_email: string;
  actor_role: string;
  created_at: string | null;
}

// Project Canvas — Section 22: Audit Timeline. Reuses the tenant-wide
// `/api/audit-logs` surface (already tenant_admin/site_admin-gated) rather
// than a second audit store; filters client-side to this resource. If the
// caller's role can't reach that endpoint, the panel renders nothing rather
// than a broken-looking error, since audit access is intentionally
// restricted to elevated roles.
export function AuditTimeline({ resourceType, resourceId }: { resourceType: string; resourceId: string }) {
  const [rows, setRows] = useState<AuditLogRow[] | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    apiFetch<{ items: AuditLogRow[] }>("/api/audit-logs?limit=200")
      .then((r) => setRows(r.items.filter((i) => i.resource_type === resourceType && i.resource_id === resourceId)))
      .catch(() => setUnavailable(true));
  }, [resourceType, resourceId]);

  if (unavailable) return null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center gap-2">
        <History className="h-4 w-4 text-slate-400" />
        <CardTitle className="text-base">Audit Timeline</CardTitle>
      </CardHeader>
      <CardContent>
        {!rows && <p className="text-sm text-slate-400">Loading…</p>}
        {rows && rows.length === 0 && <p className="text-sm text-slate-400">No audit events recorded for this resource yet.</p>}
        {rows && rows.length > 0 && (
          <ol className="space-y-2">
            {rows.map((r) => (
              <li key={r.id} className="text-sm border-l-2 border-slate-200 pl-3">
                <p className="font-medium text-slate-800">{r.action_type.replace(/_/g, " ")}</p>
                <p className="text-slate-500 text-xs">
                  {r.actor_email} ({r.actor_role}) · {r.created_at ? new Date(r.created_at).toLocaleString() : "—"}
                </p>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
