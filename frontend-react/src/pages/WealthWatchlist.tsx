import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { EmptyState, PageContent, ConfirmButton } from "../components/ui";
import { getWatchlist, addWatchlistItem, updateWatchlistItem, deleteWatchlistItem, type WatchlistItem } from "../api/client";
import { formatMoney } from "../lib/utils";

export default function WealthWatchlist() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getWatchlist();
      setItems(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load watchlist.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <PageHeader
        title="Watchlist"
        subtitle="Track stocks you're interested in. Add from Portfolio discovery or here."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading watchlist…">
        {!loading && (
          <div className="space-y-6">
            <AddWatchlistForm onAdded={load} />
            {items.length === 0 ? (
              <EmptyState message="No watchlist items. Add a ticker above or from Portfolio → Discover stocks." />
            ) : (
              <div className="space-y-3">
                {items.map((item) => (
                  <WatchlistRow
                    key={item.id}
                    item={item}
                    onUpdated={load}
                    onDeleted={load}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </PageContent>
    </>
  );
}

function AddWatchlistForm({ onAdded }: { onAdded: () => void }) {
  const [ticker, setTicker] = useState("");
  const [stock_name, setStockName] = useState("");
  const [target_buy_price, setTargetBuyPrice] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim()) return;
    setSubmitting(true);
    try {
      await addWatchlistItem({
        ticker: ticker.trim().toUpperCase(),
        stock_name: stock_name.trim() || undefined,
        target_buy_price: target_buy_price ? Number(target_buy_price) : undefined,
        notes: notes.trim() || undefined,
      });
      setTicker("");
      setStockName("");
      setTargetBuyPrice("");
      setNotes("");
      onAdded();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card flex flex-wrap gap-4 items-end">
      <label className="flex flex-col gap-1">
        <span className="text-sm text-text-secondary">Ticker *</span>
        <input
          className="input-field w-28"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="AAPL"
          required
          aria-label="Ticker"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-sm text-text-secondary">Name</span>
        <input
          className="input-field w-40"
          value={stock_name}
          onChange={(e) => setStockName(e.target.value)}
          placeholder="Apple Inc."
          aria-label="Stock name"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-sm text-text-secondary">Target buy price</span>
        <input
          type="number"
          step={0.01}
          className="input-field w-28"
          value={target_buy_price}
          onChange={(e) => setTargetBuyPrice(e.target.value)}
          placeholder="150"
          aria-label="Target buy price"
        />
      </label>
      <label className="flex flex-col gap-1 flex-1 min-w-[200px]">
        <span className="text-sm text-text-secondary">Notes</span>
        <input
          className="input-field"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Optional"
          aria-label="Notes"
        />
      </label>
      <button type="submit" className="btn-primary" disabled={submitting}>
        {submitting ? "Adding…" : "Add"}
      </button>
    </form>
  );
}

function WatchlistRow({ item, onUpdated, onDeleted }: { item: WatchlistItem; onUpdated: () => void; onDeleted: () => void }) {
  const [editing, setEditing] = useState(false);
  const [target_buy_price, setTargetBuyPrice] = useState(item.target_buy_price ?? "");
  const [current_price, setCurrentPrice] = useState(item.current_price ?? "");
  const [notes, setNotes] = useState(item.notes ?? "");
  const [submitting, setSubmitting] = useState(false);

  const handleSave = async () => {
    setSubmitting(true);
    try {
      await updateWatchlistItem(item.id, {
        target_buy_price: target_buy_price ? Number(target_buy_price) : undefined,
        current_price: current_price ? Number(current_price) : undefined,
        notes: notes.trim() || undefined,
      });
      setEditing(false);
      onUpdated();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card flex flex-wrap items-center gap-4">
      <div className="font-mono font-medium text-text-primary">{item.ticker}</div>
      <div className="text-text-secondary text-sm">{item.stock_name || "—"}</div>
      {item.sector && <span className="text-xs text-text-muted bg-surface-muted px-2 py-0.5 rounded">{item.sector}</span>}
      <div className="text-sm text-text-secondary">
        Target: {item.target_buy_price != null ? formatMoney(item.target_buy_price) : "—"}
        {item.current_price != null && ` · Price: ${formatMoney(item.current_price)}`}
      </div>
      {item.notes && <p className="text-sm text-text-muted w-full">{item.notes}</p>}
      {editing ? (
        <div className="flex flex-wrap gap-2 items-center w-full mt-2">
          <input
            type="number"
            step={0.01}
            className="input-field w-24 text-sm"
            placeholder="Target price"
            value={target_buy_price}
            onChange={(e) => setTargetBuyPrice(e.target.value)}
          />
          <input
            type="number"
            step={0.01}
            className="input-field w-24 text-sm"
            placeholder="Current price"
            value={current_price}
            onChange={(e) => setCurrentPrice(e.target.value)}
          />
          <input
            className="input-field flex-1 min-w-[120px] text-sm"
            placeholder="Notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <button type="button" className="btn-primary text-sm" onClick={handleSave} disabled={submitting}>
            Save
          </button>
          <button type="button" className="btn-secondary text-sm" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </div>
      ) : (
        <div className="flex gap-2 ml-auto">
          <button type="button" className="btn-secondary text-sm" onClick={() => setEditing(true)}>
            Edit
          </button>
          <ConfirmButton
            label="Remove"
            confirmLabel="Remove"
            cancelLabel="Cancel"
            onConfirm={async () => {
              await deleteWatchlistItem(item.id);
              onDeleted();
            }}
            variant="danger"
          />
        </div>
      )}
    </div>
  );
}
