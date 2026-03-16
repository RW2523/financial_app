import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { MetricCard, PageContent } from "../components/ui";
import { getProjections, getSuggestions } from "../api/client";
import { formatMoney } from "../lib/utils";
import type { ProjectionScenario } from "../api/client";
import { currentYear, currentMonth, WealthMonthYearPicker, MiniSuggestionsBlock } from "../wealth";

const GROWTH_MODES = [
  { value: "no_growth", label: "No growth" },
  { value: "conservative", label: "Conservative" },
  { value: "moderate", label: "Moderate" },
  { value: "aggressive", label: "Aggressive" },
];

const SUGGESTIONS_TOP_N = 2;

export default function WealthProjections() {
  const [year, setYear] = useState(currentYear);
  const [month, setMonth] = useState(currentMonth);
  const [mode, setMode] = useState("moderate");
  const [data, setData] = useState<Awaited<ReturnType<typeof getProjections>> | null>(null);
  const [suggestions, setSuggestions] = useState<Awaited<ReturnType<typeof getSuggestions>>["suggestions"]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [proj, sugRes] = await Promise.all([
        getProjections(year, month, mode),
        getSuggestions(year, month),
      ]);
      setData(proj);
      setSuggestions(sugRes.suggestions?.slice(0, SUGGESTIONS_TOP_N) ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load projections.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [year, month, mode]);

  return (
    <>
      <PageHeader
        title="Projections"
        subtitle="Where you're headed: projected expenses, surplus, yearly invested, portfolio growth, and scenario comparison."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading projections…">
        {!loading && data && (
          <div className="space-y-8">
            <div className="flex gap-4 items-center flex-wrap">
              <WealthMonthYearPicker
                year={year}
                month={month}
                onYearChange={setYear}
                onMonthChange={setMonth}
              />
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                Portfolio growth
                <select className="input-field w-36" value={mode} onChange={(e) => setMode(e.target.value)} aria-label="Growth mode">
                  {GROWTH_MODES.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </label>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard label="Projected EOM expenses" value={formatMoney(data.projected_end_of_month_expenses)} />
              <MetricCard label="Projected monthly surplus" value={formatMoney(data.projected_monthly_surplus)} accent />
              <MetricCard label="Projected yearly invested" value={formatMoney(data.projected_yearly_invested)} />
              {data.current_portfolio_value != null && (
                <MetricCard label="Current portfolio value" value={formatMoney(data.current_portfolio_value)} />
              )}
            </div>

            <section className="card">
              <h3 className="font-medium text-text-primary mb-2">Portfolio projection</h3>
              <p className="text-sm text-text-secondary mb-4">
                Mode: {data.portfolio_growth_mode}
                {data.annual_return_assumption != null && ` · Annual return: ${(data.annual_return_assumption * 100).toFixed(1)}%`}
              </p>
              <div className="grid grid-cols-3 gap-4">
                <MetricCard label="6 months" value={formatMoney(data.portfolio_projection["6m"])} />
                <MetricCard label="1 year" value={formatMoney(data.portfolio_projection["1y"])} />
                <MetricCard label="3 years" value={formatMoney(data.portfolio_projection["3y"])} />
              </div>
            </section>

            {/* Scenario views */}
            {data.scenarios && data.scenarios.length > 0 && (
              <section className="card">
                <h3 className="font-medium text-text-primary mb-3">Scenario comparison</h3>
                <p className="text-sm text-text-secondary mb-4">Deterministic views based on current data and assumptions.</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {data.scenarios.map((sc: ProjectionScenario) => (
                    <div key={sc.id} className="p-4 rounded-lg bg-surface-muted border border-border">
                      <p className="font-medium text-text-primary">{sc.label}</p>
                      <p className="text-sm text-text-secondary mt-1">{sc.description}</p>
                      <div className="mt-3 flex flex-wrap gap-3 text-sm">
                        <span>Surplus: {formatMoney(sc.projected_monthly_surplus)}</span>
                        <span>Invested/yr: {formatMoney(sc.projected_yearly_invested)}</span>
                        <span>Portfolio 1y: {formatMoney(sc.portfolio_1y)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Contextual guidance */}
            <section className="card">
              <h3 className="font-medium text-text-primary mb-2">Projected guidance</h3>
              <ul className="text-sm text-text-secondary space-y-1">
                <li>• Current pace: your projected surplus and portfolio path assume today’s income, expenses, and investing level.</li>
                <li>• Lowering expenses increases investable surplus and can accelerate portfolio growth if you invest the difference.</li>
                <li>• Increasing monthly investing raises projected portfolio value over time (see scenario comparison).</li>
              </ul>
            </section>

            <MiniSuggestionsBlock title="Suggestions" suggestions={suggestions} viewAllLabel="View all" compact />
          </div>
        )}
      </PageContent>
    </>
  );
}
