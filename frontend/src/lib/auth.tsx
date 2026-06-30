import React, { createContext, useContext, useState, useCallback } from "react";

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "https://lumen-ai-53u4.onrender.com";

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
