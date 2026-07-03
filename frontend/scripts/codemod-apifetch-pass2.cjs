/**
 * Second codemod pass — the stragglers the first pass intentionally skipped:
 *
 *   (a) files that alias the base URL to a local name (`${BASE}`, `${API}`,
 *       `${base}`) instead of `${API_BASE}`,
 *   (b) relative `fetch("/api/...")` / `fetch(`/api/...`)` calls, and
 *   (c) `fetch(<urlVariable>)` where the URL is pre-built (absolute) — safe to
 *       route through apiFetch because it passes absolute URLs through and just
 *       attaches auth.
 *
 * Same conservative contract as pass 1: fetch -> apiFetch with { raw: true },
 * response handling untouched. Runs ONLY on an explicit allow-list so it can't
 * touch the kiosk/streaming/login files.
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "src");

// Explicit allow-list of straggler files (relative to src/).
const FILES = [
  "components/DigitalTwinDashboard.tsx",
  "components/InspectionCopilotDashboard.tsx",
  "components/PredictiveAnalyticsDashboard.tsx",
  "components/UpgradeModal.tsx",
  "components/CVInspectionDashboard.tsx",
  "components/EnterpriseAuditCommandCenter.tsx",
  "components/EnterpriseIntakeHistoryPanel.tsx",
  "components/PowerBiExecutiveAnalyticsCards.jsx",
  "components/PacketActionButtonsPanel.tsx",
  "pages/AutonomousOperationsConsole.tsx",
  "pages/BaselineReadinessPage.tsx",
  "pages/ExecutiveAdoptionPage.tsx",
  "pages/GoLiveCenterPage.tsx",
  "pages/GlobalIntelligenceConsole.tsx",
  "pages/GlobalStandardsConsole.tsx",
  "pages/ImageQualityPage.tsx",
  "pages/InspectionReadinessPage.tsx",
  "pages/NetworkDashboardPage.tsx",
  "pages/QualityIntelligencePage.tsx",
  "pages/TrainingCompliancePage.tsx",
  "pages/ValueRealizationPage.tsx",
];

// Reuse pass-1's raw-option injector by requiring it would export it; instead
// inline a copy (kept identical) to avoid coupling the two scripts.
function injectRawOption(code) {
  let out = "";
  let i = 0;
  const NEEDLE = "apiFetch(";
  while (i < code.length) {
    const idx = code.indexOf(NEEDLE, i);
    if (idx === -1) {
      out += code.slice(i);
      break;
    }
    out += code.slice(i, idx + NEEDLE.length);
    let depth = 1;
    let j = idx + NEEDLE.length;
    let inStr = null;
    let commaTop = -1;
    let tmpl = 0;
    while (j < code.length && depth > 0) {
      const c = code[j];
      const prev = code[j - 1];
      if (inStr) {
        if (c === inStr && prev !== "\\") inStr = null;
      } else if (c === "`") {
        tmpl ^= 1;
      } else if (!tmpl && (c === '"' || c === "'")) {
        inStr = c;
      } else if (!tmpl) {
        if (c === "(" || c === "{" || c === "[") depth++;
        else if (c === ")" || c === "}" || c === "]") depth--;
        else if (c === "," && depth === 1 && commaTop === -1) commaTop = j;
      }
      if (depth === 0) break;
      j++;
    }
    const call = code.slice(idx + NEEDLE.length, j);
    let newCall;
    if (commaTop === -1) {
      newCall = `${call}, { raw: true }`;
    } else {
      const before = code.slice(idx + NEEDLE.length, commaTop + 1);
      const after = code.slice(commaTop + 1, j);
      const braceIdx = after.indexOf("{");
      if (braceIdx !== -1) {
        newCall =
          before + after.slice(0, braceIdx + 1) + " raw: true," + after.slice(braceIdx + 1);
      } else {
        newCall = call;
      }
    }
    out += newCall + ")";
    i = j + 1;
  }
  return out;
}

function ensureImport(code) {
  if (/from\s+["']@\/lib\/api["']/.test(code)) {
    if (!/\bapiFetch\b/.test(code.match(/import\s*\{[^}]*\}\s*from\s*["']@\/lib\/api["'];/)?.[0] || "")) {
      return code.replace(
        /import\s*\{([^}]*)\}\s*from\s*["']@\/lib\/api["'];/,
        (m, inner) => {
          const have = inner.split(",").map((s) => s.trim()).filter(Boolean);
          if (!have.includes("apiFetch")) have.push("apiFetch");
          return `import { ${have.join(", ")} } from "@/lib/api";`;
        }
      );
    }
    return code;
  }
  // add a new import after the import block
  const lines = code.split("\n");
  let end = -1, depth = 0, sawImport = false;
  for (let k = 0; k < lines.length; k++) {
    const t = lines[k].trim();
    if (depth === 0 && /^import\b/.test(t)) sawImport = true;
    if (sawImport) {
      for (const ch of lines[k]) {
        if (ch === "{") depth++;
        else if (ch === "}") depth = Math.max(0, depth - 1);
      }
      if (depth === 0 && /;\s*$/.test(t)) { end = k; sawImport = false; }
    } else if (end !== -1 && t !== "" && !/^import\b/.test(t)) break;
  }
  const imp = `import { apiFetch } from "@/lib/api";`;
  if (end === -1) return imp + "\n" + code;
  lines.splice(end + 1, 0, imp);
  return lines.join("\n");
}

const changed = [];
for (const rel of FILES) {
  const file = path.join(ROOT, rel);
  if (!fs.existsSync(file)) {
    console.log("MISSING (skipped): " + rel);
    continue;
  }
  let src = fs.readFileSync(file, "utf8");
  const before = src;

  // (a) aliased template bases -> strip the ${ALIAS} prefix
  src = src.replace(/(?<!api)fetch\(\s*`\$\{(?:BASE|API|base)\}/g, "apiFetch(`");
  // (a') string-concat alias: fetch(BASE + "/api/...") / fetch(API + ...)
  src = src.replace(/(?<!api)fetch\(\s*(?:BASE|API|base)\s*\+\s*/g, "apiFetch(");
  // (b) relative string fetches -> apiFetch (base prepended by client)
  src = src.replace(/(?<!api)fetch\(\s*(["'`])\/api/g, "apiFetch($1/api");
  // (c) fetch(<urlVariable or builderCall>) -> apiFetch(...)  [absolute URLs
  //     pass through the client]. Match a bare identifier / call / member as
  //     the first arg (NOT a string/template already handled above).
  src = src.replace(
    /(?<!api)fetch\(\s*([A-Za-z_$][\w$]*(?:\([^()]*\))?)/g,
    "apiFetch($1"
  );

  if (src === before) continue;

  src = injectRawOption(src);
  src = ensureImport(src);

  if (src !== before) {
    fs.writeFileSync(file, src, "utf8");
    changed.push(rel);
  }
}

console.log(`Pass 2 changed ${changed.length} files:`);
changed.forEach((f) => console.log("  " + f));
