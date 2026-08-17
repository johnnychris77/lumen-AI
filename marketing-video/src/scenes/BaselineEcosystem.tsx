import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { WorkflowArrow } from "../components/WorkflowArrow";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";
import { demo } from "../data/demo";

/**
 * Scene 8 — The Baseline Ecosystem (1:09–1:20).
 * Manufacturer, Vendor, and Healthcare Organization contribute/use trusted
 * reference information through LumenAI. Governance is explicit:
 * Submit → Verify → Approve → Publish. Uploads are NOT automatically approved.
 */
export const BaselineEcosystem: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = (p: number) => durationInFrames * p;

  const hubIn = reveal(frame, t(0.28), 14);
  const flowIn = reveal(frame, t(0.5), 14);

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", top: 60, left: 100 }}>
        <Kicker>A governed reference pathway</Kicker>
      </div>

      {/* Org nodes */}
      <div style={{ position: "absolute", top: 150, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 70 }}>
        {demo.orgNodes.map((node, i) => {
          const r = reveal(frame, 6 + i * (fps * 0.2), 14);
          return (
            <div
              key={node}
              style={{
                opacity: r.opacity,
                transform: `translateY(${r.translateY}px)`,
                width: 300,
                textAlign: "center",
                padding: "22px 18px",
                borderRadius: theme.radius.md,
                background: theme.color.charcoalPanel,
                border: `1px solid rgba(255,255,255,0.1)`,
              }}
            >
              <div style={{ fontSize: 23, fontWeight: 600, color: theme.color.onDark }}>{node}</div>
              <div style={{ fontSize: 15, color: theme.color.onDarkSoft, marginTop: 6 }}>
                {i === 0 ? "uploads baseline imagery" : i === 1 ? "submits reference info" : "performs inspection"}
              </div>
            </div>
          );
        })}
      </div>

      {/* Converging into LumenAI */}
      <div style={{ position: "absolute", top: 300, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <WorkflowArrow direction="down" length={44} progress={progress(frame, t(0.22), t(0.34))} color={theme.color.primary} />
      </div>
      <div style={{ position: "absolute", top: 350, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <div
          style={{
            opacity: hubIn.opacity,
            transform: `translateY(${hubIn.translateY}px)`,
            padding: "20px 40px",
            borderRadius: theme.radius.lg,
            background: "linear-gradient(180deg, rgba(46,125,175,0.22), rgba(59,182,166,0.14))",
            border: `1px solid rgba(59,182,166,0.5)`,
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 26, fontWeight: 700, color: theme.color.onDark }}>LumenAI</div>
          <div style={{ display: "flex", gap: 22, marginTop: 12, color: theme.color.onDarkSoft, fontSize: 16 }}>
            <span>Baseline Governance</span>
            <span>·</span>
            <span>Inspection Evidence</span>
            <span>·</span>
            <span>Instrument History</span>
          </div>
        </div>
      </div>

      {/* Governance flow */}
      <div
        style={{
          position: "absolute",
          top: 500,
          left: 0,
          right: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 10,
          opacity: flowIn.opacity,
          transform: `translateY(${flowIn.translateY}px)`,
        }}
      >
        {demo.baselineFlow.map((step, i) => {
          const active = frame > t(0.52) + i * (fps * 0.4);
          return (
            <React.Fragment key={step}>
              <div
                style={{
                  padding: "16px 26px",
                  borderRadius: theme.radius.pill,
                  fontSize: 22,
                  fontWeight: 700,
                  color: active ? "#08131f" : theme.color.onDarkSoft,
                  background: active ? theme.color.teal : "transparent",
                  border: `2px solid ${active ? theme.color.teal : "rgba(255,255,255,0.2)"}`,
                }}
              >
                {step}
              </div>
              {i < demo.baselineFlow.length - 1 ? (
                <WorkflowArrow direction="right" length={40} progress={active ? 1 : 0} color={theme.color.teal} />
              ) : null}
            </React.Fragment>
          );
        })}
      </div>

      <div style={{ position: "absolute", bottom: 230, left: 0, right: 0, textAlign: "center", fontSize: 19, color: theme.color.amber }}>
        Submitted references are not automatically approved — approval is required before publication.
      </div>
    </Stage>
  );
};
