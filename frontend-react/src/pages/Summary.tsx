import { useState } from "react";
import PageHeader from "../components/PageHeader";
import { ErrorMessage } from "../components/ui";
import { getMonthlySummary, type Expense } from "../api/client";
import { formatMoney } from "../lib/utils";

export default function Summary() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<{ total_expenses: number; summary: string; expenses?: Expense[] } | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await getMonthlySummary(year, month);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate summary.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Monthly summary"
        subtitle="Pick a month and generate an AI summary with insights."
      />
      <div className="p-6 max-w-3xl">
        <div className="card flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1">
            <span className="text-sm text-text-secondary">Year</span>
            <input
              type="number"
              className="input-field w-24"
              min={2020}
              max={2030}
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              aria-label="Year"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm text-text-secondary">Month</span>
            <input
              type="number"
              className="input-field w-24"
              min={1}
              max={12}
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
              aria-label="Month"
            />
          </label>
          <button type="button" className="btn-primary" onClick={handleGenerate} disabled={loading}>
            {loading ? "Analyzing…" : "Generate summary"}
          </button>
        </div>

        {error && <div className="mt-4"><ErrorMessage message={error} /></div>}

        {data && (
          <div className="mt-6 space-y-6">
            <div className="card">
              <h2 className="text-lg font-semibold text-text-primary mb-2">
                {year}-{String(month).padStart(2, "0")} Summary
              </h2>
              <p className="text-text-secondary text-sm mb-4">Transactions: {data.total_expenses}</p>
              <h3 className="font-medium text-text-primary mb-2">AI insights</h3>
              <p className="text-text-secondary whitespace-pre-wrap">{data.summary}</p>
            </div>
            {data.expenses && data.expenses.length > 0 && (
              <div className="card overflow-hidden p-0">
                <div className="p-4 border-b border-border font-medium text-text-primary">Detailed expenses</div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-surface-muted/50">
                        <th className="text-left py-2 px-4 text-text-secondary">Date</th>
                        <th className="text-left py-2 px-4 text-text-secondary">Category</th>
                        <th className="text-right py-2 px-4 text-text-secondary">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.expenses.map((e, i) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="py-2 px-4">{e.date}</td>
                          <td className="py-2 px-4">{e.category}</td>
                          <td className="py-2 px-4 text-right">{formatMoney(e.amount ?? 0, e.currency)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
