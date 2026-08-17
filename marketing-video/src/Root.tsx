import React from "react";
import { Composition } from "remotion";
import { LumenAIExplainer } from "./compositions/LumenAIExplainer";
import { FPS, SIZES, TOTAL_FRAMES } from "./timing";

/**
 * Three delivery sizes share one composition, driven by centralized timing:
 *  - 1920×1080 landscape (primary — website / YouTube)
 *  - 1080×1080 square (LinkedIn / social)
 *  - 1080×1920 vertical (stories / vertical social)
 *
 * The scenes are laid out for landscape; square/vertical scale the same content
 * (see the production guide for the crop-safe note).
 */
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id={SIZES.landscape.id}
        component={LumenAIExplainer}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={SIZES.landscape.width}
        height={SIZES.landscape.height}
      />
      <Composition
        id={SIZES.square.id}
        component={LumenAIExplainer}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={SIZES.square.width}
        height={SIZES.square.height}
      />
      <Composition
        id={SIZES.vertical.id}
        component={LumenAIExplainer}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={SIZES.vertical.width}
        height={SIZES.vertical.height}
      />
    </>
  );
};
