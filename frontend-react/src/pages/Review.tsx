import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { EmptyState, PageContent, ConfirmButton } from "../components/ui";
import { getReviewQueue, verifyExpense, deleteExpense, type Expense } from "../api/client";
import { formatMoney } from "../lib/utils";

export default function Review() {
  const [list, setList] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getReviewQueue();
      setList(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load review queue.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleVerify = async (id: number, payload: { date?: string; category?: string; amount?: number; currency?: string }) => {
    try {
      await verifyExpense(id, payload);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verify failed.");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteExpense(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed.");
    }
  };

  return (
    <>
      <PageHeader
        title="Review queue"
        subtitle="Verify or correct low-confidence expenses before they are fully accepted."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading…">
        {!loading && list.length === 0 && (
          <EmptyState message="No items to review. All expenses are verified or none need attention." />
        )}
        {!loading && list.length > 0 && (
          <div className="space-y-4">
            {list.map((e) => (
              <ReviewCard
                key={e.id}
                expense={e}
                onVerify={(p) => handleVerify(e.id!, p)}
                onDelete={() => handleDelete(e.id!)}
              />
            ))}
          </div>
        )}
      </PageContent>
    </>
  );
}

function ReviewCard({
  expense,
  onVerify,
  onDelete,
}: {
  expense: Expense;
  onVerify: (p: { date?: string; category?: string; amount?: number; currency?: string }) => void;
  onDelete: () => void;
}) {
  const [date, setDate] = useState(expense.date ?? "");
  const [category, setCategory] = useState(expense.category ?? "");
  const [amount, setAmount] = useState(String(expense.amount ?? ""));
  const [currency, setCurrency] = useState(expense.currency ?? "USD");

  const handleSubmit = () => {
    onVerify({
      date: date || undefined,
      category: category || undefined,
      amount: amount ? Number(amount) : undefined,
      currency: currency || undefined,
    });
  };

  return (
    <div className="card">
      <div className="flex justify-between items-start gap-4">
        <div>
          <p className="text-text-secondary text-sm">{expense.raw_text || "—"}</p>
          <p className="text-text-primary font-medium mt-1">
            {expense.date} · {expense.category} · {formatMoney(expense.amount ?? 0, expense.currency)}
          </p>
        </div>
        <ConfirmButton
          label="Delete"
          confirmLabel="Delete"
          cancelLabel="Cancel"
          onConfirm={onDelete}
          variant="danger"
        />
      </div>
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-text-secondary">Date</span>
          <input
            className="input-field text-sm"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            aria-label="Date"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-text-secondary">Category</span>
          <input
            className="input-field text-sm"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            aria-label="Category"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-text-secondary">Amount</span>
          <input
            className="input-field text-sm"
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            aria-label="Amount"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-text-secondary">Currency</span>
          <input
            className="input-field text-sm"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            aria-label="Currency"
          />
        </label>
      </div>
      <button type="button" className="btn-primary mt-3" onClick={handleSubmit}>
        Verify / Update
      </button>
    </div>
  );
}
