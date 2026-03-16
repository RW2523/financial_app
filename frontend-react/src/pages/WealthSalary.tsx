import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { EmptyState, MetricCard, PageContent, ConfirmButton } from "../components/ui";
import {
  getSalaryRecords,
  getSalarySummary,
  createSalaryRecord,
  deleteSalaryRecord,
  type SalaryRecord,
  type SalarySummary,
} from "../api/client";
import { formatMoney, formatDate } from "../lib/utils";

const now = new Date();
const currentYear = now.getFullYear();
const currentMonth = now.getMonth() + 1;

export default function WealthSalary() {
  const [year, setYear] = useState(currentYear);
  const [month, setMonth] = useState(currentMonth);
  const [records, setRecords] = useState<SalaryRecord[]>([]);
  const [summary, setSummary] = useState<SalarySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    date: now.toISOString().slice(0, 10),
    source: "Salary",
    gross_amount: 5000,
    deductions: 0,
    bonus_amount: 0,
    notes: "",
  });

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [recs, sum] = await Promise.all([
        getSalaryRecords({ year, month }),
        getSalarySummary(year, month),
      ]);
      setRecords(Array.isArray(recs) ? recs : []);
      setSummary(sum);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load salary data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [year, month]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const net = form.gross_amount - form.deductions;
    try {
      await createSalaryRecord({
        date: form.date.slice(0, 10),
        source: form.source,
        gross_amount: form.gross_amount,
        deductions: form.deductions,
        net_amount: net,
        bonus_amount: form.bonus_amount,
        notes: form.notes.trim() || undefined,
      });
      setShowForm(false);
      setForm({ ...form, date: now.toISOString().slice(0, 10), source: "Salary", gross_amount: 5000, deductions: 0, bonus_amount: 0, notes: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed.");
    }
  };

  return (
    <>
      <PageHeader
        title="Income"
        subtitle="Add salary and other income. Your monthly total feeds Cashflow and Projections."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading salary…">
        {!loading && (
          <div className="space-y-6">
            <div className="flex gap-4 items-center flex-wrap">
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                Year
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
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                Month
                <select
                  className="input-field w-32"
                  value={month}
                  onChange={(e) => setMonth(Number(e.target.value))}
                  aria-label="Month"
                >
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {summary && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <MetricCard label="Net income (month)" value={formatMoney(summary.net_income)} />
                <MetricCard label="Bonus" value={formatMoney(summary.bonus_total)} />
                <MetricCard label="Records" value={summary.record_count ?? records.length} />
              </div>
            )}

            {showForm ? (
              <div className="card">
                <h3 className="font-medium text-text-primary mb-4">Add salary record</h3>
                <form onSubmit={handleCreate} className="space-y-4 max-w-md">
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
                    <span className="text-sm text-text-secondary">Source</span>
                    <input
                      className="input-field mt-1 w-full"
                      value={form.source}
                      onChange={(e) => setForm({ ...form, source: e.target.value })}
                      placeholder="e.g. Employer"
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm text-text-secondary">Gross amount</span>
                    <input
                      type="number"
                      className="input-field mt-1 w-full"
                      min={0}
                      step={0.01}
                      value={form.gross_amount}
                      onChange={(e) => setForm({ ...form, gross_amount: Number(e.target.value) })}
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm text-text-secondary">Deductions</span>
                    <input
                      type="number"
                      className="input-field mt-1 w-full"
                      min={0}
                      step={0.01}
                      value={form.deductions}
                      onChange={(e) => setForm({ ...form, deductions: Number(e.target.value) })}
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm text-text-secondary">Bonus</span>
                    <input
                      type="number"
                      className="input-field mt-1 w-full"
                      min={0}
                      step={0.01}
                      value={form.bonus_amount}
                      onChange={(e) => setForm({ ...form, bonus_amount: Number(e.target.value) })}
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm text-text-secondary">Notes (optional)</span>
                    <input
                      className="input-field mt-1 w-full"
                      value={form.notes}
                      onChange={(e) => setForm({ ...form, notes: e.target.value })}
                      placeholder="Optional"
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
                Add salary record
              </button>
            )}

            {records.length === 0 ? (
              <EmptyState message="No salary records for this month. Add one above." />
            ) : (
              <div className="card overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-text-secondary border-b border-border">
                      <th className="pb-2 pr-4">Date</th>
                      <th className="pb-2 pr-4">Source</th>
                      <th className="pb-2 pr-4">Gross</th>
                      <th className="pb-2 pr-4">Deductions</th>
                      <th className="pb-2 pr-4">Net</th>
                      <th className="pb-2 pr-4">Bonus</th>
                      <th className="pb-2"></th>
                    </tr>
                  </thead>
                  <tbody className="text-text-primary">
                    {records.map((r) => (
                      <tr key={r.id} className="border-b border-border/50">
                        <td className="py-2 pr-4">{formatDate(r.date)}</td>
                        <td className="py-2 pr-4">{r.source}</td>
                        <td className="py-2 pr-4">{formatMoney(r.gross_amount)}</td>
                        <td className="py-2 pr-4">{formatMoney(r.deductions)}</td>
                        <td className="py-2 pr-4">{formatMoney(r.net_amount ?? 0)}</td>
                        <td className="py-2 pr-4">{formatMoney(r.bonus_amount ?? 0)}</td>
                        <td className="py-2">
                          <ConfirmButton
                            label="Delete"
                            confirmLabel="Delete"
                            variant="danger"
                            onConfirm={async () => {
                              await deleteSalaryRecord(r.id);
                              await load();
                            }}
                          />
                        </td>
                      </tr>
                    ))}
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
