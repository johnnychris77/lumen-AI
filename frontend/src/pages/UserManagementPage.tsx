import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { UserCheck, ChevronRight } from "lucide-react";
import { useAuth, API_BASE } from "@/lib/auth";

type RoleRow = { username: string; role: string; assigned_by: string; updated_at: string | null };

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  spd_manager: "Manager",
  supervisor: "Supervisor",
  viewer: "Viewer",
  vendor_user: "Vendor",
};

export default function UserManagementPage() {
  const { headers, role } = useAuth();
  const [users, setUsers] = useState<RoleRow[]>([]);
  const [assignable, setAssignable] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newUser, setNewUser] = useState("");
  const [newRole, setNewRole] = useState("spd_manager");
  const [saving, setSaving] = useState(false);
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const isAdmin = role === "admin";

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/admin/users`, { headers: headers() });
      if (res.status === 403) { setError("Admin access required to manage users."); setUsers([]); return; }
      if (!res.ok) { setError(`Failed to load users (${res.status}).`); return; }
      const data = await res.json();
      setUsers(data.users ?? []);
      setAssignable(data.assignable_roles ?? []);
    } catch {
      setError("Unable to reach the server.");
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => { if (isAdmin) load(); else setLoading(false); }, [load, isAdmin]);

  async function assign(e: React.FormEvent) {
    e.preventDefault();
    setBanner(null);
    if (!newUser.trim()) { setBanner({ type: "error", message: "Enter the user's email/username." }); return; }
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/users/role`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ username: newUser.trim(), role: newRole }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        setBanner({ type: "error", message: d?.detail || `Failed (${res.status}).` });
        return;
      }
      setBanner({ type: "success", message: `${newUser.trim()} is now ${ROLE_LABELS[newRole] ?? newRole}.` });
      setNewUser("");
      load();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/" className="hover:text-slate-600">Dashboard</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-600 font-medium">User Roles</span>
      </nav>

      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100">
          <UserCheck className="h-5 w-5 text-indigo-600" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-slate-900">User Roles</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Assign Admin, Manager, Supervisor, or Viewer access. Managers and supervisors can review
            baselines and inspections; admins can manage users.
          </p>
        </div>
      </div>

      {!isAdmin && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
          Admin access is required to manage user roles. Your current role is {role}.
        </div>
      )}

      {isAdmin && (
        <>
          {/* Assign role */}
          <form onSubmit={assign} className="rounded-xl border border-slate-200 bg-white p-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-900">Assign a role</h3>
            {banner && (
              <div className={`rounded-lg px-3 py-2 text-sm ${banner.type === "success" ? "bg-emerald-50 border border-emerald-200 text-emerald-800" : "bg-red-50 border border-red-200 text-red-700"}`}>
                {banner.message}
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-slate-700 mb-1">User email / username</label>
                <input
                  value={newUser}
                  onChange={(e) => setNewUser(e.target.value)}
                  placeholder="person@hospital.org"
                  className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  {(assignable.length ? assignable : ["admin", "spd_manager", "supervisor", "viewer"]).map((r) => (
                    <option key={r} value={r}>{ROLE_LABELS[r] ?? r}</option>
                  ))}
                </select>
              </div>
            </div>
            <button type="submit" disabled={saving}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? "Saving…" : "Assign role"}
            </button>
          </form>

          {/* Current assignments */}
          <div className="rounded-xl border border-slate-200 bg-white">
            <div className="border-b border-slate-100 px-5 py-3">
              <h3 className="text-sm font-semibold text-slate-900">Current role assignments</h3>
            </div>
            {loading && <div className="px-5 py-8 text-center text-sm text-slate-400">Loading…</div>}
            {error && <div className="px-5 py-6 text-center text-sm text-red-600">{error}</div>}
            {!loading && !error && users.length === 0 && (
              <div className="px-5 py-8 text-center text-sm text-slate-400">No roles assigned yet.</div>
            )}
            {!loading && !error && users.length > 0 && (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
                    <th className="px-5 py-2 font-medium">User</th>
                    <th className="px-5 py-2 font-medium">Role</th>
                    <th className="px-5 py-2 font-medium">Assigned by</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.username} className="border-b border-slate-50">
                      <td className="px-5 py-2.5 text-slate-800">{u.username}</td>
                      <td className="px-5 py-2.5">
                        <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                          {ROLE_LABELS[u.role] ?? u.role}
                        </span>
                      </td>
                      <td className="px-5 py-2.5 text-slate-500">{u.assigned_by || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
