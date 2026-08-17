import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Stage } from "../components/Stage";
import { LumenImage } from "../components/LumenImage";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";
import { demo } from "../data/demo";
import { mediaSrc } from "../media";

/**
 * Scene 7 — Supervisor Review (real workflow, expanded).
 * The technician submits an inspection that requires review; LumenAI routes it
 * to the Supervisor Review Queue; an SPD supervisor at another workstation opens
 * it, reviews the evidence, and records a disposition. Resolves to the film's key
 * line: "AI assists. People decide."
 */
export const SupervisorReview: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = (p: number) => durationInFrames * p;

  // Cross-fade: technician submit (early) → supervisor review (mid).
  const techOpacity = interpolate(frame, [0, 10, t(0.26), t(0.34)], [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const supOpacity = interpolate(frame, [t(0.3), t(0.4)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const evidenceP = progress(frame, t(0.44), t(0.72));
  const dispChosen = frame > t(0.72);
  const lineOpacity = interpolate(frame, [t(0.8), t(0.9)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const dim = interpolate(frame, [t(0.82), t(0.92)], [1, 0.22], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", inset: 0, opacity: dim }}>
        {/* Status badge (evolves) */}
        <div style={{ position: "absolute", top: 70, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
          <StatusBadge frame={frame} t={t} />
        </div>

        {/* Technician submit (early) */}
        <div style={{ position: "absolute", top: 190, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: techOpacity }}>
          <div style={{ width: 720, background: theme.color.charcoalPanel, border: `1px solid rgba(255,255,255,0.1)`, borderRadius: theme.radius.lg, padding: 28, textAlign: "center" }}>
            <div style={{ fontSize: 20, color: theme.color.onDarkSoft }}>Technician completes the inspection</div>
            <div style={{ marginTop: 16, display: "flex", justifyContent: "center", gap: 14 }}>
              <div style={{ padding: "14px 28px", borderRadius: theme.radius.md, background: theme.color.primary, color: "#fff", fontSize: 20, fontWeight: 700 }}>Submit for Review</div>
            </div>
            <div style={{ marginTop: 16, color: theme.color.teal, fontSize: 17 }}>→ routed to Supervisor Review Queue</div>
          </div>
        </div>

        {/* Supervisor review (mid) */}
        <div style={{ position: "absolute", top: 150, left: 90, right: 90, opacity: supOpacity }}>
          <div style={{ display: "flex", gap: 24 }}>
            {/* Supervisor identity + evidence images */}
            <div style={{ width: 470, background: theme.color.charcoalPanel, border: `1px solid rgba(255,255,255,0.1)`, borderRadius: theme.radius.lg, padding: 22 }}>
              <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: theme.color.teal }}>{demo.supervisor}</div>
              <div style={{ fontSize: 18, color: theme.color.onDarkSoft, marginTop: 4 }}>Reviewing inspection · {demo.instrument.id}</div>
              <div style={{ display: "flex", gap: 14, marginTop: 18, alignItems: "center" }}>
                <div style={{ background: "#0c1119", borderRadius: 12, padding: 8 }}>
                  <LumenImage size={150} depth={0.55} showAreas areaOpacity={1} src={mediaSrc("lumenCurrent")} />
                  <div style={{ textAlign: "center", fontSize: 13, color: theme.color.onDarkSoft, marginTop: 6 }}>Current</div>
                </div>
                <div style={{ color: theme.color.onDarkSoft, fontSize: 14 }}>vs</div>
                <div style={{ background: "#0c1119", borderRadius: 12, padding: 8 }}>
                  <LumenImage size={150} depth={0.5} src={mediaSrc("lumenBaseline")} />
                  <div style={{ textAlign: "center", fontSize: 13, color: theme.color.onDarkSoft, marginTop: 6 }}>Baseline</div>
                </div>
              </div>
            </div>

            {/* Evidence checklist */}
            <div style={{ flex: 1, background: theme.color.charcoalPanel, border: `1px solid rgba(255,255,255,0.1)`, borderRadius: theme.radius.lg, padding: 22 }}>
              <div style={{ fontSize: 18, color: theme.color.onDarkSoft, marginBottom: 14 }}>Supervisor reviews the evidence</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {demo.reviewEvidence.map((label, i) => {
                  const on = evidenceP > (i + 1) / (demo.reviewEvidence.length + 1);
                  return (
                    <div key={label} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderRadius: theme.radius.md, background: theme.color.charcoal2, border: `1px solid rgba(255,255,255,0.06)` }}>
                      <Check on={on} />
                      <span style={{ fontSize: 18, color: theme.color.onDark, fontWeight: 500 }}>{label}</span>
                    </div>
                  );
                })}
              </div>

              {/* Disposition */}
              <div style={{ marginTop: 18, fontSize: 16, color: theme.color.onDarkSoft }}>Record disposition</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 10 }}>
                {demo.dispositions.map((disp, i) => {
                  const chosen = dispChosen && i === 0;
                  return (
                    <div key={disp} style={{ padding: "10px 18px", borderRadius: theme.radius.pill, fontSize: 16, fontWeight: 600, color: chosen ? "#08131f" : theme.color.onDarkSoft, background: chosen ? theme.color.teal : "transparent", border: `2px solid ${chosen ? theme.color.teal : "rgba(255,255,255,0.18)"}` }}>{disp}</div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* THE line */}
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", opacity: lineOpacity }}>
        <div style={{ fontSize: 68, fontWeight: 700, color: theme.color.onDark, letterSpacing: 0.5 }}>
          AI assists. <span style={{ color: theme.color.teal }}>People decide.</span>
        </div>
      </div>
    </Stage>
  );
};

const StatusBadge: React.FC<{ frame: number; t: (p: number) => number }> = ({ frame, t }) => {
  const inQueue = frame > t(0.26);
  const reviewing = frame > t(0.4);
  const label = reviewing ? "In Supervisor Review" : inQueue ? "Supervisor Review Queue" : "Supervisor Review Required";
  const r = reveal(frame, 4, 12);
  return (
    <div style={{ opacity: r.opacity, transform: `translateY(${r.translateY}px)`, display: "inline-flex", alignItems: "center", gap: 12, background: "rgba(217,164,65,0.14)", border: `1px solid ${theme.color.amber}`, color: theme.color.amber, padding: "12px 24px", borderRadius: theme.radius.pill, fontSize: 22, fontWeight: 700 }}>
      <span style={{ width: 10, height: 10, borderRadius: 999, background: theme.color.amber }} />
      {label}
    </div>
  );
};

const Check: React.FC<{ on: boolean }> = ({ on }) => (
  <div style={{ width: 24, height: 24, borderRadius: 999, background: on ? theme.color.teal : "transparent", border: `2px solid ${on ? theme.color.teal : theme.color.inkFaint}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
    {on ? (
      <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="#08131f" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round"><path d="M5 12 l4 4 L19 6" /></svg>
    ) : null}
  </div>
);
