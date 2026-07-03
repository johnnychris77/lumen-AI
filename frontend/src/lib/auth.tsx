import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { API_BASE, setUnauthorizedHandler } from "@/lib/api";

// API_BASE now has a single definition in lib/api.ts. Re-exported here so the
// many existing `import { API_BASE } from "@/lib/auth"` call sites keep working.
export { API_BASE };

interface AuthState {
  token: string;
  role: string;
  actor: string;
}

interface AuthContextValue extends AuthState {
  headers: () => Record<string, string>;
  setAuth: (state: AuthState) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuthState] = useState<AuthState>(() => ({
    token: localStorage.getItem("token") || import.meta.env.VITE_AUTH_TOKEN || "",
    role: localStorage.getItem("role") || "viewer",
    actor: localStorage.getItem("actor") || "user@lumenai.com",
  }));

  const setAuth = useCallback((state: AuthState) => {
    localStorage.setItem("token", state.token);
    localStorage.setItem("role", state.role);
    localStorage.setItem("actor", state.actor);
    setAuthState(state);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("actor");
    // Reset auth state in-place (no full page reload). With an empty token the
    // RequireAuth guard redirects to /login using already-loaded code, so a
    // stale cached index.html can't blank the page on a fresh deploy.
    setAuthState({ token: "", role: "viewer", actor: "" });
  }, []);

  // Let the central apiFetch client trigger sign-out on any 401 (expired or
  // invalid session), instead of each of the ~43 call sites handling it.
  useEffect(() => {
    setUnauthorizedHandler(() => logout());
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  const headers = useCallback(
    () => ({
      "Content-Type": "application/json",
      Authorization: `Bearer ${auth.token}`,
      "X-LumenAI-Role": auth.role,
      "X-LumenAI-Actor": auth.actor,
    }),
    [auth]
  );

  return (
    <AuthContext.Provider value={{ ...auth, headers, setAuth, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
