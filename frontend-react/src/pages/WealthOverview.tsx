import { useState, useEffect } from "react";
import { NavLink } from "react-router-dom";
import { ArrowRight, TrendingUp, Wallet, PiggyBank, BarChart3, Target, Lightbulb, AlertTriangle, CheckCircle } from "lucide-react";
import PageHeader from "../components/PageHeader";
import { MetricCard, PageContent } from "../components/ui";
import { getWealthOverview } from "../api/client";
import { formatMoney } from "../lib/utils";
import { WEALTH_ROUTES, SECTION_HEADING_CLASS, CARD_HEADING_CLASS } from "../wealth";

const FLOW_STEPS = [
  { to: WEALTH_ROUTES.salary, label: "Income", icon: Wallet, description: "Add salary and other income" },
  { to: WEALTH_ROUTES.investments, label: "Investments", icon: TrendingUp, description: "Record BUY / SELL / DIVIDEND" },
  { to: WEALTH_ROUTES.portfolio, label: "Portfolio", icon: BarChart3, description: "View holdings and value" },
  { to: WEALTH_ROUTES.cashflow, label: "Cashflow", icon: PiggyBank, description: "Income vs expenses vs invested" },
  { to: WEALTH_ROUTES.projections, label: "Projections", icon: Target, description: "Surplus and portfolio growth" },
  { to: WEALTH_ROUTES.manager, label: "Portfolio Intelligence", icon: BarChart3, description: "Allocation and stocks for you" },
  { to: WEALTH_ROUTES.suggestions, label: "Suggestions", icon: Lightbulb, description: "Grounded tips from your data" },
];

