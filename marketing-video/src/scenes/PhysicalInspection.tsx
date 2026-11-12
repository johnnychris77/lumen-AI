import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Panel, Kicker } from "../components/Stage";
import { LumenImage } from "../components/LumenImage";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";
import { demo } from "../data/demo";
import { mediaSrc } from "../media";

/**
 * Scene 3 — Physical Borescope Inspection (the hero scene).
 * LEFT: the technician physically holds the instrument and advances a compatible
 * borescope probe into the lumen. RIGHT: the live internal feed appears INSIDE
 * the active LumenAI inspection; the technician captures, keeps the image
 * (Retake / Use Image), and attaches multiple representative images.
 *
 * THE TECHNICIAN performs the inspection. THE BORESCOPE provides visual access.
 * LUMENAI captures, structures, assists, and preserves the evidence.
 */
export const PhysicalInspection: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = (p: number) => durationInFrames * p;

  const appIn = reveal(frame, 4, 16);
  // Probe insertion depth 0..1 across the middle of the scene, with a brief
  // re-advance for the 2nd/3rd images near the end.
  const insert = interpolate(
    frame,
    [t(0.22), t(0.58), t(0.72), t(0.82), t(0.9), t(1)],
    [0, 1, 1, 0.7, 1, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const feedLive = frame > t(0.24);
  const captureFlash = interpolate(frame, [t(0.58), t(0.6), t(0.64)], [0, 0.85, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const useImage = frame > t(0.7);
  const attached = frame > t(0.72);

  return (
    <Stage mode="light">
      <div style={{ position: "absolute", top: 56, left: 90 }}>
        <Kicker tone="light">LumenAI · New Inspection · {demo.instrument.id}</Kicker>
        <div style={{ fontSize: 30, fontWeight: 600, color: theme.color.ink, marginTop: 6 }}>
          The technician performs the inspection.
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          left: 90,
          right: 90,
          top: 150,
          bottom: 140,
          display: "flex",
          gap: 26,
          opacity: appIn.opacity,
          transform: `translateY(${appIn.translateY}px)`,
        }}
      >
        {/* LEFT — physical workstation */}
        <div
          style={{
            width: 760,
            background: theme.color.surfaceAlt,
            border: `1px solid ${theme.color.border}`,
            borderRadius: theme.radius.lg,
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div style={{ position: "absolute", top: 18, left: 22, fontSize: 15, fontWeight: 700, letterSpacing: 2, color: theme.color.inkFaint, textTransform: "uppercase" }}>
            Physical inspection
          </div>
          <PhysicalRig insert={insert} />
          <div style={{ position: "absolute", bottom: 18, left: 22, right: 22, fontSize: 16, color: theme.color.inkSoft }}>
            Technician advances a compatible borescope probe through the instrument lumen.
          </div>
        </div>

        {/* RIGHT — LumenAI inspection */}
        <div style={{ flex: 1 }}>
          <Panel style={{ height: "100%", padding: 26, display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 600, color: theme.color.ink }}>Add Inspection Image</div>
              <StatusPill on={frame > t(0.16)} label="Capture from Borescope" />
            </div>

            {/* Live feed / captured frame */}
            <div style={{ position: "relative", alignSelf: "center", background: "#0c1119", borderRadius: 14, padding: 12 }}>
              <LumenImage size={300} depth={0.25 + insert * 0.45} showAreas={frame > t(0.54)} areaOpacity={progress(frame, t(0.54), t(0.6))} src={mediaSrc("lumenFeed")} />
              <div style={{ position: "absolute", top: 20, left: 22, display: "flex", alignItems: "center", gap: 8, color: feedLive ? theme.color.green : theme.color.inkFaint, fontSize: 15, fontWeight: 700 }}>
                <span style={{ width: 9, height: 9, borderRadius: 999, background: feedLive ? theme.color.green : theme.color.inkFaint }} />
                {feedLive ? "LIVE" : "READY"}
              </div>
              {/* capture flash */}
              <div style={{ position: "absolute", inset: 12, borderRadius: 300, background: "#fff", opacity: captureFlash }} />
            </div>

            {/* Capture controls -> Retake / Use Image -> attached */}
            <div style={{ display: "flex", justifyContent: "center", gap: 14, minHeight: 52 }}>
              {frame > t(0.6) && !attached ? (
                <>
                  <GhostButton label="Retake" />
                  <SolidButton label="Use Image" active={useImage} />
                </>
              ) : null}
              {attached ? (
                <div style={{ display: "inline-flex", alignItems: "center", gap: 10, color: theme.color.green, fontSize: 19, fontWeight: 600 }}>
                  <Check /> Image attached to inspection
                </div>
              ) : (
                frame <= t(0.6) ? (
                  <div style={{ display: "inline-flex", alignItems: "center", gap: 10, color: theme.color.inkFaint, fontSize: 17 }}>
                    Examine the surface, then capture a representative image.
                  </div>
                ) : null
              )}
            </div>

            {/* Inspection images (multiple representative images) */}
            <div style={{ marginTop: "auto" }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: theme.color.inkSoft, marginBottom: 8 }}>Inspection Images</div>
              <div style={{ display: "flex", gap: 12 }}>
                {demo.inspectionImages.map((label, i) => {
                  const on = frame > t(0.75 + i * 0.08);
                  return (
                    <div
                      key={label}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "10px 16px",
                        borderRadius: theme.radius.sm,
                        border: `1px solid ${on ? theme.color.green : theme.color.border}`,
                        background: on ? "rgba(62,158,118,0.10)" : theme.color.surface,
                        color: on ? theme.color.ink : theme.color.inkFaint,
                        fontSize: 17,
                        fontWeight: 600,
                      }}
                    >
                      {on ? <Check /> : <span style={{ width: 18, height: 18, borderRadius: 999, border: `2px solid ${theme.color.border}` }} />}
                      {label}
                    </div>
                  );
                })}
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </Stage>
  );
};

