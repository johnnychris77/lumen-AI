import { UserCheck } from "lucide-react";

export default function RolesPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[420px] text-center px-4">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 mb-5">
        <UserCheck className="h-7 w-7 text-slate-500" />
      </div>
      <h2 className="text-lg font-semibold text-slate-900 mb-2">Roles & Permissions</h2>
      <p className="text-sm text-slate-500 max-w-md">
        Configure role-based access control for your team. Roles include{" "}
        <span className="font-medium">admin</span>,{" "}
        <span className="font-medium">spd_manager</span>,{" "}
        <span className="font-medium">vendor_user</span>,{" "}
        <span className="font-medium">executive</span>, and{" "}
        <span className="font-medium">viewer</span>. Role assignment is managed via the
        backend API and will surface here in a future release.
      </p>
    </div>
  );
}
