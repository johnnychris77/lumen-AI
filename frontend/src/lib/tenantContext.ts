/**
 * Session tenant context (P472-03 Batch 5, B5.1) — pure logic, no React, no DOM.
 *
 * The backend decides which tenant a request acts in: a tenant the signed-in
 * user is not an enabled member of is refused (403). The client therefore:
 *
 *   1. asks the server which tenants it may act in (GET /api/auth/tenants —
 *      derived from the authenticated principal, never from client input);
 *   2. uses the sole tenant, or makes the user choose when there are several;
 *   3. sends the choice as `X-Tenant-Id` on every request, and repeats the SAME
 *      value where a route still requires a `tenant_id` parameter.
 *
 * The stored choice is only a convenience for reloads. It is never treated as
 * authority: it is discarded unless the server lists it again, and every API
 * request re-verifies it server-side. No hard-coded tenant (`default-tenant`,
 * `demo-tenant`, …) is ever used as a fallback.
 */

export const TENANT_STORAGE_KEY = "lumenai.selectedTenant";
export const TENANT_HEADER = "X-Tenant-Id";
export const TENANT_DENIED_EVENT = "lumenai:tenant-denied";

export interface TenantMembership {
  tenant_id: string;
  role: string;
}

export interface SessionTenants {
  memberships: TenantMembership[];
  active_tenant_id: string | null;
  selection_required: boolean;
}

export type TenantState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "none"; options: [] }
  | { status: "selection_required"; options: string[] }
  | { status: "selected"; tenantId: string; options: string[] };

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

const TENANT_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:@-]{0,254}$/;

export function isValidTenantId(value: unknown): value is string {
  return typeof value === "string" && TENANT_ID_PATTERN.test(value);
}

/** Strictly validate the server response; anything malformed is rejected (fail closed). */
export function parseSessionTenants(body: unknown): SessionTenants {
  if (!body || typeof body !== "object") throw new Error("Malformed tenant context response");
  const raw = body as Record<string, unknown>;
  if (!Array.isArray(raw.memberships)) throw new Error("Malformed tenant context response");
  const memberships: TenantMembership[] = [];
  const seen = new Set<string>();
  for (const item of raw.memberships) {
    const entry = item as Record<string, unknown> | null;
    if (!entry || !isValidTenantId(entry.tenant_id) || typeof entry.role !== "string") {
      throw new Error("Malformed tenant membership");
    }
    if (seen.has(entry.tenant_id)) continue;
    seen.add(entry.tenant_id);
    memberships.push({ tenant_id: entry.tenant_id, role: entry.role });
  }
  const active = raw.active_tenant_id;
  if (active !== null && active !== undefined && !(isValidTenantId(active) && seen.has(active))) {
    throw new Error("Active tenant is not one of the listed memberships");
  }
  return {
    memberships,
    active_tenant_id: (active as string | null | undefined) ?? null,
    selection_required: raw.selection_required === true,
  };
}

/**
 * Combine the server's list with a previously stored choice.
 * Returns the new state and the value to store (null = clear storage).
 */
export function reconcileTenantSelection(
  server: SessionTenants,
  stored: string | null,
): { state: TenantState; store: string | null } {
  const options = server.memberships.map((m) => m.tenant_id);
  if (options.length === 0) return { state: { status: "none", options: [] }, store: null };
  if (stored && options.includes(stored)) {
    return { state: { status: "selected", tenantId: stored, options }, store: stored };
  }
  if (options.length === 1) {
    return { state: { status: "selected", tenantId: options[0], options }, store: options[0] };
  }
  if (server.active_tenant_id && options.includes(server.active_tenant_id)) {
    return {
      state: { status: "selected", tenantId: server.active_tenant_id, options },
      store: server.active_tenant_id,
    };
  }
  // Several memberships and no (or a stale) stored choice: the user must choose.
  return { state: { status: "selection_required", options }, store: null };
}

/** The user picks a tenant; only one the server listed is accepted. */
export function chooseTenant(state: TenantState, tenantId: string): TenantState {
  if (state.status !== "selected" && state.status !== "selection_required") {
    throw new Error("No tenant can be selected in the current state");
  }
  if (!state.options.includes(tenantId)) {
    throw new Error("Tenant is not one of your memberships");
  }
  return { status: "selected", tenantId, options: state.options };
}

export function selectedTenantOf(state: TenantState): string | null {
  return state.status === "selected" ? state.tenantId : null;
}

/** Header to attach to API requests; empty when no verified selection exists. */
export function tenantHeaders(selected: string | null): Record<string, string> {
  return selected ? { [TENANT_HEADER]: selected } : {};
}

/** True when a 403 says the named tenant was refused (stale or revoked selection). */
export function isTenantDenial(status: number, detail: unknown): boolean {
  if (status !== 403 || typeof detail !== "string") return false;
  return /tenant/i.test(detail);
}

export function readStoredTenant(storage: StorageLike | null): string | null {
  try {
    const value = storage?.getItem(TENANT_STORAGE_KEY) ?? null;
    return isValidTenantId(value) ? value : null;
  } catch {
    return null;
  }
}

export function writeStoredTenant(storage: StorageLike | null, value: string | null): void {
  try {
    if (!storage) return;
    if (value) storage.setItem(TENANT_STORAGE_KEY, value);
    else storage.removeItem(TENANT_STORAGE_KEY);
  } catch {
    /* storage unavailable — the in-memory selection still works */
  }
}
