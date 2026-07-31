import { useState } from "react";
import { Play, ChevronLeft, ChevronRight } from "lucide-react";
import { VIDEO_SCENES } from "../lib/content";
import { track } from "../lib/analytics";

/**
 * Storyboard-based interactive preview standing in for the finished explainer
 * video. Acts as an accessible, captioned placeholder player: stepping through
 * scenes shows on-screen text, narration, animation direction, and timing.
 * The full script + storyboard + captions live in docs/marketing/.
 */
export function VideoStoryboard() {
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(false);
  const scene = VIDEO_SCENES[i];
  const total = VIDEO_SCENES.length;
  const elapsed = VIDEO_SCENES.slice(0, i).reduce((a, s) => a + s.seconds, 0);
  const runtime = VIDEO_SCENES.reduce((a, s) => a + s.seconds, 0);

  const go = (next: number) => setI(Math.max(0, Math.min(total - 1, next)));

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      {/* Stage — placeholder player frame */}
      <div className="relative aspect-video w-full bg-gradient-to-br from-slate-900 via-slate-800 to-primary-active">
        <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center">
          {!playing ? (
            <button
              type="button"
              onClick={() => {
                setPlaying(true);
                track("video_play", { scene: scene.n });
              }}
              className="flex flex-col items-center gap-3 text-white/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
              aria-label="Play storyboard preview"
            >
              <span className="flex h-16 w-16 items-center justify-center rounded-full bg-white/15 ring-1 ring-white/40 transition-transform hover:scale-105 motion-reduce:transition-none">
                <Play size={26} className="ml-1" aria-hidden />
              </span>
              <span className="text-sm font-medium">Play storyboard preview · ~{runtime}s</span>
            </button>
          ) : (
            <>
              <p className="text-xs font-semibold uppercase tracking-widest text-white/60">
                Scene {scene.n} / {total} · {scene.name}
              </p>
              <p className="mt-3 max-w-lg text-2xl font-bold leading-snug text-white">{scene.onScreen}</p>
              <p className="mt-4 max-w-md text-sm italic text-white/70">“{scene.narration}”</p>
            </>
          )}
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/10">
          <div
            className="h-full bg-white/70 transition-all motion-reduce:transition-none"
            style={{ width: `${((elapsed + (playing ? scene.seconds : 0)) / runtime) * 100}%` }}
          />
        </div>
      </div>

      {/* Controls + scene detail */}
      <div className="flex items-center justify-between gap-3 border-t border-slate-200 p-3">
        <button
          type="button"
          onClick={() => go(i - 1)}
          disabled={i === 0}
          className="inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <ChevronLeft size={16} aria-hidden /> Prev
        </button>
        <div className="text-center text-xs text-slate-500">
          {String(Math.floor(elapsed / 60)).padStart(2, "0")}:{String(elapsed % 60).padStart(2, "0")} ·{" "}
          <span className="font-medium text-slate-700">{scene.animation}</span>
        </div>
        <button
          type="button"
          onClick={() => {
            setPlaying(true);
            go(i + 1);
          }}
          disabled={i === total - 1}
          className="inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          Next <ChevronRight size={16} aria-hidden />
        </button>
      </div>
    </div>
  );
}
