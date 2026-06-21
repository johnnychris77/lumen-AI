import React, { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  ClipboardList,
  ShieldCheck,
  FileSearch,
  BarChart3,
  Building2,
  Package,
  CheckCircle2,
  History,
  Store,
  ChevronLeft,
  ChevronRight,
  Bell,
  LogOut,
  Menu,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const NAV_GROUPS = [
  {
    label: "Overview",
    items: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard },
      { to: "/operations", label: "Operations", icon: Building2 },
      { to: "/analytics", label: "Analytics", icon: BarChart3 },
    ],
  },
  {
    label: "Inspection Intelligence",
    items: [
      { to: "/vendor-intake", label: "Vendor Intake", icon: ClipboardList },
      { to: "/intake-history", label: "Intake History", icon: History },
      { to: "/manufacturer-baselines", label: "Manufacturer Baselines", icon: Package },
      { to: "/baseline-review", label: "Baseline Review", icon: CheckCircle2 },
      { to: "/vendor-baseline-portal", label: "Vendor Baseline Portal", icon: Store },
    ],
  },
  {
    label: "Quality & Compliance",
    items: [
      { to: "/findings", label: "Findings Queue", icon: FileSearch },
      { to: "/capa", label: "CAPA Workflow", icon: ShieldCheck },
    ],
  },
];

function NavItem({
  to,
  label,
  icon: Icon,
  collapsed,
}: {
  to: string;
  label: string;
  icon: React.ElementType;
  collapsed: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          "hover:bg-slate-100 hover:text-slate-900",
          isActive
            ? "bg-blue-50 text-blue-700 hover:bg-blue-50 hover:text-blue-700"
            : "text-slate-600"
        )
      }
      title={collapsed ? label : undefined}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </NavLink>
  );
}

function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <aside
      className={cn(
        "flex flex-col border-r border-slate-200 bg-white transition-all duration-200 shrink-0",
        collapsed ? "w-16" : "w-60"
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-slate-200 px-4 gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600">
          <span className="text-xs font-bold text-white">LA</span>
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">LumenAI</p>
            <p className="truncate text-xs text-slate-500">Healthcare ERP</p>
          </div>
        )}
        <button
          onClick={onToggle}
          className="ml-auto rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-4">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            {!collapsed && (
              <p className="mb-1.5 px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                {group.label}
              </p>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <NavItem key={item.to} {...item} collapsed={collapsed} />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-200 p-3">
        <button
          className={cn(
            "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100",
            collapsed && "justify-center"
          )}
          onClick={() => {
            localStorage.removeItem("token");
            window.location.href = "/";
          }}
          title={collapsed ? "Sign out" : undefined}
        >
          <LogOut className="h-4 w-4 shrink-0" />
          {!collapsed && <span>Sign out</span>}
        </button>
      </div>
    </aside>
  );
}

function Header() {
  const location = useLocation();
  const role = localStorage.getItem("role") || "viewer";

  const breadcrumb = React.useMemo(() => {
    const path = location.pathname;
    const map: Record<string, string> = {
      "/": "Dashboard",
      "/operations": "Operations",
      "/analytics": "Analytics",
      "/vendor-intake": "Vendor Intake",
      "/intake-history": "Intake History",
      "/manufacturer-baselines": "Manufacturer Baselines",
      "/baseline-review": "Baseline Review",
      "/vendor-baseline-portal": "Vendor Baseline Portal",
      "/findings": "Findings Queue",
      "/capa": "CAPA Workflow",
    };
    return map[path] || path.replace("/", "").replace(/-/g, " ");
  }, [location.pathname]);

  return (
    <header className="flex h-16 items-center border-b border-slate-200 bg-white px-6 gap-4 shrink-0">
      <div className="flex-1 min-w-0">
        <h1 className="text-sm font-semibold text-slate-900 capitalize">{breadcrumb}</h1>
        <p className="text-xs text-slate-500">LumenAI · Healthcare Sterile Processing ERP</p>
      </div>

      <div className="flex items-center gap-3">
        <Badge variant="secondary" className="capitalize hidden sm:inline-flex">
          {role.replace(/_/g, " ")}
        </Badge>
        <button
          className="relative rounded-full p-2 text-slate-500 hover:bg-slate-100"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
          {(localStorage.getItem("actor") || "U")[0].toUpperCase()}
        </div>
      </div>
    </header>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
