import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { SCENE_WINDOWS, SceneId } from "../timing";
import { Caption } from "../components/Caption";

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

/** Scenes rendered on a light background get a light-toned caption. */
const LIGHT_SCENES: ReadonlySet<SceneId> = new Set<SceneId>(["ImageAcquisition"]);

/** The Closing scene carries its own lockup text — no burned-in caption. */
const NO_CAPTION: ReadonlySet<SceneId> = new Set<SceneId>(["Closing"]);

export const LumenAIExplainer: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0A0E17" }}>
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
            {NO_CAPTION.has(win.id) ? null : (
              <Caption
                text={win.caption}
                durationInFrames={win.durationInFrames}
                tone={LIGHT_SCENES.has(win.id) ? "light" : "dark"}
              />
            )}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
