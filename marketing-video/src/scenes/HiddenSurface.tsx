import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Stage } from "../components/Stage";
import { LumenImage } from "../components/LumenImage";
import { theme } from "../theme";
import { fadeInOut } from "../components/anim";
import { mediaSrc } from "../media";

/**
 * Scene 1 — The Hidden Surface (0:00–0:08).
 * A clean instrument rotates, the camera pushes toward an opening and travels
 * into the internal lumen. Slow, cinematic, clinical — no sci-fi.
 */
export const HiddenSurface: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Phase 1 (0..55%): external instrument, slow rotate + push-in.
  // Phase 2 (45%..100%): transition into the lumen interior.
  const pushIn = interpolate(frame, [0, durationInFrames], [1, 1.8], {
    extrapolateRight: "clamp",
  });
  const rotate = interpolate(frame, [0, durationInFrames], [-8, 6]);
  const instrOpacity = interpolate(
    frame,
    [0, 12, durationInFrames * 0.5, durationInFrames * 0.62],
    [0, 1, 1, 0],
    { extrapolateRight: "clamp" },
  );
  const lumenOpacity = interpolate(
    frame,
    [durationInFrames * 0.48, durationInFrames * 0.66],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const lumenScale = interpolate(
    frame,
    [durationInFrames * 0.48, durationInFrames],
    [0.7, 1.06],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const depth = interpolate(frame, [durationInFrames * 0.5, durationInFrames], [0.2, 0.85], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const headline = fadeInOut(frame, durationInFrames, 16) * (frame > durationInFrames * 0.55 ? 1 : 0.0);

  return (
    <Stage mode="dark">
      {/* External instrument */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: instrOpacity,
          transform: `scale(${pushIn}) rotate(${rotate}deg)`,
        }}
      >
        <Instrument />
      </div>

      {/* Lumen interior */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: lumenOpacity,
          transform: `scale(${lumenScale})`,
        }}
      >
        <LumenImage size={620} depth={depth} src={mediaSrc("lumenS1")} />
      </div>

      {/* On-screen text */}
      <div
        style={{
          position: "absolute",
          top: 90,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: headline,
          color: theme.color.onDark,
          fontSize: 40,
          fontWeight: 600,
          letterSpacing: 0.3,
        }}
      >
        What happens inside the instrument matters.
      </div>
    </Stage>
  );
};

/** A clean cannulated surgical instrument silhouette with a visible opening. */
const Instrument: React.FC = () => (
  <svg width={1100} height={260} viewBox="0 0 1100 260">
    <defs>
      <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#e7edf4" />
        <stop offset="45%" stopColor="#aeb9c6" />
        <stop offset="55%" stopColor="#8b97a6" />
        <stop offset="100%" stopColor="#5c6675" />
      </linearGradient>
    </defs>
    {/* shaft */}
    <rect x="120" y="112" width="820" height="36" rx="18" fill="url(#steel)" />
    {/* distal opening (the lumen entry the camera enters) */}
    <circle cx="940" cy="130" r="30" fill="#12100d" stroke="#8b97a6" strokeWidth="6" />
    <circle cx="940" cy="130" r="14" fill="#000" />
    {/* handle */}
    <rect x="70" y="96" width="90" height="68" rx="16" fill="url(#steel)" />
    <rect x="150" y="120" width="30" height="20" rx="6" fill="#4a5361" />
    {/* subtle highlight */}
    <rect x="140" y="118" width="800" height="6" rx="3" fill="rgba(255,255,255,0.35)" />
  </svg>
);
