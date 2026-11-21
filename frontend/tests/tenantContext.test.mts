/**
 * P472-03 Batch 5 (B5.1) — session tenant context.
 *
 *   node --test --experimental-strip-types tests/tenantContext.test.mts
 *
 * Part 1 exercises the pure contract in src/lib/tenantContext.ts: the client
 * acts only in a tenant the SERVER listed for the signed-in user; a stored or
 * forged value is never authority. Part 2 audits the whole source tree for the
 * patterns that caused the AccreditationConsole 403 regression: hard-coded
 * tenants, locally stored tenants, editable tenant fields, and hard-coded
 * credentials.
 */
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { test } from "node:test";

import {
  chooseTenant,
  isTenantDenial,
  parseSessionTenants,
  readStoredTenant,
  reconcileTenantSelection,
  selectedTenantOf,
  TENANT_HEADER,
  TENANT_STORAGE_KEY,
  tenantHeaders,
  writeStoredTenant,
  type StorageLike,
} from "../src/lib/tenantContext.ts";

function memoryStorage(initial: Record<string, string> = {}): StorageLike & { data: Record<string, string> } {
  const data = { ...initial };
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = v; },
    removeItem: (k) => { delete data[k]; },
  };
}

const single = { memberships: [{ tenant_id: "hosp-a", role: "tenant_admin" }], active_tenant_id: "hosp-a", selection_required: false };
const multi = {
  memberships: [{ tenant_id: "hosp-a", role: "viewer" }, { tenant_id: "hosp-c", role: "tenant_admin" }],
  active_tenant_id: null,
  selection_required: true,
};
const none = { memberships: [], active_tenant_id: null, selection_required: false };

// ── Part 1: contract ─────────────────────────────────────────────────────────

test("single-membership user acts in their only tenant", () => {
  const { state, store } = reconcileTenantSelection(parseSessionTenants(single), null);
  assert.deepEqual(state, { status: "selected", tenantId: "hosp-a", options: ["hosp-a"] });
  assert.equal(store, "hosp-a");
  assert.deepEqual(tenantHeaders(selectedTenantOf(state)), { [TENANT_HEADER]: "hosp-a" });
});

test("multi-membership user must choose; nothing is guessed", () => {
  const { state, store } = reconcileTenantSelection(parseSessionTenants(multi), null);
  assert.equal(state.status, "selection_required");
  assert.equal(store, null);
  assert.equal(selectedTenantOf(state), null);
  assert.deepEqual(tenantHeaders(selectedTenantOf(state)), {}, "no tenant header until the user chooses");
  const chosen = chooseTenant(state, "hosp-c");
  assert.equal(selectedTenantOf(chosen), "hosp-c");
});

test("a previous choice is kept only while the server still lists it", () => {
  assert.equal(selectedTenantOf(reconcileTenantSelection(parseSessionTenants(multi), "hosp-c").state), "hosp-c");
  // stale (membership revoked) or forged in storage → discarded, user must choose again
  for (const stale of ["hosp-b", "default-tenant", "demo-tenant"]) {
    const { state, store } = reconcileTenantSelection(parseSessionTenants(multi), stale);
    assert.equal(state.status, "selection_required", stale);
    assert.equal(store, null, stale);
  }
});

test("a single-membership user's forged stored tenant is replaced by the verified one", () => {
  const { state } = reconcileTenantSelection(parseSessionTenants(single), "hosp-b");
  assert.equal(selectedTenantOf(state), "hosp-a");
});

test("a user with no membership gets no tenant at all", () => {
  const { state, store } = reconcileTenantSelection(parseSessionTenants(none), "default-tenant");
  assert.equal(state.status, "none");
  assert.equal(store, null);
  assert.deepEqual(tenantHeaders(selectedTenantOf(state)), {});
});

test("choosing a tenant the server did not list is refused", () => {
  const { state } = reconcileTenantSelection(parseSessionTenants(multi), null);
  assert.throws(() => chooseTenant(state, "hosp-b"), /not one of your memberships/);
  assert.throws(() => chooseTenant({ status: "loading" }, "hosp-a"));
  assert.throws(() => chooseTenant({ status: "none", options: [] }, "hosp-a"));
});

test("malformed or inconsistent server responses fail closed", () => {
  for (const bad of [
    null,
    "hosp-a",
    {},
    { memberships: "hosp-a" },
    { memberships: [{ tenant_id: "", role: "x" }] },
    { memberships: [{ tenant_id: "a b", role: "x" }] },
    { memberships: [{ tenant_id: "hosp-a" }] },
    { memberships: [{ tenant_id: "hosp-a", role: "x" }], active_tenant_id: "hosp-b" },
  ]) {
    assert.throws(() => parseSessionTenants(bad), JSON.stringify(bad));
  }
});

