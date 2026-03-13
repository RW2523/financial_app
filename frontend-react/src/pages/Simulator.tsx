import { useState } from "react";
import PageHeader from "../components/PageHeader";
import { ErrorMessage } from "../components/ui";
import { simulate, type SimulateAdjustment } from "../api/client";
import { formatMoney } from "../lib/utils";

function buildAdjustments(
  opts: {
    reducePct: boolean; reduceCat: string; reduceVal: number;
    removeRec: boolean; removeMerchant: string;
    addOne: boolean; addCat: string; addAmt: number;
    changeCap: boolean; capCat: string; capAmt: number;
    saveWeekly: boolean; saveVal: number;
  }
): SimulateAdjustment[] {
  const list: SimulateAdjustment[] = [];
  if (opts.reducePct) list.push({ type: "reduce_category_percent", category: opts.reduceCat.trim() || "other", value: opts.reduceVal });
  if (opts.removeRec && opts.removeMerchant.trim()) list.push({ type: "remove_recurring_merchant", merchant: opts.removeMerchant.trim() });
  if (opts.addOne) list.push({ type: "add_one_time_expense", category: (opts.addCat || "other").trim(), amount: opts.addAmt });
  if (opts.changeCap) list.push({ type: "change_category_cap", category: (opts.capCat || "other").trim(), amount: opts.capAmt });
  if (opts.saveWeekly) list.push({ type: "save_fixed_per_week", value: opts.saveVal });
  return list;
}

export default function Simulator() {
  const [reducePct, setReducePct] = useState(false);
  const [reduceCat, setReduceCat] = useState("transport");
  const [reduceVal, setReduceVal] = useState(20);
  const [removeRec, setRemoveRec] = useState(false);
  const [removeMerchant, setRemoveMerchant] = useState("");
  const [addOne, setAddOne] = useState(false);
  const [addCat, setAddCat] = useState("travel");
  const [addAmt, setAddAmt] = useState(300);
  const [changeCap, setChangeCap] = useState(false);
  const [capCat, setCapCat] = useState("food");
  const [capAmt, setCapAmt] = useState(400);
  const [saveWeekly, setSaveWeekly] = useState(false);
  const [saveVal, setSaveVal] = useState(50);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Awaited<ReturnType<typeof simulate>> | null>(null);

  const handleRun = async () => {
    const adj = buildAdjustments({
      reducePct, reduceCat, reduceVal, removeRec, removeMerchant,
      addOne, addCat, addAmt, changeCap, capCat, capAmt, saveWeekly, saveVal,
    });
    if (adj.length === 0) {
      setError("Add at least one adjustment above, then run again.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await simulate(adj);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed.");
    } finally {
      setLoading(false);
    }
  };

  const base = result?.baseline_summary;
  const sim = result?.simulated_summary;
  const delta = result?.delta_summary;

  return (
    <>
      <PageHeader
        title="Scenario simulator"
        subtitle="Test hypothetical changes without affecting real data. See how adjustments would impact projected spending, limits, and goals."
      />
      <div className="p-6 max-w-4xl">
        <div className="card">
          <h3 className="font-medium text-text-primary mb-4">Adjustments</h3>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={reducePct} onChange={(e) => setReducePct(e.target.checked)} />
                <span className="text-text-primary">Reduce category spend by %</span>
              </label>
              {reducePct && (
                <div className="flex gap-3 pl-6">
                  <input className="input-field flex-1" placeholder="Category" value={reduceCat} onChange={(e) => setReduceCat(e.target.value)} aria-label="Category" />
                  <input type="number" className="input-field w-24" min={0} max={100} value={reduceVal} onChange={(e) => setReduceVal(Number(e.target.value))} aria-label="Percent" />
                </div>
              )}
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={removeRec} onChange={(e) => setRemoveRec(e.target.checked)} />
                <span className="text-text-primary">Remove recurring subscription</span>
              </label>
              {removeRec && (
                <input className="input-field ml-6" placeholder="Merchant name" value={removeMerchant} onChange={(e) => setRemoveMerchant(e.target.value)} aria-label="Merchant" />
              )}
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={addOne} onChange={(e) => setAddOne(e.target.checked)} />
                <span className="text-text-primary">Add one-time expense</span>
              </label>
              {addOne && (
                <div className="flex gap-3 pl-6">
                  <input className="input-field flex-1" placeholder="Category" value={addCat} onChange={(e) => setAddCat(e.target.value)} aria-label="Category" />
                  <input type="number" className="input-field w-28" min={0} value={addAmt} onChange={(e) => setAddAmt(Number(e.target.value))} aria-label="Amount" />
                </div>
              )}
            </div>
            <div className="space-y-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={changeCap} onChange={(e) => setChangeCap(e.target.checked)} />
                <span className="text-text-primary">Change category cap</span>
              </label>
              {changeCap && (
                <div className="flex gap-3 pl-6">
                  <input className="input-field flex-1" placeholder="Category" value={capCat} onChange={(e) => setCapCat(e.target.value)} aria-label="Category" />
                  <input type="number" className="input-field w-28" min={0} value={capAmt} onChange={(e) => setCapAmt(Number(e.target.value))} aria-label="New cap" />
                </div>
              )}
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={saveWeekly} onChange={(e) => setSaveWeekly(e.target.checked)} />
                <span className="text-text-primary">Save fixed amount per week</span>
              </label>
              {saveWeekly && (
                <input type="number" className="input-field w-32 ml-6" min={0} value={saveVal} onChange={(e) => setSaveVal(Number(e.target.value))} aria-label="Amount per week" />
              )}
            </div>
          </div>
          <button type="button" className="btn-primary mt-4" onClick={handleRun} disabled={loading}>
            {loading ? "Running…" : "Run simulation"}
          </button>
        </div>

        {error && <div className="mt-4"><ErrorMessage message={error} /></div>}

        {result && (
          <div className="mt-6 space-y-6">
            <div className="grid grid-cols-3 gap-4">
              <div className="card">
                <p className="text-text-secondary text-sm">Baseline projected</p>
                <p className="text-xl font-semibold text-text-primary">{base?.projected_total != null ? formatMoney(base.projected_total) : "—"}</p>
                <p className="text-text-muted text-xs">current month</p>
              </div>
              <div className="card">
                <p className="text-text-secondary text-sm">Simulated projected</p>
                <p className="text-xl font-semibold text-text-primary">{sim?.projected_total != null ? formatMoney(sim.projected_total) : "—"}</p>
                <p className="text-text-muted text-xs">after adjustments</p>
              </div>
              <div className="card">
                <p className="text-text-secondary text-sm">Delta</p>
                <p className={`text-xl font-semibold ${(delta?.total_change ?? 0) < 0 ? "text-accent" : "text-amber-400"}`}>
                  {delta?.total_change != null ? formatMoney(delta.total_change) : "—"}
                </p>
                <p className="text-text-muted text-xs">{(delta?.total_change ?? 0) < 0 ? "savings" : "increase"}</p>
              </div>
            </div>
            {(result.projected_limit_changes?.length ?? 0) > 0 && (
              <details className="card">
                <summary className="cursor-pointer font-medium text-text-secondary">Limit impact</summary>
                <pre className="mt-2 text-xs text-text-secondary overflow-x-auto">{JSON.stringify(result.projected_limit_changes, null, 2)}</pre>
              </details>
            )}
            {(result.goal_impact?.length ?? 0) > 0 && (
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
