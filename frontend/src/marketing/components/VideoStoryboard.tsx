import { useEffect, useRef, useState } from "react";
import { Play, Pause, RotateCcw, ChevronLeft, ChevronRight } from "lucide-react";
import { VIDEO_SCENES } from "../lib/content";
import { track } from "../lib/analytics";

/**
 * Explainer video surface for the marketing site.
 *
 * Two modes, chosen at build time:
 *   1. PRODUCED VIDEO — if `VITE_EXPLAINER_VIDEO_URL` is set, render a real
 *      HTML5 <video> player (with captions) that plays the operator-supplied
 *      MP4. This is the slot for actual technician/borescope footage once it is
 *      filmed. No footage is fabricated here.
 *   2. ANIMATED STORYBOARD (default fallback) — a self-playing, timed, captioned
 *      walkthrough built from the synthetic scene list. It advances on its own
 *      (play / pause / restart), so it reads like a ~110s explainer rather than a
 *      click-through slideshow. All content is synthetic — not for clinical use.
 *
 * The full script + storyboard + captions live in docs/marketing/.
 */

const VIDEO_URL = (import.meta.env.VITE_EXPLAINER_VIDEO_URL as string | undefined) || "";
const POSTER_URL = (import.meta.env.VITE_EXPLAINER_POSTER_URL as string | undefined) || "";
// Captions ship at /site/lumenai-explainer.vtt in both the in-app and standalone builds.
const CAPTIONS_URL = "/site/lumenai-explainer.vtt";

export function VideoStoryboard() {
  return VIDEO_URL ? <ProducedVideo url={VIDEO_URL} poster={POSTER_URL} /> : <AnimatedStoryboard />;
}

/** Real <video> player — plays the operator-supplied explainer MP4. */
function ProducedVideo({ url, poster }: { url: string; poster: string }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <video
        className="aspect-video w-full bg-slate-900"
        controls
        playsInline
        preload="metadata"
        poster={poster || undefined}
        aria-label="LumenAI explainer video"
        onPlay={() => track("video_play", { mode: "produced" })}
      >
        <source src={url} />
        <track kind="captions" src={CAPTIONS_URL} srcLang="en" label="English" default />
        Your browser does not support the video element. The transcript is available in the storyboard below.
      </video>
      <p className="border-t border-slate-200 p-3 text-xs text-slate-500">
        Captions available (CC). Demonstration content — not for clinical use.
      </p>
    </div>
  );
}

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const on = () => setReduced(mq.matches);
    on();
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);
  return reduced;
}

/** Self-playing, timed, captioned storyboard (synthetic). */
function AnimatedStoryboard() {
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [started, setStarted] = useState(false);
  const reduced = usePrefersReducedMotion();
  const liveRef = useRef<HTMLParagraphElement>(null);

  const total = VIDEO_SCENES.length;
  const scene = VIDEO_SCENES[i];
  const runtime = VIDEO_SCENES.reduce((a, s) => a + s.seconds, 0);
  const elapsedBefore = VIDEO_SCENES.slice(0, i).reduce((a, s) => a + s.seconds, 0);
  const atEnd = i === total - 1;

  // Auto-advance: hold each scene for its own duration, then move on.
  useEffect(() => {
    if (!playing) return;
    const t = setTimeout(() => {
      if (atEnd) setPlaying(false);
      else setI((v) => Math.min(total - 1, v + 1));
    }, scene.seconds * 1000);
    return () => clearTimeout(t);
  }, [playing, i, scene.seconds, atEnd, total]);

  const startFromCurrentOrRestart = () => {
    if (atEnd && !playing) setI(0);
    setStarted(true);
    setPlaying(true);
    track("video_play", { mode: "storyboard", scene: scene.n });
  };
  const restart = () => {
    setI(0);
    setStarted(true);
    setPlaying(true);
  };
  const step = (next: number) => {
    setPlaying(false);
    setStarted(true);
    setI(Math.max(0, Math.min(total - 1, next)));
  };

  // Progress: fill across the current scene while playing; hold at its start when paused.
  const targetPct = ((elapsedBefore + (playing ? scene.seconds : 0)) / runtime) * 100;
  const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      {/* Stage */}
      <div className="relative aspect-video w-full bg-gradient-to-br from-slate-900 via-slate-800 to-primary-active">
        <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center">
          {!started ? (
            <button
              type="button"
              onClick={startFromCurrentOrRestart}
              className="flex flex-col items-center gap-3 text-white/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
              aria-label={`Play the animated explainer, about ${runtime} seconds`}
            >
              <span className="flex h-16 w-16 items-center justify-center rounded-full bg-white/15 ring-1 ring-white/40 transition-transform hover:scale-105 motion-reduce:transition-none">
                <Play size={26} className="ml-1" aria-hidden />
              </span>
              <span className="text-sm font-medium">Play the animated explainer · ~{runtime}s</span>
              <span className="text-xs text-white/60">Auto-plays · synthetic demonstration</span>
            </button>
          ) : (
            <div aria-live="polite" ref={liveRef}>
              <p className="text-xs font-semibold uppercase tracking-widest text-white/60">
                Scene {scene.n} / {total} · {scene.name}
              </p>
              <p className="mt-3 max-w-lg text-2xl font-bold leading-snug text-white">{scene.onScreen}</p>
              <p className="mt-4 max-w-md text-sm italic text-white/70">“{scene.narration}”</p>
              {atEnd && !playing && (
                <p className="mt-4 text-xs font-medium text-white/70">End of demonstration · synthetic content</p>
              )}
            </div>
          )}
        </div>
        {/* Progress bar (exposed value + text equivalent in controls below) */}
        <div
          className="absolute bottom-0 left-0 right-0 h-1 bg-white/10"
          role="progressbar"
          aria-label={`Explainer progress: scene ${scene.n} of ${total}`}
          aria-valuenow={i + 1}
          aria-valuemin={1}
          aria-valuemax={total}
        >
          <div
            className="h-full bg-white/70"
            style={{
              width: `${targetPct}%`,
              transitionProperty: "width",
              transitionTimingFunction: "linear",
              transitionDuration: playing && !reduced ? `${scene.seconds}s` : "0s",
            }}
          />
        </div>
      </div>

      {/* Controls + scene detail */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 p-3">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={playing ? () => setPlaying(false) : startFromCurrentOrRestart}
            aria-label={playing ? "Pause the explainer" : atEnd ? "Replay the explainer" : "Play the explainer"}
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1"
          >
            {playing ? <Pause size={16} aria-hidden /> : <Play size={16} aria-hidden />}
            {playing ? "Pause" : atEnd ? "Replay" : "Play"}
          </button>
          <button
            type="button"
            onClick={restart}
            aria-label="Restart from the beginning"
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-slate-500 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <RotateCcw size={15} aria-hidden />
          </button>
        </div>

        <p className="text-center text-xs text-slate-500">
          <span className="font-medium text-slate-700">{mmss(elapsedBefore)} / {mmss(runtime)}</span>
          {" · "}
          Scene {scene.n} of {total}: {scene.animation}
        </p>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => step(i - 1)}
            disabled={i === 0}
            aria-label="Previous scene"
            className="inline-flex min-h-[40px] items-center gap-1 rounded-md px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <ChevronLeft size={16} aria-hidden /> Prev
          </button>
          <button
            type="button"
            onClick={() => step(i + 1)}
            disabled={i === total - 1}
            aria-label="Next scene"
            className="inline-flex min-h-[40px] items-center gap-1 rounded-md px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            Next <ChevronRight size={16} aria-hidden />
          </button>
        </div>
      </div>
    </div>
  );
}
