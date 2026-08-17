import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { WorkflowArrow } from "../components/WorkflowArrow";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";
import { demo } from "../data/demo";

/**
 * Scene 13 — Operational & Cost Intelligence.
 * Documented inspections and decisions inform maintenance / replacement trends.
 * NO dollar values, ROI, or avoided-cost claims. Financial impact is explicitly
 * gated behind validated organizational cost data (Level 3 shown as "not shown").
 */
export const OperationalCostIntelligence: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const levelsIn = reveal(frame, durationInFrames * 0.4, 14);

  const stateColor = (state: string): string =>
    state === "shown"
      ? theme.color.teal
      : state.startsWith("with")
        ? theme.color.amber
        : theme.color.inkFaint;

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", top: 58, left: 100 }}>
        <Kicker>Operational &amp; Cost Intelligence</Kicker>
      </div>

      <div style={{ position: "absolute", top: 140, left: 100, right: 100, display: "flex", gap: 40 }}>
        {/* progression */}
        <div style={{ width: 470 }}>
          {demo.operationalChain.map((step, i) => {
            const r = reveal(frame, 6 + i * (fps * 0.13), 10);
            const last = i === demo.operationalChain.length - 1;
            return (
              <div key={step} style={{ opacity: r.opacity, transform: `translateY(${r.translateY}px)` }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "9px 18px", borderRadius: theme.radius.md, background: last ? "rgba(59,182,166,0.14)" : theme.color.charcoalPanel, border: `1px solid ${last ? "rgba(59,182,166,0.5)" : "rgba(255,255,255,0.08)"}` }}>
                  <span style={{ width: 8, height: 8, borderRadius: 999, background: last ? theme.color.teal : theme.color.primary }} />
                  <span style={{ fontSize: 18, fontWeight: last ? 700 : 500, color: theme.color.onDark }}>{step}</span>
                </div>
                {!last ? <div style={{ height: 10, marginLeft: 22 }}><WorkflowArrow direction="down" length={10} progress={progress(frame, 6 + i * (fps * 0.13), 6 + (i + 1) * (fps * 0.13))} /></div> : null}
              </div>
            );
          })}
        </div>

        {/* three levels of value */}
        <div style={{ flex: 1, opacity: levelsIn.opacity, transform: `translateY(${levelsIn.translateY}px)`, display: "flex", flexDirection: "column", gap: 14 }}>
          {demo.valueLevels.map((lv) => (
            <div key={lv.level} style={{ background: theme.color.charcoalPanel, border: `1px solid rgba(255,255,255,0.1)`, borderRadius: theme.radius.md, padding: "16px 22px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: theme.color.onDark }}>{lv.level} · {lv.title}</div>
                <span style={{ fontSize: 13, fontWeight: 700, color: stateColor(lv.state), border: `1px solid ${stateColor(lv.state)}`, borderRadius: 999, padding: "3px 12px", textTransform: "uppercase", letterSpacing: 0.5 }}>{lv.state}</span>
              </div>
              <div style={{ fontSize: 15, color: theme.color.onDarkSoft, marginTop: 8 }}>{lv.items.join(" · ")}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ position: "absolute", top: 470, left: 0, right: 0, textAlign: "center", fontSize: 18, color: theme.color.amber }}>
        No dollar-value savings claimed — financial impact is evaluated with validated organizational cost data.
      </div>
    </Stage>
  );
};
