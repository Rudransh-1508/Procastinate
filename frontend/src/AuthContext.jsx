// Bearer-token auth state. Token lives in localStorage; user info is fetched
// from /api/users/me whenever the token changes.
import { createContext, useContext, useEffect, useState, useCallback } from "react";

const AuthContext = createContext(null);
const TOKEN_KEY = "profiler_token";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async (tok) => {
    if (!tok) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const res = await fetch("/api/users/me", {
        headers: { Authorization: `Bearer ${tok}` },
      });
      if (!res.ok) throw new Error("invalid session");
      setUser(await res.json());
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser(token);
  }, [token, loadUser]);

  const login = useCallback((tok) => {
    localStorage.setItem(TOKEN_KEY, tok);
    setToken(tok);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  // api.js dispatches this on any 401 (expired/invalid token).
  useEffect(() => {
    const onUnauthorized = () => logout();
    window.addEventListener("profiler:unauthorized", onUnauthorized);
    return () => window.removeEventListener("profiler:unauthorized", onUnauthorized);
  }, [logout]);

  return (
    <AuthContext.Provider value={{ token, user, loading, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
