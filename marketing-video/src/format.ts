import { useVideoConfig } from "remotion";

/**
 * All scenes are authored on a fixed 1920×1080 "design canvas". For the square
 * (1080×1080) and vertical (1080×1920) deliveries we scale that canvas to the
 * target width and center it, then place captions and light brand furniture in
 * the format's safe area — so social cuts are intentionally composed rather than
 * naively cropped. Timing is identical across all three (see src/timing.ts).
 */
export const DESIGN_WIDTH = 1920;
export const DESIGN_HEIGHT = 1080;

export type Format = "landscape" | "square" | "vertical";

export interface FormatInfo {
  format: Format;
  width: number;
  height: number;
  /** Scale applied to the 1920×1080 design canvas to fit the target width. */
  scale: number;
  /** Top offset (px, composition space) of the scaled design band. */
  bandTop: number;
  /** Height (px, composition space) of the scaled design band. */
  bandHeight: number;
}

export const useFormat = (): FormatInfo => {
  const { width, height } = useVideoConfig();
  const ratio = width / height;
  const format: Format =
    Math.abs(ratio - 1) < 0.02 ? "square" : ratio < 1 ? "vertical" : "landscape";
  const scale = width / DESIGN_WIDTH;
  const bandHeight = DESIGN_HEIGHT * scale;
  const bandTop = (height - bandHeight) / 2;
  return { format, width, height, scale, bandTop, bandHeight };
};
