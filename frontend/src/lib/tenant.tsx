import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch, setSelectedTenant } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  chooseTenant,
  parseSessionTenants,
  readStoredTenant,
  reconcileTenantSelection,
  selectedTenantOf,
  TENANT_DENIED_EVENT,
  writeStoredTenant,
  type StorageLike,
  type TenantState,
} from "@/lib/tenantContext";

/**
 * Session tenant context (P472-03 B5.1). See lib/tenantContext.ts for the
 * contract. The tenant comes from the server's list of the signed-in user's
 * enabled memberships — never from a hard-coded default or an editable field.
 */

interface TenantContextValue {
  state: TenantState;
  /** The verified selection, or null while loading / when none can be used. */
  tenantId: string | null;
  select: (tenantId: string) => void;
  refresh: () => void;
}

const TenantContext = createContext<TenantContextValue | null>(null);

function browserStorage(): StorageLike | null {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}

export function TenantProvider({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  const [state, setState] = useState<TenantState>({ status: "loading" });
  const [generation, setGeneration] = useState(0);

  const apply = useCallback((next: TenantState) => {
    setSelectedTenant(selectedTenantOf(next));
    setState(next);
  }, []);

  useEffect(() => {
    let cancelled = false;
    // Until the server answers, no tenant is sent.
    setSelectedTenant(null);
    setState({ status: "loading" });
    if (!token) return;
    apiFetch<unknown>("/api/auth/tenants", { signOutOn401: true })
      .then((body) => {
        if (cancelled) return;
        const storage = browserStorage();
        const { state: next, store } = reconcileTenantSelection(parseSessionTenants(body), readStoredTenant(storage));
        writeStoredTenant(storage, store);
        apply(next);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setSelectedTenant(null);
        setState({ status: "error", message: error instanceof Error ? error.message : "Tenant context unavailable" });
      });
    return () => {
      cancelled = true;
    };
  }, [token, generation, apply]);

  const refresh = useCallback(() => setGeneration((g) => g + 1), []);

  // A 403 naming the tenant (revoked membership, stale selection) re-reads the list.
  useEffect(() => {
    const onDenied = () => refresh();
    window.addEventListener(TENANT_DENIED_EVENT, onDenied);
    return () => window.removeEventListener(TENANT_DENIED_EVENT, onDenied);
  }, [refresh]);

  const select = useCallback(
    (tenantId: string) => {
      const next = chooseTenant(state, tenantId);
      writeStoredTenant(browserStorage(), tenantId);
      apply(next);
    },
    [state, apply],
  );

  return (
    <TenantContext.Provider value={{ state, tenantId: selectedTenantOf(state), select, refresh }}>
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant(): TenantContextValue {
  const ctx = useContext(TenantContext);
  if (!ctx) throw new Error("useTenant must be used within TenantProvider");
  return ctx;
}

/** Selector for users with several memberships; read-only label otherwise. */
export function TenantSwitcher({ className = "" }: { className?: string }) {
  const { state, select } = useTenant();
  if (state.status === "selected" && state.options.length === 1) {
    return (
      <span className={`text-xs text-slate-500 ${className}`} data-testid="tenant-current">
        Tenant: <span className="font-medium text-slate-700">{state.tenantId}</span>
      </span>
    );
  }
  if (state.status !== "selected" && state.status !== "selection_required") return null;
  return (
    <label className={`flex items-center gap-2 text-xs text-slate-500 ${className}`}>
      Tenant
      <select
        data-testid="tenant-switcher"
        className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800"
        value={state.status === "selected" ? state.tenantId : ""}
        onChange={(event) => event.target.value && select(event.target.value)}
      >
        {state.status === "selection_required" && <option value="">Select a tenant…</option>}
        {state.options.map((tenantId) => (
          <option key={tenantId} value={tenantId}>
            {tenantId}
          </option>
        ))}
      </select>
    </label>
  );
}

/**
 * Renders children only once a verified tenant is selected; otherwise explains
 * why nothing is loaded. Pages that act in a tenant wrap their content in this
 * so no request is ever made with a guessed tenant.
 */
export function RequireTenant({ children }: { children: (tenantId: string) => React.ReactNode }) {
  const { state } = useTenant();
  if (state.status === "selected") return <>{children(state.tenantId)}</>;
  const message =
    state.status === "loading"
      ? "Loading your tenant…"
      : state.status === "selection_required"
        ? "You belong to more than one tenant. Select one to continue."
        : state.status === "none"
          ? "Your account is not a member of any tenant. Contact your administrator."
          : `Tenant context is unavailable: ${state.message}`;
  return (
    <div role="status" data-testid="tenant-required" className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">
      <p>{message}</p>
      {state.status === "selection_required" && <TenantSwitcher className="mt-3" />}
    </div>
  );
}