export default function WealthOverview() {
  const [overview, setOverview] = useState<Awaited<ReturnType<typeof getWealthOverview>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getWealthOverview()
      .then(setOverview)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load."))
      .finally(() => setLoading(false));
  }, []);

  const strip = overview?.summary_strip;
  const score = overview?.wealth_score ?? strip?.wealth_score ?? null;

  return (
    <>
      <PageHeader
        title="Wealth Hub"
        subtitle="Your financial command center. Income, investments, portfolio, and guidance in one place."
      />
      <PageContent loading={loading} error={error} loadingMessage="Loading…">
        {!loading && overview && (
          <div className="space-y-6 max-w-6xl">
            {/* Top summary strip */}
            <section>
              <h2 className={SECTION_HEADING_CLASS}>This month</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                <MetricCard label="Net income" value={formatMoney(strip?.net_income_this_month ?? 0)} />
                <MetricCard label="Expenses" value={formatMoney(strip?.total_expenses_this_month ?? 0)} />
                <MetricCard label="Free cash" value={formatMoney(strip?.free_cash_this_month ?? 0)} />
                <MetricCard label="Invested" value={formatMoney(strip?.invested_this_month ?? 0)} />
                <MetricCard label="Portfolio" value={formatMoney(strip?.portfolio_value ?? 0)} accent />
                {strip?.net_worth != null && (
                  <MetricCard label="Net worth" value={formatMoney(strip.net_worth)} />
                )}
                {score != null && (
                  <MetricCard
                    label="Wealth Score"
                    value={`${score}/100`}
                    sub={score >= 60 ? "Good" : score >= 40 ? "Moderate" : "Needs attention"}
                  />
                )}
              </div>
            </section>

            {/* Priority alerts */}
            {overview.priority_alerts && overview.priority_alerts.length > 0 && (
              <section className="card">
                <h2 className={`${CARD_HEADING_CLASS} flex items-center gap-2`}>
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                  Priority alerts
                </h2>
                <ul className="space-y-2">
                  {overview.priority_alerts.slice(0, 3).map((a) => (
                    <li key={a.id}>
                      {a.destination ? (
                        <NavLink
                          to={a.destination}
                          className="block p-3 rounded-lg bg-surface-muted hover:bg-surface-elevated border border-border"
                        >
                          <span className="font-medium text-text-primary">{a.title}</span>
                          <p className="text-sm text-text-secondary mt-1">{a.message}</p>
                        </NavLink>
                      ) : (
                        <div className="p-3 rounded-lg bg-surface-muted border border-border">
                          <span className="font-medium text-text-primary">{a.title}</span>
                          <p className="text-sm text-text-secondary mt-1">{a.message}</p>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* What should I do next? */}
            {overview.next_actions && overview.next_actions.length > 0 && (
              <section className="card">
                <h2 className={`${CARD_HEADING_CLASS} flex items-center gap-2`}>
                  <CheckCircle className="w-5 h-5 text-accent" />
                  What should I do next?
                </h2>
                <ul className="space-y-2">
                  {overview.next_actions.map((action, i) => (
                    <li key={i}>
                      <NavLink
                        to={action.destination}
                        className="flex items-center gap-3 p-3 rounded-lg bg-surface-muted hover:bg-surface-elevated border border-border group"
                      >
                        <span className="font-medium text-text-primary group-hover:text-accent">{action.action}</span>
                        <span className="text-sm text-text-secondary flex-1">{action.reason}</span>
                        <ArrowRight className="w-4 h-4 text-text-muted shrink-0" />
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* Wealth flow */}
            <section className="card">
              <h2 className={CARD_HEADING_CLASS}>Your wealth flow</h2>
              <p className="text-sm text-text-secondary mb-4">
                Add income, record investments, then check portfolio, cashflow, and projections. Use Portfolio Intelligence and Suggestions for recommendations.
              </p>
              <ul className="space-y-3">
                {FLOW_STEPS.map(({ to, label, icon: Icon, description }) => (
                  <li key={to}>
                    <NavLink
                      to={to}
                      className="flex items-center gap-4 p-3 rounded-lg bg-surface-muted hover:bg-surface-elevated border border-border transition-colors group"
                    >
                      <span className="flex items-center justify-center w-10 h-10 rounded-lg bg-accent/20 text-accent shrink-0">
                        <Icon className="w-5 h-5" />
                      </span>
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-text-primary group-hover:text-accent">{label}</span>
                        <p className="text-sm text-text-secondary">{description}</p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-text-muted shrink-0" />
                    </NavLink>
                  </li>
                ))}
              </ul>
            </section>

            {/* Goal progress preview */}
            <section className="card">
              <h2 className={CARD_HEADING_CLASS}>Goal progress</h2>
              {overview.has_goals && overview.goals_preview && overview.goals_preview.length > 0 ? (
                <ul className="space-y-3">
                  {overview.goals_preview.map((g) => (
                    <li key={g.id} className="flex items-center justify-between gap-4">
                      <span className="text-text-primary">{g.description}</span>
                      <span className="text-text-secondary text-sm">
                        {formatMoney(g.current)} / {formatMoney(g.target)} ({Math.round(g.progress_pct)}%)
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-text-secondary text-sm mb-3">No goals yet. Set targets to track progress.</p>
              )}
              <NavLink to={WEALTH_ROUTES.goals} className="text-accent hover:underline text-sm font-medium">
                {overview.has_goals ? "View all goals" : "Create a goal"}
              </NavLink>
            </section>

            {/* Net worth preview */}
            <section className="card">
              <h2 className={CARD_HEADING_CLASS}>Net worth</h2>
              {overview.net_worth_preview ? (
                <div className="space-y-2">
                  <p className="text-text-primary font-medium">{formatMoney(overview.net_worth_preview.net_worth)}</p>
                  <p className="text-sm text-text-secondary">
                    Assets {formatMoney(overview.net_worth_preview.total_assets)} · Liabilities {formatMoney(overview.net_worth_preview.total_liabilities)}
                  </p>
                  {overview.net_worth_preview.delta_vs_previous_month != null && (
                    <p className="text-sm text-text-muted">
                      vs last month: {overview.net_worth_preview.delta_vs_previous_month >= 0 ? "+" : ""}
                      {formatMoney(overview.net_worth_preview.delta_vs_previous_month)}
                    </p>
                  )}
                  <NavLink to={WEALTH_ROUTES.netWorth} className="text-accent hover:underline text-sm font-medium">
                    View Net Worth
                  </NavLink>
                </div>
              ) : (
                <>
                  <p className="text-text-secondary text-sm mb-2">Track assets and liabilities in one place.</p>
                  <NavLink to={WEALTH_ROUTES.netWorth} className="text-accent hover:underline text-sm font-medium">
                    Set up Net Worth
                  </NavLink>
                </>
              )}
            </section>
          </div>
        )}
      </PageContent>
    </>
  );
}
