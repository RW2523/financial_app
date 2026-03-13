import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { PageContent } from "../components/ui";
import {
  getLimitsStatus,
  setLimit,
  deleteLimit,
  getForecastMonth,
  getForecastCategories,
  getPredictiveAlerts,
} from "../api/client";
import { formatMoney } from "../lib/utils";

const LIMIT_CATEGORIES = ["total", "food", "transport", "shopping", "entertainment", "utilities", "healthcare", "other"];

export default function Limits() {
  const [status, setStatus] = useState<Awaited<ReturnType<typeof getLimitsStatus>> | null>(null);
  const [forecast, setForecast] = useState<Awaited<ReturnType<typeof getForecastMonth>> | null>(null);
  const [forecastCat, setForecastCat] = useState<Record<string, number> | null>(null);
  const [alerts, setAlerts] = useState<{ message: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState("food");
  const [amount, setAmount] = useState(500);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, fc, pred] = await Promise.all([
        getLimitsStatus(),
        getForecastMonth().catch(() => null),
        getPredictiveAlerts().catch(() => ({ alerts: [] })),
      ]);
      setStatus(s);
      setForecast(fc);
      setAlerts(pred?.alerts ?? []);
      const cat = await getForecastCategories(s.year, s.month).catch(() => null);
      setForecastCat(typeof cat === "object" && cat !== null && !Array.isArray(cat) ? cat : null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load limits.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSetLimit = async () => {
    try {
      await setLimit(category, amount);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to set limit.");
    }
  };

  const handleDelete = async (cat: string) => {
    try {
      await deleteLimit(cat);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete limit.");
    }
  };

  return (
    <>
      <PageHeader
        title="Limits & alerts"
        subtitle="Set monthly limits per category. Get alerts when you are near (80%+) or over."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading limits…">
        {!loading && status && (
          <div className="space-y-6">
            <div className="card">
              <h3 className="font-medium text-text-primary mb-3">Set a limit</h3>
              <div className="flex flex-wrap gap-4 items-end">
                <label className="flex flex-col gap-1">
                  <span className="text-sm text-text-secondary">Category</span>
                  <select
                    className="input-field w-40"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    aria-label="Category"
                  >
                    {LIMIT_CATEGORIES.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-sm text-text-secondary">Amount ($)</span>
                  <input
                    type="number"
                    className="input-field w-32"
                    min={0}
                    step={50}
                    value={amount}
                    onChange={(e) => setAmount(Number(e.target.value))}
                    aria-label="Amount"
                  />
                </label>
                <button type="button" className="btn-primary" onClick={handleSetLimit}>
                  Save limit
                </button>
              </div>
            </div>

            <div className="card">
              <h3 className="font-medium text-text-primary mb-4">Current limits & this month</h3>
              {!status.limits?.length ? (
                <p className="text-text-secondary text-sm">No limits set. Set one above to get alerts.</p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border text-left">
                          <th className="py-2 pr-4 text-text-secondary">Category</th>
                          <th className="py-2 pr-4 text-text-secondary">Limit</th>
                          <th className="py-2 pr-4 text-text-secondary">Spent</th>
                          <th className="py-2 pr-4 text-text-secondary">%</th>
                          <th className="py-2 text-text-secondary"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {status.limits.map((lim) => {
                          const spent = status.spending?.[lim.category] ?? 0;
                          const pct = lim.amount ? (spent / lim.amount) * 100 : 0;
                          return (
                            <tr key={lim.category} className="border-b border-border/50">
                              <td className="py-2 pr-4 font-medium">{lim.category}</td>
                              <td className="py-2 pr-4">{formatMoney(lim.amount)}</td>
                              <td className="py-2 pr-4">{formatMoney(spent)}</td>
                              <td className="py-2 pr-4">{pct.toFixed(1)}%</td>
                              <td className="py-2">
                                <button
                                  type="button"
                                  className="text-red-400 hover:underline text-sm"
                                  onClick={() => handleDelete(lim.category)}
                                >
                                  Delete
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  {status.alerts?.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-border">
                      <h4 className="font-medium text-text-primary mb-2">Active alerts</h4>
                      <ul className="space-y-1 text-sm">
                        {status.alerts.map((a, i) => (
                          <li
                            key={i}
                            className={a.alert_type === "over" ? "text-red-400" : "text-amber-400"}
                          >
                            {a.category}: {formatMoney(a.spent)} / {formatMoney(a.limit)} ({a.percent}%) — {a.alert_type}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </div>

            {forecast && (
              <div className="card">
                <h3 className="font-medium text-text-primary mb-2">Forecast</h3>
                <p className="text-text-secondary text-sm">
                  Projected month-end total: {formatMoney(forecast.projected_total ?? 0)} ({forecast.days_elapsed ?? 0}/{forecast.days_in_month ?? 30} days)
                </p>
                {forecastCat && Object.keys(forecastCat).length > 0 && (
                  <div className="mt-3 text-sm">
                    <p className="text-text-secondary mb-2">By category:</p>
                    <ul className="space-y-1">
                      {Object.entries(forecastCat).map(([k, v]) => (
                        <li key={k} className="flex justify-between">
                          <span className="text-text-secondary">{k}</span>
                          <span className="text-text-primary">{formatMoney(v)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {alerts.length > 0 && (
                  <ul className="mt-3 space-y-1 text-amber-400 text-sm">
                    {alerts.map((a, i) => (
                      <li key={i}>{a.message}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}
      </PageContent>
    </>
  );
}
