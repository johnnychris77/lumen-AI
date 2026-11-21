/**
 * P472-03 remediation batch 1, client compatibility.
 *
 * The enterprise quality, vendor-governance and CAPA routes now require a
 * signed-in member and serve only that member's tenant:
 *
 *  - the tenant comes from the verified session, so a component must not send a
 *    hard-coded tenant header (a non-member of that tenant is refused, 403);
 *  - exports are authenticated, so they cannot be opened with a plain link or
 *    window.open (a browser navigation carries no bearer token and gets 401).
 */
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { test } from "node:test";

const SRC = join(import.meta.dirname, "..", "src");
const PROTECTED = [
  "/api/enterprise/intake",
  "/api/enterprise/executive-quality-review-dashboard",
  "/api/enterprise/export-readiness-history",
  "/api/enterprise/audit-command-center.",
  "/api/enterprise/audit/",
  "/api/enterprise/vendor-governance/",
  "/api/capa",
];

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx|js|jsx)$/.test(name) ? [path] : [];
  });
}

const files = sourceFiles(SRC).map((path) => ({ path: relative(SRC, path), text: readFileSync(path, "utf8") }));

test("no component sends a hard-coded tenant header", () => {
  for (const { path, text } of files) {
    assert.ok(!/["']X-(LumenAI-)?Tenant-(Id|Name)["']\s*:\s*["'`]/i.test(text), `${path} hard-codes a tenant header`);
  }
});

test("no protected export is opened with window.open", () => {
  for (const { path, text } of files) {
    for (const call of text.match(/window\.open\([^)]*\)/g) ?? []) {
      if (/\/health\b/.test(call)) continue;
      assert.ok(!PROTECTED.some((prefix) => call.includes(prefix)), `${path}: ${call}`);
    }
  }
});

test("links to protected exports download through the authenticated helper", () => {
  const exportUrl = /const\s+(\w+)\s*=\s*`\$\{API_BASE\}(\/api\/[^`]*)`/g;
  let checked = 0;
  for (const { path, text } of files) {
    const names = [...text.matchAll(exportUrl)]
      .filter(([, , url]) => PROTECTED.some((prefix) => url.startsWith(prefix)) && !/\/health\b/.test(url))
      .map(([, name]) => name);
    for (const name of names) {
      for (const line of text.split("\n")) {
        if (!new RegExp(`href=\\{${name}\\}`).test(line)) continue;
        checked += 1;
        assert.ok(line.includes("onProtectedLinkClick"), `${path}: plain link to ${name}`);
      }
    }
  }
  assert.ok(checked >= 7, `expected at least 7 protected links to check, found ${checked}`);
});

test("the authenticated download helper exists and uses the session token", () => {
  const api = files.find(({ path }) => path === join("lib", "api.ts"))!.text;
  assert.match(api, /export async function openProtectedFile\(/);
  assert.match(api, /apiFetch\(url, \{ raw: true \}\)/);
});
