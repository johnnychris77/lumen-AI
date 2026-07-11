/**
 * v4.9 — LumenAI OS: Project Phoenix — Platform Health Dashboard.
 *
 * Frontend route `/platform-health`, API prefix `/api/phoenix`.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

function ScoreTile({ label, area }: { label: string; area: Record<string, unknown> | undefined }) {
  const score = area?.score;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-700">{label}</h3>
      {score === null || score === undefined ? (
        <p className="mt-2 text-xs text-slate-400">{String(area?.note ?? "insufficient data")}</p>
      ) : (
        <p className="mt-2 text-3xl font-bold text-indigo-600">{String(score)}</p>
      )}
    </div>
  );
}

export default function PlatformHealthDashboard() {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.get("/api/phoenix/platform-health/dashboard").then(setHealth).catch(() => {});
  }, []);

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-xl font-bold text-slate-800">Platform Health Dashboard</h1>
      <p className="text-xs text-slate-400">
        Seven health areas plus overall platform maturity, composed from real signals across the platform.
        Areas with no recorded data yet show "insufficient data" rather than a fabricated score.
      </p>

      {health && (
        <>
          <div className="rounded-lg border-2 border-indigo-300 bg-indigo-50 p-4">
            <h3 className="text-sm font-semibold text-indigo-800">Overall Platform Maturity</h3>
            <p className="mt-2 text-4xl font-bold text-indigo-700">
              {health.overall_platform_maturity === null ? "—" : String(health.overall_platform_maturity)}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <ScoreTile label="AI Health" area={health.ai_health as Record<string, unknown>} />
            <ScoreTile label="Knowledge Health" area={health.knowledge_health as Record<string, unknown>} />
            <ScoreTile label="Workflow Health" area={health.workflow_health as Record<string, unknown>} />
            <ScoreTile label="Digital Twin Health" area={health.digital_twin_health as Record<string, unknown>} />
            <ScoreTile label="Security Health" area={health.security_health as Record<string, unknown>} />
            <ScoreTile label="Integration Health" area={health.integration_health as Record<string, unknown>} />
            <ScoreTile label="Quality Health" area={health.quality_health as Record<string, unknown>} />
          </div>
        </>
      )}
    </div>
  );
}
