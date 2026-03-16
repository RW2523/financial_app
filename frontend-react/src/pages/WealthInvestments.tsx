import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { EmptyState, PageContent, ConfirmButton } from "../components/ui";
import {
  getInvestmentTransactions,
  createInvestmentTransaction,
  deleteInvestmentTransaction,
  type InvestmentTransaction,
} from "../api/client";
import { formatMoney, formatDate } from "../lib/utils";

export default function WealthInvestments() {
  const [list, setList] = useState<InvestmentTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const now = new Date();
  const [form, setForm] = useState<{
    ticker: string;
    stock_name: string;
    transaction_type: string;
    quantity: number;
    price: number;
    fees: number;
    date: string;
    broker: string;
    notes: string;
  }>({
    ticker: "AAPL",
    stock_name: "",
    transaction_type: "BUY",
    quantity: 10,
    price: 150,
    fees: 0,
    date: now.toISOString().slice(0, 10),
    broker: "",
    notes: "",
  });

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getInvestmentTransactions();
      setList(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load transactions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createInvestmentTransaction({
        ticker: form.ticker.trim().toUpperCase(),
        stock_name: form.stock_name.trim() || undefined,
        transaction_type: form.transaction_type,
        quantity: form.quantity,
        price: form.price,
        fees: form.fees,
        date: form.date.slice(0, 10),
        broker: form.broker.trim() || undefined,
        notes: form.notes.trim() || undefined,
      });
      setShowForm(false);
      setForm({
        ticker: "AAPL",
        stock_name: "",
        transaction_type: "BUY",
        quantity: 10,
        price: 150,
        fees: 0,
        date: now.toISOString().slice(0, 10),
        broker: "",
        notes: "",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed.");
    }
  };

  return (
    <>
      <PageHeader
        title="Investments"
        subtitle="Record BUY, SELL, and DIVIDEND. Your portfolio value and allocation are computed from these transactions."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading transactions…">
        {!loading && (
          <div className="space-y-6">
            {showForm ? (
              <div className="card">
                <h3 className="font-medium text-text-primary mb-4">Add transaction</h3>
                <form onSubmit={handleCreate} className="space-y-4 max-w-md">
                  <label className="block">
                    <span className="text-sm text-text-secondary">Ticker</span>
                    <input
                      className="input-field mt-1 w-full"
                      value={form.ticker}
                      onChange={(e) => setForm({ ...form, ticker: e.target.value })}
                      placeholder="e.g. AAPL"
                      required
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm text-text-secondary">Stock name (optional)</span>
                    <input
                      className="input-field mt-1 w-full"
                      value={form.stock_name}
                      onChange={(e) => setForm({ ...form, stock_name: e.target.value })}
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm text-text-secondary">Type</span>
                    <select
                      className="input-field mt-1 w-full"
                      value={form.transaction_type}
                      onChange={(e) => setForm({ ...form, transaction_type: e.target.value })}
                    >
                      <option value="BUY">BUY</option>
                      <option value="SELL">SELL</option>
                      <option value="DIVIDEND">DIVIDEND</option>
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-sm text-text-secondary">Quantity</span>
                    <input
                      type="number"
                      className="input-field mt-1 w-full"
                      min={0}
                      step={0.0001}
                      value={form.quantity}
                      onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
                      required
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm text-text-secondary">Price</span>
                    <input
                      type="number"
                      className="input-field mt-1 w-full"
                      min={0}
                      step={0.01}
                      value={form.price}
                      onChange={(e) => setForm({ ...form, price: Number(e.target.value) })}
                      required
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm text-text-secondary">Fees</span>
                    <input
                      type="number"
                      className="input-field mt-1 w-full"
                      min={0}
                      step={0.01}
                      value={form.fees}
                      onChange={(e) => setForm({ ...form, fees: Number(e.target.value) })}
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm text-text-secondary">Date</span>
                    <input
                      type="date"
                      className="input-field mt-1 w-full"
                      value={form.date}
                      onChange={(e) => setForm({ ...form, date: e.target.value })}
                      required
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm text-text-secondary">Broker (optional)</span>
                    <input
                      className="input-field mt-1 w-full"
                      value={form.broker}
                      onChange={(e) => setForm({ ...form, broker: e.target.value })}
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm text-text-secondary">Notes (optional)</span>
                    <input
                      className="input-field mt-1 w-full"
                      value={form.notes}
                      onChange={(e) => setForm({ ...form, notes: e.target.value })}
                    />
                  </label>
                  <div className="flex gap-2">
                    <button type="submit" className="btn-primary">
                      Add
                    </button>
                    <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            ) : (
              <button type="button" className="btn-primary" onClick={() => setShowForm(true)}>
                Add transaction
              </button>
            )}

            {list.length === 0 ? (
              <EmptyState message="No investment transactions yet. Add a BUY, SELL, or DIVIDEND above." />
            ) : (
              <div className="card overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-text-secondary border-b border-border">
                      <th className="pb-2 pr-4">Date</th>
                      <th className="pb-2 pr-4">Ticker</th>
                      <th className="pb-2 pr-4">Type</th>
                      <th className="pb-2 pr-4">Qty</th>
                      <th className="pb-2 pr-4">Price</th>
                      <th className="pb-2 pr-4">Fees</th>
                      <th className="pb-2 pr-4">Total</th>
                      <th className="pb-2"></th>
                    </tr>
                  </thead>
                  <tbody className="text-text-primary">
                    {list.map((t) => {
                      const total = t.quantity * t.price + (t.fees ?? 0);
                      return (
                        <tr key={t.id} className="border-b border-border/50">
                          <td className="py-2 pr-4">{formatDate(t.date)}</td>
                          <td className="py-2 pr-4">{t.ticker}</td>
                          <td className="py-2 pr-4">{t.transaction_type}</td>
                          <td className="py-2 pr-4">{t.quantity}</td>
                          <td className="py-2 pr-4">{formatMoney(t.price)}</td>
                          <td className="py-2 pr-4">{formatMoney(t.fees ?? 0)}</td>
                          <td className="py-2 pr-4">{formatMoney(total)}</td>
                          <td className="py-2">
                            <ConfirmButton
                              label="Delete"
                              confirmLabel="Delete"
                              variant="danger"
                              onConfirm={async () => {
                                await deleteInvestmentTransaction(t.id);
                                await load();
                              }}
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </PageContent>
    </>
  );
}