/** Stylized side view: gloved hands, the instrument, and the advancing probe. */
const PhysicalRig: React.FC<{ insert: number }> = ({ insert }) => {
  // Probe tip travels from the distal opening (right) leftward into the shaft.
  const tipX = interpolate(insert, [0, 1], [770, 250]);
  return (
    <svg width="100%" height="100%" viewBox="0 0 760 560" preserveAspectRatio="xMidYMid meet">
      {/* workstation surface */}
      <rect x="0" y="420" width="760" height="140" fill="rgba(15,27,45,0.06)" />
      {/* instrument shaft */}
      <rect x="150" y="292" width="470" height="34" rx="17" fill="#b9c3cf" />
      <rect x="150" y="296" width="470" height="7" rx="3" fill="rgba(255,255,255,0.6)" />
      {/* handle + gloved hand (left) */}
      <rect x="96" y="278" width="70" height="62" rx="14" fill="#8b97a6" />
      <ellipse cx="118" cy="309" rx="52" ry="40" fill={theme.color.primary} opacity="0.9" />
      <ellipse cx="150" cy="309" rx="30" ry="26" fill={theme.color.primaryDeep} opacity="0.9" />
      {/* distal opening */}
      <circle cx="620" cy="309" r="22" fill="#12100d" stroke="#8b97a6" strokeWidth="5" />
      {/* borescope cable entering the lumen + control grip (right, gloved) */}
      <line x1={tipX} y1="309" x2="720" y2="309" stroke="#2b3442" strokeWidth="6" strokeLinecap="round" />
      <circle cx={tipX} cy="309" r="6" fill={theme.color.teal} />
      <path d="M720 309 C 760 309, 790 240, 700 200" fill="none" stroke="#2b3442" strokeWidth="6" strokeLinecap="round" />
      <ellipse cx="690" cy="196" rx="46" ry="36" fill={theme.color.primary} opacity="0.9" />
      <rect x="650" y="150" width="80" height="40" rx="10" fill="#2b3442" />
      {/* insertion-depth marker */}
      <text x="250" y="360" fontFamily={theme.font.mono} fontSize="16" fill={theme.color.inkFaint}>
        probe · advancing
      </text>
    </svg>
  );
};

const StatusPill: React.FC<{ on: boolean; label: string }> = ({ on, label }) => (
  <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "8px 16px", borderRadius: 999, border: `2px solid ${on ? theme.color.primary : theme.color.border}`, background: on ? "rgba(46,125,175,0.10)" : theme.color.white, color: on ? theme.color.primaryDeep : theme.color.inkFaint, fontSize: 16, fontWeight: 600 }}>
    <svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke={on ? theme.color.primary : theme.color.inkFaint} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="7" width="18" height="12" rx="2" /><circle cx="12" cy="13" r="3.2" /><path d="M8 7 l1.5-2 h5 L16 7" />
    </svg>
    {label}
  </div>
);

const GhostButton: React.FC<{ label: string }> = ({ label }) => (
  <div style={{ padding: "12px 24px", borderRadius: theme.radius.md, border: `2px solid ${theme.color.border}`, color: theme.color.inkSoft, fontSize: 18, fontWeight: 600 }}>{label}</div>
);

const SolidButton: React.FC<{ label: string; active: boolean }> = ({ label, active }) => (
  <div style={{ padding: "12px 26px", borderRadius: theme.radius.md, background: active ? theme.color.primary : theme.color.primaryDeep, color: "#fff", fontSize: 18, fontWeight: 700, boxShadow: active ? theme.shadow.soft : "none", opacity: active ? 1 : 0.85 }}>{label}</div>
);

const Check: React.FC = () => (
  <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={theme.color.green} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" stroke={theme.color.green} strokeWidth={2} />
    <path d="M7 12 l3 3 L17 8" />
  </svg>
);
