import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { useApiUrl } from "../context/ApiContext";
import { apiHealth } from "../api/client";

const ENDPOINTS: { method: string; path: string }[] = [
  { method: "GET", path: "/" },
  { method: "GET", path: "/expenses" },
  { method: "GET", path: "/limits" },
  { method: "GET", path: "/limits/status" },
  { method: "GET", path: "/forecast/month" },
  { method: "GET", path: "/goals" },
  { method: "GET", path: "/gmail/status" },
];

export default function Settings() {
  const { apiUrl: url, setApiUrl } = useApiUrl();
  const [inputUrl, setInputUrl] = useState(url);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [checks, setChecks] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setInputUrl(url);
  }, [url]);

  useEffect(() => {
    apiHealth()
      .then(() => setConnected(true))
      .catch(() => setConnected(false));
  }, [url]);

  const handleSaveUrl = () => {
    const normalized = inputUrl.replace(/\/$/, "").trim() || "http://127.0.0.1:8000";
    setApiUrl(normalized);
  };

  const runEndpointCheck = async () => {
    const base = url.replace(/\/$/, "");
    const next: Record<string, boolean> = {};
    for (const { path } of ENDPOINTS) {
      try {
        const res = await fetch(`${base}${path}`, { method: "GET" });
        next[path] = res.ok;
      } catch {
        next[path] = false;
      }
    }
    setChecks(next);
  };

  return (
    <>
      <PageHeader
        title="Settings"
        subtitle="Backend API URL and connectivity. Change if your backend runs on another host or port."
      />
      <div className="p-6 max-w-2xl space-y-6">
        <div className="card">
          <label className="block">
            <span className="text-sm text-text-secondary">Backend API URL</span>
            <input
              className="input-field mt-1"
              placeholder="http://127.0.0.1:8000"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              aria-label="Backend API URL"
            />
          </label>
          <button type="button" className="btn-primary mt-3" onClick={handleSaveUrl}>
            Save
          </button>
        </div>

        <div className="card">
          <p className="text-text-secondary text-sm">Status</p>
          <p className="mt-1">
            {connected === null ? "Checking…" : connected ? (
              <span className="text-accent">Connected</span>
            ) : (
              <span className="text-red-400">Not connected</span>
            )}
          </p>
          <p className="text-text-muted text-xs mt-2">{new Date().toLocaleString()}</p>
        </div>

        <div className="card">
          <h3 className="font-medium text-text-primary mb-2">API endpoints check</h3>
          <p className="text-text-secondary text-sm mb-3">Hit key backend routes to verify connectivity.</p>
          <button type="button" className="btn-secondary text-sm mb-3" onClick={runEndpointCheck}>
            Check endpoints
          </button>
          {Object.keys(checks).length > 0 && (
            <ul className="space-y-1 text-sm">
              {ENDPOINTS.map(({ path }) => (
                <li key={path} className="flex items-center gap-2">
                  {checks[path] ? "✅" : "❌"} GET {path}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card">
          <h3 className="font-medium text-text-primary mb-2">About</h3>
          <p className="text-text-secondary text-sm">
            Stack: Ollama (LLM) · Whisper (voice) · SQLite · FastAPI · React. Runs locally.
          </p>
        </div>
      </div>
    </>
  );
}
