import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { EmptyState, PageContent } from "../components/ui";
import { getRecurring, recomputeRecurring } from "../api/client";
import { formatMoney } from "../lib/utils";

interface RecurringItem {
  merchant?: string;
  category?: string;
  typical_amount?: number;
  currency?: string;
  frequency_type?: string;
  next_expected_date?: string;
}

export default function Recurring() {
  const [items, setItems] = useState<RecurringItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [recomputing, setRecomputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getRecurring();
      const list = (res as { items?: RecurringItem[] }).items ?? [];
      setItems(Array.isArray(list) ? list : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load recurring expenses.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleRecompute = async () => {
    setRecomputing(true);
    setError(null);
    try {
      await recomputeRecurring();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Recompute failed.");
    } finally {
      setRecomputing(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Recurring expenses"
        subtitle="Detected subscriptions and recurring transactions from your history."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading…">
        {!loading && (
          <>
            <button
              type="button"
              className="btn-primary mb-6"
              onClick={handleRecompute}
              disabled={recomputing}
            >
              {recomputing ? "Recomputing…" : "Recompute recurring"}
            </button>
            {items.length === 0 ? (
              <EmptyState message="No recurring expenses detected. Add more expenses and run Recompute." />
            ) : (
              <div className="card overflow-hidden p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-surface-muted/50">
                        <th className="text-left py-3 px-4 text-text-secondary">Merchant</th>
                        <th className="text-left py-3 px-4 text-text-secondary">Category</th>
                        <th className="text-right py-3 px-4 text-text-secondary">Amount</th>
                        <th className="text-left py-3 px-4 text-text-secondary">Frequency</th>
                        <th className="text-left py-3 px-4 text-text-secondary">Next expected</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((x, i) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="py-3 px-4 text-text-primary">{x.merchant ?? x.category ?? "—"}</td>
                          <td className="py-3 px-4 text-text-secondary">{x.category ?? "—"}</td>
                          <td className="py-3 px-4 text-right">{formatMoney(x.typical_amount ?? 0, x.currency ?? "USD")}</td>
                          <td className="py-3 px-4 text-text-secondary">{x.frequency_type ?? "—"}</td>
                          <td className="py-3 px-4 text-text-secondary">{x.next_expected_date ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </PageContent>
    </>
  );
}
