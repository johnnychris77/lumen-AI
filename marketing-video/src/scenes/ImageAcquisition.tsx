import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Panel, Kicker } from "../components/Stage";
import { LumenImage } from "../components/LumenImage";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";
import { mediaSrc } from "../media";

/**
 * Scene 3 — Introduce LumenAI (0:18–0:29).
 * Image acquisition happens INSIDE the inspection workflow. "Add Inspection
 * Image" → source selector (Capture from Borescope / Upload Existing Image) →
 * a live borescope feed opens inside the same inspection. The borescope is an
 * image source, never a separate application.
 */
export const ImageAcquisition: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const t = (p: number) => durationInFrames * p;
  const appIn = reveal(frame, 4, 16);
  const selectorIn = reveal(frame, t(0.32), 12);
  const clickCapture = frame > t(0.55);
  const feedIn = reveal(frame, t(0.6), 14);
  const feedProgress = progress(frame, t(0.62), t(0.95));

  // Cursor path: to "Add Inspection Image" then to "Capture from Borescope".
  const cx = frame < t(0.32)
    ? 300 + progress(frame, t(0.1), t(0.3)) * 40
    : 300 + progress(frame, t(0.4), t(0.58)) * 250;
  const cy = frame < t(0.32)
    ? 430 + progress(frame, t(0.1), t(0.3)) * 0
    : 430 + progress(frame, t(0.4), t(0.58)) * 150;

  return (
    <Stage mode="light">
      <div style={{ position: "absolute", top: 70, left: 90 }}>
        <Kicker tone="light">LumenAI · New Inspection</Kicker>
        <div style={{ fontSize: 34, fontWeight: 600, color: theme.color.ink, marginTop: 8 }}>
          Capture where the work happens.
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          left: 90,
          right: 90,
          top: 180,
          bottom: 150,
          opacity: appIn.opacity,
          transform: `translateY(${appIn.translateY}px)`,
        }}
      >
        <Panel style={{ height: "100%", display: "flex", overflow: "hidden" }}>
          {/* Left rail */}
          <div style={{ width: 230, background: theme.color.surface, borderRight: `1px solid ${theme.color.border}`, padding: 24 }}>
            <div style={{ fontWeight: 700, color: theme.color.primaryDeep, fontSize: 20 }}>LumenAI</div>
            <div style={{ marginTop: 22, display: "flex", flexDirection: "column", gap: 12 }}>
              {["Dashboard", "New Inspection", "Inspection History", "Baselines"].map((m, i) => (
                <div
                  key={m}
                  style={{
                    fontSize: 16,
                    color: i === 1 ? theme.color.primaryDeep : theme.color.inkSoft,
                    fontWeight: i === 1 ? 700 : 500,
                    background: i === 1 ? theme.color.surfaceAlt : "transparent",
                    padding: "8px 12px",
                    borderRadius: 8,
                  }}
                >
                  {m}
                </div>
              ))}
            </div>
          </div>

          {/* Main */}
          <div style={{ flex: 1, padding: 34, position: "relative" }}>
            <div style={{ fontSize: 15, color: theme.color.inkFaint }}>Inspection / New Inspection</div>
            <div style={{ fontSize: 26, fontWeight: 600, color: theme.color.ink, marginTop: 6 }}>
              Add Inspection Image
            </div>

            {/* Add image button */}
            <div
              style={{
                marginTop: 26,
                display: "inline-flex",
                alignItems: "center",
                gap: 12,
                border: `2px dashed ${theme.color.primary}`,
                color: theme.color.primaryDeep,
                borderRadius: theme.radius.md,
                padding: "18px 26px",
                fontSize: 20,
                fontWeight: 600,
                background: "rgba(46,125,175,0.05)",
              }}
            >
              + Add Inspection Image
            </div>

            {/* Source selector */}
            <div
              style={{
                marginTop: 26,
                display: "flex",
                gap: 18,
                opacity: selectorIn.opacity,
                transform: `translateY(${selectorIn.translateY}px)`,
              }}
            >
              <SourceButton label="Capture from Borescope" active={clickCapture} icon="camera" />
              <SourceButton label="Upload Existing Image" active={false} icon="upload" />
            </div>

            {/* Live feed opens inside the inspection */}
            <div
              style={{
                marginTop: 26,
                opacity: feedIn.opacity,
                transform: `translateY(${feedIn.translateY}px)`,
                display: "flex",
                gap: 22,
                alignItems: "center",
              }}
            >
              <div style={{ background: "#0c1119", borderRadius: 14, padding: 12 }}>
                <LumenImage size={230} depth={0.3 + feedProgress * 0.35} src={mediaSrc("lumenFeed")} />
              </div>
              <div>
                <div style={{ display: "inline-flex", alignItems: "center", gap: 8, color: theme.color.green, fontWeight: 600, fontSize: 18 }}>
                  <span style={{ width: 9, height: 9, borderRadius: 999, background: theme.color.green }} />
                  Live borescope feed — inside the inspection
                </div>
                <div style={{ marginTop: 10, color: theme.color.inkSoft, fontSize: 16, maxWidth: 320 }}>
                  No separate application. The borescope is an image source; LumenAI owns the workflow.
                </div>
              </div>
            </div>

            {/* Cursor */}
            <Cursor x={cx} y={cy} pressed={clickCapture && frame < t(0.62)} />
          </div>
        </Panel>
      </div>
    </Stage>
  );
};

const SourceButton: React.FC<{ label: string; active: boolean; icon: "camera" | "upload" }> = ({ label, active, icon }) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: 12,
      padding: "16px 22px",
      borderRadius: theme.radius.md,
      border: `2px solid ${active ? theme.color.primary : theme.color.border}`,
      background: active ? "rgba(46,125,175,0.10)" : theme.color.white,
      color: active ? theme.color.primaryDeep : theme.color.ink,
      fontSize: 19,
      fontWeight: 600,
      boxShadow: active ? theme.shadow.soft : "none",
    }}
  >
    <svg width={26} height={26} viewBox="0 0 24 24" fill="none" stroke={active ? theme.color.primary : theme.color.inkSoft} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      {icon === "camera" ? (
        <>
          <rect x="3" y="7" width="18" height="12" rx="2" />
          <circle cx="12" cy="13" r="3.2" />
          <path d="M8 7 l1.5-2 h5 L16 7" />
        </>
      ) : (
        <>
          <path d="M12 16 V5" />
          <path d="M7 9 l5-5 5 5" />
          <path d="M4 18 h16" />
        </>
      )}
    </svg>
    {label}
  </div>
);

const Cursor: React.FC<{ x: number; y: number; pressed: boolean }> = ({ x, y, pressed }) => (
  <svg
    width={30}
    height={30}
    viewBox="0 0 24 24"
    style={{ position: "absolute", left: x, top: y, filter: "drop-shadow(0 2px 3px rgba(0,0,0,0.35))", transform: pressed ? "scale(0.9)" : "scale(1)" }}
  >
    <path d="M4 2 L4 20 L9 15 L12 22 L15 21 L12 14 L19 14 Z" fill="#0F1B2D" stroke="#fff" strokeWidth={1.2} strokeLinejoin="round" />
  </svg>
);
