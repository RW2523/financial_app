import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { apiUrl as getApiUrl } from "../api/client";

type ApiContextValue = {
  apiUrl: string;
  setApiUrl: (url: string) => void;
};

const defaultUrl = import.meta.env.VITE_EXPENSE_API_URL || "http://127.0.0.1:8000";

const ApiContext = createContext<ApiContextValue | null>(null);

export function ApiProvider({ children }: { children: ReactNode }) {
  const [url, setUrl] = useState(() => {
    try {
      const stored = localStorage.getItem("expense_api_url");
      return stored || defaultUrl;
    } catch {
      return defaultUrl;
    }
  });

  useEffect(() => {
    (window as unknown as { __API_URL?: string }).__API_URL = url;
  }, [url]);

  const setApiUrl = useCallback((newUrl: string) => {
    const normalized = newUrl.replace(/\/$/, "") || defaultUrl;
    setUrl(normalized);
    try {
      localStorage.setItem("expense_api_url", normalized);
    } catch {}
    (window as unknown as { __API_URL?: string }).__API_URL = normalized;
  }, []);

  return (
    <ApiContext.Provider value={{ apiUrl: url, setApiUrl }}>
      {children}
    </ApiContext.Provider>
  );
}

export function useApiUrl() {
  const ctx = useContext(ApiContext);
  return ctx ?? { apiUrl: getApiUrl(), setApiUrl: () => {} };
}
