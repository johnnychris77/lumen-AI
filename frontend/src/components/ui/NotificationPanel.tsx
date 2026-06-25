import { useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import { Bell, X, CheckCheck, AlertTriangle, Info, XCircle } from "lucide-react";
import { useNotifications, AppAlert, AlertSeverity } from "@/lib/notifications";
import { cn } from "@/lib/utils";

function severityIcon(s: AlertSeverity) {
  if (s === "critical") return <XCircle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />;
  if (s === "warning") return <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />;
  return <Info className="h-4 w-4 text-blue-500 flex-shrink-0 mt-0.5" />;
}

function timeAgo(ts: number) {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function AlertRow({ alert }: { alert: AppAlert }) {
  const { markRead, dismiss } = useNotifications();
  return (
    <div
      className={cn(
        "flex gap-3 px-4 py-3 border-b border-slate-100 last:border-0",
        !alert.read && "bg-indigo-50/50"
      )}
      onClick={() => markRead(alert.id)}
    >
      {severityIcon(alert.severity)}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className={cn("text-sm font-medium text-slate-800", alert.read && "font-normal text-slate-600")}>
            {alert.title}
          </p>
          <button
            onClick={e => { e.stopPropagation(); dismiss(alert.id); }}
            className="text-slate-300 hover:text-slate-500 flex-shrink-0"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
        <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{alert.detail}</p>
        <div className="flex items-center justify-between mt-1.5">
          <span className="text-xs text-slate-400">{timeAgo(alert.ts)}</span>
          {alert.route && (
            <Link
              to={alert.route}
              className="text-xs text-indigo-600 hover:underline"
              onClick={() => markRead(alert.id)}
            >
              {alert.routeLabel ?? "View →"}
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

interface NotificationPanelProps {
  open: boolean;
  onClose: () => void;
}

export function NotificationPanel({ open, onClose }: NotificationPanelProps) {
  const { alerts, unreadCount, markAllRead } = useNotifications();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      ref={ref}
      className="absolute right-0 top-full mt-2 w-96 max-h-[480px] bg-white rounded-xl shadow-xl border border-slate-200 z-50 flex flex-col overflow-hidden"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4 text-slate-600" />
          <span className="font-semibold text-slate-800 text-sm">Alerts</span>
          {unreadCount > 0 && (
            <span className="text-xs font-bold bg-red-500 text-white rounded-full px-1.5 py-0.5 leading-none">
              {unreadCount}
            </span>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={markAllRead}
            className="text-xs text-indigo-600 hover:underline flex items-center gap-1"
          >
            <CheckCheck className="h-3.5 w-3.5" />
            Mark all read
          </button>
        )}
      </div>

      <div className="overflow-y-auto flex-1">
        {alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-400 gap-2">
            <Bell className="h-8 w-8 opacity-30" />
            <span className="text-sm">No alerts</span>
          </div>
        ) : (
          alerts
            .slice()
            .sort((a, b) => {
              const severityOrder = { critical: 0, warning: 1, info: 2 };
              if (a.read !== b.read) return a.read ? 1 : -1;
              return severityOrder[a.severity] - severityOrder[b.severity];
            })
            .map(alert => <AlertRow key={alert.id} alert={alert} />)
        )}
      </div>

      <div className="px-4 py-2.5 border-t border-slate-100 bg-slate-50">
        <p className="text-xs text-slate-400 text-center">
          Alerts refresh every 5 minutes · Dismissed alerts won't reappear
        </p>
      </div>
    </div>
  );
}
