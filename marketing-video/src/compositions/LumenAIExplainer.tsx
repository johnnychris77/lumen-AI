import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { SCENE_WINDOWS, SceneId } from "../timing";
import { DESIGN_HEIGHT, DESIGN_WIDTH, useFormat } from "../format";
import { CaptionTrack } from "../components/CaptionTrack";
import { BrandFurniture } from "../components/BrandFurniture";
import { theme } from "../theme";
import { AudioBed } from "../audio";

import { HiddenSurface } from "../scenes/HiddenSurface";
import { SPDReality } from "../scenes/SPDReality";
import { ImageAcquisition } from "../scenes/ImageAcquisition";
import { UniversalCapture } from "../scenes/UniversalCapture";
import { IntelligencePipeline } from "../scenes/IntelligencePipeline";
import { HumanReview } from "../scenes/HumanReview";
import { EvidenceGovernance } from "../scenes/EvidenceGovernance";
import { BaselineEcosystem } from "../scenes/BaselineEcosystem";
import { OperationalIntelligence } from "../scenes/OperationalIntelligence";
import { Closing } from "../scenes/Closing";

const SCENE_COMPONENTS: Record<SceneId, React.FC> = {
  HiddenSurface,
  SPDReality,
  ImageAcquisition,
  UniversalCapture,
  IntelligencePipeline,
  HumanReview,
  EvidenceGovernance,
  BaselineEcosystem,
  OperationalIntelligence,
  Closing,
};

/**
 * One composition, three deliveries. Scenes are authored at 1920×1080 and drawn
 * into a scaled "design band"; square/vertical center that band on a charcoal
 * frame with format-aware captions + brand furniture (see src/format.ts). Audio
 * is an optional layer that is inert until real assets are supplied (src/audio.ts).
 */
export const LumenAIExplainer: React.FC = () => {
  const fmt = useFormat();

  return (
    <AbsoluteFill style={{ backgroundColor: theme.color.charcoal }}>
      {/* Scaled 1920×1080 design band */}
      <div
        style={{
          position: "absolute",
          top: fmt.bandTop,
          left: 0,
          width: DESIGN_WIDTH,
          height: DESIGN_HEIGHT,
          transform: `scale(${fmt.scale})`,
          transformOrigin: "top left",
          overflow: "hidden",
        }}
      >
        {SCENE_WINDOWS.map((win) => {
          const SceneComponent = SCENE_COMPONENTS[win.id];
          return (
            <Sequence
              key={win.id}
              from={win.from}
              durationInFrames={win.durationInFrames}
              name={`${win.index + 1}. ${win.id}`}
            >
              <SceneComponent />
            </Sequence>
          );
        })}
      </div>

      {/* Format-aware overlays (composition space, not scaled) */}
      <BrandFurniture fmt={fmt} />
      <CaptionTrack fmt={fmt} />

      {/* Optional audio bed / VO — inert until assets are supplied. */}
      <AudioBed />
    </AbsoluteFill>
  );
};
