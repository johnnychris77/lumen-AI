import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { apiFetch } from "@/lib/api";

interface ImageTag {
  id: number;
  anatomy_zone: string;
  image_view: string;
  instrument_family: string;
  quality_score: number | null;
  quality_band: string | null;
  technician: string;
  flagged: boolean;
  flag_reason: string;
  notes: string;
}

interface TimelineEntry {
  sequence: number;
  tag_id: number;
  anatomy_zone: string;
  image_view: string;
  captured: boolean;
  quality_band: string | null;
  flagged: boolean;
}

interface MissingAnatomy {
  prompts: { zone: string; message: string }[];
  suggested_next: string | null;
  coverage: { overall_coverage: number | null; quality: string };
}

interface DuplicateFinding {
  type: string;
  message: string;
}

interface CrossImageReasoning {
  contamination_found: boolean;
  structural_found: boolean;
  overall_result: string;
}

interface EvidenceFusion {
  recommendation: string;
  narrative: string;
}

interface VisionSession {
  inspection_id: number;
  instrument_type: string;
  image_count: number;
  image_timeline: TimelineEntry[];
  missing_anatomy: MissingAnatomy;
  duplicate_detection: { findings: DuplicateFinding[]; has_warnings: boolean };
  cross_image_reasoning: CrossImageReasoning;
  evidence_fusion: EvidenceFusion;
}

interface Gallery {
  groups: { anatomy_zone: string; images: ImageTag[] }[];
}

const QUALITY_CLASS: Record<string, string> = {
  excellent: "bg-emerald-100 text-emerald-800",
  good: "bg-emerald-50 text-emerald-700",
  acceptable: "bg-amber-100 text-amber-800",
  poor: "bg-orange-100 text-orange-800",
  reject: "bg-red-100 text-red-800",
};

const RECOMMENDATION_CLASS: Record<string, string> = {
  PASS: "bg-emerald-100 text-emerald-800",
  MONITOR: "bg-slate-100 text-slate-700",
  "SUPERVISOR REVIEW": "bg-purple-100 text-purple-800",
  REPROCESS: "bg-amber-100 text-amber-800",
  "REMOVE FROM SERVICE": "bg-red-100 text-red-800",
};

function Badge({ children, cls }: { children: React.ReactNode; cls: string }) {
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>{children}</span>;
}

export default function VisionSessionPage() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<VisionSession | null>(null);
  const [gallery, setGallery] = useState<Gallery | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      apiFetch<VisionSession>(`/api/inspections/${id}/vision-session`),
      apiFetch<Gallery>(`/api/inspections/${id}/gallery`),
    ])
      .then(([s, g]) => { setSession(s); setGallery(g); setError(null); })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);

  const flagImage = async (tagId: number, flagged: boolean, reason: string) => {
    if (!id) return;
    await apiFetch(`/api/inspections/${id}/images/${tagId}/flag`, {
      method: "POST",
      body: { flagged, reason },
    });
    load();
  };

  if (loading) return <p className="p-6 text-sm text-slate-400">Loading vision session…</p>;
  if (error) return <p className="p-6 text-sm text-red-600">Vision session unavailable: {error}</p>;
  if (!session) return null;

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div>
        <Link to="/findings" className="text-sm text-blue-600 hover:underline">← Back to Review Queue</Link>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">Vision Session — Inspection #{session.inspection_id}</h1>
        <p className="text-sm text-slate-500 mt-1">
          <span className="capitalize">{session.instrument_type.replace(/_/g, " ")}</span> · {session.image_count} image(s) captured
        </p>
      </div>

      {/* Fused recommendation */}
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-base font-semibold text-slate-900">Evidence Fusion — Clinical Recommendation</h2>
          <Badge cls={RECOMMENDATION_CLASS[session.evidence_fusion.recommendation] ?? "bg-slate-100 text-slate-700"}>
            {session.evidence_fusion.recommendation}
          </Badge>
        </div>
        <p className="text-sm text-slate-700">{session.evidence_fusion.narrative}</p>
      </section>

      {/* Duplicate / anatomy warnings */}
      {session.duplicate_detection.has_warnings && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <h2 className="text-base font-semibold text-amber-900 mb-2">Warnings</h2>
          <ul className="list-disc list-inside space-y-1">
            {session.duplicate_detection.findings.map((f, i) => (
              <li key={i} className="text-sm text-amber-800">{f.message}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Missing anatomy */}
      {session.missing_anatomy.prompts.length > 0 && (
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold text-slate-900 mb-2">Missing Anatomy</h2>
          <ul className="list-disc list-inside space-y-1">
            {session.missing_anatomy.prompts.map((p) => (
              <li key={p.zone} className="text-sm text-slate-700">{p.message}</li>
            ))}
          </ul>
          {session.missing_anatomy.suggested_next && (
            <p className="text-sm text-blue-700 mt-3">
              Suggested next capture: <span className="font-semibold capitalize">{session.missing_anatomy.suggested_next}</span>
            </p>
          )}
        </section>
      )}

      {/* Image timeline */}
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-base font-semibold text-slate-900 mb-3">Image Timeline</h2>
        <ol className="space-y-2">
          {session.image_timeline.map((t) => (
            <li key={t.tag_id} className="flex items-center gap-2 text-sm">
              <span className="font-medium text-slate-900 capitalize">{t.sequence}. {t.anatomy_zone}</span>
              <span className="text-slate-400">({t.image_view || "no view tagged"})</span>
              {t.quality_band && <Badge cls={QUALITY_CLASS[t.quality_band] ?? "bg-slate-100 text-slate-700"}>{t.quality_band}</Badge>}
              {t.flagged && <Badge cls="bg-red-100 text-red-800">flagged</Badge>}
              <span className="text-emerald-600 font-bold">✓</span>
            </li>
          ))}
        </ol>
      </section>

      {/* Cross-image reasoning */}
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-base font-semibold text-slate-900 mb-2">Cross-Image Reasoning</h2>
        <p className="text-sm text-slate-700">{session.cross_image_reasoning.overall_result}</p>
      </section>

      {/* Gallery grouped by anatomy */}
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-base font-semibold text-slate-900 mb-3">Inspection Gallery</h2>
        {gallery?.groups.map((g) => (
          <div key={g.anatomy_zone} className="mb-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 capitalize mb-2">{g.anatomy_zone}</p>
            <div className="flex flex-wrap gap-3">
              {g.images.map((img) => (
                <div key={img.id} className="rounded-lg border border-slate-200 p-3 min-w-[180px]">
                  <p className="text-sm text-slate-800 mb-1">{img.image_view || "untitled view"}</p>
                  <p className="text-xs text-slate-500 mb-2">
                    {img.quality_band && <Badge cls={QUALITY_CLASS[img.quality_band] ?? "bg-slate-100 text-slate-700"}>{img.quality_band}</Badge>}
                    {" "}score {img.quality_score ?? "—"}
                  </p>
                  <button
                    onClick={() => flagImage(img.id, !img.flagged, img.flagged ? "" : "flagged for review")}
                    className={`text-xs rounded px-2 py-1 border ${img.flagged ? "bg-red-600 text-white border-red-600" : "border-slate-300 text-slate-700"}`}
                  >
                    {img.flagged ? "Unflag" : "Flag"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
