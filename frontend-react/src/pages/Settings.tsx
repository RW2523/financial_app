import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { useApiUrl } from "../context/ApiContext";
import { useAuth } from "../context/AuthContext";
import { apiHealth, clearAllData, addSampleData, getGmailStatus, syncGmail } from "../api/client";
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
  const navigate = useNavigate();
  const { user, logout } = useAuth();
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
  const [gmailStatus, setGmailStatus] = useState<Awaited<ReturnType<typeof getGmailStatus>> | null>(null);
  const [gmailSyncing, setGmailSyncing] = useState(false);
  const [gmailError, setGmailError] = useState<string | null>(null);
  const [gmailLastSync, setGmailLastSync] = useState<{ added: number; errors: string[] } | null>(null);

  useEffect(() => {
    setInputUrl(url);
  }, [url]);

  useEffect(() => {
    getGmailStatus()
      .then(setGmailStatus)
      .catch(() => setGmailStatus(null));
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

  const handleGmailSync = async () => {
    setGmailError(null);
    setGmailLastSync(null);
    setGmailSyncing(true);
    try {
      const res = await syncGmail();
      setGmailLastSync({ added: res.added ?? 0, errors: res.errors ?? [] });
      const s = await getGmailStatus();
      setGmailStatus(s);
    } catch (e) {
      setGmailError(e instanceof Error ? e.message : "Sync failed.");
    } finally {
      setGmailSyncing(false);
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

        <div className="card border-border">
          <h3 className="font-medium text-text-primary mb-2">Gmail sync</h3>
          <p className="text-text-secondary text-sm mb-3">
            Sync expenses from Gmail. Receipts and payments are extracted and saved.
          </p>
          {gmailStatus && (
            <>
              <p className="text-sm font-medium text-text-primary mb-1">
                {gmailStatus.connected ? "Connected" : "Not connected"}
              </p>
              <p className="text-sm text-text-secondary">{gmailStatus.message}</p>
              {!gmailStatus.connected && (gmailStatus.credentials_path || gmailStatus.token_path) && (
                <div className="mt-4 p-3 rounded-lg bg-surface-muted text-xs text-text-secondary space-y-2">
                  <p className="font-medium text-text-primary">Setup steps:</p>
                  <ol className="list-decimal list-inside space-y-1">
                    <li>Google Cloud Console → create project → enable Gmail API → create OAuth 2.0 credentials (Desktop app) → download JSON.</li>
                    <li>Save the JSON as <code className="bg-surface-elevated px-1 rounded">{gmailStatus.credentials_path ?? "backend/credentials.json"}</code></li>
                    <li>From the project root run: <code className="bg-surface-elevated px-1 rounded">python backend/gmail_auth.py</code> — a browser will open to sign in; token saves to <code className="bg-surface-elevated px-1 rounded">{gmailStatus.token_path ?? "backend/token.json"}</code></li>
                    <li>Restart the app and return here; then click Sync Gmail.</li>
                  </ol>
                </div>
              )}
              <button
                type="button"
                className="btn-primary mt-4"
                onClick={handleGmailSync}
                disabled={gmailSyncing || !gmailStatus.connected}
              >
                {gmailSyncing ? "Syncing…" : "Sync Gmail"}
              </button>
              {gmailError && <div className="mt-3"><ErrorMessage message={gmailError} /></div>}
              {gmailLastSync && (
                <p className="mt-3 text-sm text-text-secondary">
                  Last sync: <strong>{gmailLastSync.added}</strong> expense(s) added.
                  {gmailLastSync.errors.length > 0 && (
                    <span className="text-amber-400 ml-1"> ({gmailLastSync.errors.slice(0, 2).join("; ")})</span>
                  )}
                </p>
              )}
            </>
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

        <div className="card">
          <h3 className="font-medium text-text-primary mb-2">Account</h3>
          {user && (
            <p className="text-sm text-text-secondary mb-2">
              Logged in as <strong>{user.username}</strong>
              {user.salary > 0 && ` · Salary: ${user.currency} ${user.salary}`}
              {user.monthly_budget > 0 && ` · Budget: ${user.currency} ${user.monthly_budget}`}
            </p>
          )}
          <button
            type="button"
            className="btn-secondary"
            onClick={() => { logout(); navigate("/login", { replace: true }); }}
          >
            Log out
          </button>
        </div>
      </div>
    </>
  );
}
