import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { LumenImage } from "../components/LumenImage";
import { WorkflowArrow } from "../components/WorkflowArrow";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";
import { demo } from "../data/demo";
import { mediaSrc, MediaSlot } from "../media";

/**
 * Scene 5 — Image Becomes Intelligence (0:36–0:48).
 * Four stages: Image Quality → AI-Assisted Analysis → Baseline Comparison →
 * Review Routing. Then a restrained side-by-side of Current Inspection vs
 * Approved Baseline. Safety language: AI-assisted, support, surface, compare.
 */
export const IntelligencePipeline: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = (p: number) => durationInFrames * p;

  const compareIn = reveal(frame, t(0.6), 16);
  const areaReveal = progress(frame, t(0.7), t(0.9));

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", top: 66, left: 100 }}>
        <Kicker>From image to structured evidence</Kicker>
      </div>

      {/* Pipeline stages */}
      <div
        style={{
          position: "absolute",
          top: 150,
          left: 100,
          right: 100,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {demo.pipeline.map((stage, i) => {
          const r = reveal(frame, 6 + i * (fps * 0.5), 14);
          const active = frame > 6 + i * (fps * 0.5) + 8;
          return (
            <React.Fragment key={stage}>
              <div
                style={{
                  opacity: r.opacity,
                  transform: `translateY(${r.translateY}px)`,
                  flex: 1,
                  maxWidth: 300,
                  textAlign: "center",
                  padding: "20px 16px",
                  borderRadius: theme.radius.md,
                  background: active ? "rgba(46,125,175,0.16)" : theme.color.charcoalPanel,
                  border: `1px solid ${active ? "rgba(46,125,175,0.5)" : "rgba(255,255,255,0.08)"}`,
                }}
              >
                <div style={{ fontSize: 15, color: theme.color.onDarkSoft }}>Stage {i + 1}</div>
                <div style={{ fontSize: 21, fontWeight: 600, color: theme.color.onDark, marginTop: 6 }}>{stage}</div>
              </div>
              {i < demo.pipeline.length - 1 ? (
                <div style={{ width: 60, display: "flex", justifyContent: "center" }}>
                  <WorkflowArrow direction="right" length={44} progress={progress(frame, 6 + i * (fps * 0.5), 6 + (i + 1) * (fps * 0.5))} />
                </div>
              ) : null}
            </React.Fragment>
          );
        })}
      </div>

      {/* Side-by-side comparison */}
      <div
        style={{
          position: "absolute",
          top: 320,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          gap: 60,
          opacity: compareIn.opacity,
          transform: `translateY(${compareIn.translateY}px)`,
        }}
      >
        <CompareCard title="Current Inspection" showAreas areaOpacity={areaReveal} depth={0.55} slot="lumenCurrent" />
        <div style={{ display: "flex", alignItems: "center", color: theme.color.onDarkSoft, fontSize: 20, fontWeight: 600 }}>
          compared with
        </div>
        <CompareCard title="Approved Baseline" showAreas={false} depth={0.5} badge="when available" slot="lumenBaseline" />
      </div>
    </Stage>
  );
};

const CompareCard: React.FC<{
  title: string;
  showAreas: boolean;
  areaOpacity?: number;
  depth: number;
  badge?: string;
  slot: MediaSlot;
}> = ({ title, showAreas, areaOpacity = 1, depth, badge, slot }) => (
  <div style={{ background: "#0c1119", borderRadius: 16, padding: 16, border: `1px solid rgba(255,255,255,0.08)` }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
      <span style={{ fontSize: 18, fontWeight: 600, color: theme.color.onDark }}>{title}</span>
      {badge ? (
        <span style={{ fontSize: 13, color: theme.color.onDarkSoft, border: `1px solid rgba(255,255,255,0.15)`, borderRadius: 999, padding: "2px 10px" }}>{badge}</span>
      ) : null}
    </div>
    <LumenImage size={300} depth={depth} showAreas={showAreas} areaOpacity={areaOpacity} src={mediaSrc(slot)} />
  </div>
);
