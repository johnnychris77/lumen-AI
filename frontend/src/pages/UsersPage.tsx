import { Users } from "lucide-react";

export default function UsersPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[420px] text-center px-4">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 mb-5">
        <Users className="h-7 w-7 text-slate-500" />
      </div>
      <h2 className="text-lg font-semibold text-slate-900 mb-2">User Management</h2>
      <p className="text-sm text-slate-500 max-w-md">
        Invite users, manage accounts, and assign roles across your organization. User
        management is configured via the backend administration interface and will be
        available here in a future release.
      </p>
    </div>
  );
}
