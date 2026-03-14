import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { setApiUserId } from "../api/client";
import type { AuthUser } from "../api/client";

const STORAGE_KEY = "expense_tracker_user";

type AuthContextValue = {
  user: AuthUser | null;
  login: (user: AuthUser) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const u = JSON.parse(raw) as AuthUser;
      return u?.user_id ? u : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (user?.user_id) {
      setApiUserId(user.user_id);
    } else {
      setApiUserId(null);
    }
  }, [user?.user_id]);

  const login = useCallback((u: AuthUser) => {
    setUser(u);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(u));
    } catch {}
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setApiUserId(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
