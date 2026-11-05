import { Config } from "@remotion/cli/config";

/**
 * Remotion project config. This project is intentionally isolated from the
 * LumenAI application build — it has its own package.json and node_modules.
 */
Config.setVideoImageFormat("jpeg");
Config.setConcurrency(2);
Config.setChromiumOpenGlRenderer("angle");
Config.overrideWebpackConfig((config) => config);

/**
 * In this container a Chromium is pre-installed by Playwright and Remotion is
 * pointed at it so no browser download is attempted at render time. Override
 * with the REMOTION_BROWSER_EXECUTABLE env var if the path differs.
 */
const browser = process.env.REMOTION_BROWSER_EXECUTABLE;
if (browser) {
  Config.setBrowserExecutable(browser);
}
