/**
 * Codemod: route raw `fetch(`${API_BASE}...`)` calls through the central
 * `apiFetch` client, conservatively.
 *
 * Strategy — minimize behavioral change:
 *   1. Replace `fetch(` with `apiFetch(` ONLY where the first argument uses
 *      `${API_BASE}` (i.e. a call to our own backend). Relative "/api/..."
 *      fetches and third-party fetches are left alone.
 *   2. Strip the `${API_BASE}` prefix from the URL (apiFetch prepends the base).
 *   3. Pass `{ raw: true }` so the existing `response.ok` / `response.json()`
 *      handling in each component keeps working verbatim — we are NOT rewriting
 *      each call's response logic, only who builds the request.
 *   4. Remove now-redundant per-file `const API_BASE = ...` declarations.
 *   5. Ensure `import { apiFetch } from "@/lib/api";` is present.
 *
 * apiFetch still attaches Authorization/role/actor centrally, so leftover
 * hand-built auth headers are harmless (apiFetch won't overwrite an explicitly
 * provided header, and duplicate identity headers are ignored by the backend,
 * which resolves identity from the token). A follow-up pass can delete them.
 *
 * SKIPPED (auth model or response model differs — must stay raw):
 *   - pages/LoginPage.tsx          unauthenticated login POST
 *   - pages/StationPage.tsx        kiosk device-key auth (X-Device-Key), not user token
 *   - pages/GlobalInfrastructureConsole.tsx  streaming/body-reader response
 *   - lib/api.ts, lib/auth.tsx     the client itself
 *   - components/EnterpriseAuditTrailPanel.tsx  already migrated by hand
 */
const fs = require("fs");
const path = require("path");

const ROOT = process.env.CODEMOD_ROOT
  ? path.resolve(process.env.CODEMOD_ROOT)
  : path.resolve(__dirname, "..", "src");

const SKIP = new Set(
  [
    "pages/LoginPage.tsx",
    "pages/StationPage.tsx",
    "pages/GlobalInfrastructureConsole.tsx",
    "lib/api.ts",
    "lib/auth.tsx",
    "lib/notifications.tsx", // relative "/api" + own header var; convert separately
    "components/EnterpriseAuditTrailPanel.tsx",
  ].map((p) => path.join(ROOT, p))
);

function walk(dir, acc = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, acc);
    else if (/\.(t|j)sx?$/.test(entry.name) && !/\.test\./.test(entry.name)) acc.push(full);
  }
  return acc;
}

const changed = [];
const skippedNoApiBase = [];

