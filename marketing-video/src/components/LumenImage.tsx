import React from "react";
import { Img, Video } from "remotion";
import { theme } from "../theme";
import { isVideoSrc } from "../media";

/**
 * Internal-lumen (borescope) view. If `src` is supplied (via the media manifest)
 * it renders real footage/stills clipped to the circular frame; otherwise it
 * falls back to a restrained, procedural placeholder (subtle surface variation,
 * gentle vignette, no exaggerated pathology). See the production guide's
 * "Assets still required".
 */
export const LumenImage: React.FC<{
  size?: number;
  /** 0..1 — how deep into the channel (shifts highlight + texture). */
  depth?: number;
  /** Show subtle, restrained areas-of-interest rings. */
  showAreas?: boolean;
  areaOpacity?: number;
  /** Optional real asset (from `mediaSrc(...)`). Falls back to procedural. */
  src?: string | null;
  style?: React.CSSProperties;
}> = ({ size = 460, depth = 0.5, showAreas = false, areaOpacity = 1, src = null, style }) => {
  const d = Math.max(0, Math.min(1, depth));
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        overflow: "hidden",
        position: "relative",
        boxShadow: "inset 0 0 80px rgba(0,0,0,0.75), 0 20px 50px rgba(0,0,0,0.5)",
        ...style,
      }}
    >
      {src ? (
        isVideoSrc(src) ? (
          <Video src={src} loop style={{ width: "100%", height: "100%", objectFit: "cover" }} muted />
        ) : (
          <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        )
      ) : (
      <svg width={size} height={size} viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice">
        <defs>
          <radialGradient id="lumenWall" cx="50%" cy={`${38 + d * 8}%`} r="75%">
            <stop offset="0%" stopColor="#8a7f74" />
            <stop offset="45%" stopColor="#5f5346" />
            <stop offset="80%" stopColor="#332b22" />
            <stop offset="100%" stopColor="#14100c" />
          </radialGradient>
          <radialGradient id="lumenLight" cx="50%" cy={`${34 + d * 10}%`} r="30%">
            <stop offset="0%" stopColor="rgba(255,246,230,0.55)" />
            <stop offset="100%" stopColor="rgba(255,246,230,0)" />
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="100" height="100" fill="url(#lumenWall)" />
        {/* Machined surface striations — subtle, curved along the channel. */}
        {Array.from({ length: 9 }).map((_, i) => (
          <ellipse
            key={i}
            cx={50}
            cy={38 + d * 8}
            rx={12 + i * 6}
            ry={9 + i * 5}
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth={0.4}
          />
        ))}
        {/* Faint residue-like variation and fine scratches (restrained). */}
        <ellipse cx={62} cy={44} rx={5} ry={3} fill="rgba(120,100,70,0.35)" />
        <ellipse cx={40} cy={58} rx={4} ry={2.4} fill="rgba(90,80,60,0.32)" />
        <path d="M34 40 L44 47" stroke="rgba(230,230,235,0.18)" strokeWidth={0.5} />
        <path d="M58 54 L66 60" stroke="rgba(230,230,235,0.14)" strokeWidth={0.4} />
        <rect x="0" y="0" width="100" height="100" fill="url(#lumenLight)" />
      </svg>
      )}
      {showAreas ? (
        <div style={{ position: "absolute", inset: 0, opacity: areaOpacity }}>
          <Ring xPct={62} yPct={44} d={54} />
          <Ring xPct={40} yPct={58} d={46} />
        </div>
      ) : null}
    </div>
  );
};

const Ring: React.FC<{ xPct: number; yPct: number; d: number }> = ({ xPct, yPct, d }) => (
  <div
    style={{
      position: "absolute",
      left: `${xPct}%`,
      top: `${yPct}%`,
      width: d,
      height: d,
      marginLeft: -d / 2,
      marginTop: -d / 2,
      borderRadius: "50%",
      border: `2px solid ${theme.color.teal}`,
      boxShadow: `0 0 0 4px rgba(59,182,166,0.18)`,
    }}
  />
);
