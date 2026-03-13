import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { PageContent } from "../components/ui";
import { getGmailStatus, syncGmail } from "../api/client";

export default function Gmail() {
  const [status, setStatus] = useState<Awaited<ReturnType<typeof getGmailStatus>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    try {
      await syncGmail();
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
        {!loading && (
          <div className="card max-w-md">
            <p className="text-text-secondary text-sm mb-4">
              {status?.connected ? "Connected" : "Not connected"}. {status?.message ?? ""}
            </p>
            <button
              type="button"
              className="btn-primary"
              onClick={handleSync}
              disabled={syncing}
            >
              {syncing ? "Syncing…" : "Sync Gmail"}
            </button>
          </div>
        )}
      </PageContent>
    </>
  );
}
