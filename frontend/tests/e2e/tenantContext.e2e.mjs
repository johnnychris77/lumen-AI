/**
 * P472-03 Batch 5 (B5.1) — authenticated browser test of the tenant contract.
 *
 * Drives the real login form and the Accreditation console in Chromium against
 * a real LumenAI backend seeded by backend/scripts/e2e_seed_tenant_context.py.
 * Not part of `npm test` (it needs both servers running). Run:
 *
 *   # backend (throw-away DB)
 *   E2E_PASSWORD=... DATABASE_URL=sqlite:////tmp/e2e.db python scripts/e2e_seed_tenant_context.py
 *   APP_ENV=development DATABASE_URL=sqlite:////tmp/e2e.db uvicorn app.main:app --port 8000
 *   # frontend
 *   VITE_API_BASE_URL=http://127.0.0.1:8000 npx vite --port 5173 --strictPort
 *   # test
 *   E2E_PASSWORD=... APP_URL=http://127.0.0.1:5173 node tests/e2e/tenantContext.e2e.mjs
 *
 * Checks, for every API request the page makes to a tenant-scoped route:
 *   * the X-Tenant-Id header is one of the user's verified memberships,
 *   * any tenant_id query/body claim equals that header,
 *   * no request is answered 403,
 * plus: multi-member users must choose before anything is requested, a forged
 * stored tenant is ignored, a user with no membership is told so and nothing
 * tenant-scoped is requested, and tenants do not see each other's records.
 */
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const APP = process.env.APP_URL || "http://127.0.0.1:5173";
const PASSWORD = process.env.E2E_PASSWORD;
if (!PASSWORD) throw new Error("set E2E_PASSWORD (same value used by the seed script)");

const SCOPED = /\/api\/(accreditation|auth\/tenants)/;
const results = [];

async function session(browser, email, { storedTenant } = {}) {
  const context = await browser.newContext();
  if (storedTenant) {
    await context.addInitScript((value) => {
      try { window.localStorage.setItem("lumenai.selectedTenant", value); } catch { /* ignore */ }
    }, storedTenant);
  }
  const page = await context.newPage();
  const requests = [];
  page.on("response", async (response) => {
    const request = response.request();
    const url = new URL(request.url());
    if (!SCOPED.test(url.pathname)) return;
    let bodyClaim = null;
    try { bodyClaim = JSON.parse(request.postData() || "null")?.tenant_id ?? null; } catch { /* not JSON */ }
    // Record synchronously (assertions may run right after the response
    // arrives); the parsed body is filled in when it is ready.
    const entry = {
      method: request.method(),
      path: url.pathname,
      header: request.headers()["x-tenant-id"] ?? null,
      queryClaim: url.searchParams.get("tenant_id"),
      bodyClaim,
      status: response.status(),
      json: null,
    };
    requests.push(entry);
    entry.json = await response.json().catch(() => null);
  });
  await page.goto(`${APP}/login`);
  await page.fill("#email", email);
  await page.fill("#password", PASSWORD);
  await Promise.all([page.waitForURL((u) => !u.pathname.startsWith("/login")), page.click("button[type=submit]")]);
  return { context, page, requests };
}

function readinessLoaded(page) {
  return page.waitForResponse((r) => new URL(r.url()).pathname === "/api/accreditation/readiness", { timeout: 15000 });
}

function accreditationCalls(requests) {
  return requests.filter((r) => r.path.startsWith("/api/accreditation"));
}

function assertTenantDiscipline(requests, allowed) {
  const calls = accreditationCalls(requests);
  assert.ok(calls.length > 0, "the console made accreditation requests");
  for (const call of calls) {
    assert.ok(allowed.includes(call.header), `${call.method} ${call.path}: X-Tenant-Id ${call.header}`);
    for (const claim of [call.queryClaim, call.bodyClaim]) {
      if (claim !== null) assert.equal(claim, call.header, `${call.method} ${call.path}: claim ${claim} != header`);
    }
    assert.notEqual(call.status, 403, `${call.method} ${call.path} refused`);
  }
}

async function check(name, fn) {
  try {
    await fn();
    results.push({ name, ok: true });
    console.log(`ok - ${name}`);
  } catch (error) {
    results.push({ name, ok: false, error: String(error) });
    console.log(`not ok - ${name}\n  ${String(error).split("\n").join("\n  ")}`);
  }
}