for (const file of walk(ROOT)) {
  if (SKIP.has(file)) continue;
  let src = fs.readFileSync(file, "utf8");
  const original = src;

  // Only touch files that call our backend via ${API_BASE}.
  if (!/fetch\(\s*`?\$\{API_BASE\}/.test(src)) {
    if (/\bfetch\(/.test(src)) skippedNoApiBase.push(file);
    continue;
  }

  // 1+2+3: fetch(`${API_BASE}<url>`<rest>) -> apiFetch(`<url>`<rest>, { raw:true })
  // Handle both single-arg and two-arg (options object) forms.
  //
  //   fetch(`${API_BASE}/api/x`)            -> apiFetch(`/api/x`, { raw: true })
  //   fetch(`${API_BASE}/api/x`, { ... })   -> apiFetch(`/api/x`, { ... , raw: true })
  //
  // Strip the ${API_BASE} token inside the template literal first.
  src = src.replace(/fetch\(\s*`\$\{API_BASE\}/g, "apiFetch(`");

  // Some callers use string concat: fetch(API_BASE + "/api/x", ...)
  src = src.replace(/fetch\(\s*API_BASE\s*\+\s*/g, "apiFetch(");

  // Inject raw:true into the options object of the calls we just rewrote.
  // We do a targeted parse: find each `apiFetch(` we produced and ensure its
  // options object carries raw:true. To stay safe, only add when an options
  // object literal is present; single-arg calls get a `, { raw: true }`.
  src = injectRawOption(src);

  let needsApiBaseImport = false;

  // 4: remove the local API_BASE declaration ONLY if nothing else in the file
  // still references API_BASE (many files use it for <a href>, window.open, or
  // export-URL builders that we did NOT rewrite). If other references remain,
  // repoint the declaration at the central API_BASE instead of deleting it.
  const declRe = /^\s*const\s+API_BASE\s*=\s*[\s\S]*?;\s*$/m;
  if (declRe.test(src)) {
    const withoutDecl = src.replace(declRe, "__API_BASE_DECL_REMOVED__");
    const stillReferenced = /\bAPI_BASE\b/.test(
      withoutDecl.replace("__API_BASE_DECL_REMOVED__", "")
    );
    if (stillReferenced) {
      // Keep a single source of truth: import API_BASE from the central client.
      src = src.replace(declRe, "");
      needsApiBaseImport = true;
    } else {
      src = src.replace(declRe, "");
    }
  }

  // 5: ensure the import exists, including API_BASE when the file still needs it.
  const importSymbols = needsApiBaseImport ? "apiFetch, API_BASE" : "apiFetch";
  if (!/from\s+["']@\/lib\/api["']/.test(src)) {
    src = addImport(src, `import { ${importSymbols} } from "@/lib/api";`);
  } else {
    // import line exists — make sure it includes the symbols we need.
    src = src.replace(
      /import\s*\{([^}]*)\}\s*from\s*["']@\/lib\/api["'];/,
      (m, inner) => {
        const have = inner.split(",").map((s) => s.trim()).filter(Boolean);
        for (const sym of ["apiFetch", ...(needsApiBaseImport ? ["API_BASE"] : [])]) {
          if (!have.includes(sym)) have.push(sym);
        }
        return `import { ${have.join(", ")} } from "@/lib/api";`;
      }
    );
  }

  if (src !== original) {
    fs.writeFileSync(file, src, "utf8");
    changed.push(path.relative(ROOT, file));
  }
}

/**
 * For every `apiFetch(` produced above, make sure raw:true is passed. We scan
 * from each occurrence, find the matching close paren of the call, and inspect
 * whether a second argument (options object) is present.
 */
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
    // Walk the argument list to the matching close paren.
    let depth = 1;
    let j = idx + NEEDLE.length;
    let inStr = null;
    let commaTop = -1; // index of top-level comma separating args
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
    // code[idx..j] is the full apiFetch(...) call; j points at close paren.
    const call = code.slice(idx + NEEDLE.length, j);
    let newCall;
    if (commaTop === -1) {
      // single argument -> add options object
      newCall = `${call}, { raw: true }`;
    } else {
      // has an options object as 2nd arg -> insert raw:true after its opening {
      const before = code.slice(idx + NEEDLE.length, commaTop + 1);
      const after = code.slice(commaTop + 1, j);
      const braceIdx = after.indexOf("{");
      if (braceIdx !== -1) {
        newCall =
          before +
          after.slice(0, braceIdx + 1) +
          " raw: true," +
          after.slice(braceIdx + 1);
      } else {
        // 2nd arg isn't an object literal (e.g. a variable) — leave as-is.
        newCall = call;
      }
    }
    out += newCall + ")";
    i = j + 1;
  }
  return out;
}

function addImport(code, importLine) {
  const lines = code.split("\n");
  // Find the end of the top-of-file import block. A named import can span
  // multiple lines (`import {\n ... \n} from "x";`), so we track when we're
  // inside a brace group and only treat a line as "end of an import statement"
  // when it terminates with `;` (or is a single-line import) at brace depth 0.
  let lastImportEnd = -1;
  let depth = 0;
  let sawImport = false;
  for (let k = 0; k < lines.length; k++) {
    const line = lines[k];
    const trimmed = line.trim();
    if (depth === 0 && /^import\b/.test(trimmed)) {
      sawImport = true;
    }
    if (sawImport) {
      for (const ch of line) {
        if (ch === "{") depth++;
        else if (ch === "}") depth = Math.max(0, depth - 1);
      }
      if (depth === 0 && /;\s*$/.test(trimmed)) {
        lastImportEnd = k;
        sawImport = false;
      } else if (depth === 0 && trimmed === "") {
        // stray blank inside scan; ignore
      }
    } else if (lastImportEnd !== -1 && trimmed !== "" && !/^import\b/.test(trimmed)) {
      break; // reached first non-import statement
    }
  }
  if (lastImportEnd === -1) return importLine + "\n" + code;
  lines.splice(lastImportEnd + 1, 0, importLine);
  return lines.join("\n");
}

console.log(`Changed ${changed.length} files:`);
changed.forEach((f) => console.log("  " + f));
console.log(`\nSkipped (raw fetch but no ${"$"}{API_BASE}, review manually): ${skippedNoApiBase.length}`);
skippedNoApiBase.forEach((f) => console.log("  " + path.relative(ROOT, f)));
