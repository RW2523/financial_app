import { useState } from "react";
import PageHeader from "../components/PageHeader";
import { ErrorMessage } from "../components/ui";
import { checkAffordability } from "../api/client";

export default function Affordability() {
  const [amount, setAmount] = useState(50);
  const [category, setCategory] = useState("food");
  const [merchant, setMerchant] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Awaited<ReturnType<typeof checkAffordability>> | null>(null);

  const handleCheck = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await checkAffordability({
        amount,
        category: category.trim() || undefined,
        merchant: merchant.trim() || undefined,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Check failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Can I afford this?"
        subtitle="Check whether a purchase fits your budget, limits, projected spend, and goals."
      />
      <div className="p-6 max-w-2xl">
        <div className="card space-y-4">
          <label className="block">
            <span className="text-sm text-text-secondary">Amount</span>
            <input
              type="number"
              className="input-field mt-1"
              min={0}
              step={1}
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              aria-label="Amount"
            />
          </label>
          <label className="block">
            <span className="text-sm text-text-secondary">Category</span>
            <input
              className="input-field mt-1"
              placeholder="e.g. food, transport"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              aria-label="Category"
            />
          </label>
          <label className="block">
            <span className="text-sm text-text-secondary">Merchant (optional)</span>
            <input
              className="input-field mt-1"
              placeholder="e.g. Starbucks"
              value={merchant}
              onChange={(e) => setMerchant(e.target.value)}
              aria-label="Merchant"
            />
          </label>
          <button
            type="button"
            className="btn-primary"
            onClick={handleCheck}
            disabled={loading}
          >
            {loading ? "Checking…" : "Check affordability"}
          </button>
        </div>

        {error && <div className="mt-4"><ErrorMessage message={error} /></div>}

        {result && (
          <div className="mt-6 space-y-4">
            <div className={`card ${result.can_afford ? "border-accent/50" : "border-red-500/30"}`}>
              {result.can_afford ? (
                <p className="text-accent font-medium">Yes — you can afford this purchase.</p>
              ) : (
                <p className="text-red-400 font-medium">This purchase would exceed your limits or conflict with goals.</p>
              )}
              <p className="text-text-secondary text-sm mt-2"><strong>Recommendation:</strong> {result.recommendation_text}</p>
              {result.reasons?.length > 0 && (
                <ul className="mt-2 text-text-secondary text-sm list-disc list-inside">
                  {result.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
            </div>
            {result.projected_impact != null && (
              <details className="card">
                <summary className="cursor-pointer font-medium text-text-secondary">Projected impact</summary>
                <pre className="mt-2 text-xs text-text-secondary overflow-x-auto">{JSON.stringify(result.projected_impact, null, 2)}</pre>
              </details>
            )}
            {result.budget_impact != null && (
              <details className="card">
                <summary className="cursor-pointer font-medium text-text-secondary">Budget impact</summary>
                <pre className="mt-2 text-xs text-text-secondary overflow-x-auto">{JSON.stringify(result.budget_impact, null, 2)}</pre>
              </details>
            )}
            {result.goal_impact != null && (
              <details className="card">
                <summary className="cursor-pointer font-medium text-text-secondary">Goal impact</summary>
                <pre className="mt-2 text-xs text-text-secondary overflow-x-auto">{JSON.stringify(result.goal_impact, null, 2)}</pre>
              </details>
            )}
          </div>
        )}
      </div>
    </>
  );
}
