import { interpolate, spring } from "remotion";

/**
 * Small, shared animation helpers so scenes stay declarative and consistent.
 * Kept restrained on purpose — fades, gentle rises, soft springs. No neon.
 */

/** Fade + rise reveal. `delay`/`length` are in frames. */
export const reveal = (
  frame: number,
  delay = 0,
  length = 16,
): { opacity: number; translateY: number } => {
  const t = interpolate(frame, [delay, delay + length], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return { opacity: t, translateY: (1 - t) * 18 };
};

/** Fade in then out across a window. */
export const fadeInOut = (
  frame: number,
  total: number,
  edge = 12,
): number => {
  const a = interpolate(frame, [0, edge], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const b = interpolate(frame, [total - edge, total], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return Math.min(a, b);
};

/** Soft spring in [0,1]. */
export const softSpring = (
  frame: number,
  fps: number,
  delay = 0,
): number =>
  spring({
    frame: frame - delay,
    fps,
    config: { damping: 200, mass: 0.9, stiffness: 120 },
  });

/** Linear progress [0,1] over a window, clamped. */
export const progress = (
  frame: number,
  from: number,
  to: number,
): number =>
  interpolate(frame, [from, to], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
