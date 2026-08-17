import React from "react";
import { theme } from "../theme";

/**
 * A connector between workflow/evidence nodes. `progress` (0..1) draws the line
 * and reveals the arrowhead — pass a clamped interpolation from the scene.
 */
export const WorkflowArrow: React.FC<{
  direction?: "down" | "right";
  length?: number;
  progress?: number;
  color?: string;
}> = ({ direction = "down", length = 48, progress = 1, color = theme.color.primary }) => {
  const p = Math.max(0, Math.min(1, progress));
  const vertical = direction === "down";
  const drawn = length * p;

  return (
    <div
      style={{
        position: "relative",
        width: vertical ? 2 : length,
        height: vertical ? length : 2,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: vertical ? 2 : drawn,
          height: vertical ? drawn : 2,
          background: color,
          borderRadius: 2,
        }}
      />
      <div
        style={{
          position: "absolute",
          opacity: p > 0.85 ? 1 : 0,
          transition: "none",
          [vertical ? "bottom" : "right"]: -1,
          [vertical ? "left" : "top"]: vertical ? -3 : -3,
          width: 0,
          height: 0,
          borderLeft: vertical ? "5px solid transparent" : `7px solid ${color}`,
          borderRight: vertical ? "5px solid transparent" : "5px solid transparent",
          borderTop: vertical ? `7px solid ${color}` : "5px solid transparent",
          borderBottom: vertical ? "0" : "5px solid transparent",
        }}
      />
    </div>
  );
};
