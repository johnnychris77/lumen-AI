import React from "react";
import { Audio, staticFile } from "remotion";
import { SCENE_WINDOWS } from "./timing";

/**
 * Audio manifest — INERT BY DEFAULT.
 *
 * No audio ships with this repo (music/VO/sfx are production assets). Drop files
 * into `public/audio/` and set the paths below; the composition then mixes them
 * automatically. Leaving a value `null` renders no <Audio> for it, so `npm run
 * render` always works with or without audio present.
 *
 *   public/audio/music.mp3   — restrained cinematic bed (full runtime)
 *   public/audio/vo.mp3       — voiceover from LUMENAI_VIDEO_SCRIPT.md (full runtime)
 */
export const AUDIO = {
  music: null as string | null, // e.g. "audio/music.mp3"
  voiceover: null as string | null, // e.g. "audio/vo.mp3"
  musicVolume: 0.5,
  voiceoverVolume: 1,
} as const;

/** Supervisor-review scene window — music ducks under "AI assists. People decide." */
const HUMAN_REVIEW = SCENE_WINDOWS.find((w) => w.id === "SupervisorReview");

/**
 * Music volume envelope: gentle fade-in, a dip under the human-review moment,
 * and a fade-out at the end. Driven off `src/timing.ts`, so it stays in sync if
 * scene durations change.
 */
const musicVolume = (frame: number): number => {
  const base = AUDIO.musicVolume;
  const total = SCENE_WINDOWS.reduce((a, w) => a + w.durationInFrames, 0);
  let v = base;
  // fade in over first 1s
  if (frame < 30) v *= frame / 30;
  // fade out over last 1s
  if (frame > total - 30) v *= Math.max(0, (total - frame) / 30);
  // duck under the human-review scene
  if (HUMAN_REVIEW && frame >= HUMAN_REVIEW.from && frame < HUMAN_REVIEW.to) {
    v *= 0.45;
  }
  return Math.max(0, v);
};

export const AudioBed: React.FC = () => {
  const children: React.ReactNode[] = [];
  if (AUDIO.music) {
    children.push(
      React.createElement(Audio, {
        key: "music",
        src: staticFile(AUDIO.music),
        volume: (f: number) => musicVolume(f),
      }),
    );
  }
  if (AUDIO.voiceover) {
    children.push(
      React.createElement(Audio, {
        key: "vo",
        src: staticFile(AUDIO.voiceover),
        volume: AUDIO.voiceoverVolume,
      }),
    );
  }
  return React.createElement(React.Fragment, null, ...children);
};
