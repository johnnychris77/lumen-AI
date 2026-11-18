/**
 * P472-03 client compatibility: the regulatory, predictions, benchmarks and
 * vendor-intelligence API routes take the tenant from the signed-in user's
 * verified membership. A client that names a tenant other than the caller's own
 * is refused (HTTP 403), so no component may send a hardcoded or locally stored
 * tenant to those routes.
 */
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

const SRC = join(import.meta.dirname, "..", "src");
const ROUTE_GROUPS = [
  "/api/regulatory",
  "/api/predictions",
  "/api/enterprise/benchmarks",
  "/api/vendor-intelligence",
];

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(name) ? [path] : [];
  });
}

const callers = sourceFiles(SRC)
  .map((path) => ({ path, text: readFileSync(path, "utf8") }))
  .filter(({ text }) => ROUTE_GROUPS.some((group) => text.includes(group)));

test("the tenant-scoped route groups still have frontend callers to check", () => {
  assert.ok(callers.length >= 3, `expected at least 3 caller files, found ${callers.length}`);
});

test("no request to a tenant-scoped route group carries a tenant_id in its URL", () => {
  for (const { path, text } of callers) {
    for (const line of text.split("\n")) {
      if (!ROUTE_GROUPS.some((group) => line.includes(group))) continue;
      assert.ok(!/tenant_id/.test(line), `${path}: ${line.trim()}`);
    }
  }
});

test("callers of tenant-scoped routes hold no hardcoded or locally stored tenant", () => {
  for (const { path, text } of callers) {
    assert.ok(!/["'`](demo-tenant|default-tenant)["'`]/.test(text), `${path} hardcodes a tenant`);
    assert.ok(!/localStorage\.getItem\(["']tenant_id["']\)/.test(text), `${path} reads a stored tenant`);
    assert.ok(!/^\s*tenant_id\s*:/m.test(text.replace(/^\s*tenant_id\s*:\s*string;?\s*$/gm, "")),
      `${path} sends tenant_id in a request body`);
  }
});
