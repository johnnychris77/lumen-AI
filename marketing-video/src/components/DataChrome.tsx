import React from "react";
import { theme } from "../theme";
import { SYNTHETIC_LABEL } from "../data/demo";

/**
 * Persistent "Synthetic demonstration data" marker. Every dashboard / history /
 * trend screen must carry this so illustrative values are never mistaken for
 * validated customer, hospital, or pilot outcomes.
 */
export const SyntheticBadge: React.FC<{ tone?: "dark" | "light" }> = ({ tone = "dark" }) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      padding: "8px 14px",
      borderRadius: theme.radius.pill,
      border: `1px dashed ${tone === "dark" ? "rgba(255,255,255,0.35)" : theme.color.inkFaint}`,
      color: tone === "dark" ? theme.color.onDarkSoft : theme.color.inkSoft,
      fontSize: 14,
      fontWeight: 700,
      letterSpacing: 0.6,
      textTransform: "uppercase",
    }}
  >
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8 v5" /><path d="M12 16 h.01" />
    </svg>
    {SYNTHETIC_LABEL}
  </div>
);

const RESULT_COLORS: Record<string, string> = {
  Pass: theme.color.green,
  Fair: theme.color.amber,
  Review: theme.color.primary,
};

/** Pass / Fair / Review result pill. */
export const ResultBadge: React.FC<{ result: string }> = ({ result }) => {
  const color = RESULT_COLORS[result] ?? theme.color.inkFaint;
  const label = result === "Review" ? "Review Required" : result;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 9,
        padding: "8px 18px",
        borderRadius: theme.radius.pill,
        background: `${color}22`,
        border: `1px solid ${color}`,
        color: theme.color.onDark,
        fontSize: 18,
        fontWeight: 600,
      }}
    >
      <span style={{ width: 10, height: 10, borderRadius: 999, background: color }} />
      {label}
    </span>
  );
};
