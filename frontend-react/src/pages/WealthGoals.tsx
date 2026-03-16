import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { EmptyState, PageContent, ConfirmButton } from "../components/ui";
import { getGoals, createGoal, updateGoal, deleteGoal, type Goal } from "../api/client";
import { formatMoney } from "../lib/utils";

const WEALTH_GOAL_TYPES = [
  { value: "monthly_investment_target", label: "Monthly investment target" },
  { value: "emergency_fund", label: "Emergency fund target" },
  { value: "portfolio_value_target", label: "Portfolio value target" },
  { value: "savings_target", label: "Savings target" },
  { value: "free_cash_buffer", label: "Free cash buffer target" },
  { value: "reduce_expense_ratio", label: "Reduce expense ratio" },
  { value: "spending_reduction", label: "Spending reduction" },
  { value: "category_cap", label: "Category cap" },
];

export default function WealthGoals() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [statusFilter, setStatusFilter] = useState("active");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Goal | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getGoals(statusFilter);
      setGoals(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load goals.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [statusFilter]);

  return (
    <>
      <PageHeader
        title="Goals"
        subtitle="Set and track wealth goals: investment targets, emergency fund, portfolio value, savings, and more."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading goals…">
        {!loading && (
          <div className="space-y-6">
            <div className="flex gap-4 items-center">
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                Status
                <select
                  className="input-field w-32"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  aria-label="Filter by status"
                >
                  <option value="active">Active</option>
                  <option value="completed">Completed</option>
                  <option value="all">All</option>
                </select>
              </label>
            </div>

            {editing ? (
              <GoalEditForm
                goal={editing}
                onSave={async (payload) => {
                  await updateGoal(editing.id, payload);
                  setEditing(null);
                  await load();
                }}
                onCancel={() => setEditing(null)}
              />
            ) : (
              <CreateGoalForm
                onCreate={async (payload) => {
                  await createGoal(payload);
                  await load();
                }}
              />
            )}

            {goals.length === 0 ? (
              <EmptyState message="No goals yet. Create one above." />
            ) : (
              <div className="space-y-4">
                {goals.map((g) => (
                  <div key={g.id} className="card">
                    <div className="flex justify-between items-start gap-4">
                      <div>
                        <p className="font-medium text-text-primary">{g.description || g.goal_type}</p>
                        <p className="text-text-secondary text-sm mt-1">
                          {formatMoney(g.current_amount ?? 0)} / {formatMoney(g.target_amount ?? 0)} · {WEALTH_GOAL_TYPES.find((t) => t.value === g.goal_type)?.label ?? g.goal_type}
                        </p>
                        {g.suggested_reduction_per_month != null && (
                          <p className="text-text-muted text-xs">
                            Suggested: {formatMoney(g.suggested_reduction_per_month)}/mo
                          </p>
                        )}
                      </div>
                      <div className="flex gap-2 shrink-0">
                        <button type="button" className="btn-secondary text-sm" onClick={() => setEditing(g)}>
                          Edit
                        </button>
                        <ConfirmButton
                          label="Delete"
                          confirmLabel="Delete"
                          cancelLabel="Cancel"
                          onConfirm={async () => {
                            await deleteGoal(g.id);
                            await load();
                          }}
                          variant="danger"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </PageContent>
    </>
  );
}

function CreateGoalForm({ onCreate }: { onCreate: (p: Parameters<typeof createGoal>[0]) => Promise<void> }) {
  const [goal_type, setGoalType] = useState("monthly_investment_target");
  const [target_amount, setTargetAmount] = useState(1000);
  const [current_amount, setCurrentAmount] = useState(0);
  const [target_date, setTargetDate] = useState("");
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onCreate({
        goal_type,
        target_amount,
        current_amount,
        target_date: target_date || undefined,
        category: category.trim() || undefined,
        description: description.trim() || undefined,
      });
      setTargetAmount(1000);
      setCurrentAmount(0);
      setTargetDate("");
      setCategory("");
      setDescription("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card">
      <h3 className="font-medium text-text-primary mb-4">Create goal</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="flex flex-col gap-1">
          <span className="text-sm text-text-secondary">Goal type</span>
          <select className="input-field" value={goal_type} onChange={(e) => setGoalType(e.target.value)} aria-label="Goal type">
            {WEALTH_GOAL_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-text-secondary">Target amount</span>
          <input
            type="number"
            className="input-field"
            min={0}
            step={50}
            value={target_amount}
            onChange={(e) => setTargetAmount(Number(e.target.value))}
            aria-label="Target amount"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-text-secondary">Current amount</span>
          <input
            type="number"
            className="input-field"
            min={0}
            step={50}
            value={current_amount}
            onChange={(e) => setCurrentAmount(Number(e.target.value))}
            aria-label="Current amount"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-text-secondary">Target date (optional)</span>
          <input type="date" className="input-field" value={target_date} onChange={(e) => setTargetDate(e.target.value)} aria-label="Target date" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-text-secondary">Category (optional)</span>
          <input className="input-field" value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. food" aria-label="Category" />
        </label>
        <label className="flex flex-col gap-1 md:col-span-2">
          <span className="text-sm text-text-secondary">Description</span>
          <input className="input-field" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. 6 months expenses" aria-label="Description" />
        </label>
      </div>
      <button type="button" className="btn-primary mt-4" onClick={handleSubmit} disabled={submitting}>
        {submitting ? "Creating…" : "Create goal"}
      </button>
    </div>
  );
}

function GoalEditForm({
  goal,
  onSave,
  onCancel,
}: {
  goal: Goal;
  onSave: (p: Partial<Goal>) => Promise<void>;
  onCancel: () => void;
}) {
  const [goal_type, setGoalType] = useState(goal.goal_type || "monthly_investment_target");
  const [target_amount, setTargetAmount] = useState(goal.target_amount ?? 0);
  const [current_amount, setCurrentAmount] = useState(goal.current_amount ?? 0);
  const [target_date, setTargetDate] = useState(goal.target_date?.slice(0, 10) ?? "");
  const [category, setCategory] = useState(goal.category ?? "");
  const [description, setDescription] = useState(goal.description ?? "");
  const [status, setStatus] = useState(goal.status ?? "active");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onSave({
        goal_type,
        target_amount,
        current_amount,
        target_date: target_date || undefined,
        category: category.trim() || undefined,
        description: description.trim() || undefined,
        status,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card">
      <h3 className="font-medium text-text-primary mb-4">Edit goal</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="flex flex-col gap-1">
          <span className="text-sm text-text-secondary">Goal type</span>
          <select className="input-field" value={goal_type} onChange={(e) => setGoalType(e.target.value)} aria-label="Goal type">
            {WEALTH_GOAL_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-text-secondary">Target amount</span>
          <input type="number" className="input-field" min={0} value={target_amount} onChange={(e) => setTargetAmount(Number(e.target.value))} aria-label="Target amount" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-text-secondary">Current amount</span>
          <input type="number" className="input-field" min={0} value={current_amount} onChange={(e) => setCurrentAmount(Number(e.target.value))} aria-label="Current amount" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-text-secondary">Target date</span>
          <input type="date" className="input-field" value={target_date} onChange={(e) => setTargetDate(e.target.value)} aria-label="Target date" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-text-secondary">Category</span>
          <input className="input-field" value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-text-secondary">Status</span>
          <select className="input-field" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
            <option value="active">Active</option>
            <option value="completed">Completed</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 md:col-span-2">
          <span className="text-sm text-text-secondary">Description</span>
          <input className="input-field" value={description} onChange={(e) => setDescription(e.target.value)} aria-label="Description" />
        </label>
      </div>
      <div className="flex gap-2 mt-4">
        <button type="button" className="btn-primary" onClick={handleSubmit} disabled={submitting}>
          {submitting ? "Saving…" : "Save changes"}
        </button>
        <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}
