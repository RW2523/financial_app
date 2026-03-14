import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { PageContent } from "../components/ui";
import { getGmailStatus, syncGmail } from "../api/client";

export default function Gmail() {
  const [status, setStatus] = useState<Awaited<ReturnType<typeof getGmailStatus>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<{ added: number; errors: string[] } | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const s = await getGmailStatus();
      setStatus(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load status.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    setLastSync(null);
    try {
      const res = await syncGmail();
      setLastSync({ added: res.added ?? 0, errors: res.errors ?? [] });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sync failed.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Gmail → Expenses"
        subtitle="Sync expenses from Gmail. Receipts and payments are extracted and saved."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading…">
        {!loading && status && (
          <div className="max-w-lg space-y-4">
            <div className={`card ${status.connected ? "border-accent/30" : "border-amber-500/30"}`}>
              <p className="text-sm font-medium text-text-primary mb-1">
                {status.connected ? "Connected" : "Not connected"}
              </p>
              <p className="text-sm text-text-secondary">{status.message}</p>
              {!status.connected && (status.credentials_path || status.token_path) && (
                <div className="mt-4 p-3 rounded-lg bg-surface-muted text-xs text-text-secondary space-y-2">
                  <p className="font-medium text-text-primary">Setup steps:</p>
                  <ol className="list-decimal list-inside space-y-1">
                    <li>Google Cloud Console → create project → enable Gmail API → create OAuth 2.0 credentials (Desktop app) → download JSON.</li>
                    <li>Save the JSON as <code className="bg-surface-elevated px-1 rounded">{status.credentials_path ?? "backend/credentials.json"}</code></li>
                    <li>From the project root run: <code className="bg-surface-elevated px-1 rounded">python backend/gmail_auth.py</code> — a browser will open to sign in with Google; token saves to <code className="bg-surface-elevated px-1 rounded">{status.token_path ?? "backend/token.json"}</code></li>
                    <li>Restart the app and return here; then click Sync Gmail.</li>
                  </ol>
                </div>
              )}
              <button
                type="button"
                className="btn-primary mt-4"
                onClick={handleSync}
                disabled={syncing || !status.connected}
              >
                {syncing ? "Syncing…" : "Sync Gmail"}
              </button>
            </div>
            {lastSync && (
              <div className="card">
                <p className="text-sm text-text-primary">
                  Last sync: <strong>{lastSync.added}</strong> expense(s) added.
                </p>
                {lastSync.errors.length > 0 && (
                  <ul className="mt-2 text-sm text-amber-400 list-disc list-inside">
                    {lastSync.errors.slice(0, 5).map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}
      </PageContent>
    </>
  );
}
