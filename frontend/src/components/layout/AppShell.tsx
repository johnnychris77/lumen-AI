import React, { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useNotifications } from "@/lib/notifications";
import { useAuth } from "@/lib/auth";
import { NotificationPanel } from "@/components/ui/NotificationPanel";
import {
  LayoutDashboard,
  FilePlus,
  History,
  ClipboardCheck,
  LineChart,
  Package,
  Store,
  Thermometer,
  BookOpen,
  CheckCircle2,
  Database,
  CreditCard,
  ScanLine,
  Images,
  Upload,
  FileSearch,
  ShieldCheck,
  FileText,
  Building2,
  TrendingUp,
  BarChart3,
  AlertTriangle,
  Activity,
  Users,
  UserCheck,
  Settings,
  ChevronLeft,
  ChevronRight,
  Bell,
  LogOut,
  Rocket,
  GraduationCap,
  DollarSign,
  Camera,
  Network,
  Workflow,
  Cpu,
  ListChecks,
  ClipboardList,
  BookMarked,
  FilePlus2,
  EyeOff,
  GitCompareArrows,
  Scale,
  PackageCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

type NavLeaf = { to: string; label: string; icon: React.ElementType; roles?: string[] };
type NavGroup = { label: string; roles?: string[]; items: NavLeaf[] };

// ─── Role model ──────────────────────────────────────────────────────────────
// Elevated roles see administrative/enterprise groups. Everyone authenticated
// sees the operational core (inspection, baselines, instruments, quality).
// This is UX decluttering ONLY — the backend independently enforces access, so
// hiding a link is never the security boundary.
const ELEVATED_ROLES = ["admin", "spd_manager", "site_admin", "tenant_admin"];
const EXECUTIVE_ROLES = [...ELEVATED_ROLES, "executive"];

// `roles` restricts visibility. Omitted = visible to every authenticated user.
const NAV_GROUPS: NavGroup[] = [
  {
    label: "Executive",
    roles: EXECUTIVE_ROLES,
    items: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard },
      { to: "/executive-command-center", label: "Command Center", icon: BarChart3 },
      { to: "/surgical-readiness", label: "Surgical Readiness", icon: Thermometer },
      { to: "/global-registry", label: "Global Registry", icon: Database },
    ],
  },
  {
    label: "Inspection Intelligence",
    items: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard },
      { to: "/inspection/new", label: "New Inspection", icon: FilePlus },
      { to: "/inspection/capture", label: "Borescope Capture", icon: Camera },
      { to: "/intake-history", label: "Inspection History", icon: History },
      { to: "/findings", label: "Review Queue", icon: ClipboardCheck },
      { to: "/analytics", label: "Inspection Analytics", icon: LineChart },
      { to: "/inspection-work-queue", label: "Smart Work Queue", icon: ListChecks },
    ],
  },
  {
    label: "Baselines",
    items: [
      { to: "/manufacturer-baselines", label: "Manufacturer Baselines", icon: Package },
      { to: "/vendor-baseline-portal", label: "Vendor Baselines", icon: Store },
      { to: "/baseline-library", label: "Baseline Library", icon: BookOpen },
      { to: "/baseline-review", label: "Baseline Reviews", icon: CheckCircle2, roles: ELEVATED_ROLES },
    ],
  },
  {
    label: "Instruments",
    items: [
      { to: "/infrastructure", label: "Instrument Registry", icon: Database },
      { to: "/instrument-passport", label: "Instrument Passport", icon: CreditCard },
      { to: "/instrument-library", label: "Instrument Library", icon: BookOpen },
      { to: "/anatomy-library", label: "Anatomy Library", icon: Network },
      { to: "/inspection-zones", label: "Inspection Zones", icon: FileSearch },
      { to: "/coverage-dashboard", label: "Coverage Dashboard", icon: BarChart3 },
      { to: "/vendor-intake", label: "Barcode / QR / KeyDot", icon: ScanLine },
      { to: "/demo-image-library", label: "Image Library", icon: Images },
      { to: "/baseline-image-upload", label: "Upload Baseline Image", icon: Upload },
      { to: "/inspection-image-upload", label: "Upload Inspection Image", icon: Upload },
    ],
  },
  {
    label: "Quality & Compliance",
    items: [
      { to: "/findings", label: "Findings", icon: FileSearch },
      { to: "/capa", label: "CAPA", icon: ShieldCheck },
      { to: "/audit-evidence", label: "Audit Evidence", icon: FileText, roles: [...ELEVATED_ROLES, "auditor"] },
      { to: "/enterprise", label: "Enterprise Quality", icon: Building2, roles: ELEVATED_ROLES },
      { to: "/education-library", label: "SPD Education Library", icon: BookOpen },
      { to: "/coaching-dashboard", label: "Supervisor Coaching", icon: ClipboardCheck, roles: ELEVATED_ROLES },
      { to: "/pre-sterilization-command-center", label: "Pre-Sterilization Command Center", icon: CheckCircle2 },
      { to: "/knowledge-graph", label: "Knowledge Graph", icon: Network },
      { to: "/knowledge-center", label: "Knowledge Center", icon: BookMarked },
      { to: "/agent-trace", label: "Agent Trace", icon: Workflow },
      { to: "/cios-dashboard", label: "Clinical Intelligence OS", icon: Cpu },
    ],
  },
  {
    label: "Analytics",
    roles: [...EXECUTIVE_ROLES, "operator"],
    items: [
      { to: "/pilot-analytics", label: "Executive Dashboard", icon: TrendingUp, roles: EXECUTIVE_ROLES },
      { to: "/analytics", label: "Benchmarking", icon: BarChart3 },
      { to: "/quality-intelligence", label: "Risk Signals", icon: AlertTriangle },
      { to: "/quality-dashboard", label: "Quality Dashboard", icon: BarChart3 },
      { to: "/clinical-readiness", label: "Clinical Service Readiness", icon: ShieldCheck },
      { to: "/operations", label: "Operational Analytics", icon: Activity },
      { to: "/operations-board", label: "Operations Board", icon: ClipboardList, roles: ["admin", "spd_manager"] },
      { to: "/pilot-data-collection", label: "Pilot Data Collection", icon: Database, roles: ["admin", "spd_manager"] },
      { to: "/pilot-validation", label: "Pilot Validation", icon: Activity, roles: ["admin", "spd_manager"] },
    ],
  },
  {
    label: "Enterprise",
    roles: ELEVATED_ROLES,
    items: [
      { to: "/network-dashboard", label: "Network Dashboard", icon: Building2 },
      { to: "/image-quality", label: "Image Quality", icon: Camera },
    ],
  },
  {
    label: "Go-Live",
    roles: ELEVATED_ROLES,
    items: [
      { to: "/go-live-center", label: "Go-Live Center", icon: Rocket },
      { to: "/implementation-tracker", label: "Implementation Tracker", icon: ClipboardCheck },
      { to: "/training-compliance", label: "Training Compliance", icon: GraduationCap },
      { to: "/baseline-readiness", label: "Baseline Readiness", icon: Package },
      { to: "/inspection-readiness", label: "Inspection Readiness", icon: ScanLine },
      { to: "/executive-adoption", label: "Executive Adoption", icon: TrendingUp },
      { to: "/value-realization", label: "Value Realization", icon: DollarSign },
    ],
  },
  {
    label: "Customer Success",
    roles: ELEVATED_ROLES,
    items: [
      { to: "/customer-onboarding", label: "Onboarding Center", icon: Building2 },
      { to: "/customer-success", label: "Customer Health", icon: TrendingUp },
      { to: "/deployment-readiness", label: "Deployment Readiness", icon: ShieldCheck },
      { to: "/training-center", label: "Training Center", icon: BookOpen },
      { to: "/roi-center", label: "ROI Center", icon: BarChart3 },
      { to: "/subscription-readiness", label: "Subscription", icon: CreditCard },
    ],
  },
  {
    label: "Administration",
    roles: ELEVATED_ROLES,
    items: [
      { to: "/user-management", label: "User Roles", icon: UserCheck },
      { to: "/users", label: "Users", icon: Users },
      { to: "/roles", label: "Roles", icon: UserCheck },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
  {
    label: "Annotation Workspace",
    items: [
      { to: "/dataset/images", label: "Image Library", icon: Images },
      { to: "/dataset/images/upload", label: "Ingest Image", icon: Upload },
      { to: "/annotations", label: "Annotations", icon: FilePlus2 },
      { to: "/review/primary", label: "Primary Review", icon: ClipboardCheck },
      { to: "/review/secondary", label: "Secondary (Blind) Review", icon: EyeOff },
      { to: "/review/disagreements", label: "Disagreements", icon: GitCompareArrows },
      { to: "/review/adjudication", label: "Adjudication", icon: Scale, roles: ["admin", "clinical_reviewer"] },
      { to: "/ground-truth", label: "Ground Truth", icon: ShieldCheck },
      { to: "/dataset/releases", label: "Dataset Release Builder", icon: PackageCheck, roles: ["admin", "ai_researcher"] },
    ],
  },
];

function visibleGroups(role: string): NavGroup[] {
  return NAV_GROUPS
    .filter((g) => !g.roles || g.roles.includes(role))
    .map((g) => {
      // Filter by role, then drop duplicate destinations (a few pages, e.g.
      // Dashboard and Findings, intentionally appear in more than one group's
      // source list; within a single rendered group show each `to` once).
      const seen = new Set<string>();
      const items = g.items
        .filter((it) => !it.roles || it.roles.includes(role))
        .filter((it) => {
          if (seen.has(it.to)) return false;
          seen.add(it.to);
          return true;
        });
      return { ...g, items };
    })
    .filter((g) => g.items.length > 0);
}

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
            ? "bg-primary-subtle text-primary hover:bg-primary-subtle hover:text-primary"
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
  const { role: authRole, logout } = useAuth();
  const role = authRole || localStorage.getItem("role") || "viewer";
  const groups = visibleGroups(role);
  return (
    <aside
      className={cn(
        "flex flex-col border-r border-slate-200 bg-white transition-all duration-200 shrink-0",
        collapsed ? "w-16" : "w-60"
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-slate-200 px-4 gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary">
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
        {groups.map((group) => (
          <div key={group.label}>
            {!collapsed && (
              <p className="mb-1.5 px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                {group.label}
              </p>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <NavItem key={`${item.to}-${item.label}`} {...item} collapsed={collapsed} />
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
          onClick={() => logout()}
          title={collapsed ? "Sign out" : undefined}
        >
          <LogOut className="h-4 w-4 shrink-0" />
          {!collapsed && <span>Sign out</span>}
        </button>
      </div>
    </aside>
  );
}

function Breadcrumb({ path }: { path: string }) {
  // Build label from first matching nav entry (breadcrumb uses first match, not last)
  const label = React.useMemo(() => {
    for (const group of NAV_GROUPS) {
      for (const item of group.items) {
        if (item.to === path) return item.label;
      }
    }
    return path.replace(/^\//, "").replace(/-/g, " ") || "Dashboard";
  }, [path]);

  const segments = path.split("/").filter(Boolean);

  return (
    <nav className="flex items-center gap-1.5 text-xs text-slate-400" aria-label="Breadcrumb">
      <span className="hover:text-slate-600 cursor-default">LumenAI</span>
      {segments.map((seg, i) => (
        <React.Fragment key={i}>
          <span>/</span>
          {i === segments.length - 1 ? (
            <span className="text-slate-700 font-medium capitalize">{label}</span>
          ) : (
            <span className="capitalize">{seg.replace(/-/g, " ")}</span>
          )}
        </React.Fragment>
      ))}
      {segments.length === 0 && <><span>/</span><span className="text-slate-700 font-medium">Dashboard</span></>}
    </nav>
  );
}

function Header() {
  const location = useLocation();
  const { role, actor, logout } = useAuth();
  const [notifOpen, setNotifOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { unreadCount } = useNotifications();

  return (
    <header className="flex h-16 items-center border-b border-slate-200 bg-white px-6 gap-4 shrink-0">
      <div className="flex-1 min-w-0">
        <Breadcrumb path={location.pathname} />
      </div>

      <div className="flex items-center gap-3">
        <Badge variant="secondary" className="capitalize hidden sm:inline-flex">
          {role.replace(/_/g, " ")}
        </Badge>
        <div className="relative">
          <button
            className="relative rounded-full p-2 text-slate-500 hover:bg-slate-100"
            aria-label="Notifications"
            onClick={() => setNotifOpen(o => !o)}
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-danger ring-2 ring-white" />
            )}
          </button>
          <NotificationPanel open={notifOpen} onClose={() => setNotifOpen(false)} />
        </div>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setUserMenuOpen(o => !o)}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-semibold text-white hover:ring-2 hover:ring-primary-subtle"
            aria-label="User menu"
          >
            {(actor || "U")[0].toUpperCase()}
          </button>
          {userMenuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setUserMenuOpen(false)} />
              <div className="absolute right-0 mt-2 w-56 rounded-lg border border-slate-200 bg-white shadow-lg z-20 py-1">
                <div className="px-4 py-2 border-b border-slate-100">
                  <p className="text-sm font-medium text-slate-800 truncate">{actor || "user"}</p>
                  <p className="text-xs text-slate-500 capitalize">Role: {role.replace(/_/g, " ")}</p>
                </div>
                {(role === "admin" || role === "spd_manager") && (
                  <NavLink
                    to="/user-management"
                    onClick={() => setUserMenuOpen(false)}
                    className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
                  >
                    Manage user roles
                  </NavLink>
                )}
                <button
                  onClick={() => { setUserMenuOpen(false); logout(); }}
                  className="flex w-full items-center gap-2 px-4 py-2 text-sm text-danger hover:bg-danger-subtle"
                >
                  <LogOut className="h-4 w-4" /> Log out
                </button>
              </div>
            </>
          )}
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
