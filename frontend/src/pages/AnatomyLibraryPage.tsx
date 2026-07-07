import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

interface AnatomyFamilySummary {
  family: string;
  category: string;
  zone_names: string[];
  required_images: string[];
  min_images: number;
  high_risk_zones: string[];
}

interface AnatomyProfile {
  family: string;
  category: string;
  instrument_family: string;
  profile_found: boolean;
  zone_names: string[];
  required_zones: string[];
  high_risk_zones: string[];
  recommended_image_views: string[];
  zone_descriptions: Record<string, string>;
  contamination_risks: Record<string, string[]>;
  condition_risks: Record<string, string[]>;
  manual_check_steps: string[];
  warning: string | null;
}

function Tag({ children, tone = "slate" }: { children: React.ReactNode; tone?: "slate" | "red" }) {
  const cls = tone === "red" ? "bg-red-50 text-red-700" : "bg-slate-100 text-slate-700";
  return <span className={`inline-block text-xs ${cls} rounded px-2 py-0.5 mr-1 mb-1`}>{children}</span>;
}

function LookupPanel() {
  const { headers } = useAuth();
  const [instrumentType, setInstrumentType] = useState("rigid scope");
  const [manufacturer, setManufacturer] = useState("");
  const [model, setModel] = useState("");
  const [profile, setProfile] = useState<AnatomyProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    if (manufacturer) params.set("manufacturer", manufacturer);
    if (model) params.set("model", model);
    fetch(`${API_BASE}/api/instrument-anatomy/${encodeURIComponent(instrumentType)}?${params}`, { headers: headers() })
      .then((r) => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); })
      .then(setProfile)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => { run(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap gap-2 mb-4">
        <input value={instrumentType} onChange={(e) => setInstrumentType(e.target.value)} placeholder="Instrument type"
          className="text-sm border border-slate-300 rounded px-2 py-1 flex-1 min-w-[160px]" />
        <input value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} placeholder="Manufacturer (optional)"
          className="text-sm border border-slate-300 rounded px-2 py-1 flex-1 min-w-[160px]" />
        <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Model (optional)"
          className="text-sm border border-slate-300 rounded px-2 py-1 flex-1 min-w-[160px]" />
        <button onClick={run} className="text-sm bg-blue-600 text-white rounded px-3 py-1">Resolve anatomy profile</button>
      </div>
      {loading && <p className="text-sm text-slate-400">Resolving…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {profile && !loading && (
        <div className="space-y-2 text-sm">
          {profile.warning && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">{profile.warning}</p>
          )}
          <p><span className="font-medium">Instrument family:</span> {profile.instrument_family} <span className="text-slate-400">({profile.category})</span></p>
          <div><span className="font-medium">Anatomy zones: </span>{profile.zone_names.map((z) => <Tag key={z}>{z}</Tag>)}</div>
          <div><span className="font-medium">Required zones: </span>{profile.required_zones.map((z) => <Tag key={z}>{z}</Tag>)}</div>
          <div><span className="font-medium">High-risk zones: </span>{profile.high_risk_zones.map((z) => <Tag key={z} tone="red">{z}</Tag>)}</div>
          <div><span className="font-medium">Recommended image views: </span>{profile.recommended_image_views.map((z) => <Tag key={z}>{z}</Tag>)}</div>
          <div>
            <span className="font-medium">Zone descriptions:</span>
            <ul className="mt-1 list-disc list-inside text-slate-700">
              {Object.entries(profile.zone_descriptions).map(([zone, desc]) => (
                <li key={zone}><span className="font-medium capitalize">{zone}:</span> {desc}</li>
              ))}
            </ul>
          </div>
          <div>
            <span className="font-medium">Manual check steps:</span>
            <ul className="mt-1 list-disc list-inside text-slate-700">
              {profile.manual_check_steps.map((s, i) => <li key={i}>{s}</li>)}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

function FamilyCard({ f }: { f: AnatomyFamilySummary }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <button className="w-full text-left" onClick={() => setExpanded((e) => !e)}>
        <p className="font-semibold text-slate-900 capitalize">{f.family.replace(/_/g, " ")}</p>
        <p className="text-xs text-slate-500 mt-1">{f.category} · min {f.min_images} required image{f.min_images === 1 ? "" : "s"}</p>
      </button>
      {expanded && (
        <div className="mt-3 space-y-2 text-sm border-t border-slate-100 pt-3">
          <div><span className="font-medium">Zones: </span>{f.zone_names.map((z) => <Tag key={z}>{z}</Tag>)}</div>
          <div><span className="font-medium">Required images: </span>{f.required_images.map((z) => <Tag key={z}>{z}</Tag>)}</div>
          <div><span className="font-medium">High-risk zones: </span>{f.high_risk_zones.map((z) => <Tag key={z} tone="red">{z}</Tag>)}</div>
        </div>
      )}
    </div>
  );
}

export default function AnatomyLibraryPage() {
  const { headers } = useAuth();
  const [families, setFamilies] = useState<AnatomyFamilySummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/instrument-anatomy`, { headers: headers() })
      .then((r) => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); })
      .then((d) => setFamilies(d.families ?? []))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="p-6 space-y-8 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Anatomy Library</h1>
        <p className="text-sm text-slate-500 mt-1">
          The Anatomy Profile Service: every declared instrument-family zone taxonomy, required image views,
          and high-risk zones — the same data LumenAI resolves before contamination/damage analysis.
        </p>
      </div>

      <section>
        <h2 className="text-lg font-semibold text-slate-900 mb-3">Resolve a profile</h2>
        <LookupPanel />
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-900 mb-3">Browse anatomy families</h2>
        {loading && <p className="text-sm text-slate-400">Loading…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {families.map((f) => <FamilyCard key={f.family} f={f} />)}
        </div>
      </section>

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
        ⚠ Unrecognized instruments fall back to a generic SPD profile with a supervisor-review flag — nothing
        is fabricated as a specific match.
      </p>
    </div>
  );
}
