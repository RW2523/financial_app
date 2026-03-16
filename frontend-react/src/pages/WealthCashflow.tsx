import { useState, useEffect } from "react";
import PageHeader from "../components/PageHeader";
import { MetricCard, PageContent } from "../components/ui";
import { getCashflowSummary, getSuggestions } from "../api/client";
import { formatMoney } from "../lib/utils";
import {
  currentYear,
  currentMonth,
  SECTION_HEADING_CLASS,
  CARD_HEADING_CLASS,
  WealthMonthYearPicker,
  MiniSuggestionsBlock,
  formatDelta,
} from "../wealth";

const SUGGESTIONS_TOP_N = 2;

export default function WealthCashflow() {
  const [year, setYear] = useState(currentYear);
  const [month, setMonth] = useState(currentMonth);
  const [data, setData] = useState<Awaited<ReturnType<typeof getCashflowSummary>> | null>(null);
  const [suggestions, setSuggestions] = useState<Awaited<ReturnType<typeof getSuggestions>>["suggestions"]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [summary, sugRes] = await Promise.all([
        getCashflowSummary(year, month),
        getSuggestions(year, month),
      ]);
      setData(summary);
      setSuggestions(sugRes.suggestions?.slice(0, SUGGESTIONS_TOP_N) ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load cashflow.");
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
        title="Cashflow"
        subtitle="The money truth: income → expenses → investing → remaining cash. Ratios, investable surplus, and month-over-month."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading cashflow…">
        {!loading && data && (
          <div className="space-y-8">
            <WealthMonthYearPicker
              year={year}
              month={month}
              onYearChange={setYear}
              onMonthChange={setMonth}
            />

            <section>
              <h2 className={SECTION_HEADING_CLASS}>Monthly flow</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                <MetricCard label="Total income" value={formatMoney(data.total_income)} accent />
                <MetricCard label="Total expenses" value={formatMoney(data.total_expenses)} />
                <MetricCard label="Total invested" value={formatMoney(data.total_invested)} />
                <MetricCard label="Net savings" value={formatMoney(data.net_savings)} />
                <MetricCard label="Free cash remaining" value={formatMoney(data.free_cash)} />
              </div>
            </section>

            <section className="card">
              <h2 className={CARD_HEADING_CLASS}>Flow: Income → Expenses → Investments → Remaining</h2>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="px-3 py-1.5 rounded bg-green-500/20 text-green-300">Income {formatMoney(data.total_income)}</span>
                <span className="text-text-muted">−</span>
                <span className="px-3 py-1.5 rounded bg-amber-500/20 text-amber-300">Expenses {formatMoney(data.total_expenses)}</span>
                <span className="text-text-muted">=</span>
                <span className="px-3 py-1.5 rounded bg-surface-muted text-text-primary">Net savings {formatMoney(data.net_savings)}</span>
                <span className="text-text-muted">−</span>
                <span className="px-3 py-1.5 rounded bg-accent/20 text-accent">Invested {formatMoney(data.total_invested)}</span>
                <span className="text-text-muted">=</span>
                <span className="px-3 py-1.5 rounded bg-blue-500/20 text-blue-300 font-medium">Free cash {formatMoney(data.free_cash)}</span>
              </div>
            </section>

            <section>
              <h2 className={SECTION_HEADING_CLASS}>Ratios</h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <MetricCard label="Expense ratio" value={`${data.expense_ratio.toFixed(1)}%`} sub="of income" />
                <MetricCard label="Savings ratio" value={`${data.savings_ratio.toFixed(1)}%`} sub="of income" />
                <MetricCard label="Investment ratio" value={`${data.investment_ratio.toFixed(1)}%`} sub="of income" />
              </div>
            </section>

            {(data.fixed_expenses != null || data.variable_expenses != null) && ((data.fixed_expenses ?? 0) > 0 || (data.variable_expenses ?? 0) > 0) && (
              <section className="card">
                <h2 className={CARD_HEADING_CLASS}>Fixed vs variable spend</h2>
                <div className="flex flex-wrap gap-4">
                  <span className="text-text-secondary">Fixed obligations: <strong className="text-text-primary">{formatMoney(data.fixed_expenses != null ? data.fixed_expenses : 0)}</strong></span>
                  <span className="text-text-secondary">Variable spend: <strong className="text-text-primary">{formatMoney(data.variable_expenses != null ? data.variable_expenses : 0)}</strong></span>
                </div>
              </section>
            )}

            {(data.safe_investable_surplus != null || data.aggressive_investable_surplus != null) && (
              <section className="card">
                <h2 className={CARD_HEADING_CLASS}>Investable surplus</h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <MetricCard label="Safe investable" value={formatMoney(data.safe_investable_surplus ?? 0)} sub="~50% of free cash" />
                  <MetricCard label="Aggressive investable" value={formatMoney(data.aggressive_investable_surplus ?? 0)} sub="~80% of free cash" />
                  <MetricCard label="Remaining buffer" value={formatMoney(data.remaining_buffer ?? 0)} />
                </div>
              </section>
            )}

            {(data.mom_delta_income != null || data.mom_delta_expenses != null) && (
              <section className="card">
                <h2 className={CARD_HEADING_CLASS}>Month-over-month change</h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-text-muted">Income</p>
                    <p className={data.mom_delta_income! >= 0 ? "text-green-400" : "text-red-400"}>
                      {formatDelta(data.mom_delta_income)}
                    </p>
                  </div>
                  <div>
                    <p className="text-text-muted">Expenses</p>
                    <p className={data.mom_delta_expenses! <= 0 ? "text-green-400" : "text-amber-400"}>
                      {formatDelta(data.mom_delta_expenses)}
                    </p>
                  </div>
                  <div>
                    <p className="text-text-muted">Invested</p>
                    <p className="text-text-primary">{formatDelta(data.mom_delta_invested)}</p>
                  </div>
                  <div>
                    <p className="text-text-muted">Savings</p>
                    <p className={data.mom_delta_savings != null && data.mom_delta_savings >= 0 ? "text-green-400" : "text-amber-400"}>
                      {formatDelta(data.mom_delta_savings)}
                    </p>
                  </div>
                </div>
              </section>
            )}

            <MiniSuggestionsBlock
              title="Suggestions for this month"
              suggestions={suggestions}
              viewAllLabel="View all suggestions"
            />
          </div>
        )}
      </PageContent>
    </>
  );
}
