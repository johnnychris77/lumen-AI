/**
 * LumenAI explainer — design tokens.
 *
 * Visual standard: "Apple product film + enterprise healthcare technology".
 * Restrained, clinical, cinematic. Dark charcoal for cinematic scenes; bright
 * clinical panels for UI scenes. No neon, no sci-fi.
 */
export const theme = {
  color: {
    // Cinematic / dark
    charcoal: "#0A0E17",
    charcoal2: "#0E1420",
    charcoalPanel: "#141C2B",
    // Clinical / light UI
    white: "#FFFFFF",
    surface: "#F5F8FC",
    surfaceAlt: "#EAF0F7",
    border: "#D8E1EC",
    // Ink
    ink: "#0F1B2D",
    inkSoft: "#3C4B60",
    inkFaint: "#7E8CA0",
    // Brand accents (restrained clinical blue + teal)
    primary: "#2E7DAF",
    primaryDeep: "#1E5C86",
    teal: "#3BB6A6",
    tealDeep: "#2A8C80",
    // Status
    amber: "#D9A441",
    green: "#3E9E76",
    // On-dark text
    onDark: "#EAF1FA",
    onDarkSoft: "#9FB0C6",
  },
  font: {
    // System UI stack — no external font fetch (self-contained render).
    sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: '"SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace',
  },
  radius: {
    sm: 8,
    md: 14,
    lg: 22,
    pill: 999,
  },
  shadow: {
    panel: "0 24px 60px rgba(8, 16, 30, 0.28)",
    card: "0 12px 30px rgba(8, 16, 30, 0.16)",
    soft: "0 6px 18px rgba(8, 16, 30, 0.12)",
  },
} as const;

export type Theme = typeof theme;
