import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { EmptyState, PageContent, ConfirmButton } from "../components/ui";
import {
  getNetWorth,
  getLiabilities,
  createLiability,
  updateLiability,
  deleteLiability,
  type Liability,
} from "../api/client";
import { formatMoney } from "../lib/utils";
import { currentYear, currentMonth } from "../wealth";

export default function WealthNetWorth() {
  const [netWorth, setNetWorth] = useState<Awaited<ReturnType<typeof getNetWorth>> | null>(null);
  const [liabilities, setLiabilities] = useState<Liability[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [year, setYear] = useState(currentYear);
  const [month, setMonth] = useState(currentMonth);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [nw, liab] = await Promise.all([getNetWorth(year, month), getLiabilities()]);
      setNetWorth(nw);
      setLiabilities(Array.isArray(liab) ? liab : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load net worth.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [year, month]);

  return (
    <>
      <PageHeader
        title="Net Worth"
        subtitle="Assets (cash, portfolio) minus liabilities. Track your full wealth picture."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading…">
        {!loading && netWorth && (
          <div className="space-y-8">
            <section className="flex flex-wrap gap-4 items-center">
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                Month
                <select
                  className="input-field w-32"
                  value={`${year}-${month}`}
                  onChange={(e) => {
                    const [y, m] = e.target.value.split("-").map(Number);
                    setYear(y);
                    setMonth(m);
                  }}
                  aria-label="Month"
                >
                  {Array.from({ length: 24 }, (_, i) => {
                    const d = new Date(currentYear, currentMonth - 1 - i, 1);
                    const y = d.getFullYear();
                    const m = d.getMonth() + 1;
                    return (
                      <option key={`${y}-${m}`} value={`${y}-${m}`}>
                        {new Date(y, m - 1).toLocaleString("default", { month: "short", year: "numeric" })}
                      </option>
                    );
                  })}
                </select>
              </label>
            </section>

            <section className="card">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Summary</h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-text-secondary">Total assets</p>
                  <p className="text-xl font-semibold text-text-primary">{formatMoney(netWorth.total_assets)}</p>
                  <p className="text-xs text-text-muted">
                    Cash: {formatMoney(netWorth.assets_breakdown.free_cash)} · Portfolio: {formatMoney(netWorth.assets_breakdown.portfolio_value)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-text-secondary">Total liabilities</p>
                  <p className="text-xl font-semibold text-text-primary">{formatMoney(netWorth.total_liabilities)}</p>
                  <p className="text-xs text-text-muted">{netWorth.liabilities_count} item(s)</p>
                </div>
                <div>
                  <p className="text-sm text-text-secondary">Net worth</p>
                  <p className="text-xl font-semibold text-accent">{formatMoney(netWorth.net_worth)}</p>
                  {netWorth.delta_vs_previous_month != null && (
                    <p className="text-xs text-text-muted">
                      vs last month: {netWorth.delta_vs_previous_month >= 0 ? "+" : ""}
                      {formatMoney(netWorth.delta_vs_previous_month)}
                    </p>
                  )}
                </div>
              </div>
            </section>

            <section className="card">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Liabilities</h2>
              <AddLiabilityForm onAdded={load} />
              {liabilities.length === 0 ? (
                <EmptyState message="No liabilities. Add credit card, loan, or other debt above." />
              ) : (
                <ul className="mt-4 space-y-3">
                  {liabilities.map((l) => (
                    <LiabilityRow key={l.id} liability={l} onUpdated={load} onDeleted={load} />
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </PageContent>
    </>
  );
}

function AddLiabilityForm({ onAdded }: { onAdded: () => void }) {
  const [name, setName] = useState("");
  const [balance, setBalance] = useState("");
  const [liability_type, setLiabilityType] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || balance === "" || Number(balance) < 0) return;
    setSubmitting(true);
    try {
      await createLiability({
        name: name.trim(),
        balance: Number(balance),
        liability_type: liability_type.trim() || undefined,
        notes: notes.trim() || undefined,
      });
      setName("");
      setBalance("");
      setLiabilityType("");
      setNotes("");
      onAdded();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap gap-4 items-end">
      <label className="flex flex-col gap-1">
        <span className="text-sm text-text-secondary">Name *</span>
        <input
          className="input-field w-40"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Credit card"
          required
          aria-label="Name"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-sm text-text-secondary">Balance *</span>
        <input
          type="number"
          step={0.01}
          className="input-field w-28"
          value={balance}
          onChange={(e) => setBalance(e.target.value)}
          placeholder="0"
          required
          min={0}
          aria-label="Balance"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-sm text-text-secondary">Type</span>
        <select
          className="input-field w-36"
          value={liability_type}
          onChange={(e) => setLiabilityType(e.target.value)}
          aria-label="Type"
        >
          <option value="">—</option>
          <option value="credit_card">Credit card</option>
          <option value="personal_loan">Personal loan</option>
          <option value="student_loan">Student loan</option>
          <option value="mortgage">Mortgage</option>
          <option value="emi">EMI</option>
          <option value="other">Other</option>
        </select>
      </label>
      <label className="flex flex-col gap-1 flex-1 min-w-[120px]">
        <span className="text-sm text-text-secondary">Notes</span>
        <input className="input-field" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional" aria-label="Notes" />
      </label>
      <button type="submit" className="btn-primary" disabled={submitting}>
        {submitting ? "Adding…" : "Add liability"}
      </button>
    </form>
  );
}

function LiabilityRow({ liability, onUpdated, onDeleted }: { liability: Liability; onUpdated: () => void; onDeleted: () => void }) {
  const [editing, setEditing] = useState(false);
  const [balance, setBalance] = useState(String(liability.balance));
  const [notes, setNotes] = useState(liability.notes ?? "");
  const [submitting, setSubmitting] = useState(false);

  const handleSave = async () => {
    setSubmitting(true);
    try {
      await updateLiability(liability.id, { balance: Number(balance), notes: notes.trim() || undefined });
      setEditing(false);
      onUpdated();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <li className="flex flex-wrap items-center gap-4 p-3 rounded-lg bg-surface-muted border border-border">
      <span className="font-medium text-text-primary">{liability.name}</span>
      {liability.liability_type && (
        <span className="text-xs text-text-muted bg-surface-elevated px-2 py-0.5 rounded">{liability.liability_type}</span>
      )}
      {editing ? (
        <>
          <input
            type="number"
            step={0.01}
            className="input-field w-28 text-sm"
            value={balance}
            onChange={(e) => setBalance(e.target.value)}
          />
          <input
            className="input-field flex-1 min-w-[120px] text-sm"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Notes"
          />
          <button type="button" className="btn-primary text-sm" onClick={handleSave} disabled={submitting}>
            Save
          </button>
          <button type="button" className="btn-secondary text-sm" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </>
      ) : (
        <>
          <span className="text-text-primary font-medium">{formatMoney(liability.balance)}</span>
          {liability.notes && <span className="text-sm text-text-muted">{liability.notes}</span>}
          <div className="flex gap-2 ml-auto">
            <button type="button" className="btn-secondary text-sm" onClick={() => setEditing(true)}>
              Edit
            </button>
            <ConfirmButton
              label="Delete"
              confirmLabel="Delete"
              cancelLabel="Cancel"
              onConfirm={async () => {
                await deleteLiability(liability.id);
                onDeleted();
              }}
              variant="danger"
            />
          </div>
        </>
      )}
    </li>
  );
}
