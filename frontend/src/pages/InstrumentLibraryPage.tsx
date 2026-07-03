import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

interface FamilyProfile {
  family_key: string;
  display_name: string;
  typical_anatomy: string[];
  high_risk_zones: string[];
  typical_contamination: string[];
  typical_damage: string[];
  typical_repair_issues: string[];
  inspection_priorities: string[];
  cleaning_priorities: string[];
  supervisor_focus_areas: string[];
  anatomy_family_note?: string;
}

function Tag({ children, tone = "slate" }: { children: React.ReactNode; tone?: "slate" | "red" }) {
  const cls = tone === "red" ? "bg-red-50 text-red-700" : "bg-slate-100 text-slate-700";
  return <span className={`inline-block text-xs ${cls} rounded px-2 py-0.5 mr-1 mb-1`}>{children}</span>;
}

function FamilyDetail({ profile }: { profile: FamilyProfile }) {
  return (
    <div className="mt-3 space-y-2 text-sm border-t border-slate-100 pt-3">
      {profile.anatomy_family_note && (
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">{profile.anatomy_family_note}</p>
      )}
      <div><span className="font-medium">Anatomy zones: </span>{profile.typical_anatomy.map((z) => <Tag key={z}>{z}</Tag>)}</div>
      <div><span className="font-medium">High-risk zones: </span>{profile.high_risk_zones.map((z) => <Tag key={z} tone="red">{z}</Tag>)}</div>
      <div><span className="font-medium">Typical contamination risks: </span>{profile.typical_contamination.map((z) => <Tag key={z}>{z}</Tag>)}</div>
      <div><span className="font-medium">Typical damage risks: </span>{profile.typical_damage.map((z) => <Tag key={z}>{z}</Tag>)}</div>
      <div><span className="font-medium">Typical repair issues: </span>{profile.typical_repair_issues.map((z) => <Tag key={z}>{z}</Tag>)}</div>
      <div><span className="font-medium">Inspection priorities: </span>{profile.inspection_priorities.map((z) => <Tag key={z}>{z}</Tag>)}</div>
      <div><span className="font-medium">Cleaning priorities (manual-check guidance): </span>{profile.cleaning_priorities.map((z) => <Tag key={z}>{z}</Tag>)}</div>
      <div><span className="font-medium">Supervisor focus areas: </span>{profile.supervisor_focus_areas.map((z) => <Tag key={z}>{z}</Tag>)}</div>
    </div>
  );
}

function FamilyCard({ profile }: { profile: FamilyProfile }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <button className="w-full text-left" onClick={() => setExpanded((e) => !e)}>
        <div className="flex items-center justify-between">
          <p className="font-semibold text-slate-900">{profile.display_name}</p>
          <span className="text-xs text-slate-400">{expanded ? "▲" : "▼"}</span>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          {profile.typical_anatomy.length} anatomy zones · {profile.high_risk_zones.length} high-risk
        </p>
      </button>
      {expanded && <FamilyDetail profile={profile} />}
    </div>
  );
}

export default function InstrumentLibraryPage() {
  const { headers } = useAuth();
  const [families, setFamilies] = useState<FamilyProfile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/knowledge-graph/instrument-families`, { headers: headers() })
      .then((r) => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); })
      .then((d) => setFamilies(d.families ?? []))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Instrument Knowledge Library</h1>
        <p className="text-sm text-slate-500 mt-1">
          Structured knowledge profiles — anatomy, high-risk zones, typical contamination/damage/repair patterns,
          inspection and cleaning priorities — for the instrument families LumenAI reasons over before AI analysis.
        </p>
      </div>

      {loading && <p className="text-sm text-slate-400">Loading instrument library…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {families.map((f) => <FamilyCard key={f.family_key} profile={f} />)}
      </div>

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
        ⚠ This is structured clinical knowledge, not a substitute for the device IFU. See also the{" "}
        <a href="/anatomy-library" className="underline">Anatomy Library</a> for per-zone detail and the{" "}
        <a href="/inspection-zones" className="underline">Inspection Zones</a> reference for the underlying taxonomy.
      </p>
    </div>
  );
}
