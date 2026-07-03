import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";

export type AlertSeverity = "critical" | "warning" | "info";

export interface AppAlert {
  id: string;
  severity: AlertSeverity;
  title: string;
  detail: string;
  route?: string;
  routeLabel?: string;
  ts: number;
  read: boolean;
}

interface NotificationContextValue {
  alerts: AppAlert[];
  unreadCount: number;
  markRead: (id: string) => void;
  markAllRead: () => void;
  dismiss: (id: string) => void;
}

const NotificationContext = createContext<NotificationContextValue>({
  alerts: [],
  unreadCount: 0,
  markRead: () => {},
  markAllRead: () => {},
  dismiss: () => {},
});

export function useNotifications() {
  return useContext(NotificationContext);
}

function generateAlerts(kpi: Record<string, number>, pwr: Record<string, number>): AppAlert[] {
  const now = Date.now();
  const alerts: AppAlert[] = [];

  const critical = kpi.high_risk_findings ?? pwr.critical_findings ?? 0;
  const turnaround = kpi.review_turnaround_hrs ?? pwr.review_turnaround_hrs ?? 0;
  const baselinePct = kpi.baseline_coverage_pct ?? pwr.baseline_coverage_pct ?? 100;
  const inspections = kpi.total_inspections ?? pwr.total_inspections ?? 0;
  const health = kpi.customer_health_score ?? 0;
  const openCapas = kpi.open_capas ?? pwr.open_capas ?? 0;
  const loginFreq = kpi.login_frequency_per_week ?? 5;

  if (critical > 0 && turnaround > 8) {
    alerts.push({
      id: "critical-findings-unreviewed",
      severity: "critical",
      title: `${critical} critical finding${critical > 1 ? "s" : ""} awaiting review`,
      detail: `Average review turnaround is ${turnaround.toFixed(1)}h — target is ≤ 8h. Immediate SPD Manager action required.`,
      route: "/findings",
      routeLabel: "Open Review Queue",
      ts: now - 1000 * 60 * 15,
      read: false,
    });
  }

  if (baselinePct < 50 && inspections > 10) {
    alerts.push({
      id: "baseline-coverage-low",
      severity: "critical",
      title: "Baseline coverage below 50%",
      detail: `Current coverage: ${baselinePct}%. AI inspection accuracy degrades below 60% coverage. Contact vendor to submit missing baselines.`,
      route: "/baseline-readiness",
      routeLabel: "View Baseline Readiness",
      ts: now - 1000 * 60 * 60 * 2,
      read: false,
    });
  }

  if (health > 0 && health < 40) {
    alerts.push({
      id: "health-score-red",
      severity: "critical",
      title: "Customer Health Score is Red",
      detail: `Health score: ${health}/100. Immediate CS intervention required — schedule call with SPD Director within 48 hours.`,
      route: "/customer-success",
      routeLabel: "View Health Dashboard",
      ts: now - 1000 * 60 * 60 * 4,
      read: false,
    });
  }

  if (openCapas > 0) {
    alerts.push({
      id: "open-capas",
      severity: "warning",
      title: `${openCapas} CAPA${openCapas > 1 ? "s" : ""} open`,
      detail: "Open CAPAs should be reviewed and closed within 30 days. CAPAs open > 60 days are a renewal risk signal.",
      route: "/capa",
      routeLabel: "Open CAPA Queue",
      ts: now - 1000 * 60 * 60 * 24,
      read: false,
    });
  }

  if (baselinePct >= 50 && baselinePct < 75) {
    alerts.push({
      id: "baseline-coverage-warn",
      severity: "warning",
      title: "Baseline coverage below 75% target",
      detail: `Current coverage: ${baselinePct}%. Go-live threshold is 75%. Follow up with vendor on pending submissions.`,
      route: "/baseline-readiness",
      routeLabel: "View Baseline Readiness",
      ts: now - 1000 * 60 * 60 * 6,
      read: false,
    });
  }

  if (loginFreq < 2) {
    alerts.push({
      id: "low-engagement",
      severity: "warning",
      title: "Low platform engagement",
      detail: `Login frequency is ${loginFreq}x/week — target is ≥5x/week. Schedule a training refresher or check for workflow barriers.`,
      route: "/customer-success",
      routeLabel: "View Customer Health",
      ts: now - 1000 * 60 * 60 * 12,
      read: false,
    });
  }

  if (inspections >= 50 && baselinePct >= 75) {
    alerts.push({
      id: "go-live-ready",
      severity: "info",
      title: "Go-Live threshold reached",
      detail: `${inspections} inspections completed and baseline coverage at ${baselinePct}%. Review your Go-Live Readiness Score.`,
      route: "/go-live-center",
      routeLabel: "View Go-Live Center",
      ts: now - 1000 * 60 * 30,
      read: false,
    });
  }

  if (inspections > 0 && inspections % 100 === 0) {
    alerts.push({
      id: `milestone-${inspections}`,
      severity: "info",
      title: `${inspections} inspection milestone reached`,
      detail: "Generate a Value Realization report to share this milestone with your executive sponsor.",
      route: "/value-realization",
      routeLabel: "View Value Realization",
      ts: now - 1000 * 60 * 5,
      read: false,
    });
  }

  return alerts;
}

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [alerts, setAlerts] = useState<AppAlert[]>([]);

  const fetchAlerts = useCallback(async () => {
    try {
      const [kpiRes, pwrRes] = await Promise.allSettled([
        apiFetch("/api/analytics/kpi-summary", { raw: true }),
        apiFetch("/api/analytics/powerbi", { raw: true }),
      ]);
      const kpi = kpiRes.status === "fulfilled" && kpiRes.value.ok ? await kpiRes.value.json() : {};
      const pwr = pwrRes.status === "fulfilled" && pwrRes.value.ok ? await pwrRes.value.json() : {};
      const generated = generateAlerts(kpi, pwr);
      setAlerts(prev => {
        const existingIds = new Set(prev.map(a => a.id));
        const readIds = new Set(prev.filter(a => a.read).map(a => a.id));
        const dismissedIds = new Set(
          (JSON.parse(localStorage.getItem("dismissed_alerts") ?? "[]") as string[])
        );
        return generated
          .filter(a => !dismissedIds.has(a.id))
          .map(a => ({ ...a, read: readIds.has(a.id) || existingIds.has(a.id) && prev.find(p => p.id === a.id)?.read === true }));
      });
    } catch {
      // Network unavailable — use demo alerts
      const now = Date.now();
      setAlerts(prev => prev.length > 0 ? prev : [
        { id: "demo-critical", severity: "critical", title: "2 critical findings awaiting review", detail: "Review turnaround is 11h — target ≤8h. SPD Manager action required.", route: "/findings", routeLabel: "Open Review Queue", ts: now - 1000 * 60 * 20, read: false },
        { id: "demo-warn", severity: "warning", title: "Baseline coverage at 72%", detail: "3% below go-live threshold of 75%. Follow up with vendor.", route: "/baseline-readiness", routeLabel: "View Baseline Readiness", ts: now - 1000 * 60 * 60 * 3, read: false },
        { id: "demo-info", severity: "info", title: "47 inspections completed", detail: "3 more inspections needed to reach the 50-inspection go-live threshold.", route: "/go-live-center", routeLabel: "View Go-Live Center", ts: now - 1000 * 60 * 60 * 6, read: false },
      ]);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 5 * 60 * 1000); // refresh every 5 min
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const markRead = useCallback((id: string) => {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, read: true } : a));
  }, []);

  const markAllRead = useCallback(() => {
    setAlerts(prev => prev.map(a => ({ ...a, read: true })));
  }, []);

  const dismiss = useCallback((id: string) => {
    setAlerts(prev => prev.filter(a => a.id !== id));
    const dismissed = JSON.parse(localStorage.getItem("dismissed_alerts") ?? "[]") as string[];
    localStorage.setItem("dismissed_alerts", JSON.stringify([...dismissed, id]));
  }, []);

  const unreadCount = alerts.filter(a => !a.read).length;

  return (
    <NotificationContext.Provider value={{ alerts, unreadCount, markRead, markAllRead, dismiss }}>
      {children}
    </NotificationContext.Provider>
  );
}
