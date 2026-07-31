#!/usr/bin/env node
/**
 * Strict `npm audit` gate with a small, DOCUMENTED allow-list.
 *
 * Fails the build on ANY high/critical advisory EXCEPT the specific GHSA IDs
 * triaged below as not applicable to this application. Every other advisory —
 * including any new one — still fails. This mirrors the repo's existing
 * pattern of `pip-audit --ignore-vuln <ID>` for a documented Python exception.
 *
 * Rationale for each entry lives here AND in
 * docs/security/FRONTEND_DEPENDENCY_AUDIT.md. Keep this list tight and revisit
 * whenever dependencies change.
 *
 * Run from the `frontend/` directory: `node scripts/audit-allowlist.mjs`.
 */
import { execSync } from "node:child_process";

/** GHSA id -> justification. Only advisories that provably do not apply. */
const ALLOWLIST = new Map([
  [
    "GHSA-qwww-vcr4-c8h2",
    "React Router 'RSC Mode CSRF Bypass'. Applies ONLY to React Router's RSC/" +
      "server framework mode; LumenAI's frontend is a client SPA using " +
      "BrowserRouter and never runs RSC mode, so the vulnerable path is " +
      "unreachable. Patched only in react-router core 8.3.0 — there is no " +
      "react-router-dom 8.x (v8 drops the package), so clearing it requires a " +
      "v7->v8 migration. Re-evaluate when a 7.x backport or react-router-dom " +
      "8.x ships. See docs/security/FRONTEND_DEPENDENCY_AUDIT.md.",
  ],
]);

const BLOCKING = new Set(["high", "critical"]);

function runAudit() {
  try {
    return execSync("npm audit --json", { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
  } catch (err) {
    // npm audit exits non-zero when advisories exist; the JSON is still emitted.
    if (err && err.stdout) return err.stdout.toString();
    throw err;
  }
}

let report;
try {
  report = JSON.parse(runAudit());
} catch (err) {
  console.error("audit-allowlist: could not run/parse `npm audit --json`:", err.message);
  process.exit(2);
}

const idFromUrl = (url) => {
  const m = typeof url === "string" ? url.match(/GHSA-[0-9a-z-]+/i) : null;
  return m ? m[0] : null;
};

const unlisted = new Map();
const ignored = new Map();

for (const vuln of Object.values(report.vulnerabilities || {})) {
  for (const via of vuln.via || []) {
    // String `via` entries are references to another vulnerable package and
    // carry no advisory URL of their own — skip; the real advisory is counted
    // on the package that owns it.
    if (typeof via !== "object" || !via.url) continue;
    if (!BLOCKING.has(via.severity)) continue;
    const id = idFromUrl(via.url) || via.url;
    const entry = { id, title: via.title, severity: via.severity, url: via.url };
    (id && ALLOWLIST.has(id) ? ignored : unlisted).set(id, entry);
  }
}

if (ignored.size) {
  console.log("Documented, allow-listed advisories (NOT failing the build):");
  for (const e of ignored.values()) {
    console.log(`  - ${e.severity} ${e.id}: ${e.title}`);
    console.log(`      reason: ${ALLOWLIST.get(e.id)}`);
  }
}

if (unlisted.size) {
  console.error("\nHigh/critical advisories NOT on the allow-list — FAILING:");
  for (const e of unlisted.values()) {
    console.error(`  - ${e.severity} ${e.id}: ${e.title} (${e.url})`);
  }
  console.error(
    "\nFix them (`npm audit`), or — only if provably inapplicable — triage " +
      "explicitly in frontend/scripts/audit-allowlist.mjs and " +
      "docs/security/FRONTEND_DEPENDENCY_AUDIT.md.",
  );
  process.exit(1);
}

console.log("\naudit-allowlist: no unlisted high/critical advisories. Gate passes.");
process.exit(0);