test("duplicate memberships collapse; header value is never empty", () => {
  const parsed = parseSessionTenants({
    memberships: [{ tenant_id: "hosp-a", role: "x" }, { tenant_id: "hosp-a", role: "y" }],
    active_tenant_id: "hosp-a",
    selection_required: false,
  });
  assert.equal(parsed.memberships.length, 1);
  assert.deepEqual(tenantHeaders(""), {});
  assert.deepEqual(tenantHeaders(null), {});
});

test("stored selection: only well-formed ids are read back; storage errors are tolerated", () => {
  const storage = memoryStorage();
  writeStoredTenant(storage, "hosp-a");
  assert.equal(storage.data[TENANT_STORAGE_KEY], "hosp-a");
  assert.equal(readStoredTenant(storage), "hosp-a");
  writeStoredTenant(storage, null);
  assert.equal(readStoredTenant(storage), null);
  assert.equal(readStoredTenant(memoryStorage({ [TENANT_STORAGE_KEY]: "<script>" })), null);
  const broken: StorageLike = {
    getItem: () => { throw new Error("denied"); },
    setItem: () => { throw new Error("denied"); },
    removeItem: () => { throw new Error("denied"); },
  };
  assert.equal(readStoredTenant(broken), null);
  assert.doesNotThrow(() => writeStoredTenant(broken, "hosp-a"));
});

test("a 403 naming the tenant is recognised as a stale selection", () => {
  assert.equal(isTenantDenial(403, "Tenant access denied."), true);
  assert.equal(isTenantDenial(403, "Enabled tenant membership required."), true);
  assert.equal(isTenantDenial(403, "Insufficient role"), false);
  assert.equal(isTenantDenial(401, "tenant"), false);
});

// ── Part 2: source audit ─────────────────────────────────────────────────────

const SRC = join(import.meta.dirname, "..", "src");
function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name) ? [path] : [];
  });
}
const FILES = sourceFiles(SRC).map((path) => ({
  path: relative(SRC, path),
  // strip comments so explanatory notes do not trip the audit
  code: readFileSync(path, "utf8").replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1"),
}));

test("no hard-coded tenant is used anywhere in the client", () => {
  for (const { path, code } of FILES) {
    assert.ok(!/["'`](default-tenant|demo-tenant|current-tenant)["'`]/.test(code), `${path} hard-codes a tenant`);
  }
});

test("no tenant is read from or written to ad-hoc storage keys", () => {
  for (const { path, code } of FILES) {
    assert.ok(!/localStorage\.(getItem|setItem)\(\s*["'](tenant_id|tenantId|tenant)["']/.test(code), `${path} uses a stored tenant`);
  }
});

test("no editable input is bound to a tenant id", () => {
  for (const { path, code } of FILES) {
    assert.ok(!/<Input[^>]*value=\{\s*tenant(Id)?\s*\}/.test(code), `${path} lets the user type a tenant`);
    assert.ok(!/setTenant(Id)?\(e\.target\.value\)/.test(code), `${path} sets the tenant from a text field`);
  }
});

test("no hard-coded credential fallback (dev-token) exists in the client", () => {
  for (const { path, code } of FILES) {
    assert.ok(!/["'`]dev-token["'`]/.test(code), `${path} falls back to a hard-coded dev token`);
  }
});

test("the consoles fixed in B5.1 act only inside a verified tenant", () => {
  for (const file of [
    "pages/AccreditationConsole.tsx",
    "pages/NetworkIntelligenceConsole.tsx",
    "pages/AutonomousOperationsConsole.tsx",
    "components/VendorIntelligenceDashboard.tsx",
  ]) {
    const entry = FILES.find((f) => f.path === file);
    assert.ok(entry, file);
    assert.ok(/<RequireTenant>/.test(entry.code), `${file} must render inside <RequireTenant>`);
  }
});

test("the central client attaches the verified selection and nothing else", () => {
  const api = FILES.find((f) => f.path === "lib/api.ts");
  assert.ok(api);
  assert.ok(/tenantHeaders\(selectedTenant\)/.test(api.code));
  assert.ok(!/localStorage[^\n]*tenant/i.test(api.code), "api.ts must not read a tenant from storage");
});
