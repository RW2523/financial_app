import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { useApiUrl } from "../context/ApiContext";
import { apiHealth, clearAllData, addSampleData } from "../api/client";
import { ErrorMessage, SuccessMessage } from "../components/ui";

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
  const [clearConfirm, setClearConfirm] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [clearError, setClearError] = useState<string | null>(null);
  const [clearSuccess, setClearSuccess] = useState<string | null>(null);
  const [sampleLoading, setSampleLoading] = useState(false);
  const [sampleError, setSampleError] = useState<string | null>(null);
  const [sampleSuccess, setSampleSuccess] = useState<string | null>(null);

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

  const handleClearAllData = async () => {
    setClearError(null);
    setClearSuccess(null);
    setClearing(true);
    try {
      const res = await clearAllData();
      const d = res.deleted;
      setClearSuccess(
        `All data cleared. Deleted: ${d.expenses} expenses, ${d.limits} limits, ${d.goals} goals, ${d.recurring} recurring, ${d.gmail_processed} Gmail records.`
      );
      setClearConfirm(false);
    } catch (e) {
      setClearError(e instanceof Error ? e.message : "Failed to clear data.");
    } finally {
      setClearing(false);
    }
  };

  const handleAddSampleData = async () => {
    setSampleError(null);
    setSampleSuccess(null);
    setSampleLoading(true);
    try {
      const res = await addSampleData();
      setSampleSuccess(
        `Sample data added: ${res.expenses} expenses, ${res.limits} limits, ${res.goals} goals. Check Dashboard, View, Limits, and Goals.`
      );
    } catch (e) {
      setSampleError(e instanceof Error ? e.message : "Failed to add sample data.");
    } finally {
      setSampleLoading(false);
    }
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

        <div className="card border-emerald-500/30">
          <h3 className="font-medium text-emerald-400 mb-2">Sample data</h3>
          <p className="text-text-secondary text-sm mb-3">
            Add sample expenses (last 4 months), spending limits, and goals so you can try the app with realistic data.
          </p>
          <button
            type="button"
            className="btn-primary bg-emerald-600 hover:bg-emerald-700"
            onClick={handleAddSampleData}
            disabled={sampleLoading}
          >
            {sampleLoading ? "Adding…" : "Add sample data"}
          </button>
          {sampleError && <div className="mt-3"><ErrorMessage message={sampleError} /></div>}
          {sampleSuccess && <div className="mt-3"><SuccessMessage message={sampleSuccess} /></div>}
        </div>

        <div className="card border-red-500/30">
          <h3 className="font-medium text-red-400 mb-2">Clear all data</h3>
          <p className="text-text-secondary text-sm mb-3">
            Permanently delete all expenses, limits, goals, recurring data, and Gmail sync state. This cannot be undone.
          </p>
          {!clearConfirm ? (
            <button
              type="button"
              className="btn-secondary border-red-500/50 text-red-400 hover:bg-red-500/10"
              onClick={() => setClearConfirm(true)}
            >
              Clear all data
            </button>
          ) : (
            <div className="space-y-3">
              <p className="text-amber-400 text-sm font-medium">Are you sure? This action cannot be undone.</p>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="px-4 py-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/50 hover:bg-red-500/30 font-medium"
                  onClick={handleClearAllData}
                  disabled={clearing}
                >
                  {clearing ? "Clearing…" : "Yes, clear everything"}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => { setClearConfirm(false); setClearError(null); setClearSuccess(null); }}
                  disabled={clearing}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
          {clearError && <div className="mt-3"><ErrorMessage message={clearError} /></div>}
          {clearSuccess && <div className="mt-3"><SuccessMessage message={clearSuccess} /></div>}
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