const browser = await chromium.launch();
try {
  await check("single-tenant user: console loads in the verified tenant, no 403", async () => {
    const { context, page, requests } = await session(browser, "e2e-single@example.test");
    await page.goto(`${APP}/accreditation`);
    await page.getByRole("button", { name: "Seed checklist" }).click();
    await page.getByText(/Seeded \d+ item/).waitFor({ timeout: 15000 });
    await page.waitForTimeout(500);
    assertTenantDiscipline(requests, ["e2e-hosp-a"]);
    const listed = accreditationCalls(requests).filter((r) => r.path === "/api/accreditation/evidence-items" && r.status === 200);
    assert.ok(listed.at(-1)?.json?.evidence_items?.length > 0, "seeded items listed");
    await context.close();
  });

  await check("forged stored tenant is ignored for a single-tenant user", async () => {
    const { context, page, requests } = await session(browser, "e2e-single@example.test", { storedTenant: "e2e-hosp-b" });
    await Promise.all([readinessLoaded(page), page.goto(`${APP}/accreditation`)]);
    await page.waitForTimeout(500);
    assertTenantDiscipline(requests, ["e2e-hosp-a"]);
    assert.equal(await page.evaluate(() => localStorage.getItem("lumenai.selectedTenant")), "e2e-hosp-a");
    await context.close();
  });

  await check("multi-tenant user must choose; requests follow the choice", async () => {
    const { context, page, requests } = await session(browser, "e2e-multi@example.test");
    await page.goto(`${APP}/accreditation`);
    await page.getByTestId("tenant-required").waitFor({ timeout: 15000 });
    assert.equal(accreditationCalls(requests).length, 0, "nothing requested before a tenant is chosen");
    await page.getByTestId("tenant-required").getByTestId("tenant-switcher").selectOption("e2e-hosp-c");
    await page.getByRole("button", { name: "Seed checklist" }).click();
    await page.getByText(/Seeded \d+ item/).waitFor({ timeout: 15000 });
    const afterC = accreditationCalls(requests).length;
    assertTenantDiscipline(requests, ["e2e-hosp-c"]);
    await Promise.all([readinessLoaded(page), page.getByTestId("tenant-switcher").first().selectOption("e2e-hosp-a")]);
    await page.waitForTimeout(500);
    await page.waitForTimeout(500);
    const switched = accreditationCalls(requests).slice(afterC);
    assert.ok(switched.length > 0 && switched.every((r) => r.header === "e2e-hosp-a"), "after switching, requests use hosp-a");
    assertTenantDiscipline(requests, ["e2e-hosp-a", "e2e-hosp-c"]);
    await context.close();
  });

  await check("forged stored tenant for a multi-tenant user forces a fresh choice", async () => {
    const { context, page, requests } = await session(browser, "e2e-multi@example.test", { storedTenant: "e2e-hosp-b" });
    await page.goto(`${APP}/accreditation`);
    await page.getByTestId("tenant-required").waitFor({ timeout: 15000 });
    assert.equal(accreditationCalls(requests).length, 0);
    assert.equal(await page.evaluate(() => localStorage.getItem("lumenai.selectedTenant")), null);
    await context.close();
  });

  await check("user with no membership is told so; nothing tenant-scoped is requested", async () => {
    const { context, page, requests } = await session(browser, "e2e-nobody@example.test");
    await page.goto(`${APP}/accreditation`);
    await page.getByText(/not a member of any tenant/).waitFor({ timeout: 15000 });
    assert.equal(accreditationCalls(requests).length, 0);
    await context.close();
  });

  await check("another tenant does not see the seeded items", async () => {
    const { context, page, requests } = await session(browser, "e2e-other@example.test");
    await Promise.all([readinessLoaded(page), page.goto(`${APP}/accreditation`)]);
    await page.waitForTimeout(500);
    assertTenantDiscipline(requests, ["e2e-hosp-b"]);
    const listed = accreditationCalls(requests).filter((r) => r.path === "/api/accreditation/evidence-items");
    assert.ok(listed.length > 0 && listed.every((r) => (r.json?.evidence_items ?? []).length === 0), "hosp-b sees none of hosp-a/c's items");
    await context.close();
  });
} finally {
  await browser.close();
}

const failed = results.filter((r) => !r.ok);
console.log(`# tests ${results.length}\n# pass ${results.length - failed.length}\n# fail ${failed.length}`);
process.exit(failed.length ? 1 : 0);
