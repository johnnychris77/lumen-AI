import React from "react";
import { useCurrentFrame } from "remotion";
import { Caption } from "./Caption";
import { SCENE_WINDOWS, SceneId } from "../timing";
import { FormatInfo } from "../format";
import { fadeInOut } from "./anim";

/** Scenes rendered on a light background get a light-toned caption. */
const LIGHT_SCENES: ReadonlySet<SceneId> = new Set<SceneId>(["PhysicalInspection"]);
/** The Closing scene carries its own narration + lockup text — no burned-in caption. */
const NO_CAPTION: ReadonlySet<SceneId> = new Set<SceneId>(["Closing"]);

/**
 * Renders the active scene's caption in the format's safe area:
 *  - landscape: lower third of the full frame;
 *  - square/vertical: in the charcoal band BELOW the scaled 16:9 design band,
 *    so it never overlaps the scene visuals.
 */
export const CaptionTrack: React.FC<{ fmt: FormatInfo }> = ({ fmt }) => {
  const frame = useCurrentFrame();
  const win = SCENE_WINDOWS.find((w) => frame >= w.from && frame < w.to);
  if (!win || NO_CAPTION.has(win.id)) return null;

  const local = frame - win.from;
  const opacity = fadeInOut(local, win.durationInFrames, 12);
  const isLight = LIGHT_SCENES.has(win.id);

  // For landscape the band fills the frame → sit near the bottom of it.
  // For square/vertical, sit in the lower letterbox area (always dark).
  const belowBand = fmt.bandTop + fmt.bandHeight;
  const lowerAreaHeight = fmt.height - belowBand;
  const isFramed = fmt.format !== "landscape";

  const containerStyle: React.CSSProperties = isFramed
    ? {
        position: "absolute",
        left: 40,
        right: 40,
        top: belowBand + Math.max(24, lowerAreaHeight * 0.18),
      }
    : {
        position: "absolute",
        left: "8%",
        right: "8%",
        bottom: 64 * fmt.scale + 40,
      };

  return (
    <div style={containerStyle}>
      <Caption
        text={win.caption}
        opacity={opacity}
        // In the framed formats the caption sits on the dark letterbox, so it is
        // always dark-toned regardless of the scene's own background.
        tone={isFramed ? "dark" : isLight ? "light" : "dark"}
        fontSize={fmt.format === "vertical" ? 34 : fmt.format === "square" ? 30 : 30}
        maxWidth={fmt.format === "landscape" ? 1200 : fmt.width - 120}
      />
    </div>
  );
};
