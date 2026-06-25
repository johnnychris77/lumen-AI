import { Settings } from "lucide-react";

export default function SettingsPage() {
  const role = localStorage.getItem("role") || "viewer";
  const actor = localStorage.getItem("actor") || "Unknown";

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Settings</h2>
        <p className="text-sm text-slate-500 mt-1">Application and account preferences.</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white divide-y divide-slate-100">
        <div className="flex items-center gap-4 px-5 py-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white shrink-0">
            {actor[0]?.toUpperCase() ?? "U"}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-900 truncate">{actor}</p>
            <p className="text-xs text-slate-500 capitalize">{role.replace(/_/g, " ")}</p>
          </div>
        </div>

        <div className="px-5 py-4 flex items-start gap-4">
          <Settings className="h-4 w-4 text-slate-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-slate-800">System Configuration</p>
            <p className="text-xs text-slate-500 mt-0.5">
              Advanced settings are managed by your LumenAI administrator. Contact
              support if you need to change organization-level configuration.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
