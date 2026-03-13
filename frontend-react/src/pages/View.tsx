import { useState, useEffect } from "react";
import { RefreshCw } from "lucide-react";
import PageHeader from "../components/PageHeader";
import { EmptyState, MetricCard, PageContent } from "../components/ui";
import { getExpenses, type Expense } from "../api/client";
import { formatMoney } from "../lib/utils";

export default function View() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getExpenses();
      setExpenses(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load expenses.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const total = expenses.reduce((s, e) => s + (e.amount || 0), 0);
  const categories = new Set(expenses.map((e) => e.category)).size;

  return (
    <>
      <PageHeader
        title="All expenses"
        subtitle="Your full expense list. Use Refresh after adding items here or via Telegram."
      >
        <button
          type="button"
          className="btn-secondary mt-3 flex items-center gap-2"
          onClick={load}
          disabled={loading}
        >
          <RefreshCw className={loading ? "animate-spin h-4 w-4" : "h-4 w-4"} aria-hidden />
          Refresh
        </button>
      </PageHeader>
      <PageContent loading={loading} error={error}>
        {!loading && expenses.length === 0 && (
          <EmptyState message="No expenses yet. Add one in Add or via Telegram." />
        )}
        {!loading && expenses.length > 0 && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <MetricCard label="Transactions" value={expenses.length} />
              <MetricCard label="Categories" value={categories} />
              <MetricCard label="Total" value={formatMoney(total)} accent />
            </div>
            <div className="card overflow-hidden p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-surface-muted/50">
                      <th className="text-left py-3 px-4 font-medium text-text-secondary">Date</th>
                      <th className="text-left py-3 px-4 font-medium text-text-secondary">Category</th>
                      <th className="text-right py-3 px-4 font-medium text-text-secondary">Amount</th>
                      <th className="text-left py-3 px-4 font-medium text-text-secondary">Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expenses.map((e, i) => (
                      <tr key={e.id ?? i} className="border-b border-border/50 hover:bg-surface-muted/30">
                        <td className="py-3 px-4 text-text-primary">{e.date}</td>
                        <td className="py-3 px-4 text-text-primary">{e.category}</td>
                        <td className="py-3 px-4 text-right font-medium">
                          {formatMoney(e.amount ?? 0, e.currency || "USD")}
                        </td>
                        <td className="py-3 px-4 text-text-secondary max-w-xs truncate">{e.raw_text || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </PageContent>
    </>
  );
}
